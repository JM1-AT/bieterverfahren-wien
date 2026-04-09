import os
import uuid
import hashlib
from cryptography.fernet import Fernet
from flask import current_app


def get_fernet():
    """Fernet-Instanz mit dem konfigurierten Schlüssel."""
    return Fernet(current_app.config['FERNET_KEY'])


def verschluesseln(daten: bytes) -> bytes:
    """Datei-Inhalt mit Fernet verschlüsseln."""
    return get_fernet().encrypt(daten)


def entschluesseln(daten: bytes) -> bytes:
    """Fernet-verschlüsselte Daten entschlüsseln."""
    return get_fernet().decrypt(daten)


def sicherer_dateiname(original_name: str) -> str:
    """UUID-Dateiname generieren – Originalname wird NICHT verwendet."""
    endung = ''
    if '.' in original_name:
        endung = '.' + original_name.rsplit('.', 1)[1].lower()
    return str(uuid.uuid4()) + endung


def erlaubte_datei(dateiname: str) -> bool:
    """Prüft ob die Dateiendung erlaubt ist."""
    if '.' not in dateiname:
        return False
    endung = dateiname.rsplit('.', 1)[1].lower()
    return endung in current_app.config['ALLOWED_EXTENSIONS']


def upload_pfad(objekt_id: int) -> str:
    """Gibt den Upload-Pfad für ein Objekt zurück (außerhalb web-root)."""
    pfad = os.path.join(current_app.config['UPLOAD_FOLDER'], 'objekte', str(objekt_id))
    os.makedirs(pfad, exist_ok=True)
    return pfad


def foto_pfad(objekt_id: int) -> str:
    """Gibt den Foto-Pfad für ein Objekt zurück (außerhalb web-root, unverschlüsselt)."""
    pfad = os.path.join(current_app.config['UPLOAD_FOLDER'], 'objekte', str(objekt_id), 'fotos')
    os.makedirs(pfad, exist_ok=True)
    return pfad


def objekt_nda_pfad(objekt_id: int) -> str:
    """Pfad zur objektspezifischen NDA-PDF-Datei."""
    verz = os.path.join(current_app.config['UPLOAD_FOLDER'], 'objekte', str(objekt_id))
    os.makedirs(verz, exist_ok=True)
    return os.path.join(verz, 'nda_dokument.pdf')


def objekt_nda_vorhanden(objekt_id: int) -> bool:
    """True wenn für dieses Objekt ein NDA-PDF hochgeladen wurde."""
    try:
        return os.path.exists(objekt_nda_pfad(objekt_id))
    except Exception:
        return False


def sha256_hash(text: str) -> str:
    """SHA256-Hash eines Texts berechnen (für NDA-Protokollierung)."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def security_headers(response):
    """Sicherheits-Header nach jedem Request setzen."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    # HSTS nur in Produktion (HTTPS erforderlich)
    if current_app.config.get('SESSION_COOKIE_SECURE'):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
