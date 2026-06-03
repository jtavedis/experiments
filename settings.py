# to get to folder in terminal: cd ~/Documents/pythonProject/campi\ flegrei

from os import environ

SESSION_CONFIGS = [
    dict(
        name='guess_two_thirds',
        app_sequence=['guess_two_thirds'],
        num_demo_participants=3,
        rounds=3,
    ),
    #dict(
    #    name='wtp_survey', app_sequence=['wtp_survey'], num_demo_participants=2
    #),
    #dict(
    #    name='pgg',        # must match app folder
    #    display_name="pgg",
    #    num_demo_participants=4,
    #    app_sequence=['pgg'],
    #),
    #dict(
    #    name='bradyseism',
    #    display_name='Studio Bradisismo - Campi Flegrei',
    #    app_sequence=['bradyseism'],
    #    num_demo_participants=10,
    #),
    dict(
        name='double_auction',
        display_name='Pit Market',
        app_sequence=['double_auction'],
        num_demo_participants=4,
        # ── Customize supply / demand here ──────────────────────────────────
        # Half the players become buyers, the rest become sellers.
        # The lists below are shuffled and re-assigned each round.
        # Make both lists the same length as your intended buyer/seller count.
        buyer_values=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
        seller_costs=[1,  2, 3, 4, 5, 6, 7, 8, 9, 10],
        #num_bots=18,
        # ────────────────────────────────────────────────────────────────────
    ),
]

# ---- Rooms (single public link + unique seats) ----
ROOMS = [
    dict(
        name='ECO_212',
        display_name='ECO 212 Lobby',
        participant_label_file='_rooms/eco212_labels.txt',
        # Optional: uncomment if you want to tag sessions created from this room
        # use_secure_urls=False,
    ),
    #dict(
    #    name='bradyseism',
    #    display_name='Studio Campi Flegrei',
    #    participant_label_file='_rooms/participant_labels.txt',
    #    use_secure_urls=True,
    #),
]


# if you set a property in SESSION_CONFIG_DEFAULTS, it will be inherited by all configs
# in SESSION_CONFIGS, except those that explicitly override it.
# the session config can be accessed from methods in your apps as self.session.config,
# e.g. self.session.config['participation_fee']

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
)

PARTICIPANT_FIELDS = []
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# e.g. EUR, GBP, CNY, JPY
REAL_WORLD_CURRENCY_CODE = 'EUR'
USE_POINTS = True
POINTS_CUSTOM_NAME = 'points'

ADMIN_USERNAME = 'admin'
# for security, best to set admin password in an environment variable
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = '2674679315957'
