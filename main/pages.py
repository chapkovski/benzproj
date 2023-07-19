from otree.api import Currency as c, currency_range
from ._builtin import Page, WaitPage
from .models import Constants
from img_desc.pages import Page
from pprint import pprint


class MyPage(Page):
    def vars_for_template(self):
        pass
        pprint(self.player.get_previous_batch())
        
    # def before_next_page(self):
    #     if self.player.inner_role == PRODUCER:
    #         self.player.update_batch()
    #     if self.round_number == self.session.vars["num_rounds"]:
    #         self.player.mark_data_processed()

 




 


page_sequence = [MyPage, ]
