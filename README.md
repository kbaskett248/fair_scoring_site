# Installation

## Production

1. Checkout repo
```bash
git clone https://github.com/kbaskett248/fair_scoring_site.git
```

2. Install dependencies. On production we need to install mysql, and we don't need to install any dev dependencies.
```bash
poetry install --only=main --extras=mysql
```

3. Create `fair_scoring_site\settings.py` and import from `settings_prod.py`. Fill in the values defined in `settings_prod.py`
```python
from fair_scoring_site.settings_prod import *

# SECURITY WARNING: keep the secret key used in production secret!
# TODO: Configure Secret Key
SECRET_KEY = "REPLACE ME"

# TODO: Replace value
ALLOWED_HOSTS = ["REPLACE URL"]

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
# TODO: Configure Datatbase
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "REPLACE DB NAME",
        "USER": "REPLACE USERNAME",
        "PASSWORD": "REPLACE PASSWORD",
        "HOST": "REPLACE HOST",
        "PORT": "REPLACE PORT",
    }
}

# Email
# https://docs.djangoproject.com/en/1.10/topics/email/#email-backends
# TODO: Configure Email
EMAIL_HOST = "smtp.gmail.com"
EMAIL_HOST_USER = "REPLACE EMAIL"
EMAIL_HOST_PASSWORD = "REPLACE PASSWORD"
EMAIL_PORT = 587


# TODO: Configure Admins
ADMINS = [("REPLACE NAME", "REPLACE EMAIL")]
```

4. Run migrations
```bash
poetry run python manage.py migrate
```

5. Create superuser
```bash
poetry run python manage.py createsuperuser
```
