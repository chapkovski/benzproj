from otree.api import Currency as c, currency_range
from ._builtin import Page as oTreePage, WaitPage
from .models import Constants
import logging
from img_desc.utils import get_url_for_image
from pprint import pprint
from json import JSONDecodeError
import json
logger = logging.getLogger("benzapp.start_pages")


class Page(oTreePage):
    instructions_path = "start/includes/instructions.html"
    instructions = False

    def get_context_data(self, **context):
        r = super().get_context_data(**context)
        r["instructions_google_doc"] = self.session.config.get("instructions_path")
        r["maxpages"] = self.participant._max_page_index
        r["page_index"] = self._index_in_pages
        r[
            "progress"
        ] = f"{int(self._index_in_pages / self.participant._max_page_index * 100):d}"
        r["instructions"] = self.instructions

        return r


class Consent(Page):
    pass


class Demographics(Page):
    def post(self):
        print(self.request.POST)
        raw_data = self.request.POST.get('survey_data')
        try:
            json_data= json.loads(raw_data)
            print(json_data)
            self.player.survey_data = json.dumps(json_data)
        except JSONDecodeError:
            logger.warning('No  demographic data')
        except Exception as e:
            logger.error(f"Error while saving demographic data: {e}")
        return super().post()



class Instructions(Page):
    pass


class _PracticePage(Page):
    instructions = True
    practice_id = None

    def is_displayed(self):
        pps = self.session.vars.get('user_settings',{}).get('practice_pages',{})
        if pps:
            curpage = pps.get(self.__class__.__name__, True)
            return curpage

        return True

    def js_vars(self):
        try:
            practice_settings = self.session.vars.get("practice_settings", {}).get(
                f"practice_{self.practice_id}"
            )
            img = practice_settings.get("image")
            if img:
                practice_settings["full_image_path"] = get_url_for_image(
                    self.player, f"practice/{img}"
                )

            return dict(settings=practice_settings)
        except Exception as e:
            print(e)
            logger.error(f"cant get settings for this practice page {self.practice_id}")
            return {}


class Practice1(_PracticePage):
    practice_id = 1


class Practice2(_PracticePage):
    practice_id = 2


class Practice3(_PracticePage):
    practice_id = 3


class Practice4(_PracticePage):
    practice_id = 4
    def js_vars(self):
        default_settings = super().js_vars().get("settings", {}).copy()

        if default_settings:
            right_answer = default_settings.get("right_answer")
            if right_answer:
                # let's convert the strings contained in each element of right_answer array to subarrays
                # so that we can use them in the template
                default_settings["right_answer"] =  [[item.strip() for item in element.split(';')] for element in right_answer]

        return dict(settings=default_settings)


class Practice5(_PracticePage):
    practice_id = 5


class Practice6(_PracticePage):
    practice_id = 6


class Practice7(_PracticePage):
    practice_id = 7


class EndOfIntro(Page):
    pass


page_sequence = [
    Consent,
    Demographics,
    Instructions,
    Practice1,
    Practice2,
    Practice3,
    Practice4,
    Practice5,
    Practice6,
    Practice7,
    EndOfIntro,
]
