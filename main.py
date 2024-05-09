from flask import Flask, request, render_template, redirect, url_for, jsonify
import pyodbc
import random

app = Flask(__name__)
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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dodaj', methods=['POST'])
def dodaj():
    try:
        od = request.form.get('od')
        if od == '':
            od = None

        do = request.form['do']
        gdzie_nadana = request.form['gdzie_nadana']
        gdzie_do_odbioru = request.form['gdzie_do_odbioru']
        klasa = request.form['klasa']
        
        is_company = request.form.get('is_company')
        if is_company:
            nazwa_firmy = request.form['nazwa_firmy']
            nip = request.form['nip']
            numer_przesylki = generuj_unikalny_numer('F')
            cursor.execute("INSERT INTO PrzesylkiFirmowe (NumerPrzesylki, Od, Do, GdzieNadana, GdzieDoOdbioru, KlasaPrzesylki, IdFirmy) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (numer_przesylki, od, do, gdzie_nadana, gdzie_do_odbioru, klasa, None))
        else:
            numer_przesylki = generuj_unikalny_numer('P')
            cursor.execute("INSERT INTO PrzesylkiOsobiste (NumerPrzesylki, Od, Do, GdzieNadana, GdzieDoOdbioru, KlasaPrzesylki) VALUES (?, ?, ?, ?, ?, ?)",
                           (numer_przesylki, od, do, gdzie_nadana, gdzie_do_odbioru, klasa))
        
        conn.commit()
    except Exception as e:
        print(f"Błąd podczas dodawania przesyłki: {e}")
        return f"Błąd: {str(e)}", 500

    return redirect(url_for('index'))

@app.route('/zarzadzanie_przesylkami', methods=['GET', 'POST'])
def zarzadzanie_przesylkami():
    if request.method == 'POST':
        numer_pojedynczy = request.form.get('numer_pojedynczy')
        numer_od = request.form.get('numer_od')
        numer_do = request.form.get('numer_do')

        try:
            if numer_pojedynczy:
                # Usuń przesyłkę z tabeli PrzesylkiOsobiste
                cursor.execute("DELETE FROM PrzesylkiOsobiste WHERE NumerPrzesylki = ?", (numer_pojedynczy,))
                # Usuń przesyłkę z tabeli PrzesylkiFirmowe
                cursor.execute("DELETE FROM PrzesylkiFirmowe WHERE NumerPrzesylki = ?", (numer_pojedynczy,))
                conn.commit()

            if numer_od and numer_do:
                # Usuń zakres przesyłek z tabeli PrzesylkiOsobiste
                cursor.execute("DELETE FROM PrzesylkiOsobiste WHERE NumerPrzesylki BETWEEN ? AND ?", (numer_od, numer_do))
                # Usuń zakres przesyłek z tabeli PrzesylkiFirmowe
                cursor.execute("DELETE FROM PrzesylkiFirmowe WHERE NumerPrzesylki BETWEEN ? AND ?", (numer_od, numer_do))
                conn.commit()

            return redirect(url_for('zarzadzanie_przesylkami'))
        except Exception as e:
            return f'Błąd: {str(e)}', 500
    else:
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
            return redirect(url_for('index'))
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
        cursor.execute("DELETE FROM Firmy WHERE IdFirmy = ?", (id_firmy,))
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
        cursor.execute("SELECT AdresMagazynu FROM Firmy WHERE NazwaFirmy = ?", (nazwa_firmy,))
        adres_nadania = cursor.fetchone()
        if adres_nadania:
            return jsonify({'adres_nadania': adres_nadania.AdresMagazynu})
    return jsonify({'adres_nadania': ''})

if __name__ == '__main__':
    app.run(debug=True)
