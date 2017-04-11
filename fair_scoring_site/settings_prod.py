"""
Django settings for fair_scoring_site project.

Generated by 'django-admin startproject' using Django 1.9.4.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

from .settings_common import *


# SECURITY WARNING: keep the secret key used in production secret!
# TODO: Configure Secret Key
SECRET_KEY = 'REPLACE ME'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# TODO: Replace value
ALLOWED_HOSTS = [
    'REPLACE URL'
]


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
# TODO: Configure Datatbase
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'REPLACE DB NAME',
        'USER': 'REPLACE USERNAME',
        'PASSWORD': 'REPLACE PASSWORD',
        'HOST': 'REPLACE HOST',
        'PORT': 'REPLACE PORT',
    }
}

# Email
# https://docs.djangoproject.com/en/1.10/topics/email/#email-backends
# TODO: Configure Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = "smtp.gmail.com"
EMAIL_HOST_USER = "REPLACE EMAIL"
EMAIL_HOST_PASSWORD = 'REPLACE PASSWORD'
EMAIL_PORT = 587
EMAIL_USE_TLS = True


# TODO: Configure Admins
ADMINS = [
    ('REPLACE NAME', 'REPLACE EMAIL')
]

X_FRAME_OPTIONS = 'DENY'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

STATIC_ROOT = os.path.join(BASE_DIR, "static")

STATICFILES_DIRS = []
