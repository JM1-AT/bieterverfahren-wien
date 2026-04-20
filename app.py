from datetime import datetime, timedelta
from flask import Flask, redirect, url_for, session
from flask_login import LoginManager, current_user, logout_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from models import db, User
from i18n import t, current_lang
from security import security_headers

# Rate-Limiter (global – in auth.py referenziert)
limiter = Limiter(key_func=get_remote_address)


def create_app():
    """Flask-App-Factory."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Erweiterungen initialisieren
    db.init_app(app)
    limiter.init_app(app)

    # Flask-Login konfigurieren
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Bitte melden Sie sich an.'
    login_manager.login_message_category = 'error'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Blueprints registrieren
    from auth import auth_bp
    from admin import admin_bp
    from bieter import bieter_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(bieter_bp)

    # Übersetzung als Jinja2-Globals registrieren
    app.jinja_env.globals['t'] = t
    app.jinja_env.globals['current_lang'] = current_lang

    # Hilfs-Filter
    @app.template_filter('euro')
    def euro_format(wert):
        """Zahlen als Euro-Betrag formatieren: 2500000 → € 2.500.000"""
        if wert is None:
            return '–'
        return f'€ {int(wert):,}'.replace(',', '.')

    @app.template_filter('roman')
    def roman_format(zahl):
        """Zahl als römische Ziffer: 1→I, 2→II, 3→III ..."""
        werte = [(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),
                 (50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]
        ergebnis = ''
        for wert, symbol in werte:
            while zahl >= wert:
                ergebnis += symbol
                zahl -= wert
        return ergebnis

    @app.template_filter('datum')
    def datum_format(dt):
        """Datetime als lesbares Datum formatieren."""
        if dt is None:
            return '–'
        return dt.strftime('%d.%m.%Y')

    @app.template_filter('datetime_de')
    def datetime_de_format(dt):
        """Datetime als deutsches Datum+Uhrzeit formatieren."""
        if dt is None:
            return '–'
        return dt.strftime('%d.%m.%Y · %H:%M:%S')

    # Landing-Page Route: eingeloggte Nutzer → Dashboard
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            if current_user.rolle == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('bieter.dashboard'))
        return redirect(url_for('auth.login'))

    # Session permanent setzen + Inaktivitäts-Timeout
    @app.before_request
    def session_erneuern():
        from flask import request as req
        if req.endpoint and req.endpoint.startswith('static'):
            return
        session.permanent = True
        if current_user.is_authenticated:
            jetzt = datetime.utcnow().timestamp()
            letzte = session.get('_last_activity')
            if letzte and (jetzt - letzte) > 900:  # 15 Minuten
                logout_user()
                session.clear()
                return
            session['_last_activity'] = jetzt

    # Rate-Limiting für Login (5 Versuche/Minute)
    limiter.limit('5 per minute')(auth_bp.view_functions.get('login', lambda: None))

    # Rate-Limiting für Anfrage-Formular (3/Stunde)
    limiter.limit('3 per hour')(auth_bp.view_functions.get('anfrage', lambda: None))

    # Sicherheits-Header nach jedem Request
    app.after_request(security_headers)

    # Datei zu groß (413)
    @app.errorhandler(413)
    def zu_gross(e):
        return '''<!DOCTYPE html><html><head><meta charset="UTF-8">
        <title>Datei zu groß</title></head><body style="font-family:sans-serif;padding:40px">
        <h2>Datei zu groß</h2>
        <p>Die Datei überschreitet das Limit. Bitte kleinere Dateien hochladen.</p>
        <a href="javascript:history.back()">← Zurück</a></body></html>''', 413

    # Datenbank erstellen und Testdaten befüllen
    with app.app_context():
        db.create_all()
        _migrate_db()
        _testdaten_anlegen()

    # Scheduler starten
    from scheduler import scheduler_starten
    scheduler_starten(app)

    return app


def _migrate_db():
    """Neue Spalten sicher hinzufügen (idempotent – ignoriert Fehler wenn bereits vorhanden)."""
    from sqlalchemy import text
    objekt_cols = [
        ('veroeffentlicht', 'BOOLEAN DEFAULT 0'),
        ('teilen_token', 'VARCHAR(64)'),
        ('ist_miete', 'REAL'),
        ('soll_miete', 'REAL'),
        ('einheiten_befristet', 'INTEGER DEFAULT 0'),
        ('einheiten_unbefristet', 'INTEGER DEFAULT 0'),
        ('einheiten_leerstand', 'INTEGER DEFAULT 0'),
        ('rendite_sichtbar', 'BOOLEAN DEFAULT 0'),
        ('objektdaten_sichtbar', 'BOOLEAN DEFAULT 0'),
        ('mindestspread', 'REAL DEFAULT 0'),
    ]
    user_cols = [
        ('passwort_reset_token', 'VARCHAR(100)'),
        ('passwort_reset_ablauf', 'DATETIME'),
        ('firmenname', 'VARCHAR(200)'),
        ('adresse', 'VARCHAR(300)'),
        ('position', 'VARCHAR(100)'),
        ('mobilnummer', 'VARCHAR(50)'),
        ('benachrichtigung_email', 'BOOLEAN DEFAULT 1'),
        ('benachrichtigung_sms', 'BOOLEAN DEFAULT 0'),
        ('benachrichtigung_push', 'BOOLEAN DEFAULT 0'),
    ]
    dok_cols = [
        ('ist_nda', 'BOOLEAN DEFAULT 0'),
    ]
    def _add_columns(table: str, cols: list):
        for col, typ in cols:
            try:
                db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {typ}'))
                db.session.commit()
            except Exception:
                db.session.rollback()

    _add_columns('objekt', objekt_cols)
    _add_columns('"user"', user_cols)
    _add_columns('dokument', dok_cols)


def _testdaten_anlegen():
    """Testdaten beim ersten Start anlegen (nur wenn DB leer)."""
    if User.query.first():
        return  # Bereits Daten vorhanden

    print('\n[App] Erste Ausführung – Testdaten werden angelegt...')

    from auth import passwort_hashen
    from models import Objekt, ObjektZugang, AuditLog

    # ── Testaccounts ──────────────────────────────────────────────────────

    # Admin (Entwicklung)
    admin = User(
        email='admin@bieterverfahren.at',
        name='RA Maierhofer',
        firma='Bieterverfahren Wien',
        rolle='admin',
        status='aktiv',
        passwort_hash=passwort_hashen('admin123'),
        totp_aktiviert=False
    )
    db.session.add(admin)

    # Admin (Produktion)
    admin_prod = User(
        email='office@bieterverfahrenwien.at',
        name='RA Maierhofer',
        firma='Bieterverfahren Wien',
        rolle='admin',
        status='aktiv',
        passwort_hash=passwort_hashen('Kx7$mR2vQp'),
        totp_aktiviert=False
    )
    db.session.add(admin_prod)

    # Bieter 1
    bieter1 = User(
        email='bieter1@bieterverfahren.at',
        name='Klaus Eder',
        firma='Eder Immobilien GmbH',
        rolle='bieter',
        status='aktiv',
        passwort_hash=passwort_hashen('bieter123')
    )
    db.session.add(bieter1)

    # Bieter 2
    bieter2 = User(
        email='bieter2@bieterverfahren.at',
        name='Anna Muster',
        firma='AM Invest AG',
        rolle='bieter',
        status='aktiv',
        passwort_hash=passwort_hashen('bieter456')
    )
    db.session.add(bieter2)

    # Nutzer mit ausstehender Anfrage
    anfrage_user = User(
        email='anfrage@bieterverfahren.at',
        name='Thomas Wolf',
        firma='Wolf Capital',
        rolle='bieter',
        status='ausstehend'
    )
    db.session.add(anfrage_user)

    db.session.flush()  # IDs generieren

    # ── Testobjekt ────────────────────────────────────────────────────────

    jetzt = datetime.utcnow()
    testobjekt = Objekt(
        titel='Testobjekt – Zinshaus Währinger Str. 12',
        objektnummer='BV-2025-001',
        geschaeftsbeziehung='B2C',
        flaeche_m2=680,
        strasse='Währinger Straße 12',
        plz='1180',
        ort='Wien',
        land='Österreich',
        beschreibung=(
            'Gepflegtes Zinshaus in bester Lage des 18. Bezirks (Währing). '
            'Das Objekt umfasst 12 Wohneinheiten und 2 Gewerbeeinheiten. '
            'Vollständig vermietet, solide Mieterstruktur. '
            'Baujahr 1910, generalsaniertes Stiegenhaus.'
        ),
        link_detailbeschreibung=None,
        link_3d_rundgang=None,
        beginn=jetzt,
        ende=jetzt + timedelta(days=14),
        startpreis=2_500_000,
        zielpreis=2_900_000,
        sofortkauf_aktiv=False,
        maklerprovision=3.0,
        notarkosten=1.5,
        grunderwerbssteuer=3.5,
        grundbuch_gebuehr=1.1,
        aktiv=True,
        veroeffentlicht=True,
        erstellt_von=admin.id
    )
    db.session.add(testobjekt)
    db.session.flush()

    # Bieter 1 und 2 haben Zugang zum Testobjekt
    db.session.add(ObjektZugang(objekt_id=testobjekt.id, user_id=bieter1.id))
    db.session.add(ObjektZugang(objekt_id=testobjekt.id, user_id=bieter2.id))

    # Audit-Log Eintrag
    db.session.add(AuditLog(
        aktion='system_initialisiert',
        details='{"info": "Testdaten angelegt"}'
    ))

    db.session.commit()

    print('[App] Testdaten angelegt:')
    print('  admin@bieterverfahren.at       / admin123    (Admin, Entwicklung)')
    print('  office@bieterverfahrenwien.at  / Kx7$mR2vQp  (Admin, Produktion)')
    print('  bieter1@bieterverfahren.at / bieter123  (Bieter, Zugang zu Testobjekt)')
    print('  bieter2@bieterverfahren.at / bieter456  (Bieter, Zugang zu Testobjekt)')
    print('  anfrage@bieterverfahren.at             (Status: ausstehend)')
    print(f'  Testobjekt: {testobjekt.titel}')
    print()


# ── Anwendung starten ─────────────────────────────────────────────────────────

app = create_app()

if __name__ == '__main__':
    print('\n' + '='*60)
    print('  Bieterverfahren Wien – Plattform')
    print('  http://localhost:5000')
    print('='*60)
    print()
    app.run(debug=True, host='0.0.0.0', port=5001, use_reloader=False)
