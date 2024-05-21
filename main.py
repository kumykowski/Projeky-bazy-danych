from flask import Flask, request, render_template, redirect, url_for, jsonify
import pyodbc
import random
import barcode
from barcode.writer import ImageWriter
from datetime import datetime

app = Flask(__name__)
conn_str = 'Driver={SQL Server};Server=TS-0002\\SQLEXPRESS;Database=ProjektPrzesylka;Trusted_Connection=yes;'

conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

def szukaj_przesylki(numer_przesylki):
    try:
        query = "SELECT NumerPrzesylki, Od, Do, GdzieNadana, GdzieDoOdbioru, KlasaPrzesylki, StanPrzesylki FROM Przesylki WHERE NumerPrzesylki = ?"
        cursor.execute(query, (numer_przesylki,))
        przesylki = cursor.fetchall()
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
    filename = my_barcode.save(f"static/{numer_przesylki}")
    return filename

@app.route('/')
def index():
    cursor.execute("SELECT IdFirmy, NazwaFirmy FROM Firmy")
    firmy = cursor.fetchall()
    return render_template('index.html', firmy=firmy)

@app.route('/<filename>')
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
        is_company = request.form.get('is_company') == 'on'

        data_nadania = datetime.now()

        if is_company:
            nazwa_firmy = request.form.get('nazwa_firmy')
            numer_przesylki = generuj_unikalny_numer('F')
            print(f"Numer przesyłki firmowej: {numer_przesylki}")
            print(f"Dane przesyłki firmowej: {od}, {do}, {gdzie_nadana}, {gdzie_do_odbioru}, {klasa}, {nazwa_firmy}, {data_nadania}")
            try:
                cursor.execute("""
                    INSERT INTO PrzesylkiFirmowe (NumerPrzesylki, Od, Do, GdzieNadana, GdzieDoOdbioru, KlasaPrzesylki, IdFirmy, DataNadania)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (numer_przesylki, od, do, gdzie_nadana, gdzie_do_odbioru, klasa, nazwa_firmy, data_nadania))
                conn.commit()
            except Exception as e:
                return f'Błąd przy dodawaniu przesyłki firmowej: {str(e)}'
        else:
            numer_przesylki = generuj_unikalny_numer('P')
            print(f"Numer przesyłki osobistej: {numer_przesylki}")
            print(f"Dane przesyłki osobistej: {od}, {do}, {gdzie_nadana}, {gdzie_do_odbioru}, {klasa}, {data_nadania}")
            try:
                cursor.execute("""
                    INSERT INTO PrzesylkiOsobiste (NumerPrzesylki, Od, Do, GdzieNadana, GdzieDoOdbioru, KlasaPrzesylki, DataNadania)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (numer_przesylki, od, do, gdzie_nadana, gdzie_do_odbioru, klasa, data_nadania))
                conn.commit()
            except Exception as e:
                return f'Błąd przy dodawaniu przesyłki prywatnej: {str(e)}'

        filename = generuj_kod_kreskowy(numer_przesylki)
        return redirect(url_for('pokaz_kod_kreskowy', filename=f"{numer_przesylki}.png"))
    else:
        cursor.execute("SELECT IdFirmy, NazwaFirmy FROM Firmy")
        firmy = cursor.fetchall()
        return render_template('dodaj_przesylke.html', firmy=firmy)

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
        print(f"Dodawanie firmy: {nazwa_firmy}, {nip}, {adres_magazynu}")
        try:
            cursor.execute("INSERT INTO Firmy (NazwaFirmy, NIP, AdresMagazynu) VALUES (?, ?, ?)", (nazwa_firmy, nip, adres_magazynu))
            conn.commit()
            cursor.execute("EXEC UpdateDaneFirm")
            conn.commit()
            return redirect(url_for('dodaj_firme'))
        except Exception as e:
            return f"Błąd podczas dodawania firmy: {str(e)}", 500
    else:
        cursor.execute("SELECT IdFirmy, NazwaFirmy FROM Firmy")
        firmy = cursor.fetchall()
        return render_template('dodaj_firme.html', firmy=firmy)

@app.route('/usun_firme', methods=['POST'])
def usun_firme():
    id_firmy = request.form.get('nazwa_firmy')
    try:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM PrzesylkiFirmowe 
            WHERE IdFirmy = ? AND StanPrzesylki != 'Odebrana'
        """, (id_firmy,))
        przesylki_count = cursor.fetchone()[0]

        if przesylki_count > 0:
            error_message = "Nie można usunąć firmy, która ma przesyłki w stanie innym niż 'Odebrana'."
            cursor.execute("SELECT IdFirmy, NazwaFirmy FROM Firmy")
            firmy = cursor.fetchall()
            return render_template('dodaj_firme.html', firmy=firmy, error=error_message)
        
        cursor.execute("""
            DELETE FROM PrzesylkiFirmowe
            WHERE IdFirmy = ? AND StanPrzesylki = 'Odebrana'
        """, (id_firmy,))
        
        cursor.execute("DELETE FROM Firmy WHERE IdFirmy = ?", (id_firmy,))
        conn.commit()
        cursor.execute("EXEC UpdateDaneFirm")
        conn.commit()
        return redirect(url_for('dodaj_firme'))
    except Exception as e:
        return f"Błąd podczas usuwania firmy: {str(e)}", 500

@app.route('/firmy')
def firmy():
    cursor.execute("SELECT IdFirmy, NazwaFirmy, NIP, AdresMagazynu FROM Firmy")
    firmy = cursor.fetchall()
    return jsonify([{ 'IdFirmy': firma.IdFirmy, 'NazwaFirmy': firma.NazwaFirmy, 'NIP': firma.NIP, 'AdresMagazynu': firma.AdresMagazynu } for firma in firmy])

@app.route('/adres_nadania')
def adres_nadania():
    nazwa_firmy = request.args.get('nazwa_firmy')
    if nazwa_firmy:
        cursor.execute("SELECT AdresMagazynu FROM Firmy WHERE IdFirmy = ?", (nazwa_firmy,))
        adres_nadania = cursor.fetchone()
        if adres_nadania:
            return jsonify({'adres_nadania': adres_nadania.AdresMagazynu})
    return jsonify({'adres_nadania': ''})

if __name__ == '__main__':
    app.run(debug=True)
