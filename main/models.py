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
from django.forms.models import model_to_dict
from reading_xls.get_data import long_data
from otree.models import Session, Participant
import json
from pprint import pprint
from django.db import models as djmodels
import logging

PRODUCER = "P"
INTERPRETER = "I"
logger = logging.getLogger("benzapp.main.models")
author = "Philipp Chapkovski"

doc = """
Your app description
"""


class Constants(BaseConstants):
    name_in_url = "main"
    players_per_group = None
    num_rounds = 60


class Subsession(BaseSubsession):
    active_batch = models.IntegerField()

    def creating_session(self):
        self.active_batch = 1
        if self.round_number == 1:
            df = long_data("benz")

            assert (
                df.group_enumeration.max() <= Constants.num_rounds
            ), "PLEASE SET NUMBER OF ROUNDS IN OTREE HIGHER!"
            dbatches = df.to_dict(orient="records")
            raws = [
                dict(
                    session=self.session,
                    batch=i.get("Exp"),
                    item_nr=i.get("Item.Nr"),
                    condition=i.get("Condition"),
                    image=i.get("Item"),
                    round_number=i.get("group_enumeration"),
                    role=i.get("role"),
                    id_in_group=i.get("id"),
                    partner_id=i.get("partner_id"),
                    sentences=i.get("sentences"),
                )
                for i in dbatches
            ]
            raws = [Batch(**i) for i in raws]
            Batch.objects.bulk_create(raws)
            pprint(self.session.batches.all().count())

    def check_for_batch_completion(self):
        """
        Here we check if all participants users data marked as completed
        if yes we increase currrent active batch id by 1
        we also increase number of available slots by batch size so new prolific users can join
        """

        s = self
        session = s.session
        active_batch = s.active_batch
        logger.info(
            f"oTree session {session.code}. quick check if batch {active_batch} is completed"
        )
        q = s.users.filter(batch=s.active_batch, processed=False)
        logger.info(
            f"CURRENT ACTIVE BANCTHS!: {active_batch}; NON PROCESSED SLOTS{q.count()}"
        )
        if not q.exists():
            session.vars["active_batch"] = active_batch + 1
            Subsession.objects.filter(session=session).update(
                active_batch=active_batch + 1
            )
            if session.config.get("expand_slots", False):
                self.expand_slots()


class Group(BaseGroup):
    pass


class Batch(djmodels.Model):
    def __str__(self) -> str:
        if self.owner:
            return f"batch: {self.batch}; round: {self.round_number}; belongs to: {self.owner.code}"
        return f"batch: {self.batch}; round: {self.round_number}; doesnt belongs to anyone yet"

    session = djmodels.ForeignKey(
        to=Session,
        on_delete=djmodels.CASCADE,
        related_name="batches",
    )
    owner = djmodels.ForeignKey(
        to=Participant, on_delete=djmodels.CASCADE, related_name="infos", null=True
    )
    sentences = models.LongStringField()
    condition = models.StringField()
    item_nr = models.StringField()
    image = models.StringField()
    round_number = models.IntegerField()
    role = models.StringField()
    batch = models.IntegerField()
    id_in_group = models.IntegerField()
    partner_id = models.IntegerField()
    busy = models.BooleanField(initial=False)
    processed = models.BooleanField(initial=False)
    overwrite = models.BooleanField()


class Player(BasePlayer):
    inner_role = models.StringField()
    faulty = models.BooleanField(initial=False)
    link = djmodels.ForeignKey(
        to=Batch, on_delete=djmodels.CASCADE, related_name="players", null=True
    )

    def get_previous_batch(self):
        """
        Procedure notes:
        so, for Interpreter the sentences are taken from the previous batch.
        the procedure is the following: it looks for:
        batch=current_batch-1
        role=producer
        partner_id=self_id
        id=self.link.partner_id
        condition=condition
        """
        if self.inner_role == INTERPRETER:
            l = self.link
            if l.partner_id==0:
                return
            obj = self.session.batches.get(
                batch=self.subsession.active_batch - 1,
                role=PRODUCER,
                partner_id=l.id_in_group,
                id_in_group=l.partner_id,
                condition=l.condition,
            )
            pprint(model_to_dict(obj))
            return obj

    def start(self):
        if self.round_number == 1:
            # linking batch to participant, marking it busy

            active_batch = self.session.batches.filter(
                batch=self.subsession.active_batch,
            )
            try:
                free_user_id = (
                    active_batch.filter(busy=False, owner__isnull=True)
                    .first()
                    .id_in_group
                )
            except AttributeError as e:
                logger.error(
                    f"no more free slots for participant {self.participant.code}!!!"
                )
                # with all built-in mechanisms, it is unlikely that we will invite someone
                # without a slot for him available, but JIC:
                # in this case we mark him as faulty, and redirect back to prolific with a faulty code
                # so we can still pay him because it's definitely our fault that this would happen.
                self.faulty = True
                return
            free_user = active_batch.filter(busy=False, id_in_group=free_user_id)
            free_user.update(busy=True, owner=self.participant)

        self.link = self.participant.infos.get(round_number=self.round_number)

        self.inner_role = self.link.role
