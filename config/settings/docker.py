import os
import sys
import importlib.util
from pathlib import Path

settings_dir = Path(__file__).parent

# Cargar base.py
base_path = settings_dir / 'base.py'
base_spec = importlib.util.spec_from_file_location('config.settings.base', base_path)
base_module = importlib.util.module_from_spec(base_spec)
base_spec.loader.exec_module(base_module)
for attr_name in dir(base_module):
    if not attr_name.startswith('_'):
        globals()[attr_name] = getattr(base_module, attr_name)

if 'BASE_DIR' not in globals():
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Cargar security.py
security_path = settings_dir / 'security.py'
security_spec = importlib.util.spec_from_file_location('config.settings.security', security_path)
security_module = importlib.util.module_from_spec(security_spec)
security_spec.loader.exec_module(security_module)
for attr_name in dir(security_module):
    if not attr_name.startswith('_'):
        globals()[attr_name] = getattr(security_module, attr_name)

# --- Configuración Docker ---

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

SECRET_KEY = os.environ['SECRET_KEY']

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Base de datos PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'sagec'),
        'USER': os.environ.get('POSTGRES_USER', 'sagec'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': os.environ.get('POSTGRES_HOST', 'db'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

# Archivos estáticos (collectstatic los pone en staticfiles/)
STATICFILES_DIRS = []

# Seguridad: desactivar para HTTP en desarrollo con Docker
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

# Correo (consola para desarrollo)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Axes activado en Docker
AXES_ENABLED = True
