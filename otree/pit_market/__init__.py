import random
import statistics
import time

from otree.api import *

doc = """
Pit market (Experiment 6), decentralized version.

Mirrors the classroom pit market: each student is a buyer or a seller and gets
one private card per period. Students appear as dots in a shared "room".
Clicking a dot shows the price that person chose to announce (never their
card). Buyers and sellers talk in private one-to-one chats and send each other
price offers; the receiver of an offer can accept or decline it, so a seller
holding several offers can pick the one they like. An accepted offer goes to
the "front desk": if the price is below the seller's cost, above the buyer's
value, or above a price ceiling, the trade is invalidated and both keep
negotiating, as in the paper version. Valid trades are written on a public
whiteboard and both traders leave the market for the rest of the period.

Every chat message, offer, decline, withdrawal, invalidation and trade is
stored with a timestamp (download it from the Data tab: "pit_market" custom
export).
"""

# ── The deck used in the Fall 2026 analog session ─────────────────────────────
# Sellers hold black cards (costs), buyers hold red cards (values).
DEFAULT_BUYER_VALUES = [10, 9, 9, 8, 8, 7, 7, 6, 6]
DEFAULT_SELLER_COSTS = [2, 3, 3, 4, 5, 5, 6, 6, 7]

# Policy rounds (same as the analog session). Override in the session config.
DEFAULT_TAX_ROUND = 7       # round with a per-unit tax paid by sellers
DEFAULT_TAX_AMOUNT = 1
DEFAULT_CEILING_ROUND = 8   # round with a legal maximum price
DEFAULT_CEILING_PRICE = 6

MAX_CHAT_LENGTH = 200
MAX_PRICE = 100


class C(BaseConstants):
    NAME_IN_URL = 'pit_market'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 8
    TRADING_SECONDS = 300


# ── Models ────────────────────────────────────────────────────────────────────
class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    start_time = models.FloatField()


def likert(label):
    return models.IntegerField(
        label=label,
        choices=[
            [1, '1 — strongly disagree'],
            [2, '2 — disagree'],
            [3, '3 — agree'],
            [4, '4 — strongly agree'],
        ],
        widget=widgets.RadioSelectHorizontal,
    )


class Player(BasePlayer):
    name_entry = models.StringField(label='Please enter your first name (other traders will see it):')
    market_role = models.StringField()          # 'buyer' or 'seller'
    card = models.IntegerField()                # buyer value or seller cost
    posted_price = models.FloatField(blank=True)
    traded = models.BooleanField(initial=False)
    trade_price = models.FloatField(blank=True)
    partner_id = models.IntegerField(blank=True)
    tax_paid = models.FloatField(initial=0)
    period_earnings = models.FloatField(initial=0)

    survey_a = likert('a. I enjoyed this activity.')
    survey_b = likert('b. This experiment contributed to my learning of the subject matter.')
    survey_c = likert('c. I interacted with other students during this activity.')
    survey_d = likert('d. I stayed focused on the activity for most of the class.')


class Msg(ExtraModel):
    """One event in a private buyer–seller conversation.

    kind:   'chat'   free text
            'offer'  a price proposal the receiver can accept or decline
            'system' front-desk notices, trade confirmations, etc.
    status (offers only): open, accepted, declined, withdrawn, replaced,
            expired (someone traded elsewhere / period ended), invalid
    """
    group = models.Link(Group)
    round_number = models.IntegerField()
    t = models.FloatField()               # seconds since the period started
    sender = models.IntegerField()        # id_in_group
    receiver = models.IntegerField()      # id_in_group
    kind = models.StringField()
    text = models.LongStringField()
    price = models.FloatField()
    status = models.StringField()
    resolved_t = models.FloatField()     # when an offer stopped being open


class PostedPrice(ExtraModel):
    """Log of announced (non-binding) prices."""
    group = models.Link(Group)
    round_number = models.IntegerField()
    t = models.FloatField()
    player_id = models.IntegerField()
    price = models.FloatField()           # -1 means cleared


# ── Session settings helpers ──────────────────────────────────────────────────
def cfg(session, key, default):
    return session.config.get(key, default)


def tax_in_round(session, rn):
    return cfg(session, 'tax_amount', DEFAULT_TAX_AMOUNT) if rn == cfg(session, 'tax_round', DEFAULT_TAX_ROUND) else 0


