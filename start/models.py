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
from reading_xls import get_data
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
    def creating_session(self):
        if self.round_number==1:
            self.session.vars['consent']=get_data.read_doc()


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    survey_data = models.LongStringField()

    def start(self):
        if self.round_number == 1:
            if self.session.config.get("for_prolific"):
                vars = self.participant.vars
                prol_session_id = vars.get("session_id")
                if prol_session_id:
                    self.participant.label = prol_session_id

