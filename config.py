import os
from dotenv import load_dotenv

load_dotenv()

# Umgebung erkennen (DEV oder PROD)
ENV = os.environ.get('FLASK_ENV', 'development')
IS_PROD = ENV == 'production'

class Config:
    # Sicherheitsschlüssel – in Produktion via ENV setzen!
    # Fixer Fallback-Key für Entwicklung (Sessions überleben App-Neustarts)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'bv-wien-dev-secret-key-2026-maierhofer'

    # Datenbank
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session-Sicherheit
    SESSION_COOKIE_SECURE = IS_PROD  # Nur HTTPS in Produktion
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 900   # 15 Minuten Inaktivität

    # Upload-Einstellungen
    MAX_CONTENT_LENGTH = 3 * 1024 * 1024 * 1024  # 3 GB
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                          'jpg', 'jpeg', 'png', 'gif', 'zip', 'mp4', 'mov'}
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

    # Fernet-Verschlüsselung für Uploads
    _fernet_key = os.environ.get('FERNET_KEY')
    if _fernet_key:
        FERNET_KEY = _fernet_key.encode()
    else:
        # Stabiler Fallback für Entwicklung – in Produktion FERNET_KEY als ENV setzen!
        FERNET_KEY = b'zbGora84Hfu1cUwETEzIRQOozT57HJBQbNmt0P0kWSY='

    # Google OAuth (deaktiviert)
    AUTH_GOOGLE_ENABLED = False
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

    # E-Mail – Test-Modus nur lokal, in Produktion echter Versand
    MAIL_TEST_MODE = not IS_PROD
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'office@bieterverfahrenwien.at')

    # Backup-Einstellungen
    BACKUP_FOLDER = os.path.join(BASE_DIR, 'backups')
    BACKUP_KEEP = 30  # Letzte 30 Backups behalten

    # NDA-Text (Platzhalter – vom Client zu ersetzen)
    NDA_VERSION = '1.0'
    NDA_TEXT = {
        'de': """1. Vertraulichkeitserklärung

[NDA-Text auf Deutsch einfügen]

Der Interessent verpflichtet sich, alle im Rahmen dieses Bieterverfahrens erhaltenen Informationen streng vertraulich zu behandeln. Dies umfasst insbesondere alle Angaben zu Mietverträgen, Erträgen, Bewertungen, technischen Gutachten sowie sonstigen Unterlagen zum Objekt.

2. Bieterbedingungen

[Bieterbedingungen auf Deutsch einfügen]

Jedes abgegebene Gebot stellt ein rechtsverbindliches Angebot zum Kauf der Liegenschaft dar. Der Bieter bestätigt, dass er wirtschaftlich und rechtlich in der Lage ist, das Objekt zu erwerben und die Finanzierung als gesichert gilt.

3. Verfahrensregeln

Das Verfahren wird von RA Mag. Werner Maierhofer geleitet. Alle Gebote sind anonym. Nur das aktuelle Höchstgebot wird kommuniziert. Die Anzahl der Bieter wird nicht bekannt gegeben. Der Verkäufer behält sich das Recht vor, das Verfahren ohne Angabe von Gründen abzubrechen.

4. Datenschutz

Die erhobenen Daten werden ausschließlich für die Abwicklung des Bieterverfahrens verwendet. Die Bestätigung wird mit Zeitstempel, IP-Adresse und User-Agent protokolliert und ist im Admin-Panel jederzeit nachweisbar.""",

        'en': """1. Confidentiality Agreement

[Insert NDA text in English]

The interested party agrees to treat all information received in the course of this bidding procedure as strictly confidential. This includes in particular all information on lease agreements, returns, valuations, technical reports and other documents relating to the property.

2. Bidding Terms

[Insert bidding terms in English]

Every bid submitted constitutes a legally binding offer to purchase the property. The bidder confirms that they are financially and legally capable of acquiring the property and that financing is secured.

3. Procedure Rules

The procedure is conducted by RA Mag. Werner Maierhofer. All bids are anonymous. Only the current highest bid is communicated. The number of bidders is not disclosed. The seller reserves the right to terminate the procedure without stating reasons.

4. Data Protection

The data collected is used exclusively for the processing of the bidding procedure. The confirmation is logged with timestamp, IP address and user agent and can be verified at any time in the admin panel."""
    }
