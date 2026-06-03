import random
from otree.api import *

doc = """
Ultimatum Game (Experiment 4) — Classic Ultimatum.

Each round, roles are randomly assigned within each pair:
  Proposer  – receives a $100 endowment and chooses how to split it
  Responder – decides to Accept (Black card) or Reject (Red card)

Proposer's three card options:
  R  (Red card)   → Keep $100 / Give $0
  B  (Black card) → Keep $80  / Give $20
  RB (Both cards) → Keep $50  / Give $50

Rejection → both players receive $0.

Matching: FIXED partner by default (same pair all 10 rounds).
To switch to RANDOM matching, see the comment block in creating_session().
"""

# ── Offer look-up ─────────────────────────────────────────────────────────────
OFFER_OPTIONS = {
    'R':  dict(keep=100, give=0,  label='Red Card',   short='R'),
    'B':  dict(keep=80,  give=20, label='Black Card', short='B'),
    'RB': dict(keep=50,  give=50, label='Both Cards', short='RB'),
}


# ── Constants ─────────────────────────────────────────────────────────────────
class C(BaseConstants):
    NAME_IN_URL = 'ultimatum'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 4
    ENDOWMENT = 100


# ── Models ────────────────────────────────────────────────────────────────────
class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    name_entry = models.StringField(label="Please enter your name:")
    player_role = models.StringField()
    proposal = models.StringField(           # set by proposer: 'R' | 'B' | 'RB'
        choices=[['R', 'Red'], ['B', 'Black'], ['RB', 'Both']],
        initial='',
    )
    response = models.StringField(           # set by responder: 'A' | 'R'
        choices=[['A', 'Accept'], ['R', 'Reject']],
        initial='',
    )
    period_earnings = models.IntegerField(initial=0)


# ── Session setup & matching ──────────────────────────────────────────────────
def creating_session(subsession: Subsession):
    # ── FIXED PARTNER MATCHING (active) ──────────────────────────────────────
    # Pairs are randomised once in round 1; the same pairing holds all 10 rounds.
    if subsession.round_number == 1:
        subsession.group_randomly()
    else:
        subsession.group_like_round(1)

    # ── RANDOM MATCHING (comment out the block above and uncomment below) ─────
    # A fresh random pairing is drawn at the start of every round.
    # subsession.group_randomly()

    # Roles are re-randomised every round (coin-flip logic from the instructions)
    for group in subsession.get_groups():
        players = group.get_players()
        random.shuffle(players)
        players[0].player_role = 'proposer'
        players[1].player_role = 'responder'


# ── Payoff calculation ────────────────────────────────────────────────────────
def set_payoffs(group: Group):
    proposer  = next(p for p in group.get_players() if p.player_role == 'proposer')
    responder = next(p for p in group.get_players() if p.player_role == 'responder')

    offer = OFFER_OPTIONS[proposer.proposal]

    # Classic Ultimatum: rejection costs both players
    if responder.response == 'A':
        proposer.period_earnings  = offer['keep']
        responder.period_earnings = offer['give']
    else:
        proposer.period_earnings  = 0
        responder.period_earnings = 0

    proposer.payoff  = proposer.period_earnings
    responder.payoff = responder.period_earnings


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
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1


class ProposerDecision(Page):
    form_model  = 'player'
    form_fields = ['proposal']

    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'proposer'

    @staticmethod
    def error_message(player: Player, values):
        if values.get('proposal') not in ('R', 'B', 'RB'):
            return 'Please select one of the three card options before continuing.'

    @staticmethod
    def vars_for_template(player: Player):
        partner = player.get_others_in_group()[0]
        return dict(
            partner_name=partner.participant.full_name,
        )


class AfterProposerWait(WaitPage):
    title_text = 'Waiting for the Proposer…'
    body_text  = 'Please wait while your partner chooses an offer.'


class ResponderDecision(Page):
    form_model  = 'player'
    form_fields = ['response']

    @staticmethod
    def is_displayed(player: Player):
        return player.player_role == 'responder'

    @staticmethod
    def error_message(player: Player, values):
        if values.get('response') not in ('A', 'R'):
            return 'Please select a card (Black = Accept, Red = Reject).'

    @staticmethod
    def vars_for_template(player: Player):
        proposer = player.get_others_in_group()[0]
        offer = OFFER_OPTIONS[proposer.proposal]
        return dict(
            partner_name=proposer.participant.full_name,
            proposer_card=proposer.proposal,
            offered_amount=offer['give'],
            proposer_keeps=offer['keep'],
        )


class ResultsWaitPage(WaitPage):
    after_all_players_arrive = 'set_payoffs'
    title_text = 'Calculating results…'
    body_text  = 'Please wait while results are tallied.'


class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        partner = player.get_others_in_group()[0]

        if player.player_role == 'proposer':
            proposer, responder = player, partner
        else:
            proposer, responder = partner, player

        offer    = OFFER_OPTIONS[proposer.proposal]
        accepted = (responder.response == 'A')
        cum      = sum(p.period_earnings for p in player.in_all_rounds())

        return dict(
            my_role=player.player_role.title(),
            partner_name=partner.participant.full_name,
            proposer_card=proposer.proposal,
            offer_label=offer['label'],
            offered_amount=offer['give'],
            proposer_keeps=offer['keep'],
            accepted=accepted,
            period_earnings=player.period_earnings,
            cumulative_earnings=cum,
            is_last=(player.round_number == C.NUM_ROUNDS),
        )


class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        rows = []
        for p in player.in_all_rounds():
            partner = p.get_others_in_group()[0]
            proposer  = p       if p.player_role == 'proposer' else partner
            responder = partner if p.player_role == 'proposer' else p

            offer    = OFFER_OPTIONS[proposer.proposal]
            accepted = (responder.response == 'A')

            rows.append(dict(
                round=p.round_number,
                my_role=p.player_role.title(),
                partner_name=partner.participant.full_name,
                proposer_card=proposer.proposal,
                offer_label=offer['label'],
                offered_amount=offer['give'],
                proposer_keeps=offer['keep'],
                accepted=accepted,
                earnings=p.period_earnings,
            ))

        total = sum(p.period_earnings for p in player.in_all_rounds())
        return dict(period_data=rows, total_earnings=total)


page_sequence = [
    EnterName,
    Introduction,
    ProposerDecision,
    AfterProposerWait,
    ResponderDecision,
    ResultsWaitPage,
    Results,
    FinalResults,
]