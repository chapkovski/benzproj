from otree.api import Currency as c, currency_range
from ._builtin import WaitPage
from start.pages import Page
from .models import Constants, PRODUCER, INTERPRETER
from django.shortcuts import redirect
import json
from pprint import pprint


class FaultyCatcher(Page):
    def is_displayed(self):
        return self.player.faulty

    def get(self):
        if self.player.faulty:
            return redirect(Constants.FALLBACK_URL)
        return super().get()


class Q(Page):
    instructions = True

    def is_displayed(self):
        return self.round_number <= self.session.vars["num_rounds"]

    def post(self):
        if self.player.inner_role == PRODUCER:
            field_name = "producer_decision"
        else:
            field_name = "interpreter_decision"
        raw_decisions = self.request.POST.get(field_name)
        if raw_decisions:
            decisions = json.loads(raw_decisions)
            if self.player.inner_role == PRODUCER:
                flatten_decisions = [list(i.values()) for i in decisions]
                self.player.producer_decision = json.dumps(flatten_decisions)
            if self.player.inner_role == INTERPRETER:
                flatten_decisions = [i.get('choice') for i in decisions]
                self.player.interpreter_decision = json.dumps(flatten_decisions)

        return super().post()

    def before_next_page(self):
        if self.player.inner_role == PRODUCER:
            self.player.update_next_batch()
        if self.round_number == self.session.vars['num_rounds']:
            self.player.mark_data_processed()

        return super().before_next_page()


class FinalForProlific(Page):
    def is_displayed(self):
        return (
            self.session.config.get("for_prolific")
            and self.round_number == self.session.vars["num_rounds"]
        )

    def get(self):
        if self.player.full_return_url:
            return redirect(self.player.full_return_url)
        FALLBACK_URL = "https://cnn.com"
        return redirect(FALLBACK_URL)


page_sequence = [FaultyCatcher, Q, FinalForProlific]
