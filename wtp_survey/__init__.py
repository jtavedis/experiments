from otree.api import *
import random


class C(BaseConstants):
    NAME_IN_URL = 'wtp_survey'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

    ITEMS = [
        dict(
            slug='pastel_pink_tshirt',
            label='Pastel Pink T-Shirt (AUR)',
            image='wtp_survey/pastel_pink_tshirt.jpg',
            coarse_prices=[0, 5, 10, 15, 20, 25, 30, 35, 40],
            fine_step=0.50,
        ),
        dict(
            slug='grey_hoodie',
            label='Grey Hoodie (AUR)',
            image='wtp_survey/grey_hoodie.jpg',
            coarse_prices=[0, 10, 20, 30, 40, 50, 60, 70, 80],
            fine_step=1.00,
        ),
    ]

    ENDOWMENT = cu(0)
    MIN_WAIT = 10  # seconds on Instructions page

def price_grid(item):
    return item['coarse_prices']

class Subsession(BaseSubsession):
    winner_id_in_session = models.IntegerField(blank=True)


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    consent = models.BooleanField(initial=False)
    passed_timer = models.BooleanField(initial=False)

    attn_check = models.StringField(
        choices=[
            "If the random price is ≤ my WTP, I receive the product; otherwise I receive nothing.",
            "I receive the hoodie regardless of price.",
            "I receive both the hoodie and €35.",
            "Nothing happens for anyone; it is just hypothetical."
        ],
        label="",
        blank=True,
    )

    age = models.IntegerField(min=16, max=99, blank=True)
    gender = models.StringField(choices=["Female", "Male", "Non-binary", "Prefer not to say"], blank=True)
    major = models.StringField(blank=True)


for _it in C.ITEMS:
    _slug = _it['slug']
    setattr(Player, f"choices_{_slug}", models.LongStringField(blank=True))
    setattr(Player, f"fine_{_slug}", models.StringField(blank=True))
    setattr(Player, f"wtp_{_slug}", models.CurrencyField(initial=cu(0)))


def compute_wtp_from_choices_and_fine(choices_list, grid, fine_value):
    switch_idx = None
    for i, v in enumerate(choices_list):
        if v == 0:
            switch_idx = i
            break

    if switch_idx is None:
        lower = upper = grid[-1]
    else:
        lower = 0 if switch_idx == 0 else grid[switch_idx - 1]
        upper = grid[switch_idx]

    if fine_value is not None:
        try:
            f = float(fine_value)
            f = max(min(f, upper), lower)
            return cu(round(f, 2))
        except:
            pass

    return cu(round(lower, 2))


def draw_random_price(item):
    return random.choice(price_grid(item))


def creating_session(subsession: Subsession):
    for p in subsession.get_players():
        selected_slug = random.choice([it['slug'] for it in C.ITEMS])
        p.participant.vars['selected_item_slug'] = selected_slug
        sel_item = next(it for it in C.ITEMS if it['slug'] == selected_slug)
        p.participant.vars['random_price'] = draw_random_price(sel_item)


def set_payoff(player: Player):
    # Only the randomly chosen winner is realized
    if not player.participant.vars.get('is_winner'):
        player.payoff = cu(0)
        player.participant.vars['reward'] = 'none'
        return

    sel_slug = player.participant.vars.get('selected_item_slug')
    rand_price = player.participant.vars.get('random_price')
    wtp_field = getattr(player, f"wtp_{sel_slug}", cu(0))

    # Pure BDM: buy at the random price if WTP >= price; else nothing
    if wtp_field >= rand_price:
        player.participant.vars['reward'] = 'product'
    else:
        player.participant.vars['reward'] = 'none'

    player.payoff = cu(0)  # still hypothetical in your setup



def custom_export(players):
    yield ['session_code', 'participant_code', 'reward', 'selected_item', 'random_price'] + \
        [f"wtp_{it['slug']}" for it in C.ITEMS]
    for p in players:
        row = [
            p.session.code,
            p.participant.code,
            p.participant.vars.get('reward'),
            p.participant.vars.get('selected_item_slug'),
            p.participant.vars.get('random_price'),
        ]
        for it in C.ITEMS:
            row.append(getattr(p, f"wtp_{it['slug']}", cu(0)))
        yield row