def ceiling_in_round(session, rn):
    if rn == cfg(session, 'ceiling_round', DEFAULT_CEILING_ROUND):
        return cfg(session, 'ceiling_price', DEFAULT_CEILING_PRICE)
    return None


def policy_text(session, rn):
    tax = tax_in_round(session, rn)
    ceiling = ceiling_in_round(session, rn)
    parts = []
    if tax:
        parts.append(f'Sellers pay a tax of ${fmt(tax)} on every unit they sell.')
    if ceiling is not None:
        parts.append(f'Price ceiling: no trade may take place above ${fmt(ceiling)}.')
    return ' '.join(parts)


def fmt(x):
    if x is None:
        return ''
    x = float(x)
    return f'{x:.0f}' if x == int(x) else f'{x:.2f}'


# ── Session setup ─────────────────────────────────────────────────────────────
def creating_session(subsession: Subsession):
    session = subsession.session
    players = subsession.get_players()
    n = len(players)
    buyer_values = list(cfg(session, 'buyer_values', DEFAULT_BUYER_VALUES))
    seller_costs = list(cfg(session, 'seller_costs', DEFAULT_SELLER_COSTS))

    if subsession.round_number == 1:
        # Roles are fixed for the whole session. If the class size matches the
        # deck, use the deck's split; otherwise split the class in half.
        if n == len(buyer_values) + len(seller_costs):
            n_buyers = len(buyer_values)
        else:
            n_buyers = (n + 1) // 2
        roles = ['buyer'] * n_buyers + ['seller'] * (n - n_buyers)
        random.shuffle(roles)
        for p, r in zip(players, roles):
            p.participant.vars['market_role'] = r

    for p in players:
        p.market_role = p.participant.vars['market_role']

    # Collect and reshuffle the cards every period.
    for role, deck in (('buyer', buyer_values), ('seller', seller_costs)):
        group_players = [p for p in players if p.market_role == role]
        cards = deck_for(deck, len(group_players))
        for p, card in zip(group_players, cards):
            p.card = card


def deck_for(deck, k):
    """k cards from the deck. If there are more traders than cards, extra
    cards are drawn at random from the same deck."""
    cards = random.sample(deck, min(k, len(deck)))
    while len(cards) < k:
        cards.append(random.choice(deck))
    random.shuffle(cards)
    return cards


# ── Live market ───────────────────────────────────────────────────────────────
def display_names(group: Group):
    players = group.get_players()
    names = {}
    for p in players:
        raw = (p.participant.vars.get('display_name') or '').strip()
        names[p.id_in_group] = raw or f'Trader {p.id_in_group}'
    counts = {}
    for v in names.values():
        counts[v] = counts.get(v, 0) + 1
    return {pid: (f'{v} ({pid})' if counts[v] > 1 else v) for pid, v in names.items()}


def elapsed(group: Group):
    start = group.field_maybe_none('start_time') or time.time()
    return round(time.time() - start, 2)


def time_left(group: Group):
    start = group.field_maybe_none('start_time')
    if start is None:
        return C.TRADING_SECONDS
    return start + C.TRADING_SECONDS - time.time()


def group_msgs(group: Group):
    return sorted(Msg.filter(group=group), key=lambda m: m.id)


def public_state(group: Group):
    names = display_names(group)
    trades = sorted(
        [m for m in group_msgs(group) if m.kind == 'offer' and m.status == 'accepted'],
        key=lambda m: m.resolved_t,
    )
    return {
        'players': [
            {
                'id': p.id_in_group,
                'name': names[p.id_in_group],
                'role': p.market_role,
                'posted': p.field_maybe_none('posted_price'),
                'traded': p.traded,
            }
            for p in group.get_players()
        ],
        'board': [{'n': i + 1, 'price': m.price, 't': m.resolved_t} for i, m in enumerate(trades)],
    }


def personal_state(player: Player, public, msgs):
    me = player.id_in_group
    mine = [
        {
            'id': m.id, 'from': m.sender, 'to': m.receiver, 'kind': m.kind,
            'text': m.text, 'price': m.price, 'status': m.status, 't': m.t,
        }
        for m in msgs if m.sender == me or m.receiver == me
    ]
    return {
        'type': 'state',
        **public,
        'me': {
            'id': me,
            'traded': player.traded,
            'trade_price': player.field_maybe_none('trade_price'),
            'earnings': player.period_earnings,
            'posted': player.field_maybe_none('posted_price'),
        },
        'msgs': mine,
    }


