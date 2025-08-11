from otree.api import *
import random

doc = """
Your app description
"""


class C(BaseConstants):
    NAME_IN_URL       = 'pgg'
    PLAYERS_PER_GROUP = 4
    NUM_ROUNDS        = 10
    PGG_ENDOWMENT     = cu(300)
    THRESHOLD         = cu(600)
    HIGH_PROB         = 0.9
    LOW_PROB          = 0.6
    LOT_ENDOWMENT     = cu(400)  # Sec 1 & 3: 400 pts = €4
    LOT2_ENDOWMENT    = cu(600)  # Sec 2: 600 pts = €6
    ROUND_CHANGE      = 6
    MIN_WAIT = 10


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    total_contributions = models.CurrencyField()
    disaster_roll       = models.IntegerField(blank=True, null=True)
    disaster_occurred   = models.BooleanField(blank=True, null=True)


class Player(BasePlayer):
    # PGG
    endowment        = models.CurrencyField()
    contribution     = models.CurrencyField(
        min=0, max=C.PGG_ENDOWMENT,
        label=""
    )
    amount_kept      = models.CurrencyField()
    # NOTE: You had both final_payoff (FloatField) and final_payment (CurrencyField).
    #       We're keeping only final_payment here.
    final_payment    = models.CurrencyField()

    # ---- PERSONAL BELIEF (3 cells) ----
    personal_belief_p2 = models.CurrencyField(
        min=0, max=C.PGG_ENDOWMENT,
        label="", doc="Estimate for Participant 2"
    )
    personal_belief_p3 = models.CurrencyField(
        min=0, max=C.PGG_ENDOWMENT,
        label="", doc="Estimate for Participant 3"
    )
    personal_belief_p4 = models.CurrencyField(
        min=0, max=C.PGG_ENDOWMENT,
        label="", doc="Estimate for Participant 4"
    )

    # ---- EMPIRICAL EXPECTATION (3 cells) ----
    empirical_exp_p2 = models.CurrencyField(
        min=0, max=C.PGG_ENDOWMENT,
        label="", doc="Empirical for Participant 2"
    )
    empirical_exp_p3 = models.CurrencyField(
        min=0, max=C.PGG_ENDOWMENT,
        label="", doc="Empirical for Participant 3"
    )
    empirical_exp_p4 = models.CurrencyField(
        min=0, max=C.PGG_ENDOWMENT,
        label="", doc="Empirical for Participant 4"
    )

    # ---- NORMATIVE EXPECTATION (3 cells) ----
    normative_exp_p2 = models.CurrencyField(
        min=0, max=C.PGG_ENDOWMENT,
        label="", doc="Normative for Participant 2"
    )
    normative_exp_p3 = models.CurrencyField(
        min=0, max=C.PGG_ENDOWMENT,
        label="", doc="Normative for Participant 3"
    )
    normative_exp_p4 = models.CurrencyField(
        min=0, max=C.PGG_ENDOWMENT,
        label="", doc="Normative for Participant 4"
    )

    # Section 1 lottery
    lottery_choice   = models.IntegerField(
        choices=[[1,'Buy 1'],[2,'Buy 2'],[3,'Buy 3'],[4,'Buy 4']],
        label="(Sec 1) How many of the 4 tickets?"
    )
    lottery_draw     = models.IntegerField(blank=True, null=True)
    lottery_payoff   = models.CurrencyField(blank=True, null=True)

    # Section 2 lottery
    lottery2_choice  = models.IntegerField(
        choices=[[1,'Buy 1'],[2,'Buy 2'],[3,'Buy 3'],[4,'Buy 4']],
        label="(Sec 2) How many of the 4 tickets?"
    )
    lottery2_draw    = models.IntegerField(blank=True, null=True)
    lottery2_payoff  = models.CurrencyField(blank=True, null=True)

    # Section 3 lottery
    lottery3_choice  = models.IntegerField(
        choices=[[1,'Buy 1'],[2,'Buy 2'],[3,'Buy 3'],[4,'Buy 4']],
        label="(Sec 3) How many of the 4 tickets?"
    )
    lottery3_draw    = models.IntegerField(blank=True, null=True)
    lottery3_payoff  = models.CurrencyField(blank=True, null=True)

    # --- store the randomly-selected stuff ---
    selected_section        = models.StringField()
    # for lotteries
    selected_lottery_choice = models.IntegerField(blank=True, null=True)
    selected_lottery_draw   = models.IntegerField(blank=True, null=True)
    selected_lottery_payoff = models.CurrencyField(blank=True, null=True)
    # for PGG
    selected_pgg_round        = models.IntegerField(blank=True, null=True)
    selected_pgg_contribution = models.CurrencyField(blank=True, null=True)
    selected_pgg_payoff       = models.CurrencyField(blank=True, null=True)
    # minimum time to remain on instruction page
    passed_timer = models.BooleanField(initial=False)


