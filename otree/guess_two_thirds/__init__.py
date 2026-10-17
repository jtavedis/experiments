from otree.api import *


doc = """
a.k.a. Keynesian beauty contest.
Players all guess a number; whoever guesses closest to
2/3 of the average wins.
See https://en.wikipedia.org/wiki/Guess_2/3_of_the_average
"""


class C(BaseConstants):
    PLAYERS_PER_GROUP = None
    # Upper bound (we'll stop early based on session.config['rounds'])
    NUM_ROUNDS = 5
    NAME_IN_URL = 'guess_two_thirds'
    JACKPOT = cu(100)
    GUESS_MAX = 100


# ---- Helper: read the admin-entered "rounds" value ----
def max_rounds(session):
    # If 'rounds' is not provided, fall back to C.NUM_ROUNDS
    return session.config.get('rounds', C.NUM_ROUNDS)


class Subsession(BaseSubsession):
    def creating_session(subsession):
        # Put all players into one single group each round
        players = subsession.get_players()
        subsession.set_group_matrix([players])


class Group(BaseGroup):
    two_thirds_avg = models.FloatField()
    best_guess = models.IntegerField()
    num_winners = models.IntegerField()


class Player(BasePlayer):
    guess = models.IntegerField(
        min=0, max=C.GUESS_MAX, label="Please pick a number from 0 to 100:"
    )
    is_winner = models.BooleanField(initial=False)


# ---- FUNCTIONS ----
def set_payoffs(group: Group):
    players = group.get_players()
    guesses = [p.guess for p in players]
    two_thirds_avg = (2 / 3) * sum(guesses) / len(players)
    group.two_thirds_avg = round(two_thirds_avg, 2)
    group.best_guess = min(guesses, key=lambda guess: abs(guess - group.two_thirds_avg))
    winners = [p for p in players if p.guess == group.best_guess]
    group.num_winners = len(winners)
    for p in winners:
        p.is_winner = True
        p.payoff = C.JACKPOT / group.num_winners


def two_thirds_avg_history(group: Group):
    return [g.two_thirds_avg for g in group.in_previous_rounds()]


# ---- PAGES ----
class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player):
        # Only show once, and only if within the chosen rounds
        return player.round_number == 1 and player.round_number <= max_rounds(player.session)

    @staticmethod
    def vars_for_template(player: Player):
        session_size = len(player.subsession.get_players())
        return dict(
            participant_id=player.id_in_group,
            num_players=session_size
        )


class Guess(Page):
    form_model = 'player'
    form_fields = ['guess']

    @staticmethod
    def is_displayed(player: Player):
        # Respect the admin-entered number of rounds
        return player.round_number <= max_rounds(player.session)

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        return dict(two_thirds_avg_history=two_thirds_avg_history(group))


class ResultsWaitPage(WaitPage):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number <= max_rounds(player.session)

    after_all_players_arrive = set_payoffs


class Results(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number <= max_rounds(player.session)

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group
        sorted_guesses = sorted(p.guess for p in group.get_players())
        return dict(
            sorted_guesses=sorted_guesses,
            participant_id=player.id_in_group
        )

    @staticmethod
    def app_after_this_page(player: Player, upcoming_apps):
        # End the app once we reach the selected number of rounds
        if player.round_number >= max_rounds(player.session):
            return upcoming_apps[0] if upcoming_apps else None


page_sequence = [Introduction, Guess, ResultsWaitPage, Results]
