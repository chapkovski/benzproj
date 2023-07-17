from otree.api import (
    models,
    widgets,
    BaseConstants,
    BaseSubsession,
    BaseGroup,
    BasePlayer,
    Currency as c,
    currency_range,
)

EDUCATION_CHOICES = [
    "Less than a high school diploma",
    "High school degree or equivalent (e.g. GED)",
    "Some college, no degree",
    "Associate degree (e.g. AA, AS)",
    "Bachelor's degree (e.g. BA, BS)",
    "Master's degree (e.g. MA, MS, MEd)",
    "Doctorate or professional degree (e.g. MD, DDS, PhD)",
]
from django_countries.fields import CountryField
from img_desc.utils import get_url_for_image
author = "Your name here"

doc = """
Your app description
"""


class Constants(BaseConstants):
    name_in_url = "start"
    players_per_group = None
    num_rounds = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    gender = models.StringField(
        label="Gender",
        widget=widgets.RadioSelectHorizontal,
        choices=["female", "male", "diverse", "I prefer not to say"],
    )
    age = models.IntegerField(label="Age (years)")
    handedness = models.StringField(
        label="Handedness",
        widget=widgets.RadioSelectHorizontal,
        choices=["right-handed", "left-handed", "ambidextrous/two-handed"],
    )
    grew_up = CountryField(null=True, verbose_name='Grew up in country')
    currently_living = CountryField(null=True, verbose_name='Currently living in country')
    native_language = models.StringField(
        label='Native language',
        choices=["English", "other"], widget=widgets.RadioSelectHorizontal
    )
    education = models.StringField(
        label="Completed highest level of education	",
        choices=EDUCATION_CHOICES,
        widget=widgets.RadioSelect,
    )
    
