from .email_utils import envoyer_email
from .auth_utils import email_confirmed_required
from .currency import get_usdt_to_rub
from .email_utils import envoyer_email

# app/utils.py

MAX_FILE_SIZE = 10 * 1024 * 1024  # Limite de taille de 10 Mo (10 * 1024 * 1024)

def check_file_size(file):
    """
    Vérifie si la taille du fichier dépasse la limite autorisée.
    """
    if file.content_length > MAX_FILE_SIZE:
        raise ValueError(f"Le fichier dépasse la taille maximale autorisée de {MAX_FILE_SIZE / (1024 * 1024)} Mo.")
    return True

