import random
from otree.api import *

doc = """
Experiment 7 — Threshold Public Goods card game (whole-class, anonymous).

Each player holds 4 cards: 2 red, 2 black. Each round they play EXACTLY 2
cards onto a common stack and keep the other 2. The choice is the COMPOSITION
of the two played cards (0, 1, or 2 of them red). Earnings depend on red cards:

  earnings = $6 * (red cards you KEPT)
           + $1 * (total red cards in the stack, across everyone)

red_contributed = number of red cards played (0, 1, or 2).
red kept = 2 - red_contributed.

Phases:
  Rounds 1-4   : Standard public good, no risk.
  Rounds 5-8   : 40% wipeout risk. If total red contributed >= THRESHOLD_N the
                 round is SAFE; otherwise one class-wide RNG (1-10) is drawn and
                 a value of 1-4 wipes everyone's earnings to $0 for the round.
  Rounds 9-12  : Same mechanic, 90% risk (RNG 1-9 wipes out).

Group: the WHOLE class is one group. Players are anonymous; no one learns who
made which decision. Only aggregate counts are shown.
"""

# ── Phase / payoff parameters ─────────────────────────────────────────────────
STANDARD_ROUNDS = 2   # rounds 1-4
RISK40_ROUNDS   = 2   # rounds 5-8
RISK90_ROUNDS   = 2   # rounds 9-12

DOLLARS_PER_RED_KEPT = 6    # $6 per red card you keep
DOLLARS_PER_RED_IN_STACK = 1  # $1 per red card collected in the stack

CARDS_PLAYED = 2   # each player plays exactly 2 of their 4 cards
RED_CARDS_HELD = 2  # each player starts with 2 red, 2 black

# Threshold: minimum total RED cards in the stack to make a risky round safe.
# Set this to whatever fits your class size / design.
THRESHOLD_N = 4

# Risk roll: RNG draws 1..10. A draw <= WIPEOUT_MAX wipes out the round.
RISK40_WIPEOUT_MAX = 8   # rounds 5-8:  draws 1,2,3,4  -> wipeout (40%)
RISK90_WIPEOUT_MAX = 9   # rounds 9-12: draws 1..9     -> wipeout (90%)


# ── Constants ─────────────────────────────────────────────────────────────────
class C(BaseConstants):
    NAME_IN_URL = 'public_goods'
    PLAYERS_PER_GROUP = None   # whole class in a single group
    NUM_ROUNDS = STANDARD_ROUNDS + RISK40_ROUNDS + RISK90_ROUNDS   # 12


# ── Models ────────────────────────────────────────────────────────────────────
class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    total_red_in_stack = models.IntegerField(initial=0)
    threshold_met = models.BooleanField(initial=False)
    risk_roll = models.IntegerField(initial=0)        # 0 = no roll happened
    wiped_out = models.BooleanField(initial=False)


class Player(BasePlayer):
    name_entry = models.StringField(label="Please enter your name:")
    # ── Lottery choices (Part 1) ──────────────────────────────────────────
    lottery1 = models.IntegerField(
        label="How many tickets do you buy?",
        choices=[[1, 'I buy 1 ticket'], [2, 'I buy 2 tickets'],
                 [3, 'I buy 3 tickets'], [4, 'I buy 4 tickets']],
    )
    lottery2 = models.IntegerField(
        label="How many tickets do you buy?",
        choices=[[1, 'I buy 1 ticket'], [2, 'I buy 2 tickets'],
                 [3, 'I buy 3 tickets'], [4, 'I buy 4 tickets']],
    )
    # Each round the player plays EXACTLY 2 of their 4 cards (2 red, 2 black).
    # The choice is the COMPOSITION of the 2 played cards, captured as how many
    # of them are red:
    #   0 -> played 2 black  (kept 2 red)
    #   1 -> played 1 red + 1 black (kept 1 red)
    #   2 -> played 2 red    (kept 0 red)
    # red kept = RED_CARDS_HELD - red_contributed  (drives the player's own $6/card).
    red_contributed = models.IntegerField(
        label="Which two cards will you play onto the stack?",
        choices=[[0, 'Play 2 black (keep both red)'],
                 [1, 'Play 1 red + 1 black (keep 1 red)'],
                 [2, 'Play 2 red (keep no red)']],
    )
    period_earnings = models.IntegerField(initial=0)


# ── Helpers ───────────────────────────────────────────────────────────────────
def phase_of(round_number: int) -> int:
    """1 = standard, 2 = 40% risk, 3 = 90% risk."""
    if round_number <= STANDARD_ROUNDS:
        return 1
    if round_number <= STANDARD_ROUNDS + RISK40_ROUNDS:
        return 2
    return 3


def is_risky(round_number: int) -> bool:
    return phase_of(round_number) in (2, 3)


def wipeout_threshold(round_number: int) -> int:
    """The max RNG value (out of 10) that triggers a wipeout this round."""
    if phase_of(round_number) == 2:
        return RISK40_WIPEOUT_MAX
    if phase_of(round_number) == 3:
        return RISK90_WIPEOUT_MAX
    return 0


