from django.views.generic import View
from django.http import HttpResponse, JsonResponse
from otree.models import Session, Participant
from django.shortcuts import redirect, reverse
import pandas as pd
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
import json
from .models import Player, UserData
import logging

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
                        i=UserData.objects.filter(owner=p).update(busy=False, owner=None)         
                        if i>0:
                            msg = f"Player {p.code} released the slot. Prolific participant {participant_id} returned the study"
                        else:
                            msg=f'It seems that player {p.code} has no User Data attached (probably already released)'
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
