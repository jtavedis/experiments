import random
from otree.api import *

doc = """
Double-sided auction market experiment (Experiment 6 / CORE-Econ Pit Market).

Players are randomly assigned as buyers or sellers. Buyers have a maximum
willingness to pay (their "value"); sellers have a minimum acceptable price
(their "cost"). During each timed trading period they post bids/asks on a
shared market board and can accept each other's standing offers.

Roles are fixed across rounds. Values/costs are reshuffled each round.

Buyer earnings  = value  - trade price
Seller earnings = trade price - cost - tax
Players who do not trade earn 0 for that period.

Policy interventions (to demonstrate tax incidence and price controls):
  - Round 7: a per-unit tax on sellers.
  - Round 8: a legal price ceiling on trades.
"""

# ── Default supply / demand schedules ───────────────────────────────────────
DEFAULT_BUYER_VALUES = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
DEFAULT_SELLER_COSTS = [1,  2, 3, 4, 5, 6, 7, 8, 9, 10]

# ── Policy schedule ──────────────────────────────────────────────────────────
# Round -> per-unit tax on sellers (subtracted from seller earnings).
SELLER_TAX = {7: 1}

# Round -> maximum legal trade price (no offer or trade may exceed it).
# NOTE: a ceiling only "binds" (causes a shortage) if it is BELOW the
# equilibrium price. With the symmetric default schedule the equilibrium sits
# around €5-6, so €4 below binds and demonstrates a shortage.
# If you instead want to show that a ceiling ABOVE the market price does
# nothing, set this to 8.
PRICE_CEILING = {8: 4}

NUM_BOTS_DEFAULT = 0


def tax_this_round(rn):
    return SELLER_TAX.get(rn, 0)


def ceiling_this_round(rn):
    return PRICE_CEILING.get(rn, None)


# ── Constants ────────────────────────────────────────────────────────────────
class C(BaseConstants):
    NAME_IN_URL = 'double_auction'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 8
    TRADING_SECONDS = 300


# ── Models ───────────────────────────────────────────────────────────────────
class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    market_role = models.StringField()
    value_cost = models.IntegerField()
    traded = models.BooleanField(initial=False)
    trade_price = models.IntegerField(initial=0)
    period_earnings = models.IntegerField(initial=0)
    is_bot = models.BooleanField(initial=False)


# ── Extra models (live state) ─────────────────────────────────────────────────
class Offer(ExtraModel):
    """A standing bid or ask on the market board."""
    group = models.Link(Group)
    round_number = models.IntegerField()
    player_id = models.IntegerField()
    market_role = models.StringField()       # 'buyer' or 'seller'
    price = models.IntegerField()
    active = models.BooleanField(initial=True)


class CompletedTrade(ExtraModel):
    """Record of every executed trade."""
    group = models.Link(Group)
    round_number = models.IntegerField()
    trade_number = models.IntegerField()
    buyer_id = models.IntegerField()
    seller_id = models.IntegerField()
    price = models.IntegerField()
    buyer_earnings = models.IntegerField()
    seller_earnings = models.IntegerField()


