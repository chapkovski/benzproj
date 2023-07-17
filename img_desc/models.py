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
from .utils import get_balance, increase_space
from otree.models import Session, Participant
import json
from pprint import pprint
from django.db import models as djmodels
from reading_xls.get_data import get_data
from django.db.models.signals import post_save
from django.dispatch import receiver
from .utils import get_study, STUBURL, get_completion_info
import logging
from .utils import get_url_for_image

logger = logging.getLogger("benzapp.models")

PRODUCER = "P"
INTERPRETER = "I"


author = "Your name here"

doc = """
Your app description
"""


class Constants(BaseConstants):
    name_in_url = "img_desc"
    players_per_group = None
    num_rounds = 4
    STUBURL = STUBURL
    PLACEMENT_ERR = "ERROR_BATCH_PLACEMENT"
    API_ERR = "API_ERROR"
    FALLBACK_URL = STUBURL + PLACEMENT_ERR
    API_ERR_URL = STUBURL + API_ERR
    INTERPRETER = INTERPRETER
    PRODUCER = PRODUCER


class Subsession(BaseSubsession):
    active_batch = models.IntegerField()
    # The following three fields are study-related (on prolific level). The specific participants
    # copy these values to avoid calling prolific api with each new user
    study_id = models.StringField()
    completion_code = models.StringField()
    full_return_url = models.StringField()

    @property
    def get_active_batch(self):
        return self.users.filter(batch=self.active_batch)

    def expand_slots(self):
        study_id = self.study_id
        max_users = self.session.vars.get("max_users", 0)
        batch_size = self.session.vars.get("batch_size", 0)

        if study_id:
            logger.info(
                f"trying to expand slots at study {study_id} for {batch_size} more users (max users {max_users}). oTree session {self.session.code}"
            )
            # just a safeguard to not expand further than a number of otree session slots
            max_users = min(
                self.session.vars.get("max_users", 0), self.session.num_participants
            )
            # there are some safeguards built in increase_space function not to expand further than max users
            # we can't do it here because to get the current number of prolific study slots we need to call api
            # and I want to keep all api calls separate from this code
            pprint(
                increase_space(
                    study_id=study_id, num_extra=batch_size, max_users=max_users
                )
            )
        else:
            logger.warning("No study id data is available! slot expansion failed")

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

    def creating_session(self):
        self.active_batch = 0
        if self.round_number == 1:
            self.session.vars["active_batch"] = 0
            excel_data = get_data("benz")

            self.session.vars["user_data"] = excel_data.get("data")
            self.session.vars["practice_settings"] = excel_data.get("practice_settings")

            data = self.session.vars["user_data"]
            rounds = set(data["round"].tolist())
            real_round_set = set(range(1, Constants.num_rounds + 1))

            assert (
                rounds.issubset(real_round_set) and 1 in rounds
            ), "The dataset contains more rounds than allowed by  current oTree settings"
            self.session.vars["num_rounds"] = len(rounds)
            self.session.vars["user_settings"] = excel_data.get("settings")
            self.session.vars["s3path"] = excel_data.get("settings").get("s3path")
            self.session.vars["extension"] = excel_data.get("settings").get("extension")
            self.session.vars["prefix"] = excel_data.get("settings").get("prefix")
            self.session.vars["suffixes"] = excel_data.get("settings").get("suffixes")
            allowed_values = excel_data.get("settings").get("allowed_values")
            allowed_values = [
                [item for item in sublist if item != ""] for sublist in allowed_values
            ]
            self.session.vars["allowed_values"] = allowed_values
            assert len(self.session.vars.get("suffixes", [])) == len(
                self.session.vars.get("allowed_values", [])
            ), "Number of provided fields should coincide with number of allowed values sets."

            self.session.vars["interpreter_choices"] = excel_data.get("settings").get(
                "interpreter_choices"
            )
            self.session.vars["interpreter_title"] = excel_data.get("settings").get(
                "interpreter_title"
            )

            df = self.session.vars["user_data"]
            first_round = df[df["round"] == 1]
            max_users = len(first_round)
            batch0 = first_round[first_round["batch"] == 0]
            batch_size = len(batch0)
            # TODO: let's guarantee that number of participants is divisible by batch size
            # TODO: we need to do a lot of checking while reading xls data actually.add()
            # TODO: right now we do this in a very naive way but all this checking should be moved
            # TODO: in a separate module
            # TODO: Please, please, please, move all credentials to secrets folder and gitignore it otherwise it's path to disaster
            if self.session.config.get("expand_slots"):
                assert (
                    max_users <= self.session.num_participants
                ), "Max users from the excel sheet should be equal or less than the number of participants"
            self.session.vars["max_users"] = max_users
            assert batch_size > 0, "Somemthing wrong with the batch size!"
            self.session.vars["batch_size"] = batch_size
            pprint(self.session.vars)
        df = self.session.vars["user_data"]
        df_filtered = df[df["round"] == self.round_number]
        data = df_filtered.to_dict(orient="records")
        userdata = [UserData(**i, subsession=self, session=self.session) for i in data]
        UserData.objects.bulk_create(userdata)


