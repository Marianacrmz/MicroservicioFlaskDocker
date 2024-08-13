import re

def validate_password(password):
    # Verifica la longitud de la contraseña
    if len(password) < 8 or len(password) > 15:
        return False
    # Verifica la presencia de al menos una letra minúscula
    if not re.search("[a-z]", password):
        return False
    # Verifica la presencia de al menos una letra mayúscula
    if not re.search("[A-Z]", password):
        return False
    # Verifica la presencia de al menos un carácter especial
    if not re.search("[¡\"#$%&/()!@]", password):
        return False
    return True
