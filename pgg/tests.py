import random
from otree.api import Bot
import pgg as app

class PlayerBot(Bot):
    def play_round(self):
        # Round 1 only:
        if self.round_number == 1:
            yield app.Instructions

            yield app.Lottery,  dict(
                lottery_choice=random.randint(1, 4)
            )
            yield app.Lottery2, dict(
                lottery2_choice=random.randint(1, 4)
            )
            yield app.Lottery3, dict(
                lottery3_choice=random.randint(1, 4)
            )

            # PGGHInstructions only on round 1
            yield app.PGGHInstructions

        # PGGLInstructions only on the "round change" round
        if self.round_number == app.C.ROUND_CHANGE:
            yield app.PGGLInstructions

        # Every round: Contribution + beliefs/expectations
        yield app.Contribution, {
            'contribution':         random.randint(0, app.C.PGG_ENDOWMENT),
            'personal_belief_p2':   random.randint(0, app.C.PGG_ENDOWMENT),
            'personal_belief_p3':   random.randint(0, app.C.PGG_ENDOWMENT),
            'personal_belief_p4':   random.randint(0, app.C.PGG_ENDOWMENT),
            'empirical_exp_p2':     random.randint(0, app.C.PGG_ENDOWMENT),
            'empirical_exp_p3':     random.randint(0, app.C.PGG_ENDOWMENT),
            'empirical_exp_p4':     random.randint(0, app.C.PGG_ENDOWMENT),
            'normative_exp_p2':     random.randint(0, app.C.PGG_ENDOWMENT),
            'normative_exp_p3':     random.randint(0, app.C.PGG_ENDOWMENT),
            'normative_exp_p4':     random.randint(0, app.C.PGG_ENDOWMENT),
        }

        # Results
        yield app.Results

        # Final selection only in the last round:
        if self.round_number == app.C.NUM_ROUNDS:
            #yield app.SectionSelectionWaitPage
            yield app.FinalResults
