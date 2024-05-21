from flask import Flask, request, render_template, redirect, url_for, jsonify
import pyodbc
import random
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)
app = Flask(__name__, static_folder='static')
conn_str = 'Driver={SQL Server};Server=TS-0002\\SQLEXPRESS;Database=ProjektPrzesylka;Trusted_Connection=yes;'

conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

def szukaj_przesylki(numer_przesylki):
    try:
        query = "SELECT NumerPrzesylki, Od, Do, GdzieNadana, GdzieDoOdbioru, KlasaPrzesylki, StanPrzesylki FROM Przesylki WHERE NumerPrzesylki = ?"
        cursor.execute(query, (numer_przesylki,))
        przesylki = cursor.fetchall()

        for przesylka in przesylki:
            if 'F' in str(przesylka[0]):
                przesylka[0] += 'F'
            else:
                przesylka[0] += 'P'
            
        return przesylki
    except Exception as e:
        print(f"Błąd podczas wyszukiwania przesyłki: {e}")
        return []

def generuj_unikalny_numer(typ):
    while True:
        numer = f"{random.randint(10000, 99999)}{typ}"
        if not numer_juz_istnieje(numer):
            return numer

def numer_juz_istnieje(numer):
    cursor.execute("SELECT COUNT(*) FROM Przesylki WHERE NumerPrzesylki = ?", (numer,))
    count = cursor.fetchone()[0]
    return count > 0

def generuj_kod_kreskowy(numer_przesylki):
    barcode_class = barcode.get_barcode_class('code128')
    my_barcode = barcode_class(numer_przesylki, writer=ImageWriter())
    # Zapisz kod kreskowy w katalogu static, dostępny publicznie
    filename = my_barcode.save(f"static/{numer_przesylki}")
    return filename

@app.route('/')
def index():
    cursor.execute("SELECT IdFirmy, NazwaFirmy FROM Firmy")
    firmy = cursor.fetchall()
    return render_template('index.html', firmy=firmy)


@app.route('/pokaz_kod_kreskowy/<filename>')
def pokaz_kod_kreskowy(filename):
    return render_template('pokaz_kod_kreskowy.html', filename=filename)


