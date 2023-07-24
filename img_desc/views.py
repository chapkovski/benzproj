from django.views.generic import View
from django.http import HttpResponse, JsonResponse
from otree.models import Session, Participant
from django.shortcuts import redirect, reverse
import pandas as pd
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
import json
from .models import Player, Batch, PRODUCER, INTERPRETER
import logging
from django.utils import timezone
from pprint import pprint

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
                        i = Batch.objects.filter(owner=p).update(busy=False, owner=None)
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
    "round_number",
    "session__code",
    "start_decision_time",
    "end_decision_time",
    "decision_seconds",
    "link__id_in_group",
    "link__batch",
    "link__processed",
    "link__partner_id",
    "link__condition",
    "link__image",
    "link__sentences",
    "link__rewards",
]
def expand_lists(df, col_name, prefix, level):
    # converting from json first
    df[col_name] = df[col_name].apply(
        lambda x: json.loads(x) if pd.notna(x) and x != "" else None
    )
    # First expansion: get each list in its own column

    df_new = df[col_name].apply(pd.Series)
    if level > 1:
        for i, col in enumerate(df_new):
            # Second expansion: get each element of the inner lists in its own column
            df_temp = df_new[col].apply(pd.Series)
            df_temp.columns = [f"{prefix}_{i+1}_{j+1}" for j in range(df_temp.shape[1])]
            df = pd.concat([df, df_temp], axis=1)
    else:
        df_new=df_new.add_prefix(f'{prefix}_')
        df = pd.concat([df, df_new], axis=1)
    return df


    


 

class DataExport(PandasExport):
    display_name = "Data export"
    url_name = "data_export"
    url_pattern = rf"data_export"
    content_type = "text/csv"

    def get_data(self, params):
        events = Player.objects.filter(link__isnull=False).values(
            "producer_decision",
            "interpreter_decision",
            *COMMON_FIELDS,
        )
        if not events.exists():
            return
        if events.exists():
            df = pd.DataFrame(data=events)
            df.columns = df.columns.str.replace("^link__", "", regex=True)
            df = expand_lists(df, "rewards", "reward", level=1)
            df = expand_lists(df, "sentences", "sentence", level=2)
            prefix = "reward_"
            cols_to_convert = df.filter(regex=f'^{prefix}').columns
            df[cols_to_convert] = df[cols_to_convert].astype('Int64')

            return df