# ── Payoff calculation (runs once for the whole group) ────────────────────────
def set_payoffs(group: Group):
    players = group.get_players()
    rn = group.round_number

    # Each player contributes p.red_contributed red cards to the stack.
    total_red = sum(p.red_contributed for p in players)
    group.total_red_in_stack = total_red

    # Provisional earnings (before any wipeout):
    #   $6 per red KEPT + $1 per red in the whole stack.
    for p in players:
        red_kept = RED_CARDS_HELD - p.red_contributed
        p.period_earnings = (
            DOLLARS_PER_RED_KEPT * red_kept
            + DOLLARS_PER_RED_IN_STACK * total_red
        )

    # Risk resolution for rounds 5-12.
    if is_risky(rn):
        group.threshold_met = (total_red >= THRESHOLD_N)
        if group.threshold_met:
            # Threshold reached -> the round is completely safe.
            group.wiped_out = False
            group.risk_roll = 0
        else:
            # One class-wide draw decides the fate of everyone.
            roll = random.randint(1, 10)
            group.risk_roll = roll
            group.wiped_out = (roll <= wipeout_threshold(rn))
            if group.wiped_out:
                for p in players:
                    p.period_earnings = 0
    else:
        group.threshold_met = False
        group.wiped_out = False
        group.risk_roll = 0

    # Record payoff (oTree accumulates player.payoff into participant.payoff).
    for p in players:
        p.payoff = p.period_earnings


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


class Lottery1(Page):
    form_model = 'player'
    form_fields = ['lottery1']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def error_message(player: Player, values):
        if values.get('lottery1') not in (1, 2, 3, 4):
            return 'Please choose how many tickets you would buy.'


class Lottery2(Page):
    form_model = 'player'
    form_fields = ['lottery2']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def error_message(player: Player, values):
        if values.get('lottery2') not in (1, 2, 3, 4):
            return 'Please choose how many tickets you would buy.'


class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            threshold_n=THRESHOLD_N,
            dollars_per_red_kept=DOLLARS_PER_RED_KEPT,
        )


class PhaseChange(Page):
    """Shown before round 5 (40% risk begins) and round 9 (90% risk begins)."""

    @staticmethod
    def is_displayed(player: Player):
        rn = player.round_number
        return rn == STANDARD_ROUNDS + 1 or rn == STANDARD_ROUNDS + RISK40_ROUNDS + 1

    @staticmethod
    def vars_for_template(player: Player):
        rn = player.round_number
        ph = phase_of(rn)
        if ph == 2:
            risk_pct = RISK40_WIPEOUT_MAX * 10
        else:
            risk_pct = RISK90_WIPEOUT_MAX * 10
        return dict(
            phase=ph,
            risk_pct=risk_pct,
            threshold_n=THRESHOLD_N,
            start_round=rn,
        )


class Decision(Page):
    form_model = 'player'
    form_fields = ['red_contributed']

    @staticmethod
    def vars_for_template(player: Player):
        rn = player.round_number
        ph = phase_of(rn)
        risky = is_risky(rn)
        risk_pct = wipeout_threshold(rn) * 10
        return dict(
            phase=ph,
            risky=risky,
            risk_pct=risk_pct,
            threshold_n=THRESHOLD_N,
            dollars_per_red_kept=DOLLARS_PER_RED_KEPT,
        )

    @staticmethod
    def error_message(player: Player, values):
        if values.get('red_contributed') not in (0, 1, 2):
            return 'Please choose which two cards to play.'


class ResultsWaitPage(WaitPage):
    wait_for_all_groups = False
    after_all_players_arrive = 'set_payoffs'
    title_text = 'Waiting for the rest of the class…'
    body_text  = 'Please wait until everyone has played their cards.'

class RiskReveal(Page):
    """Suspense screen: only on risky rounds where the threshold was missed."""

    @staticmethod
    def is_displayed(player: Player):
        g = player.group
        return is_risky(player.round_number) and not g.threshold_met

    @staticmethod
    def vars_for_template(player: Player):
        g = player.group
        rn = player.round_number
        return dict(
            total_red_in_stack=g.total_red_in_stack,
            threshold_n=THRESHOLD_N,
            risk_pct=wipeout_threshold(rn) * 10,
            wipeout_max=wipeout_threshold(rn),   # roll <= this = wipeout
            risk_roll=g.risk_roll,  # the already-decided result
            wiped_out=g.wiped_out,
            wiped_out_js='true' if g.wiped_out else 'false',
        )


class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        rn = player.round_number
        ph = phase_of(rn)
        cum = sum(p.period_earnings for p in player.in_all_rounds())
        return dict(
            phase=ph,
            risky=is_risky(rn),
            red_kept=RED_CARDS_HELD - player.red_contributed,
            red_contributed=player.red_contributed,
            total_red_in_stack=group.total_red_in_stack,
            threshold_n=THRESHOLD_N,
            threshold_met=group.threshold_met,
            risk_roll=group.risk_roll,
            wiped_out=group.wiped_out,
            risk_pct=wipeout_threshold(rn) * 10,
            period_earnings=player.period_earnings,
            cumulative_earnings=cum,
            is_last=(rn == C.NUM_ROUNDS),
        )


class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        rows = []
        for p in player.in_all_rounds():
            g = p.group
            rows.append(dict(
                round=p.round_number,
                phase=phase_of(p.round_number),
                red_kept=RED_CARDS_HELD - p.red_contributed,
                red_contributed=p.red_contributed,
                total_red_in_stack=g.total_red_in_stack,
                threshold_met=g.threshold_met,
                wiped_out=g.wiped_out,
                risk_roll=g.risk_roll,
                earnings=p.period_earnings,
            ))
        r1 = player.in_round(1)
        total = sum(p.period_earnings for p in player.in_all_rounds())
        return dict(
            period_data=rows,
            total_earnings=total,
            lottery1=r1.lottery1,
            lottery2=r1.lottery2,
        )


page_sequence = [
    EnterName,
    Lottery1,
    Lottery2,
    Introduction,
    PhaseChange,
    Decision,
    ResultsWaitPage,
    RiskReveal,
    Results,
    FinalResults,
]