def creating_session(subsession):
    subsession.group_randomly()


def set_payoffs(group: Group):
    players       = group.get_players()
    contributions = [p.contribution for p in players]
    group.total_contributions = sum(contributions)

    for p in players:
        p.amount_kept = C.PGG_ENDOWMENT - p.contribution

    if group.total_contributions >= C.THRESHOLD:
        for p in players:
            p.payoff = p.amount_kept
        group.disaster_roll     = None
        group.disaster_occurred = False
    else:
        prob = C.HIGH_PROB if group.round_number <= C.ROUND_CHANGE - 1 else C.LOW_PROB
        roll = random.randint(1, 10)
        group.disaster_roll     = roll
        group.disaster_occurred = (roll <= int(prob * 10))
        for p in players:
            p.payoff = 0 if group.disaster_occurred else p.amount_kept

    for p in players:
        cs = p.participant.vars.get('pgg_contributions', [])
        ps = p.participant.vars.get('pgg_payoffs', [])
        cs.append(p.contribution)
        ps.append(p.payoff)
        p.participant.vars['pgg_contributions'] = cs
        p.participant.vars['pgg_payoffs']       = ps

# ----- Section 1 (base 400) -----
def section1_delta(choice: int, draw: int):
    # +100 for sure with 4; otherwise +{150,200,300} if draw <= choice else 0
    if choice == 4:
        return cu(100)
    pos = {3: cu(150), 2: cu(200), 1: cu(300)}
    return pos[choice] if draw <= choice else cu(0)

# ----- Section 2 (base 600) -----
def section2_delta(choice: int, draw: int):
    # Always a loss or 0:
    # 4 -> -100 always
    # 3 -> -150 if draw<=3 else 0
    # 2 -> -250 if draw<=2 else 0
    # 1 -> -400 if draw==1 else 0
    if choice == 4:
        return cu(-100)
    loss = {3: cu(-150), 2: cu(-250), 1: cu(-400)}
    return loss[choice] if draw <= choice else cu(0)

# ----- Section 3 (base 400) -----
def section3_delta(choice: int, draw: int):
    # 4 -> +100 always
    # 3 -> +200 if draw<=3 else -100
    # 2 -> +300 if draw<=2 else -200
    # 1 -> +500 if draw==1 else -300
    if choice == 4:
        return cu(100)
    pos = {3: cu(200), 2: cu(300), 1: cu(500)}
    neg = {3: cu(-100), 2: cu(-200), 1: cu(-300)}
    return pos[choice] if draw <= choice else neg[choice]

# ------------------------
# Reusable TimedPage base
# ------------------------
class TimedPage(Page):
    """Base page with a minimum time requirement."""

    @staticmethod
    def min_wait(player: Player) -> int:
        return C.MIN_WAIT

    @staticmethod
    def js_vars(player: Player):
        return dict(min_wait=TimedPage.min_wait(player))

    @staticmethod
    def _arrive_key(player: Player) -> str:
        part = player.participant
        page_id = f'{part._current_app_name}.{part._current_page_name}'
        return f'arrive_{page_id}'

    @staticmethod
    def vars_for_template(player: Player):
        import time
        part = player.participant
        key = TimedPage._arrive_key(player)
        if key not in part.vars:
            part.vars[key] = time.time()
        return {}

    @staticmethod
    def error_message(player: Player, values):
        import time
        part = player.participant
        key = TimedPage._arrive_key(player)
        arrived = part.vars.get(key, time.time())
        elapsed = time.time() - arrived
        mw = TimedPage.min_wait(player)
        if elapsed < mw:
            remaining = int(mw - elapsed)
            return f'Please spend at least {mw} seconds on this page. {remaining}s remaining.'

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        part = player.participant
        key = TimedPage._arrive_key(player)
        part.vars.pop(key, None)

# PAGES
class Instructions(TimedPage):
    form_model = 'player'
    form_fields = ['passed_timer']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1


class Lottery(Page):
    form_model  = 'player'
    form_fields = ['lottery_choice']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        draw = random.randint(1, 4)
        player.lottery_draw   = draw
        delta                 = section1_delta(player.lottery_choice, draw)
        player.lottery_payoff = C.LOT_ENDOWMENT + delta  # 400 base
        pvars = player.participant.vars
        pvars['section1_choice'] = player.lottery_choice
        pvars['section1_draw']   = draw
        pvars['section1_payoff'] = player.lottery_payoff


