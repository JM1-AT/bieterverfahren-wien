from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Nutzer der Plattform – Admin oder Bieter."""
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    firma = db.Column(db.String(255))
    rolle = db.Column(db.String(20), default='bieter')        # 'admin' oder 'bieter'
    status = db.Column(db.String(20), default='ausstehend')   # 'ausstehend', 'aktiv', 'abgelehnt'
    passwort_hash = db.Column(db.String(255))
    google_id = db.Column(db.String(255), unique=True)
    totp_secret = db.Column(db.String(64))
    totp_aktiviert = db.Column(db.Boolean, default=False)
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    letzter_login = db.Column(db.DateTime)

    # Beziehungen
    einladungen = db.relationship('Einladung', backref='erstellt_von_user', lazy=True,
                                  foreign_keys='Einladung.erstellt_von')
    gebote = db.relationship('Gebot', backref='bieter', lazy=True)
    zugaenge = db.relationship('ObjektZugang', backref='user', lazy=True)
    zustimmungen = db.relationship('Zustimmung', backref='user', lazy=True)
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'


class Einladung(db.Model):
    """Einladungstoken für neue Bieter (72h gültig)."""
    __tablename__ = 'einladung'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255))
    token = db.Column(db.String(128), unique=True, nullable=False)
    gueltig_bis = db.Column(db.DateTime, nullable=False)  # 72h ab Erstellung
    verwendet = db.Column(db.Boolean, default=False)
    erstellt_von = db.Column(db.Integer, db.ForeignKey('user.id'))
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)

    def ist_gueltig(self):
        return not self.verwendet and datetime.utcnow() < self.gueltig_bis


class Objekt(db.Model):
    """Immobilienobjekt im Bieterverfahren."""
    __tablename__ = 'objekt'

    id = db.Column(db.Integer, primary_key=True)
    titel = db.Column(db.String(255), nullable=False)
    objektnummer = db.Column(db.String(50))
    geschaeftsbeziehung = db.Column(db.String(10), default='B2C')  # 'B2C' oder 'B2B'
    flaeche_m2 = db.Column(db.Float)

    # Adresse
    strasse = db.Column(db.String(255), nullable=False)
    plz = db.Column(db.String(20), nullable=False)
    ort = db.Column(db.String(100), nullable=False)
    land = db.Column(db.String(100), default='Österreich')

    beschreibung = db.Column(db.Text)
    link_detailbeschreibung = db.Column(db.String(500))
    link_3d_rundgang = db.Column(db.String(500))

    # Zeitraum
    beginn = db.Column(db.DateTime)
    ende = db.Column(db.DateTime)
    aktiv = db.Column(db.Boolean, default=True)

    # Preise
    startpreis = db.Column(db.Float, nullable=False)
    zielpreis = db.Column(db.Float)   # Intern – NIE an Bieter zeigen
    sofortkauf_aktiv = db.Column(db.Boolean, default=False)
    sofortkauf_preis = db.Column(db.Float)

    # Nebenkosten (%)
    maklerprovision = db.Column(db.Float, default=3.0)
    notarkosten = db.Column(db.Float, default=1.5)
    grunderwerbssteuer = db.Column(db.Float, default=3.5)
    grundbuch_gebuehr = db.Column(db.Float, default=1.1)

    # Ausblenden-Flags
    gew_nebenkosten_ausblenden = db.Column(db.Boolean, default=False)
    gb_nebenkosten_ausblenden = db.Column(db.Boolean, default=False)
    binding_bestaetigung_ausblenden = db.Column(db.Boolean, default=False)
    angebotsliste_ausblenden = db.Column(db.Boolean, default=False)

    zusatzvereinbarungen = db.Column(db.Text)

    erstellt_von = db.Column(db.Integer, db.ForeignKey('user.id'))
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)

    # Beziehungen
    dokumente = db.relationship('Dokument', backref='objekt', lazy=True,
                                cascade='all, delete-orphan')
    gebote = db.relationship('Gebot', backref='objekt', lazy=True,
                             cascade='all, delete-orphan',
                             order_by='Gebot.betrag.desc()')
    zugaenge = db.relationship('ObjektZugang', backref='objekt', lazy=True,
                               cascade='all, delete-orphan')
    zustimmungen = db.relationship('Zustimmung', backref='objekt', lazy=True,
                                   cascade='all, delete-orphan')
    fotos = db.relationship('ObjektFoto', backref='objekt', lazy=True,
                            cascade='all, delete-orphan',
                            order_by='ObjektFoto.reihenfolge')

    def hoechstgebot(self):
        """Gibt das aktuelle Höchstgebot zurück."""
        if self.gebote:
            return max(g.betrag for g in self.gebote)
        return None

    def ist_aktiv(self):
        """Gibt True zurück wenn das Verfahren gerade läuft."""
        now = datetime.utcnow()
        if not self.aktiv:
            return False
        if self.beginn and now < self.beginn:
            return False
        if self.ende and now > self.ende:
            return False
        return True

    def status_label(self):
        """Status-Label für Anzeige."""
        now = datetime.utcnow()
        if not self.aktiv:
            return 'beendet'
        if self.beginn and now < self.beginn:
            return 'vorbereitung'
        if self.ende:
            diff = (self.ende - now).total_seconds()
            if diff <= 0:
                return 'beendet'
            if diff <= 86400:  # 24h
                return 'endet_bald'
        return 'aktiv'

    def __repr__(self):
        return f'<Objekt {self.titel}>'


class Dokument(db.Model):
    """Hochgeladenes Dokument zu einem Objekt (Fernet-verschlüsselt)."""
    __tablename__ = 'dokument'

    id = db.Column(db.Integer, primary_key=True)
    objekt_id = db.Column(db.Integer, db.ForeignKey('objekt.id'), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    gespeicherter_name = db.Column(db.String(255), nullable=False)  # UUID-Dateiname
    dateityp = db.Column(db.String(20))
    groesse_kb = db.Column(db.Integer)
    verschluesselt = db.Column(db.Boolean, default=True)
    nur_eingeladene = db.Column(db.Boolean, default=True)  # Nur für Bieter mit Zugang
    hochgeladen_von = db.Column(db.Integer, db.ForeignKey('user.id'))
    hochgeladen_am = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Dokument {self.original_name}>'


class Gebot(db.Model):
    """Abgegebenes Gebot eines Bieters auf ein Objekt."""
    __tablename__ = 'gebot'

    id = db.Column(db.Integer, primary_key=True)
    objekt_id = db.Column(db.Integer, db.ForeignKey('objekt.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    betrag = db.Column(db.Float, nullable=False)
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    ip_adresse = db.Column(db.String(45))

    def __repr__(self):
        return f'<Gebot €{self.betrag:,.0f} von User {self.user_id}>'


class ObjektZugang(db.Model):
    """Zugang eines Bieters zu einem Objekt."""
    __tablename__ = 'objekt_zugang'

    id = db.Column(db.Integer, primary_key=True)
    objekt_id = db.Column(db.Integer, db.ForeignKey('objekt.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    eingeladen_am = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('objekt_id', 'user_id', name='uq_zugang'),
    )

    def __repr__(self):
        return f'<ObjektZugang Objekt {self.objekt_id} User {self.user_id}>'


class Zustimmung(db.Model):
    """NDA-Bestätigung eines Bieters für ein Objekt (rechtssicher protokolliert)."""
    __tablename__ = 'zustimmung'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    objekt_id = db.Column(db.Integer, db.ForeignKey('objekt.id'), nullable=False)
    bestaetigt_am = db.Column(db.DateTime, default=datetime.utcnow)
    ip_adresse = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    version = db.Column(db.String(20))       # NDA-Version (z.B. '1.0')
    text_hash = db.Column(db.String(64))     # SHA256 des NDA-Texts

    __table_args__ = (
        db.UniqueConstraint('user_id', 'objekt_id', name='uq_zustimmung'),
    )

    def __repr__(self):
        return f'<Zustimmung User {self.user_id} Objekt {self.objekt_id}>'


class SliderBild(db.Model):
    """Plattformweites Bild für den Slider im Bieter-Dashboard."""
    __tablename__ = 'slider_bild'

    id = db.Column(db.Integer, primary_key=True)
    gespeicherter_name = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255))
    reihenfolge = db.Column(db.Integer, default=0)
    hochgeladen_am = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SliderBild {self.original_name}>'


class ObjektFoto(db.Model):
    """Foto zu einem Objekt – für den Foto-Slider auf der Detailseite."""
    __tablename__ = 'objekt_foto'

    id = db.Column(db.Integer, primary_key=True)
    objekt_id = db.Column(db.Integer, db.ForeignKey('objekt.id'), nullable=False)
    gespeicherter_name = db.Column(db.String(255), nullable=False)  # UUID-Dateiname
    original_name = db.Column(db.String(255))
    reihenfolge = db.Column(db.Integer, default=0)
    hochgeladen_am = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ObjektFoto {self.original_name}>'


class AuditLog(db.Model):
    """Audit-Trail aller sicherheitsrelevanten Aktionen."""
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    aktion = db.Column(db.String(100), nullable=False)   # z.B. 'login', 'gebot', 'nda'
    objekt_id = db.Column(db.Integer, db.ForeignKey('objekt.id'))
    details = db.Column(db.Text)                          # JSON-String
    ip_adresse = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AuditLog {self.aktion} by User {self.user_id}>'