class TimedPage(Page):
    @staticmethod
    def min_wait(player: Player) -> int:
        return C.MIN_WAIT

    @staticmethod
    def js_vars(player: Player):
        return dict(min_wait=TimedPage.min_wait(player))

    @staticmethod
    def error_message(player: Player, values):
        v = values.get('passed_timer')
        if v is True or str(v).lower() in ('1', 'true', 'on', '1.0'):
            return
        return f'Please spend at least {C.MIN_WAIT} seconds on this page before continuing.'


class WelcomeConsent(Page):
    form_model = 'player'
    form_fields = ['consent']

    @staticmethod
    def error_message(player: Player, values):
        if not values['consent']:
            return "You must consent to continue."


class Instructions(TimedPage):
    form_model = 'player'
    form_fields = ['passed_timer']


class Comprehension(Page):
    form_model = 'player'
    form_fields = ['attn_check']

    @staticmethod
    def error_message(player: Player, values):
        if values['attn_check'] != "If the random price is ≤ my WTP, I receive the product; otherwise I receive nothing.":
            return "That's not correct. Please review the instructions and try again."


class WTPPage(Page):
    form_model = 'player'

    def get_form_fields(self):
        fields = []
        for it in C.ITEMS:
            slug = it['slug']
            fields += [f"choices_{slug}", f"fine_{slug}"]
        return fields

    @staticmethod
    def error_message(player: Player, values):
        errors = {}
        for it in C.ITEMS:
            slug = it['slug']
            raw = values.get(f"choices_{slug}", "") or ""
            if not raw or not any(ch in raw for ch in ('0', '1')):
                errors[f"choices_{slug}"] = "Please complete this set of choices before proceeding."
        if errors:
            return errors

    def vars_for_template(self):
        items = []
        for it in C.ITEMS:
            grid = price_grid(it)
            rows = [{'p': float(f'{p:.2f}'), 'p_str': f'{p:.2f}'} for p in grid]
            items.append({
                **it,
                'rows': rows,
                'fine_step': float(it.get('fine_step', 0.50)),
            })
        return dict(items=items)

    def before_next_page(self, timeout_happened=False):
        for it in C.ITEMS:
            slug = it['slug']
            grid = price_grid(it)

            raw = self.field_maybe_none(f"choices_{slug}") or ''
            try:
                choices_list = [int(x) for x in raw.split(',') if x.strip() != '']
            except:
                choices_list = [0] * len(grid)

            fine_raw = self.field_maybe_none(f"fine_{slug}") or None
            wtp_val = compute_wtp_from_choices_and_fine(choices_list, grid, fine_raw)
            setattr(self, f"wtp_{slug}", wtp_val)


class Review(Page):
    def before_next_page(player, timeout_happened=False):
        player.participant.vars['wtp_done'] = True

    def vars_for_template(self):
        rows = []
        for it in C.ITEMS:
            slug = it['slug']
            rows.append(dict(label=it['label'], wtp=getattr(self, f"wtp_{slug}")))
        return dict(rows=rows)

class SelectWinnerWaitPage(WaitPage):
    wait_for_all_groups = True  # ensures all participants reach this before proceeding

    def after_all_players_arrive(self):
        subsession = self.subsession
        if subsession.field_maybe_none('winner_id_in_session') is None:
            players = subsession.get_players()
            winner = random.choice(players)
            subsession.winner_id_in_session = winner.id_in_subsession
            for p in players:
                p.participant.vars['is_winner'] = (p.id_in_subsession == winner.id_in_subsession)


class LotteryReveal(Page):
    def vars_for_template(player):
        is_winner = player.participant.vars.get('is_winner', False)

        if not is_winner:
            return dict(is_winner=False)

        sel_slug = player.participant.vars.get('selected_item_slug')
        rand_price = player.participant.vars.get('random_price')
        item = next(it for it in C.ITEMS if it['slug'] == sel_slug)
        wtp_val = getattr(player, f"wtp_{sel_slug}")
        will_buy = (wtp_val >= cu(rand_price))
        reward = player.participant.vars.get('reward', 'unknown')

        return dict(
            is_winner=True,
            item=item,
            random_price=rand_price,
            wtp=wtp_val,
            will_buy=will_buy,
            reward=reward,
        )

    def before_next_page(player, timeout_happened=False):
        set_payoff(player)


class Demographics(Page):
    form_model = 'player'
    form_fields = ['age', 'gender', 'major']


class ThankYou(Page):
    pass


page_sequence = [
    WelcomeConsent, Instructions, Comprehension,
    WTPPage, Review, SelectWinnerWaitPage,
    LotteryReveal, Demographics, ThankYou,
]

