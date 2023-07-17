from django.views.generic import View
from django.http import HttpResponse, JsonResponse
from otree.models import Session, Participant
from django.shortcuts import redirect, reverse
import pandas as pd
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
import json
from .models import Player, UserData, PRODUCER, INTERPRETER
import logging
from django.utils import timezone


RETURNED_STATUSES = ["RETURNED", "TIMED-OUT"]
STATUS_CHANGE = "submission.status.change"
logger = logging.getLogger("benzapp.views")


@method_decorator(csrf_exempt, name="dispatch")
class HookView(View):
    display_name = "Prolific hook"
    url_name = "prolific_hook"
    url_pattern = rf"prolific_hook"
    content_type = "application/json"

    def get(self, request, *args, **kwargs):
        return JsonResponse(dict(a="b"))

    def post(self, request, *args, **kwargs):
        print("---------")
        unicode_body = self.request.body.decode("utf-8")
        body = json.loads(unicode_body)
        logger.info("Got the following from prolific hook:")
        logger.info(body)
        print("---------")

        if (
            body.get("event_type") == STATUS_CHANGE
            and body.get("status") in RETURNED_STATUSES
        ):
            session_id = body.get("resource_id")
            participant_id = body.get("participant_id")
            try:
                participants = Participant.objects.filter(label=session_id)
                if participants.count() > 1:
                    logger.warning(
                        f"The strange thing is that we get more than one player with this prolific"
                        " session id {session_id}. We got {players.count()}. It can be a bug"
                    )
                if participants.exists():
                    msgs = []
                    for p in participants:
                        i = UserData.objects.filter(owner=p).update(
                            busy=False, owner=None
                        )
                        if i > 0:
                            msg = f"Player {p.code} released the slot. Prolific participant {participant_id} returned the study"
                        else:
                            msg = f"It seems that player {p.code} has no User Data attached (probably already released)"
                        logger.info(msg)
                        msgs.append(msg)

                    return JsonResponse(dict(message=msgs))
                else:
                    msg = f"Error: cant find player with the session id: {session_id}"
                    logger.error(msg)
                    return JsonResponse(dict(message=msg))
            except Exception as e:
                print(e)
                msg = "Something wrong with getting user"
                logger.error(msg)
                return JsonResponse(dict(message=msg))
        else:
            msg = "Thank you!"
            return JsonResponse(dict(message=msg))


class PandasExport(View):
    url_name = None

    def get(self, request, *args, **kwargs):
        params = dict(inner_role=PRODUCER)
        df = self.get_data(params)
        if df is not None and not df.empty:
            timestamp = timezone.now()
            curtime = timestamp.strftime("%m_%d_%Y_%H_%M_%S")
            csv_data = df.to_csv(index=False)
            response = HttpResponse(csv_data, content_type=self.content_type)
            filename = f"{self.url_name}_{curtime}.csv"
            response["Content-Disposition"] = f"attachment; filename={filename}"
            return response
        else:
            return redirect(reverse("ExportIndex"))


COMMON_FIELDS = [
    "participant__code",
    "inner_data",
    "round_number",
    "session__code",
    "batch",
    "start_decision_time",
    "end_decision_time",
    "decision_seconds",
    "current_data__id_in_group",
    "current_data__processed",
    "current_data__overwrite",
]


class ProducerExport(PandasExport):
    display_name = "Producer export"
    url_name = "producer_decisions"
    url_pattern = rf"producers"
    content_type = "text/csv"

    def get_data(self, params):
        main_dv = "producer_decision"
        suffix = "SENTENCE"
        events = Player.objects.filter(inner_role=PRODUCER).values(
            main_dv,
            *COMMON_FIELDS,
            "current_data__to_whom",
        )
        if not events.exists():
            return
        if events.exists():
            df = pd.DataFrame(data=events)
            df[main_dv] = df[main_dv].apply(lambda x: json.loads(x) if x else [])
            df["image"] = df["inner_data"].apply(
                lambda x: json.loads(x).get("image") if x else None
            )

            # Create new columns
            for i, row in df.iterrows():
                for inner_index, inner_list in enumerate(row[main_dv]):
                    for j, item in enumerate(inner_list):
                        df.at[i, f"{suffix}_{inner_index+1}_{j+1}"] = item

            # Drop the original column
            df = df.drop(columns=[main_dv, "inner_data"])
            return df


class InterperterExport(PandasExport):
    display_name = "Interpreter export"
    url_name = "interpreter_decisions"
    url_pattern = rf"interpreters"
    content_type = "text/csv"

    def get_data(self, params):
        main_dv = "interpreter_decision"
        suffix = "REWARD"
        events = Player.objects.filter(inner_role=INTERPRETER).values(
            main_dv, *COMMON_FIELDS
        )
        if not events.exists():
            return
        if events.exists():
            df = pd.DataFrame(data=events)
            df[main_dv] = df[main_dv].apply(lambda x: json.loads(x) if x else [])
            df["inner_data"] = df["inner_data"].apply(lambda x: json.loads(x))
            df["from_whom"] = df.inner_data.apply(
                lambda x: x.get("from_whom") if x else None
            )
            df["image"] = df.inner_data.apply(lambda x: x.get("image") if x else None)
            df["sentence_data"] = df.inner_data.apply(
                lambda x: x.get("sentence_data") if x else None
            )
            # Create new columns
            for i, row in df.iterrows():
                for inner_index, item in enumerate(row[main_dv]):
                    df.at[i, f"{suffix}_{inner_index+1}"] = item
                for inner_index, inner_list in enumerate(row["sentence_data"]):
                    for j, item in enumerate(inner_list):
                        df.at[i, f"SENTENCE_{inner_index+1}_{j+1}"] = item
            # Drop the original column
            df = df.drop(columns=[main_dv, "inner_data", "sentence_data"])
            return df