@app.route('/dodaj_przesylke', methods=['GET', 'POST'])
def dodaj_przesylke():
    if request.method == 'POST':
        od = request.form.get('od')
        do = request.form.get('do')
        gdzie_nadana = request.form.get('gdzie_nadana')
        gdzie_do_odbioru = request.form.get('gdzie_do_odbioru')
        klasa = request.form.get('klasa')
        is_company = request.form.get('is_company') == 'on'  # Sprawdź, czy checkbox 'is_company' został zaznaczony

        if is_company:
            nazwa_firmy = request.form.get('nazwa_firmy')
            nip = request.form.get('nip')
            numer_przesylki = generuj_unikalny_numer('F')
            try:
                cursor.execute("INSERT INTO PrzesylkiFirmowe (NumerPrzesylki, Od, Do, GdzieNadana, GdzieDoOdbioru, KlasaPrzesylki, IdFirmy) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (numer_przesylki, od, do, gdzie_nadana, gdzie_do_odbioru, klasa, None))  # Tutaj może być potrzebny ID firmy zamiast None
                conn.commit()
                # Generowanie kodu kreskowego
                filename = generuj_kod_kreskowy(numer_przesylki)
                return redirect(url_for('pokaz_kod_kreskowy', filename=f"{numer_przesylki}.png"))
            except Exception as e:
                return f'Błąd przy dodawaniu przesyłki firmowej: {str(e)}'
        else:
            numer_przesylki = generuj_unikalny_numer('P')
            try:
                cursor.execute("INSERT INTO PrzesylkiOsobiste (NumerPrzesylki, Od, Do, GdzieNadana, GdzieDoOdbioru, KlasaPrzesylki) VALUES (?, ?, ?, ?, ?, ?)",
                               (numer_przesylki, od, do, gdzie_nadana, gdzie_do_odbioru, klasa))
                conn.commit()
                # Generowanie kodu kreskowego
                filename = generuj_kod_kreskowy(numer_przesylki)
                return redirect(url_for('pokaz_kod_kreskowy', filename=f"{numer_przesylki}.png"))
            except Exception as e:
                return f'Błąd przy dodawaniu przesyłki prywatnej: {str(e)}'

    else:
        return render_template('dodaj_przesylke.html')

@app.route('/szukaj_kodu_kreskowego', methods=['GET', 'POST'])
def szukaj_kodu_kreskowego():
    if request.method == 'POST':
        numer_przesylki = request.form['numer_przesylki']
        try:
            cursor.execute("SELECT * FROM Przesylki WHERE NumerPrzesylki = ?", (numer_przesylki,))
            przesylka = cursor.fetchone()
            if przesylka:
                return redirect(url_for('pokaz_kod_kreskowy', filename=f"{numer_przesylki}.png"))
            else:
                return 'Nie znaleziono przesyłki o podanym numerze.', 404
        except Exception as e:
            return f"Błąd serwera: {str(e)}", 500
    else:
        return render_template('szukaj_kodu_kreskowego.html')


@app.route('/zarzadzanie_przesylkami', methods=['GET', 'POST'])
def zarzadzanie_przesylkami():
    if request.method == 'POST':
        if 'status' in request.form:
            numer = request.form['numer']
            nowy_status = request.form['status']
            try:
                cursor.execute("EXEC UpdateShipmentStatus @NumerPrzesylki = ?, @NowyStatus = ?", (numer, nowy_status))
                conn.commit()
            except Exception as e:
                return f'Błąd zmiany statusu: {str(e)}'

        elif 'numer_od' in request.form and 'numer_do' in request.form:
            numer_od = request.form['numer_od']
            numer_do = request.form['numer_do']
            try:
                cursor.execute("EXEC RemoveShipmentRange @NumerOd = ?, @NumerDo = ?", (numer_od, numer_do))
                conn.commit()
            except Exception as e:
                return f'Błąd usuwania zakresu przesyłek: {str(e)}'
        
        return redirect(url_for('zarzadzanie_przesylkami'))
        
    return render_template('zarzadzanie_przesylkami.html')




@app.route('/wynik')
def wynik():
    numer = request.args.get('numer')
    if not numer:
        return "Numer przesyłki jest wymagany.", 400
    try:
        cursor.execute("SELECT * FROM Przesylki WHERE NumerPrzesylki = ?", (numer,))
        przesylka = cursor.fetchone()
        if przesylka:
            return render_template('wynik.html', przesylka=przesylka)
        else:
            return 'Nie znaleziono przesyłki o podanym numerze.', 404
    except Exception as e:
        return f"Błąd serwera: {str(e)}", 500

@app.route('/dodaj_firme', methods=['GET', 'POST'])
def dodaj_firme():
    if request.method == 'POST':
        nazwa_firmy = request.form['nazwa_firmy']
        nip = request.form['nip']
        adres_magazynu = request.form['adres_magazynu']
        try:
            cursor.execute("INSERT INTO Firmy (NazwaFirmy, NIP, AdresMagazynu) VALUES (?, ?, ?)", (nazwa_firmy, nip, adres_magazynu))
            conn.commit()
            return redirect(url_for('index'))  # Przekierowanie do strony głównej
        except Exception as e:
            return f"Błąd podczas dodawania firmy: {str(e)}", 500
    else:
        return render_template('dodaj_firme.html')

@app.route('/usun_firme', methods=['POST'])
def usun_firme():
    id_firmy = request.form.get('nazwa_firmy')
    try:
        cursor.execute("DELETE FROM Firmy WHERE IdFirmy = ?", (id_firmy,))
        conn.commit()
        return redirect(url_for('dodaj_firme'))
    except Exception as e:
        if 'The DELETE statement conflicted with the REFERENCE constraint' in str(e):
            error_message = "Nie można usunąć firmy, która wysłała przesyłki."
        else:
            error_message = f"Błąd podczas usuwania firmy: {str(e)}"
        return render_template('dodaj_firme.html', error=error_message)


@app.route('/adres_nadania')
def adres_nadania():
    nazwa_firmy = request.args.get('nazwa_firmy')
    if nazwa_firmy:
        cursor.execute("SELECT AdresMagazynu FROM Firmy WHERE IdFirmy = ?", (nazwa_firmy,))
        adres_nadania = cursor.fetchone()
        if adres_nadania:
            return jsonify({'adres_nadania': adres_nadania[0]})
    return jsonify({'adres_nadania': ''})

@app.route('/firmy')
def firmy():
    cursor.execute("SELECT IdFirmy, NazwaFirmy, NIP, AdresMagazynu FROM Firmy")
    firmy = cursor.fetchall()
    return jsonify([{ 'IdFirmy': firma.IdFirmy, 'NazwaFirmy': firma.NazwaFirmy, 'NIP': firma.NIP, 'AdresMagazynu': firma.AdresMagazynu } for firma in firmy])


if __name__ == '__main__':
    app.run(debug=True)