def states_for(group: Group, ids):
    public = public_state(group)
    msgs = group_msgs(group)
    return {pid: personal_state(group.get_player_by_id(pid), public, msgs) for pid in ids}


def error(player, text):
    return {player.id_in_group: {'type': 'error', 'text': text}}


def parse_price(raw):
    try:
        price = round(float(raw), 2)
    except (TypeError, ValueError):
        return None
    if price < 0 or price > MAX_PRICE:
        return None
    return price


def new_msg(group, sender, receiver, kind, text='', price=None, status=''):
    return Msg.create(
        group=group, round_number=group.round_number, t=elapsed(group),
        sender=sender, receiver=receiver, kind=kind, text=text,
        price=price if price is not None else -1, status=status, resolved_t=-1,
    )


def set_status(group, m, status):
    m.status = status
    m.resolved_t = elapsed(group)


def counterpart(player: Player, other_id):
    """The other trader, if this pair is allowed to negotiate."""
    try:
        other_id = int(other_id)
    except (TypeError, ValueError):
        return None
    if other_id == player.id_in_group:
        return None
    try:
        other = player.group.get_player_by_id(other_id)
    except Exception:
        return None
    if other.market_role == player.market_role:
        return None
    return other


def live_trading(player: Player, data):
    group = player.group
    me = player.id_in_group
    action = data.get('type')
    everyone = [p.id_in_group for p in group.get_players()]

    if action == 'get_state':
        return states_for(group, [me])

    if time_left(group) <= 0:
        return error(player, 'The trading period is over.')
    if player.traded:
        return error(player, 'You have already traded this period. Please wait for the period to end.')

    if action == 'post_price':
        raw = data.get('price')
        if raw in (None, ''):
            player.posted_price = None
            PostedPrice.create(group=group, round_number=group.round_number, t=elapsed(group), player_id=me, price=-1)
        else:
            price = parse_price(raw)
            if price is None:
                return error(player, f'Please enter a price between 0 and {MAX_PRICE}.')
            player.posted_price = price
            PostedPrice.create(group=group, round_number=group.round_number, t=elapsed(group), player_id=me, price=price)
        return states_for(group, everyone)

    if action == 'chat':
        other = counterpart(player, data.get('to'))
        if other is None:
            return error(player, 'You can only talk with traders on the other side of the market.')
        if other.traded:
            return error(player, 'That trader has already traded and left the market.')
        text = str(data.get('text') or '').strip()[:MAX_CHAT_LENGTH]
        if not text:
            return None
        new_msg(group, me, other.id_in_group, 'chat', text=text)
        return states_for(group, [me, other.id_in_group])

    if action == 'offer':
        other = counterpart(player, data.get('to'))
        if other is None:
            return error(player, 'You can only make offers to traders on the other side of the market.')
        if other.traded:
            return error(player, 'That trader has already traded and left the market.')
        price = parse_price(data.get('price'))
        if price is None:
            return error(player, f'Please enter a price between 0 and {MAX_PRICE}.')
        # One open offer per person per conversation: a new one replaces the old.
        for m in Msg.filter(group=group):
            if m.sender == me and m.receiver == other.id_in_group and m.kind == 'offer' and m.status == 'open':
                set_status(group, m, 'replaced')
        new_msg(group, me, other.id_in_group, 'offer', price=price, status='open')
        return states_for(group, [me, other.id_in_group])

    if action in ('accept', 'decline', 'withdraw'):
        offers = [m for m in Msg.filter(group=group) if m.id == data.get('offer_id') and m.kind == 'offer']
        if not offers:
            return error(player, 'Offer not found.')
        offer = offers[0]
        if offer.status != 'open':
            return error(player, 'That offer is no longer open.')

        if action == 'withdraw':
            if offer.sender != me:
                return error(player, 'You can only withdraw your own offers.')
            set_status(group, offer, 'withdrawn')
            return states_for(group, [me, offer.receiver])

        if offer.receiver != me:
            return error(player, 'Only the person who received the offer can answer it.')
        if action == 'decline':
            set_status(group, offer, 'declined')
            return states_for(group, [me, offer.sender])

        return accept_offer(player, offer)

    return error(player, 'Unknown action.')


