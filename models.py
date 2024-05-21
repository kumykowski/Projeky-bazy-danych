from main import db

class Adres(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ulica = db.Column(db.String(255))
    numer_domu = db.Column(db.String(10))
    miasto = db.Column(db.String(255))
    kraj = db.Column(db.String(255))

class Przesylka(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numer_przesylki = db.Column(db.String(10), unique=True, nullable=False)
    imie_nadawcy = db.Column(db.String(255))
    nazwisko_nadawcy = db.Column(db.String(255))
    adres_nadawcy_id = db.Column(db.Integer, db.ForeignKey('adres.id'))
    adres_nadawcy = db.relationship('Adres', foreign_keys=[adres_nadawcy_id], uselist=False)
    imie_odbiorcy = db.Column(db.String(255))
    nazwisko_odbiorcy = db.Column(db.String(255))
    adres_odbiorcy_id = db.Column(db.Integer, db.ForeignKey('adres.id'))
    adres_odbiorcy = db.relationship('Adres', foreign_keys=[adres_odbiorcy_id], uselist=False)
    klasa_przesylki = db.Column(db.String(255))