class Group(BaseGroup):
    pass


class UserData(djmodels.Model):
    def __str__(self) -> str:
        return f"batch: {self.batch}; round: {self.round}; belongs to: {self.owner}"

    subsession = djmodels.ForeignKey(
        to=Subsession, on_delete=djmodels.CASCADE, related_name="users"
    )
    session = djmodels.ForeignKey(
        to=Session, on_delete=djmodels.CASCADE, related_name="userdata", null=True
    )
    owner = djmodels.ForeignKey(
        to=Participant, on_delete=djmodels.CASCADE, related_name="userdata", null=True
    )
    data = models.LongStringField()
    round = models.IntegerField()
    to_whom = models.IntegerField()
    role = models.StringField()
    batch = models.IntegerField()
    id_in_group = models.IntegerField()
    busy = models.BooleanField(initial=False)
    processed = models.BooleanField(initial=False)
    overwrite = models.BooleanField()


class Player(BasePlayer):
    inner_role = models.StringField()
    inner_data = models.LongStringField()
    batch = models.IntegerField()
    faulty = models.BooleanField(initial=False)

    def unmark_busy(self):
        UserData.objects.filter(owner=self.participant).update(busy=False, owner=None)

    def mark_data_processed(self):
        UserData.objects.filter(owner=self.participant).update(processed=True)
        self.subsession.check_for_batch_completion()

    def role(self):
        return self.inner_role

    prolific_id = models.StringField()
    prol_study_id = models.StringField()
    prol_session_id = models.StringField()
    completion_code = models.StringField()
    full_return_url = models.StringField()
    producer_decision = models.LongStringField()
    interpreter_decision = models.LongStringField()

    def get_sentences(self):
        prefix = self.session.vars.get("prefix", "")
        suffixes = self.session.vars.get("suffixes")
        sentences = self.get_data().get("sentence_data")
        sentences = [sublist for sublist in sentences if "" not in sublist]
        res = []
        for sentence in sentences:
            expansion_list = [
                str(item) for pair in zip(sentence, suffixes) for item in pair
            ]
            if prefix:
                expansion_list.insert(0, prefix)
            full_sentence = " ".join(expansion_list)
            res.append(full_sentence)
        return res

    def get_data(self):
        return json.loads(self.inner_data)

    def get_image_url(self):
        data = self.get_data()
        image = data.get("image")
        return get_url_for_image(self, image)

    @property
    def link_to_data(self):
        return self.participant.userdata.filter(round=self.round_number).first()

    def update_next_batch(self):
        """
        1. we need to check if next batch is available? who know what what if this is the last one?
        we get next batch, the same round number
        each subsession gets all batches of the current round.
        2. We need to check if we need to write to it - what if overwrite is false?
        3. WE need to check if we have somethig to write? that is if role is P, and text is available
        (this one can actualy become a bit more complciated later if they start producing more than one sentence
        but let's not think aobut it at this stage)
        """
        ## We only update next batch if this player is producer
        if self.inner_role == PRODUCER:
            to_whom_id = self.link_to_data.to_whom
            next_batch = self.subsession.users.filter(
                batch=self.subsession.active_batch + 1
            )
            if next_batch.exists() and to_whom_id and to_whom_id > 0:
                to_whoms = next_batch.filter(id_in_group=to_whom_id)
                if to_whoms.exists():
                    to_whom = to_whoms.first()
                else:
                    return
                if not to_whom.overwrite:
                    current_data = json.loads(self.link_to_data.data)
                    current_data["sentence_data"] = json.loads(self.producer_decision)
                    to_whom.data = json.dumps(current_data)
                    to_whom.save()

        pass

    def start(self):
        """
        This is ran once when a player starts each new round
        """
        logger.info(f"IM IN START {self.round_number}")
        if self.round_number == 1:
            # here we get ALL rounds for a specific id_in_group
            active_batch = UserData.objects.filter(
                batch=self.subsession.active_batch, session=self.session
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

            if self.session.config.get("for_prolific"):
                vars = self.participant.vars
                print("VARS", vars)
                prol_study_id = vars.get("study_id")
                prol_session_id = vars.get("session_id")
                # we want to set this study id, completion code and return code on subsession level only once
                # for the first person who has this study id.
                # The rest of the group will copy it from there if they have the same study id
                # that way we'll save some calls to prolific api
                ERR_COMPLETION_INFO = dict(
                    completion_code=Constants.API_ERR,
                    full_return_url=Constants.API_ERR_URL,
                )
                if prol_study_id:
                    # if it is not set on subsession level, let's set it:
                    if not self.subsession.study_id:
                        completion_info = get_completion_info(prol_study_id)
                        if completion_info:
                            Subsession.objects.filter(session=self.session).update(
                                study_id=prol_study_id, **completion_info
                            )
                    # if the participation has the same study id as the subsession-level study id,
                    # we just copy it from there
                    if prol_study_id == self.subsession.study_id:
                        completion_info = dict(
                            completion_code=self.subsession.completion_code,
                            full_return_url=self.subsession.full_return_url,
                        )
                    # if a participant has a different study id (unlikely sceneario but what if)
                    # we set his individual completion code
                    else:
                        completion_info = get_completion_info(prol_study_id)
                        # if we fail to get completion info (mostly for API err reasons, we set it still
                        # to the API errr code to deal with the submsission later)
                        if not completion_info:
                            completion_info = ERR_COMPLETION_INFO
                else:
                    completion_info = ERR_COMPLETION_INFO
                for_update = dict(
                    prolific_id=vars.get("prolific_id"),
                    prol_study_id=prol_study_id,
                    prol_session_id=prol_session_id,
                    **completion_info,
                )
                try:
                    if not prol_study_id:
                        raise Exception("Study_id from prolific is not available")
                    if not vars.get("prolific_id"):
                        raise Exception("prolific_id from prolific is not available")
                    if not vars.get("session_id"):
                        raise Exception("session_id from prolific is not available")

                except Exception as E:
                    logger.error("Trouble getting prolific data")
                    logger.error(str(E))

                finally:
                    # whatever we have here we update with all this info the
                    # entire set of players set belonging to the current participant
                    Player.objects.filter(participant=self.participant).update(
                        **for_update
                    )
                    if prol_session_id:
                        self.participant.label = prol_session_id

        link_update = dict(
            batch=self.link_to_data.batch,
            inner_role=self.link_to_data.role,
            inner_data=self.link_to_data.data,
        )
        Player.objects.filter(id=self.id).update(**link_update)
