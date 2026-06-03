import random
from otree.api import *

doc = """
Prisoner's Dilemma card game (Experiment 3).

Each player chooses a Red card (defect) or Black card (cooperate).
  Red  → you gain X, your partner gains nothing from your choice
  Black → you gain nothing, your partner gains Y

Payoff structure (from choices):
  R, R → (X,   X)
  R, B → (X+Y, 0)
  B, R → (0,   X+Y)
  B, B → (Y,   Y)

Rounds 1–5  : Low  stakes  (X=2, Y=3  →  R/R=$2/$2, B/B=$3/$3)
Rounds 6–10 : High stakes  (X=4, Y=6  →  R/R=$4/$4, B/B=$6/$6)

Matching: FIXED partner by default (same pair all 10 rounds).
          Swap to RANDOM matching by toggling the two blocks in creating_session().
"""

# ── Payoff parameters ────────────────────────────────────────────────────────
LOW_ROUNDS  = 2
HIGH_ROUNDS = 2

# Low-stakes payoff table  {(my_choice, partner_choice): (my_earnings, partner_earnings)}
PAYOFF_LOW = {
    ('R', 'R'): (2, 2),
    ('R', 'B'): (5, 0),
    ('B', 'R'): (0, 5),
    ('B', 'B'): (3, 3),
}

# High-stakes payoff table (stakes doubled)
PAYOFF_HIGH = {
    ('R', 'R'): (2,  2),
    ('R', 'B'): (10, 0),
    ('B', 'R'): (0,  10),
    ('B', 'B'): (8,  8),
}


# ── Constants ────────────────────────────────────────────────────────────────
class C(BaseConstants):
    NAME_IN_URL = 'prisoners_dilemma'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = LOW_ROUNDS + HIGH_ROUNDS   # 10


# ── Models ───────────────────────────────────────────────────────────────────
class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    name_entry = models.StringField(label="Please enter your name:")
    choice = models.StringField(
        choices=[['R', 'Red'], ['B', 'Black']],
        label='Your card choice',
    )
    period_earnings = models.IntegerField(initial=0)


# ── Session setup / matching ──────────────────────────────────────────────────
def creating_session(subsession: Subsession):
    # ── FIXED PARTNER MATCHING (active) ─────────────────────────────────────
    # Players are paired randomly once in round 1 and keep the same partner
    # for all 10 rounds.
    #if subsession.round_number == 1:
    #    subsession.group_randomly()
    #else:
    #    subsession.group_like_round(1)

    # ── RANDOM MATCHING (comment out the block above and uncomment below) ────
    # A fresh random pairing is drawn every round.
    subsession.group_randomly()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _is_low_round(round_number: int) -> bool:
    return round_number <= LOW_ROUNDS


def _payoff_table(round_number: int) -> dict:
    return PAYOFF_LOW if _is_low_round(round_number) else PAYOFF_HIGH


def set_payoffs(group: Group):
    p1, p2 = group.get_players()
    table = _payoff_table(group.round_number)
    key = (p1.choice, p2.choice)
    p1.period_earnings, p2.period_earnings = table[key]
    # oTree accumulates player.payoff across rounds into participant.payoff
    p1.payoff = p1.period_earnings
    p2.payoff = p2.period_earnings


# ── Pages ─────────────────────────────────────────────────────────────────────
class EnterName(Page):
    form_model = 'player'
    form_fields = ['name_entry']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.participant.full_name = player.name_entry


class Introduction(Page):
    """Full rules — shown once at the very start."""

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1


class PhaseChange(Page):
    """One-screen transition when moving from Low to High payoffs (round 6)."""

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == LOW_ROUNDS + 1

    @staticmethod
    def vars_for_template(player: Player):
        pt = PAYOFF_HIGH
        return dict(
            rr=pt[('R', 'R')], rb=pt[('R', 'B')],
            br=pt[('B', 'R')], bb=pt[('B', 'B')],
        )


class Decision(Page):
    form_model = 'player'
    form_fields = ['choice']

    @staticmethod
    def vars_for_template(player: Player):
        rn = player.round_number
        pt = _payoff_table(rn)
        low = _is_low_round(rn)
        partner = player.get_others_in_group()[0]
        return dict(
            is_low=low,
            phase=1 if low else 2,
            partner_name=partner.participant.full_name,
            rr=pt[('R', 'R')], rb=pt[('R', 'B')],
            br=pt[('B', 'R')], bb=pt[('B', 'B')],
        )

    @staticmethod
    def error_message(player: Player, values):
        if values.get('choice') not in ('R', 'B'):
            return 'Please select a card before continuing.'


class ResultsWaitPage(WaitPage):
    after_all_players_arrive = 'set_payoffs'
    title_text = 'Waiting for your partner…'
    body_text  = 'Please wait while your partner makes their choice.'


class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        partner   = player.get_others_in_group()[0]
        all_prev  = player.in_all_rounds()
        cum       = sum(p.period_earnings for p in all_prev)
        rn        = player.round_number
        low       = _is_low_round(rn)
        return dict(
            my_choice=player.choice,
            partner_choice=partner.choice,
            partner_name=partner.participant.full_name,
            period_earnings=player.period_earnings,
            cumulative_earnings=cum,
            is_low=low,
            phase=1 if low else 2,
            phase_change_next=(rn == LOW_ROUNDS),  # round 5 → 6 transition
            is_last=(rn == C.NUM_ROUNDS),
        )


class FinalResults(Page):
    """Earnings record — shown only after the last round."""

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        rows = []
        for p in player.in_all_rounds():
            partner = p.get_others_in_group()[0]
            rows.append(dict(
                round=p.round_number,
                phase='Low' if _is_low_round(p.round_number) else 'High',
                my_choice=p.choice,
                partner_choice=partner.choice,
                partner_name=partner.participant.full_name,
                earnings=p.period_earnings,
            ))
        total = sum(p.period_earnings for p in player.in_all_rounds())
        return dict(period_data=rows, total_earnings=total)


page_sequence = [
    EnterName,
    Introduction,
    PhaseChange,
    Decision,
    ResultsWaitPage,
    Results,
    FinalResults,
]