def accept_offer(player: Player, offer: Msg):
    group = player.group
    session = player.session
    rn = player.round_number
    other = group.get_player_by_id(offer.sender)
    if other.traded:
        set_status(group, offer, 'expired')
        return error(player, 'That trader has already traded.')

    buyer = player if player.market_role == 'buyer' else other
    seller = other if buyer is player else player
    price = offer.price
    tax = tax_in_round(session, rn)
    ceiling = ceiling_in_round(session, rn)

    # The front desk check, as in the paper version.
    problems = []
    if price < seller.card:
        problems.append("the price is below the seller's cost")
    if price > buyer.card:
        problems.append("the price is above the buyer's value")
    if ceiling is not None and price > ceiling:
        problems.append(f'the price is above the ${fmt(ceiling)} price ceiling')
    if problems:
        set_status(group, offer, 'invalid')
        new_msg(
            group, offer.sender, offer.receiver, 'system',
            text=f'Front desk: trade at ${fmt(price)} invalidated because {" and ".join(problems)}. '
                 'Cards returned — keep negotiating.',
        )
        return states_for(group, [buyer.id_in_group, seller.id_in_group])

    set_status(group, offer, 'accepted')
    for p, partner in ((buyer, seller), (seller, buyer)):
        p.traded = True
        p.trade_price = price
        p.partner_id = partner.id_in_group
        p.posted_price = None
    buyer.period_earnings = buyer.card - price
    seller.tax_paid = tax
    seller.period_earnings = price - seller.card - tax
    buyer.payoff = buyer.period_earnings
    seller.payoff = seller.period_earnings

    new_msg(group, offer.sender, offer.receiver, 'system',
            text=f'Trade at ${fmt(price)} accepted and verified. It is now on the whiteboard.')

    # Both traders leave the market: close their other conversations.
    names = display_names(group)
    gone = {buyer.id_in_group, seller.id_in_group}
    for m in Msg.filter(group=group):
        if m.kind == 'offer' and m.status == 'open' and (m.sender in gone or m.receiver in gone):
            set_status(group, m, 'expired')
    talked = set()
    for m in Msg.filter(group=group):
        for a, b in ((m.sender, m.receiver), (m.receiver, m.sender)):
            if a in gone and b not in gone:
                talked.add((a, b))
    for a, b in sorted(talked):
        new_msg(group, a, b, 'system', text=f'{names[a]} has made a trade and left the market.')

    return states_for(group, [p.id_in_group for p in group.get_players()])


def close_period(group: Group):
    for m in Msg.filter(group=group):
        if m.kind == 'offer' and m.status == 'open':
            set_status(group, m, 'expired')


# ── Benchmarks (for results and the admin report) ─────────────────────────────
def max_surplus(values, costs, tax=0):
    """Highest buyer matched with lowest seller, counting only pairs that gain."""
    total = 0
    for v, c in zip(sorted(values, reverse=True), sorted(costs)):
        if v - c - tax >= 0 and v - c > 0:
            total += v - c
    return total


def round_summary(group: Group, session):
    players = group.get_players()
    rn = group.round_number
    buyers = [p for p in players if p.market_role == 'buyer']
    sellers = [p for p in players if p.market_role == 'seller']
    traded_buyers = [p for p in buyers if p.traded]
    prices = [p.trade_price for p in traded_buyers]
    total = sum(p.period_earnings for p in players if p.traded) + sum(p.tax_paid for p in sellers if p.traded)
    best = max_surplus([p.card for p in buyers], [p.card for p in sellers], tax_in_round(session, rn))
    return dict(
        round=rn,
        policy=policy_text(session, rn) or 'Baseline',
        trades=len(prices),
        mean=round(statistics.mean(prices), 2) if prices else None,
        sd=round(statistics.stdev(prices), 2) if len(prices) > 1 else None,
        low=min(prices) if prices else None,
        high=max(prices) if prices else None,
        prices=', '.join(fmt(x) for x in prices),
        total_surplus=round(total, 2),
        max_surplus=best,
        efficiency=f'{100 * total / best:.0f}%' if best else '—',
    )


def vars_for_admin_report(subsession: Subsession):
    rows = []
    for ss in subsession.in_all_rounds():
        groups = ss.get_groups()
        if groups and groups[0].field_maybe_none('start_time') is not None:
            rows.append(round_summary(groups[0], ss.session))
    return dict(rows=rows)


# ── Pages ─────────────────────────────────────────────────────────────────────
class EnterName(Page):
    form_model = 'player'
    form_fields = ['name_entry']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def error_message(player, values):
        if not values['name_entry'].strip():
            return 'Please enter a name.'

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        name = player.name_entry.strip()[:20]
        player.participant.vars['display_name'] = name
        player.participant.full_name = name


