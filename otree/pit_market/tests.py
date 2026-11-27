import asyncio
import inspect

from otree.api import Bot, Submission, expect

from . import *


class PlayerBot(Bot):
    def play_round(self):
        if self.round_number == 1:
            yield EnterName, dict(name_entry=f'Bot{self.player.id_in_group}')
            yield Introduction
        yield Submission(Trading, check_html=False, timeout_happened=True)
        p, g = self.player, self.group
        # Bargaining measures and period results are filled in for the standard export.
        expect(p.conversations >= p.partners_contacted, True)
        expect(p.field_maybe_none('pos_x') is not None, True)
        if self.round_number > 1:
            # same seat every period
            prev = p.in_round(1)
            expect((p.pos_x, p.pos_y), (prev.pos_x, prev.pos_y))
        if p.partners_contacted:
            expect(p.first_contact_rank >= 1 and p.mean_contact_dist >= 0, True)
        if p.traded:
            expect(p.partner_rank >= 1, True)
        if p.traded:
            expect(p.trade_order >= 1, True)
            expect(p.trade_time >= 0, True)
        if p.offers_sent:
            expect(p.field_maybe_none('first_offer_price') is not None, True)
        expect(g.num_trades, len([q for q in g.get_players() if q.traded]) // 2)
        expect(g.max_surplus >= 0, True)   # can be 0 in a tiny class (e.g. buyer 6, seller 7)
        yield Results
        if self.round_number == C.NUM_ROUNDS:
            yield Survey, dict(survey_a=4, survey_b=3, survey_c=4, survey_d=2)
            yield Submission(FinalResults, check_html=False)


def call_live_method(method, round_number, **kwargs):
    def send(pid, **data):
        res = method(pid, data)
        if inspect.isasyncgen(res):
            # oTree 6 wraps live methods in an async generator
            async def drain():
                return [x async for x in res]
            items = asyncio.new_event_loop().run_until_complete(drain())
            res = items[-1] if items else None
        return res or {}

    state = send(1, type='get_state')[1]
    buyers = [p['id'] for p in state['players'] if p['role'] == 'buyer']
    sellers = [p['id'] for p in state['players'] if p['role'] == 'seller']
    b, s = buyers[0], sellers[0]

    # Same-side chat is refused.
    if len(buyers) > 1:
        r = send(b, type='chat', to=buyers[1], text='hi')
        expect(r[b]['type'], 'error')

    # Chat reaches only the two people talking.
    r = send(b, type='chat', to=s, text='what would you sell at?')
    expect(set(r), {b, s})
    expect(r[s]['msgs'][-1]['text'], 'what would you sell at?')

    # No price or card is ever public; announcing a price is not possible.
    pub = [p for p in state['players'] if p['id'] == s][0]
    expect(set(pub), {'id', 'name', 'role', 'traded', 'x', 'y'})
    expect(0 <= pub['x'] <= 600 and 0 <= pub['y'] <= 400, True)

    # Opening a conversation is recorded silently: nobody gets a message.
    expect(send(b, type='open', to=s, via='floor'), {})
    expect([m for m in send(s, type='get_state')[s]['msgs'] if m['kind'] == 'open'], [])
    expect(send(s, type='post_price', price='7.5')[s]['type'], 'error')

    # Front desk: price above every buyer value is invalidated, both keep trading.
    send(b, type='offer', to=s, price=50)
    offer = [m for m in send(s, type='get_state')[s]['msgs'] if m['kind'] == 'offer'][-1]
    r = send(s, type='accept', offer_id=offer['id'])
    me = r[s]
    expect([m for m in me['msgs'] if m['id'] == offer['id']][0]['status'], 'invalid')
    expect(me['me']['traded'], False)
    expect('Front desk' in me['msgs'][-1]['text'], True)

    # A new offer replaces the old open one; only the receiver may accept.
    send(b, type='offer', to=s, price=1)
    send(b, type='offer', to=s, price=2)
    msgs = send(b, type='get_state')[b]['msgs']
    offers = [m for m in msgs if m['kind'] == 'offer']
    expect(offers[-2]['status'], 'replaced')
    r = send(b, type='accept', offer_id=offers[-1]['id'])
    expect(r[b]['type'], 'error')
    send(b, type='withdraw', offer_id=offers[-1]['id'])

    # Several buyers make offers to one seller; the seller picks the best valid one.
    price = 6 if round_number != 8 else 6
    traded = False
    for buyer in buyers:
        send(buyer, type='offer', to=s, price=price)
    incoming = [m for m in send(s, type='get_state')[s]['msgs']
                if m['kind'] == 'offer' and m['status'] == 'open' and m['to'] == s]
    expect(len(incoming), len(buyers))
    for m in incoming:
        r = send(s, type='accept', offer_id=m['id'])
        if r.get(s, {}).get('me', {}).get('traded'):
            traded = True
            buyer = m['from']
            break
    if traded:
        st = send(s, type='get_state')[s]
        expect(len(st['board']), 1)
        expect(st['board'][0]['price'], price)
        # Everyone else's offers to this seller have expired.
        expect(all(m['status'] != 'open' for m in st['msgs'] if m['kind'] == 'offer'), True)
        # Traded players can no longer act.
        expect(send(s, type='chat', to=buyer, text='x')[s]['type'], 'error')
        expect(send(buyer, type='offer', to=s, price=3)[buyer]['type'], 'error')

    # Price ceiling round: a trade above the ceiling is invalidated.
    if round_number == 8 and len(sellers) > 1 and len(buyers) > 1:
        s2 = sellers[1]
        b2 = [x for x in buyers if not [p for p in send(x, type='get_state')[x]['players'] if p['id'] == x][0]['traded']][0]
        send(b2, type='offer', to=s2, price=6.5)
        o = [m for m in send(s2, type='get_state')[s2]['msgs'] if m['kind'] == 'offer' and m['status'] == 'open'][-1]
        r = send(s2, type='accept', offer_id=o['id'])
        expect('ceiling' in r[s2]['msgs'][-1]['text'] or 'invalidated' in r[s2]['msgs'][-1]['text'], True)
        expect(r[s2]['me']['traded'], False)
