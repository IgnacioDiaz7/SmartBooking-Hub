"""
Django settings for smartbooking_hub project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# ==============================================================================
# CARGA DE VARIABLES DE ENTORNO
# ==============================================================================
# Buscamos el archivo .env en la raíz del espacio de trabajo
BASE_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = BASE_DIR.parent
ENV_PATH = WORKSPACE_DIR / '.env'

# Cargamos el archivo usando la librería segura python-dotenv
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    # Respaldo por si se ejecuta dentro de smartbooking_hub directamente
    load_dotenv()

# ==============================================================================
# CONFIGURACIÓN BÁSICA DE DJANGO
# ==============================================================================
SECRET_KEY = os.getenv('SECRET_KEY')

# Transforma el string 'True' del .env a un booleano real
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# Convierte el string del .env ("localhost,127.0.0.1,*") en una lista de Python
env_hosts = os.getenv('ALLOWED_HOSTS', '*')
ALLOWED_HOSTS = [host.strip() for host in env_hosts.split(',')]

# ==============================================================================
# APLICACIONES Y MIDDLEWARE
# ==============================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'users',
    'businesses',
    'workers',
    'bookings',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # Debe ir lo más arriba posible
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config.middleware.TenantMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ==============================================================================
# BASE DE DATOS (PostgreSQL)
# ==============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# ==============================================================================
# SEGURIDAD Y VALIDACIÓN DE CONTRASEÑAS
# ==============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTH_USER_MODEL = 'users.User'

# ==============================================================================
# INTERNACIONALIZACIÓN Y ARCHIVOS ESTÁTICOS
# ==============================================================================
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuración de CORS (Permite conexiones desde tu frontend en React)
CORS_ALLOW_ALL_ORIGINS = True

# ==============================================================================
# CONFIGURACIÓN DEL SERVIDOR DE CORREO SMTP (GMAIL)
# ==============================================================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 465
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'contacto.sbhub@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = f'SmartBooking HUB <{EMAIL_HOST_USER}>'