class Lottery2(Page):
    form_model  = 'player'
    form_fields = ['lottery2_choice']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        draw = random.randint(1, 4)
        player.lottery2_draw   = draw
        delta                  = section2_delta(player.lottery2_choice, draw)
        player.lottery2_payoff = C.LOT2_ENDOWMENT + delta  # 600 base
        pvars = player.participant.vars
        pvars['section2_choice'] = player.lottery2_choice
        pvars['section2_draw']   = draw
        pvars['section2_payoff'] = player.lottery2_payoff


class Lottery3(Page):
    form_model  = 'player'
    form_fields = ['lottery3_choice']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        draw = random.randint(1, 4)
        player.lottery3_draw   = draw
        delta                  = section3_delta(player.lottery3_choice, draw)
        player.lottery3_payoff = C.LOT_ENDOWMENT + delta  # 400 base
        pvars = player.participant.vars
        pvars['section3_choice'] = player.lottery3_choice
        pvars['section3_draw']   = draw
        pvars['section3_payoff'] = player.lottery3_payoff


class LotteryWaitPage(WaitPage):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1
    title_text = "Please wait"
    body_text = "Waiting for all participants to finish the lotteries..."


class PGGHInstructions(TimedPage):
    form_model = 'player'
    form_fields = ['passed_timer']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1


class PGGLInstructions(TimedPage):
    form_model = 'player'
    form_fields = ['passed_timer']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.ROUND_CHANGE


class Contribution(Page):
    form_model = 'player'
    form_fields = [
        'contribution',
        'personal_belief_p2', 'personal_belief_p3', 'personal_belief_p4',
        'empirical_exp_p2',    'empirical_exp_p3',    'empirical_exp_p4',
        'normative_exp_p2',    'normative_exp_p3',    'normative_exp_p4',
    ]


class ResultsWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        set_payoffs(group)


class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        g = player.group
        return dict(
            total_contributions = g.total_contributions,
            disaster_roll       = g.field_maybe_none('disaster_roll'),
            disaster_occurred   = g.field_maybe_none('disaster_occurred'),
            amount_kept         = player.amount_kept,
            payoff              = player.payoff,
        )


class SectionSelectionWaitPage(WaitPage):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def after_all_players_arrive(group: Group):
        for p in group.get_players():
            pick = random.choice([
                'section1', 'section2', 'section3',
                'pgg_first5', 'pgg_last5'
            ])
            p.selected_section = pick

            if pick in ('section1', 'section2', 'section3'):
                choice = p.participant.vars[f'{pick}_choice']
                draw   = p.participant.vars[f'{pick}_draw']
                pay    = p.participant.vars[f'{pick}_payoff']

                p.selected_lottery_choice = choice
                p.selected_lottery_draw   = draw
                p.selected_lottery_payoff = pay

                p.selected_pgg_round        = None
                p.selected_pgg_contribution = None
                p.selected_pgg_payoff       = None

                final = pay

            else:
                if pick == 'pgg_first5':
                    idx = random.randint(0, 4)
                    rnd = idx + 1
                else:
                    idx = random.randint(0, 4)
                    rnd = idx + 6

                contrib = p.participant.vars['pgg_contributions'][idx]
                pay     = p.participant.vars['pgg_payoffs'][idx]

                p.selected_pgg_round        = rnd
                p.selected_pgg_contribution = contrib
                p.selected_pgg_payoff       = pay

                p.selected_lottery_choice = None
                p.selected_lottery_draw   = None
                p.selected_lottery_payoff = None

                final = pay

            p.final_payment = final
            p.payoff        = final


class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        # Use field_maybe_none for any nullable field to avoid the 500 error
        return dict(
            selected_section          = player.selected_section,
            final_payment             = player.final_payment,
            selected_lottery_choice   = player.field_maybe_none('selected_lottery_choice'),
            selected_lottery_draw     = player.field_maybe_none('selected_lottery_draw'),
            selected_lottery_payoff   = player.field_maybe_none('selected_lottery_payoff'),
            selected_pgg_round        = player.field_maybe_none('selected_pgg_round'),
            selected_pgg_contribution = player.field_maybe_none('selected_pgg_contribution'),
            selected_pgg_payoff       = player.field_maybe_none('selected_pgg_payoff'),
        )


page_sequence = [
    Instructions,
    Lottery,
    Lottery2,
    Lottery3,
    LotteryWaitPage,
    PGGHInstructions,
    PGGLInstructions,
    Contribution,
    ResultsWaitPage,
    Results,
    SectionSelectionWaitPage,
    FinalResults,
]