# ── Session setup ─────────────────────────────────────────────────────────────
def creating_session(subsession: Subsession):
    players = subsession.get_players()
    n = len(players)

    buyer_values = list(subsession.session.config.get('buyer_values', DEFAULT_BUYER_VALUES))
    seller_costs = list(subsession.session.config.get('seller_costs', DEFAULT_SELLER_COSTS))

    n_buyers = min(len(buyer_values), n // 2)
    n_sellers = min(len(seller_costs), n - n_buyers)

    # ── One-time setup in round 1: assign roles + flag bots ──────────────────
    if subsession.round_number == 1:
        roles = ['buyer'] * n_buyers + ['seller'] * n_sellers
        random.shuffle(roles)

        num_bots = subsession.session.config.get('num_bots', NUM_BOTS_DEFAULT)
        bot_ids = set(range(n - num_bots + 1, n + 1)) if num_bots > 0 else set()

        for i, p in enumerate(players):
            p.participant.vars['market_role'] = roles[i] if i < len(roles) else 'buyer'
            p.participant.vars['is_bot'] = p.id_in_group in bot_ids

    # ── Reshuffle the card pool each round (collect & redistribute) ───────────
    values_this_round = buyer_values[:n_buyers]
    costs_this_round = seller_costs[:n_sellers]
    random.shuffle(values_this_round)
    random.shuffle(costs_this_round)

    b_idx = s_idx = 0
    for p in players:
        p.is_bot = p.participant.vars.get('is_bot', False)
        market_role = p.participant.vars.get('market_role', 'buyer')
        p.market_role = market_role
        if market_role == 'buyer' and b_idx < len(values_this_round):
            p.value_cost = values_this_round[b_idx]
            b_idx += 1
        elif market_role == 'seller' and s_idx < len(costs_this_round):
            p.value_cost = costs_this_round[s_idx]
            s_idx += 1
        else:
            p.value_cost = 5  # fallback for extra players


# ── Live trading helpers ───────────────────────────────────────────────────────
def _market_state(group: Group) -> dict:
    rn = group.round_number
    all_offers = Offer.filter(group=group)
    all_trades = CompletedTrade.filter(group=group)

    active_offers = [o for o in all_offers if o.round_number == rn and o.active]
    trades = [t for t in all_trades if t.round_number == rn]

    bids = sorted(
        [{'player_id': o.player_id, 'price': o.price}
         for o in active_offers if o.market_role == 'buyer'],
        key=lambda x: -x['price'],
    )
    asks = sorted(
        [{'player_id': o.player_id, 'price': o.price}
         for o in active_offers if o.market_role == 'seller'],
        key=lambda x: x['price'],
    )
    trade_list = sorted(
        [{'trade_number': t.trade_number,
          'price': t.price,
          'buyer_id': t.buyer_id,
          'seller_id': t.seller_id,
          'buyer_earnings': t.buyer_earnings,
          'seller_earnings': t.seller_earnings}
         for t in trades],
        key=lambda x: x['trade_number'],
    )
    traded_ids = [p.id_in_group for p in group.get_players() if p.traded]

    return {
        'type': 'market_update',
        'bids': bids,
        'asks': asks,
        'trades': trade_list,
        'traded_ids': traded_ids,
    }


def live_trading(player: Player, data: dict):
    group = player.group
    msg_type = data.get('type')

    rn = player.round_number
    tax = tax_this_round(rn)
    ceiling = ceiling_this_round(rn)

    if msg_type == 'get_state':
        return {0: _market_state(group)}

    if player.traded:
        return {player.id_in_group: {
            'type': 'error',
            'message': 'You have already traded this period.',
        }}

    if msg_type == 'post_offer':
        raw = data.get('price')
        try:
            price = int(raw)
        except (TypeError, ValueError):
            return {player.id_in_group: {'type': 'error', 'message': 'Invalid price.'}}

        if price <= 0:
            return {player.id_in_group: {'type': 'error', 'message': 'Price must be positive.'}}

        if player.market_role == 'buyer' and price > player.value_cost:
            return {player.id_in_group: {
                'type': 'error',
                'message': f'Your bid cannot exceed your value of ${player.value_cost}.',
            }}

        # Seller's effective floor is cost + tax (they won't rationally sell below it).
        if player.market_role == 'seller' and price < player.value_cost + tax:
            floor = player.value_cost + tax
            tax_note = f' + ${tax} tax' if tax else ''
            return {player.id_in_group: {
                'type': 'error',
                'message': f'Your ask cannot be below ${floor} (cost ${player.value_cost}{tax_note}).',
            }}

        # Price ceiling: no offer above the legal maximum.
        if ceiling is not None and price > ceiling:
            return {player.id_in_group: {
                'type': 'error',
                'message': f'A price ceiling of ${ceiling} is in effect. Offers above ${ceiling} are not allowed.',
            }}

        # Replace any existing standing offer from this player this round
        for o in Offer.filter(group=group):
            if o.round_number == player.round_number and o.player_id == player.id_in_group and o.active:
                o.active = False

        Offer.create(
            group=group,
            round_number=player.round_number,
            player_id=player.id_in_group,
            market_role=player.market_role,
            price=price,
            active=True,
        )
        return {0: _market_state(group)}

    elif msg_type == 'retract':
        for o in Offer.filter(group=group):
            if o.round_number == player.round_number and o.player_id == player.id_in_group and o.active:
                o.active = False
        return {0: _market_state(group)}

    elif msg_type == 'accept':
        target_pid = data.get('player_id')

        # Filter manually — ExtraModel.filter() only supports one kwarg reliably
        all_offers = Offer.filter(group=group)
        standing = [
            o for o in all_offers
            if o.round_number == player.round_number
            and o.player_id == target_pid
            and o.active
        ]

        if not standing:
            return {player.id_in_group: {'type': 'error', 'message': 'Offer no longer available.'}}

        offer = standing[0]

        if offer.market_role == player.market_role:
            return {player.id_in_group: {'type': 'error', 'message': 'Cannot accept an offer from the same role.'}}

        price = offer.price

        # Price ceiling applies to executed trades too.
        if ceiling is not None and price > ceiling:
            return {player.id_in_group: {
                'type': 'error',
                'message': f'Price ${price} exceeds the legal ceiling of ${ceiling}.',
            }}

        if player.market_role == 'buyer' and price > player.value_cost:
            return {player.id_in_group: {
                'type': 'error',
                'message': f'Price ${price} exceeds your value of ${player.value_cost}.',
            }}

        # Seller accepting: must cover cost + tax.
        if player.market_role == 'seller' and price < player.value_cost + tax:
            floor = player.value_cost + tax
            tax_note = f' + ${tax} tax' if tax else ''
            return {player.id_in_group: {
                'type': 'error',
                'message': f'Price ${price} is below ${floor} (cost ${player.value_cost}{tax_note}).',
            }}

        other = group.get_player_by_id(target_pid)
        if other.traded:
            return {player.id_in_group: {'type': 'error', 'message': 'That player has already traded.'}}

        # ── Execute trade ────────────────────────────────────────────────────
        offer.active = False
        for o in all_offers:
            if o.round_number == player.round_number and o.player_id == player.id_in_group and o.active:
                o.active = False

        buyer = player if player.market_role == 'buyer' else other
        seller = player if player.market_role == 'seller' else other

        buyer.traded = True
        seller.traded = True
        buyer.trade_price = price
        seller.trade_price = price
        buyer.period_earnings = buyer.value_cost - price
        seller.period_earnings = price - seller.value_cost - tax   # tax paid by seller
        buyer.payoff = buyer.period_earnings
        seller.payoff = seller.period_earnings

        all_trades = CompletedTrade.filter(group=group)
        trade_num = len([t for t in all_trades if t.round_number == player.round_number]) + 1
        CompletedTrade.create(
            group=group,
            round_number=player.round_number,
            trade_number=trade_num,
            buyer_id=buyer.id_in_group,
            seller_id=seller.id_in_group,
            price=price,
            buyer_earnings=buyer.period_earnings,
            seller_earnings=seller.period_earnings,
        )

        return {0: _market_state(group)}


def _equilibrium(buyer_values, seller_costs):
    """Compute competitive equilibrium price band and quantity from the
    schedules in play. Demand = buyer values sorted descending; supply =
    seller costs sorted ascending. Equilibrium quantity is the number of
    units where value >= cost; the price band is between the marginal
    included buyer's value and the marginal included seller's cost."""
    if not buyer_values or not seller_costs:
        return {'price_low': None, 'price_high': None, 'quantity': 0}

    demand = sorted(buyer_values, reverse=True)
    supply = sorted(seller_costs)

    q = 0
    for v, c in zip(demand, supply):
        if v >= c:
            q += 1
        else:
            break

    if q == 0:
        return {'price_low': None, 'price_high': None, 'quantity': 0}

    marginal_value = demand[q - 1]
    marginal_cost = supply[q - 1]
    return {
        'price_low': min(marginal_value, marginal_cost),
        'price_high': max(marginal_value, marginal_cost),
        'quantity': q,
    }


# ── Pages ─────────────────────────────────────────────────────────────────────
class Introduction(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1


class WaitToStart(WaitPage):
    title_text = 'Waiting for everyone to be ready…'
    body_text = 'The trading period will begin once all participants have loaded this page.'


class Trading(Page):
    timeout_seconds = C.TRADING_SECONDS

    @staticmethod
    def live_method(player, data):
        return live_trading(player, data)

    @staticmethod
    def js_vars(player: Player):
        return {
            'role': player.market_role,
            'value_cost': player.value_cost,
            'player_id': player.id_in_group,
            'trading_seconds': C.TRADING_SECONDS,
            'round_number': player.round_number,
            'num_rounds': C.NUM_ROUNDS,
            'is_bot': player.is_bot,
            'tax': tax_this_round(player.round_number),
            'ceiling': ceiling_this_round(player.round_number),
        }

    @staticmethod
    def vars_for_template(player: Player):
        return {
            'role': player.market_role,      # template still sees 'role'
            'value_cost': player.value_cost,
            'tax': tax_this_round(player.round_number),
            'ceiling': ceiling_this_round(player.round_number),
        }


class ResultsWaitPage(WaitPage):
    title_text = 'Round over — calculating results…'
    body_text = 'Please wait while everyone finishes.'


class Results(Page):
    @staticmethod
    def vars_for_template(player: Player):
        all_rounds = player.in_all_rounds()
        cumulative = sum(p.period_earnings for p in all_rounds)
        trades = CompletedTrade.filter(group=player.group, round_number=player.round_number)
        trades_sorted = sorted(trades, key=lambda t: t.trade_number)
        return {
            'role': player.market_role,
            'value_cost': player.value_cost,
            'traded': player.traded,
            'trade_price': player.trade_price,
            'period_earnings': player.period_earnings,
            'cumulative_earnings': cumulative,
            'trades': trades_sorted,
            'tax': tax_this_round(player.round_number),
            'ceiling': ceiling_this_round(player.round_number),
        }


class FinalResults(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        all_rounds = player.in_all_rounds()
        period_data = [
            {
                'round': p.round_number,
                'role_display': 'Buyer' if p.market_role == 'buyer' else 'Seller',
                'value_cost': p.value_cost,
                'traded': p.traded,
                'trade_price': p.trade_price if p.traded else '—',
                'earnings': p.period_earnings,
            }
            for p in all_rounds
        ]
        total = sum(p.period_earnings for p in all_rounds)
        return {
            'period_data': period_data,
            'total_earnings': total,
        }


class Analysis(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def _rounds_data(player):
        rounds_data = []
        for rn in range(1, C.NUM_ROUNDS + 1):
            round_players = player.in_round(rn).group.get_players()

            traders = [p for p in round_players if p.traded]
            prices = [p.trade_price for p in traders]
            avg = round(sum(prices) / len(prices), 2) if prices else None
            num_trades = len(traders) // 2  # each trade has 2 sides

            bvals = [p.value_cost for p in round_players if p.market_role == 'buyer']
            scosts = [p.value_cost for p in round_players if p.market_role == 'seller']

            # Policy-adjusted equilibrium: a seller tax shifts supply up by the
            # tax, so compute equilibrium against (cost + tax).
            tax = tax_this_round(rn)
            ceiling = ceiling_this_round(rn)
            scosts_eff = [c + tax for c in scosts]
            eq = _equilibrium(bvals, scosts_eff)

            # Label the active policy for this round.
            if tax:
                policy = f'${tax} seller tax'
            elif ceiling is not None:
                policy = f'${ceiling} price ceiling'
            else:
                policy = '—'

            rounds_data.append({
                'round': rn,
                'avg_price': avg,
                'num_trades': num_trades,
                'eq_price_low': eq['price_low'],
                'eq_price_high': eq['price_high'],
                'eq_quantity': eq['quantity'],
                'tax': tax,
                'ceiling': ceiling,
                'policy': policy,
            })
        return rounds_data

    @staticmethod
    def _schedule_data(player):
        # Cards in play are constant across rounds (same pool, reshuffled),
        # so read them from round 1 (a no-policy round).
        round_players = player.in_round(1).group.get_players()
        buyer_values = sorted(
            [p.value_cost for p in round_players if p.market_role == 'buyer'],
            reverse=True,
        )
        seller_costs = sorted(
            [p.value_cost for p in round_players if p.market_role == 'seller']
        )
        eq = _equilibrium(buyer_values, seller_costs)
        return {
            'demand': buyer_values,  # values, descending
            'supply': seller_costs,  # costs, ascending
            'eq_price_low': eq['price_low'],
            'eq_price_high': eq['price_high'],
            'eq_quantity': eq['quantity'],
        }

    @staticmethod
    def js_vars(player: Player):
        return {
            'rounds_data': Analysis._rounds_data(player),
            'schedule': Analysis._schedule_data(player),
        }

    @staticmethod
    def vars_for_template(player: Player):
        return {
            'rounds_data': Analysis._rounds_data(player),
            'schedule': Analysis._schedule_data(player),
        }


page_sequence = [
    Introduction,
    WaitToStart,
    Trading,
    ResultsWaitPage,
    Results,
    FinalResults,
    Analysis,
]