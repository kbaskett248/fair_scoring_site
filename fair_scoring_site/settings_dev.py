"""
Django settings for fair_scoring_site project.

Generated by 'django-admin startproject' using Django 1.9.4.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os

from hypothesis import Verbosity, settings

from .settings_common import *


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# TODO: Configure Secret Key
SECRET_KEY = 'REPLACE ME'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

INSTALLED_APPS.append('debug_toolbar')

MIDDLEWARE_CLASSES.append('debug_toolbar.middleware.DebugToolbarMiddleware')

ALLOWED_HOSTS = []

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

INTERNAL_IPS = [
    '127.0.0.1'
]

# Email
# https://docs.djangoproject.com/en/1.10/topics/email/#email-backends
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = os.path.join(BASE_DIR, 'app-messages')

settings.register_profile("dev", settings(max_examples=20))
settings.register_profile("debug", settings(max_examples=10, verbosity=Verbosity.verbose))
settings.load_profile('dev')
