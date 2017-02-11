"""
Django settings for fair_scoring_site project.

Generated by 'django-admin startproject' using Django 1.9.4.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Application definition
INSTALLED_APPS = [
    'awards.apps.AwardsConfig',
    'judges.apps.JudgesConfig',
    'fair_categories.apps.FairCategoriesConfig',
    'fair_projects.apps.FairProjectsConfig',
    'rubrics.apps.RubricsConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'bootstrap3',
    'constance',
    'constance.backends.database',
    'import_export',
    'widget_tweaks'
]

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fair_scoring_site.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'constance.context_processors.config',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static")
]

WSGI_APPLICATION = 'fair_scoring_site.wsgi.application'

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher'
]


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_URL = '/static/'

BOOTSTRAP3 = {
'include_jquery': True,
}

CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'
CONSTANCE_CONFIG = {
    'FAIR_NAME': ('Science Fair', 'The name of the science fair'),
    'FAIR_ABBR': ('SF', 'Abbreviation for the name of the science fair'),
    'JUDGES_PER_PROJECT': (3, 'The number of judges that should be assigned to judge each project'),
    'PROJECTS_PER_JUDGE': (5, 'The minimum number of projects that should be assigned to each judge'),
    'JUDGING_ACTIVE': (False, 'Check this box during judging'),
    'RUBRIC_NAME': ('Judging Form', 'The name of the rubric judges will use to assess projects')
}
CONSTANCE_CONFIG_FIELDSETS = {
    'Fair Name': ('FAIR_NAME', 'FAIR_ABBR'),
    'Judging': ('JUDGES_PER_PROJECT', 'PROJECTS_PER_JUDGE', 'JUDGING_ACTIVE', 'RUBRIC_NAME')
}
CONSTANCE_DATABASE_PREFIX = 'constance:fair_scoring_site:'
