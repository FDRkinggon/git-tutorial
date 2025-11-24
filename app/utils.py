from functools import wraps
from flask import abort
from flask_login import current_user
def admin_required(f):
    """Décorateur pour les routes admin (si besoin futur)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
def allowed_file(filename, allowed_extensions):
    """Vérifie si l'extension du fichier est autorisée"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
def format_currency(amount, currency='EUR'):
    """Formate un montant avec la devise"""
    symbols = {
        'EUR': '€',
        'USD': '$',
        'GBP': '£',
        'CHF': 'CHF',
        'CAD': 'C$'
    }
    symbol = symbols.get(currency, currency)
    return f"{amount:.2f} {symbol}"