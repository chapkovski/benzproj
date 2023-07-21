from os import environ
import os
from dotenv import load_dotenv

load_dotenv()


PROLIFIC_URL = environ.get("PROLIFIC_URL", "https://cnn.com")


EXTENSION_APPS = ["img_desc"]

SESSION_CONFIGS = [
    dict(
        expand_slots=False,
        name="full",
        display_name="Full study (practice + main)",
        num_demo_participants=8,
        app_sequence=["start", "img_desc"],
    ),
    dict(
        expand_slots=False,
        name="img_desc",
        display_name="Main study only",
        num_demo_participants=8,
        app_sequence=["img_desc"],
    ),
    dict(
        name="practice",
        display_name="practice pages",
        num_demo_participants=8,
        app_sequence=[
            "start",
        ],
    ),
]

# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    filename="benz",
    s3path="https://chappyimgs.s3.us-west-1.amazonaws.com/",
    instructions_path="https://docs.google.com/document/d/e/2PACX-1vQvT3XleOaxDRAws2WDba6LsyhrkmDzD8YI4rj8duCdg4Pj5YC3ikmMy7Y81R7SMfouWa5TkQv5zldw/pub",
    expand_slots=True,
    max_users=8,
    for_prolific=True,
    prolific_redirect_url=PROLIFIC_URL,
    real_world_currency_per_point=1.00,
    participation_fee=0.00,
    doc="",
)

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = "en"

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = "USD"
USE_POINTS = True

ADMIN_USERNAME = "admin"
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get("OTREE_ADMIN_PASSWORD")

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = "str703e*an0e_=3hc3lrgy^x0=_x6qqkbbhmak@2mxbr88v9c("

# if an app is included in SESSION_CONFIGS, you don't need to list it here
INSTALLED_APPS = ["otree", "django_countries"]
COUNTRIES_FIRST = ["US", "GB"]
COUNTRIES_FIRST_REPEAT = True
