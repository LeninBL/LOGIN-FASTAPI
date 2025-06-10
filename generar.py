import secrets
import string

def generar_secret_key(length=50):
    caracteres = string.ascii_letters + string.digits + '-_'
    key = ''.join(secrets.choice(caracteres) for _ in range(length))
    return f'SECRET_KEY="{key}"'

print(generar_secret_key())