class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player: Player):
        return dict(role=player.market_role)


def set_start(group: Group):
    group.start_time = time.time()


class WaitToStart(WaitPage):
    title_text = 'Waiting for the period to start'
    body_text = 'Trading begins as soon as everyone is ready. New cards are being dealt.'
    after_all_players_arrive = 'set_start'


class Trading(Page):
    timer_text = 'Time left in this trading period:'
    @staticmethod
    def live_method(player: Player, data):
        return live_trading(player, data)

    @staticmethod
    def get_timeout_seconds(player: Player):
        return max(time_left(player.group), 1)

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            role=player.market_role,
            card=player.card,
            policy=policy_text(player.session, player.round_number),
        )

    @staticmethod
    def js_vars(player: Player):
        return dict(
            me=player.id_in_group,
            role=player.market_role,
            card=player.card,
            round=player.round_number,
            tax=tax_in_round(player.session, player.round_number),
            ceiling=ceiling_in_round(player.session, player.round_number),
            session_code=player.session.code,
        )


def close_and_wait(group: Group):
    close_period(group)


class ResultsWaitPage(WaitPage):
    title_text = 'The trading period is over'
    body_text = 'Waiting for everyone to finish…'
    after_all_players_arrive = 'close_and_wait'


class Results(Page):
    timeout_seconds = 60

    @staticmethod
    def vars_for_template(player: Player):
        summary = round_summary(player.group, player.session)
        return dict(
            role=player.market_role,
            card=player.card,
            price=fmt(player.field_maybe_none('trade_price')),
            earnings=fmt(player.period_earnings),
            tax=fmt(player.tax_paid),
            total=fmt(sum(p.period_earnings for p in player.in_all_rounds())),
            summary=summary,
            board=', '.join('$' + fmt(m.price) for m in sorted(
                (m for m in Msg.filter(group=player.group) if m.kind == 'offer' and m.status == 'accepted'),
                key=lambda m: m.resolved_t)),
        )


class Survey(Page):
    form_model = 'player'
    form_fields = ['survey_a', 'survey_b', 'survey_c', 'survey_d']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS


class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        rows = [
            dict(
                round=p.round_number,
                card=p.card,
                price=fmt(p.field_maybe_none('trade_price')) if p.traded else '—',
                earnings=fmt(p.period_earnings),
            )
            for p in player.in_all_rounds()
        ]
        return dict(
            rows=rows,
            role=player.market_role,
            total=fmt(sum(p.period_earnings for p in player.in_all_rounds())),
        )


page_sequence = [
    EnterName, Introduction, WaitToStart, Trading, ResultsWaitPage, Results, Survey, FinalResults,
]


# ── Data export: every bargaining event, one row each ─────────────────────────
def custom_export(players):
    yield [
        'session', 'round', 't_seconds', 'event', 'sender_id', 'sender_name', 'sender_role',
        'sender_card', 'receiver_id', 'receiver_name', 'receiver_role', 'receiver_card',
        'price', 'offer_status', 'offer_resolved_t', 'text',
    ]
    seen = set()
    for p in players:
        g = p.group
        if g.id in seen:
            continue
        seen.add(g.id)
        by_id = {q.id_in_group: q for q in g.get_players()}

        def who(pid):
            q = by_id.get(pid)
            if q is None:
                return ['', '', '']
            return [q.participant.vars.get('display_name', ''), q.market_role, q.field_maybe_none('card')]

        rows = []
        for m in Msg.filter(group=g):
            rows.append((m.t, m.id, [
                g.session.code, g.round_number, m.t, m.kind, m.sender, *who(m.sender),
                m.receiver, *who(m.receiver), '' if m.price < 0 else m.price, m.status,
                '' if (m.resolved_t is None or m.resolved_t < 0) else m.resolved_t, m.text,
            ]))
        for pp in PostedPrice.filter(group=g):
            rows.append((pp.t, -pp.id, [
                g.session.code, g.round_number, pp.t, 'posted_price', pp.player_id, *who(pp.player_id),
                '', '', '', '', '' if pp.price < 0 else pp.price, 'cleared' if pp.price < 0 else '', '', '',
            ]))
        for _, _, row in sorted(rows, key=lambda r: (r[0], r[1])):
            yield row
