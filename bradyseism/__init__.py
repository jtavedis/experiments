from otree.api import *
from datetime import datetime
import random

doc = """
Pozzuoli Bradyseism Study - Online Survey Version
Replication of NdT design with:
- Ambiguity (Ellsberg) addition
- HR-LR / LR-HR treatment variation
- 7 sections total
"""


class C(BaseConstants):
    NAME_IN_URL = 'bradyseism'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

    # CRSD parameters
    CRSD_ENDOWMENT = cu(300)
    THRESHOLD = cu(600)
    HIGH_RISK = 0.9  # 9/10 disaster if threshold not met
    LOW_RISK = 0.6   # 6/10 disaster if threshold not met

    # Lottery parameters (matching NdT)
    # Section 1: Loss domain - start with 600
    LOSS_ENDOWMENT = cu(600)
    # Section 2: Gain domain - start with 0
    GAIN_ENDOWMENT = cu(0)


class Subsession(BaseSubsession):
    pass


def creating_session(subsession: Subsession):
    """Assign treatment (HR-LR vs LR-HR) balanced across participants"""
    players = subsession.get_players()
    
    # Alternate treatment assignment for balance
    for i, player in enumerate(players):
        if i % 2 == 0:
            player.treatment = 'HR_LR'  # High risk first, then low risk
        else:
            player.treatment = 'LR_HR'  # Low risk first, then high risk


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # Treatment assignment
    treatment = models.StringField()  # 'HR_LR' or 'LR_HR'
    
    # Tracking
    start_time = models.StringField(blank=True)
    end_time = models.StringField(blank=True)
    duration_minutes = models.FloatField(blank=True)

    # ============ SECTION 1: LOSS LOTTERY ============
    # Comprehension check for lottery (only for Section 1)
    comp_check_lottery = models.IntegerField(
        label="Se acquisti 2 biglietti e viene estratto il biglietto numero 3 o 4, cosa succede?",
        choices=[
            [1, 'Perdo solo una parte dei miei 600€'],
            [2, 'Perdo tutti i 600€'],
            [3, 'Non perdo nulla']
        ],
        widget=widgets.RadioSelect
    )
    
    lottery_loss_choice = models.IntegerField(
        choices=[[1, '1 biglietto'], [2, '2 biglietti'], [3, '3 biglietti'], [4, '4 biglietti']],
        label="Quanti biglietti acquisti?",
        widget=widgets.RadioSelect
    )

    # ============ SECTION 2: GAIN LOTTERY ============
    lottery_gain_choice = models.IntegerField(
        choices=[[1, '1 biglietto'], [2, '2 biglietti'], [3, '3 biglietti'], [4, '4 biglietti']],
        label="Quanti biglietti acquisti?",
        widget=widgets.RadioSelect
    )

    # ============ SECTION 3: ELLSBERG AMBIGUITY ============
    # Comprehension check for Ellsberg
    comp_check_ellsberg = models.IntegerField(
        label="Qual è la differenza tra le due urne?",
        choices=[
            [1, 'L\'Urna A ha più palline rosse'],
            [2, 'Nell\'Urna A conosco la composizione, nell\'Urna B no'],
            [3, 'I premi sono diversi tra le due urne']
        ],
        widget=widgets.RadioSelect
    )
    
    ellsberg_choice = models.StringField(
        choices=[['urn_a', 'Urna A (composizione nota)'], ['urn_b', 'Urna B (composizione sconosciuta)']],
        label="Da quale urna preferisci estrarre?",
        widget=widgets.RadioSelect
    )

    # ============ SECTION 4 & 5: CRSD (order depends on treatment) ============
    # Comprehension check for CRSD (only before first CRSD)
    comp_check_crsd = models.IntegerField(
        label="Se il tuo gruppo trasferisce in totale 500€ (meno della soglia di 600€) e viene estratto un numero da 1 a 9, cosa succede?",
        choices=[
            [1, 'Tutti salvano gli euro trattenuti'],
            [2, 'Tutti perdono tutto'],
            [3, 'Solo chi ha trasferito di più salva i propri euro']
        ],
        widget=widgets.RadioSelect
    )
    
    # CRSD High Risk (90%)
    contribution_high_risk = models.CurrencyField(
        min=0, max=C.CRSD_ENDOWMENT,
        label="Quanti euro trasferisci al fondo comune?"
    )
    belief_personal_hr = models.CurrencyField(
        min=0, max=C.CRSD_ENDOWMENT,
        label="Secondo te, quanti euro dovrebbero trasferire in media al fondo comune i quattro membri del tuo gruppo, te compreso?"
    )
    belief_empirical_hr = models.CurrencyField(
        min=0, max=C.CRSD_ENDOWMENT,
        label="Secondo te, quanti euro di fatto trasferiranno in media al fondo comune gli altri tre membri del tuo gruppo?"
    )
    belief_normative_hr = models.CurrencyField(
        min=0, max=C.CRSD_ENDOWMENT,
        label="Secondo te, quanti euro gli altri tre membri del gruppo pensano che voi quattro, in media, dovreste trasferire al fondo comune?"
    )

    # CRSD Low Risk (60%)
    contribution_low_risk = models.CurrencyField(
        min=0, max=C.CRSD_ENDOWMENT,
        label="Quanti euro trasferisci al fondo comune?"
    )
    belief_personal_lr = models.CurrencyField(
        min=0, max=C.CRSD_ENDOWMENT,
        label="Secondo te, quanti euro dovrebbero trasferire in media al fondo comune i quattro membri del tuo gruppo, te compreso?"
    )
    belief_empirical_lr = models.CurrencyField(
        min=0, max=C.CRSD_ENDOWMENT,
        label="Secondo te, quanti euro di fatto trasferiranno in media al fondo comune gli altri tre membri del tuo gruppo?"
    )
    belief_normative_lr = models.CurrencyField(
        min=0, max=C.CRSD_ENDOWMENT,
        label="Secondo te, quanti euro gli altri tre membri del gruppo pensano che voi quattro, in media, dovreste trasferire al fondo comune?"
    )

    # ============ SECTION 6: CRSD AMBIGUOUS ============
    contribution_ambiguous = models.CurrencyField(
        min=0, max=C.CRSD_ENDOWMENT,
        label="Quanti euro trasferisci al fondo comune?"
    )
    belief_personal_amb = models.CurrencyField(
        min=0, max=C.CRSD_ENDOWMENT,
        label="Secondo te, quanti euro dovrebbero trasferire in media al fondo comune i quattro membri del tuo gruppo, te compreso?"
    )
    belief_empirical_amb = models.CurrencyField(
        min=0, max=C.CRSD_ENDOWMENT,
        label="Secondo te, quanti euro di fatto trasferiranno in media al fondo comune gli altri tre membri del tuo gruppo?"
    )
    belief_normative_amb = models.CurrencyField(
        min=0, max=C.CRSD_ENDOWMENT,
        label="Secondo te, quanti euro gli altri tre membri del gruppo pensano che voi quattro, in media, dovreste trasferire al fondo comune?"
    )

    # ============ SECTION 7: QUESTIONNAIRE ============
    # Demographics
    age = models.IntegerField(min=18, max=100, label="Età")
    gender = models.StringField(
        choices=[['M', 'M'], ['F', 'F']],
        label="Genere",
        widget=widgets.RadioSelectHorizontal
    )
    residence_comune = models.StringField(label="Comune di Residenza")
    residence_regione = models.StringField(label="Regione di Residenza")
    
    education = models.IntegerField(
        choices=[
            [1, 'Licenza elementare'],
            [2, 'Licenza media'],
            [3, 'Diploma'],
            [4, 'Laurea'],
            [5, 'Post Laurea (Master/Dottorato)']
        ],
        label="Titolo di studio di cui si è in possesso",
        widget=widgets.RadioSelect
    )
    
    employment = models.IntegerField(
        choices=[
            [1, 'Artista'],
            [2, 'Casalinga'],
            [3, 'Dipendente (pubblico/privato)'],
            [4, 'Disoccupato'],
            [5, 'Libero professionista'],
            [6, 'Lavoratore autonomo (autoimpiego)'],
            [7, 'Pensionato/Invalido'],
            [8, 'Studente'],
            [9, 'Altro']
        ],
        label="Professione",
        widget=widgets.RadioSelect
    )

    # Trust
    trust_general = models.IntegerField(
        choices=list(range(1, 11)),
        label="In generale, diresti che puoi fidarti della maggior parte delle persone? O diresti che non si è mai troppo prudenti? (1 = non disposto a fidarti affatto, 10 = sempre disposto a fidarti)",
        widget=widgets.RadioSelectHorizontal
    )

    # Time preference
    time_preference = models.StringField(
        choices=[
            ['a', '(a) il 20% della tua vincita'],
            ['b', '(b) il 10%'],
            ['c', '(c) il 5%'],
            ['d', '(d) il 2%']
        ],
        label="Immagina di aver vinto alla lotteria e di ricevere una somma pari al reddito che la tua famiglia guadagna in un anno. Riceverai il denaro tra un anno. Per ottenere il denaro immediatamente, rinunceresti a:",
        widget=widgets.RadioSelect
    )

    # Risk attitude
    risk_self_report = models.IntegerField(
        choices=list(range(1, 11)),
        label="In generale, ti descriveresti come una persona disposta a correre dei rischi o cerchi di evitarli? (1 = non sei affatto disposto a correre rischi, 10 = sei sempre disposto a correre tutti i rischi)",
        widget=widgets.RadioSelectHorizontal
    )

    # Big Five (short version)
    big5_reserved = models.IntegerField(choices=list(range(1, 6)), label="Mi considero una persona riservata", widget=widgets.RadioSelectHorizontal)
    big5_trusting = models.IntegerField(choices=list(range(1, 6)), label="Mi considero una persona generalmente fiduciosa", widget=widgets.RadioSelectHorizontal)
    big5_lazy = models.IntegerField(choices=list(range(1, 6)), label="Mi considero una persona che tende ad essere pigra", widget=widgets.RadioSelectHorizontal)
    big5_relaxed = models.IntegerField(choices=list(range(1, 6)), label="Mi considero una persona rilassata, che gestisce bene lo stress", widget=widgets.RadioSelectHorizontal)
    big5_artistic = models.IntegerField(choices=list(range(1, 6)), label="Mi considero una persona con pochi interessi artistici", widget=widgets.RadioSelectHorizontal)
    big5_outgoing = models.IntegerField(choices=list(range(1, 6)), label="Mi considero una persona estroversa", widget=widgets.RadioSelectHorizontal)
    big5_fault_finding = models.IntegerField(choices=list(range(1, 6)), label="Mi considero una persona che tende a trovare difetti negli altri", widget=widgets.RadioSelectHorizontal)
    big5_thorough = models.IntegerField(choices=list(range(1, 6)), label="Mi considero una persona che svolge il proprio lavoro in modo accurato", widget=widgets.RadioSelectHorizontal)
    big5_nervous = models.IntegerField(choices=list(range(1, 6)), label="Mi considero una persona che si innervosisce facilmente", widget=widgets.RadioSelectHorizontal)
    big5_imaginative = models.IntegerField(choices=list(range(1, 6)), label="Mi considero una persona con una fervida immaginazione", widget=widgets.RadioSelectHorizontal)

    # Wellbeing
    wellbeing_like_life = models.IntegerField(choices=list(range(1, 11)), label="Mi piace la mia vita", widget=widgets.RadioSelectHorizontal)
    wellbeing_happy_person = models.IntegerField(choices=list(range(1, 11)), label="Sono una persona felice", widget=widgets.RadioSelectHorizontal)
    wellbeing_satisfied = models.IntegerField(choices=list(range(1, 11)), label="Sono soddisfatto della mia vita", widget=widgets.RadioSelectHorizontal)
    wellbeing_life_happy = models.IntegerField(choices=list(range(1, 11)), label="La mia vita mi rende felice", widget=widgets.RadioSelectHorizontal)
    wellbeing_life_is_happy = models.IntegerField(choices=list(range(1, 11)), label="La mia vita è felice", widget=widgets.RadioSelectHorizontal)
    wellbeing_wonderful = models.IntegerField(choices=list(range(1, 11)), label="La mia vita è meravigliosa", widget=widgets.RadioSelectHorizontal)
    wellbeing_feel_good = models.IntegerField(choices=list(range(1, 11)), label="Mi sento bene", widget=widgets.RadioSelectHorizontal)

    # Perceived Stress Scale (PSS-10)
    pss_upset = models.IntegerField(choices=list(range(1, 6)), label="Nell'ultimo mese, quanto spesso ti sei sentito turbato a causa di qualcosa che è successo in modo inaspettato?", widget=widgets.RadioSelectHorizontal)
    pss_unable_control = models.IntegerField(choices=list(range(1, 6)), label="Nell'ultimo mese, quanto spesso ti sei sentito incapace di controllare le cose importanti della tua vita?", widget=widgets.RadioSelectHorizontal)
    pss_nervous = models.IntegerField(choices=list(range(1, 6)), label="Nell'ultimo mese, quanto spesso ti sei sentito nervoso e stressato?", widget=widgets.RadioSelectHorizontal)
    pss_confident = models.IntegerField(choices=list(range(1, 6)), label="Nell'ultimo mese, quanto spesso ti sei sentito sicuro di poter gestire le cose importanti della tua vita?", widget=widgets.RadioSelectHorizontal)
    pss_going_well = models.IntegerField(choices=list(range(1, 6)), label="Nell'ultimo mese, quanto spesso hai sentito che le cose stavano andando per il verso giusto?", widget=widgets.RadioSelectHorizontal)
    pss_could_not_cope = models.IntegerField(choices=list(range(1, 6)), label="Nell'ultimo mese, quanto spesso ti sei sentito incapace di far fronte a tutte le cose che dovevi fare?", widget=widgets.RadioSelectHorizontal)
    pss_control_irritations = models.IntegerField(choices=list(range(1, 6)), label="Nell'ultimo mese, quanto spesso sei riuscito a controllare le irritazioni?", widget=widgets.RadioSelectHorizontal)
    pss_on_top = models.IntegerField(choices=list(range(1, 6)), label="Nell'ultimo mese, quanto spesso ti sei sentito padrone della situazione?", widget=widgets.RadioSelectHorizontal)
    pss_angered = models.IntegerField(choices=list(range(1, 6)), label="Nell'ultimo mese, quanto spesso ti sei sentito arrabbiato per cose che sono successe e che erano al di fuori del tuo controllo?", widget=widgets.RadioSelectHorizontal)
    pss_difficulties_piling = models.IntegerField(choices=list(range(1, 6)), label="Nell'ultimo mese, quanto spesso ti sei sentito sopraffatto da una mole di cose da fare che non riuscivi a gestire?", widget=widgets.RadioSelectHorizontal)

    # Location question for conditional bradyseism questions
    location = models.StringField(
        choices=[
            ['pozzuoli', 'Sì, vivo nell\'area dei Campi Flegrei (Pozzuoli, Bagnoli, o zone limitrofe)'],
            ['control', 'No, vivo in un\'altra zona']
        ],
        label="Vivi nell'area dei Campi Flegrei?",
        widget=widgets.RadioSelect
    )

    # Bradyseism experience (only for Pozzuoli)
    years_in_area = models.IntegerField(
        min=0, max=100,
        label="Da quanti anni vivi nell'area dei Campi Flegrei?",
        blank=True
    )
    experienced_1982 = models.BooleanField(
        label="Hai vissuto la crisi bradisismica del 1982-1984?",
        choices=[[True, 'Sì'], [False, 'No']],
        widget=widgets.RadioSelect,
        blank=True
    )
    experienced_evacuation = models.BooleanField(
        label="Hai mai dovuto evacuare a causa del bradisismo?",
        choices=[[True, 'Sì'], [False, 'No']],
        widget=widgets.RadioSelect,
        blank=True
    )


# ============ PAGES ============

class Welcome(Page):
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.start_time = datetime.now().isoformat()


class GeneralInstructions(Page):
    """Overview of the experiment structure - like reading the paper instructions"""
    pass


# --- SECTION 1: LOSS LOTTERY ---

class Section1Instructions(Page):
    """Loss lottery instructions"""
    pass


class Section1CompCheck(Page):
    form_model = 'player'
    form_fields = ['comp_check_lottery']

    @staticmethod
    def error_message(player, values):
        if values['comp_check_lottery'] != 2:
            return 'Risposta non corretta. Rileggi le istruzioni: se acquisti 2 biglietti e viene estratto il 3 o 4, perdi tutti i 600€.'


class Section1Task(Page):
    form_model = 'player'
    form_fields = ['lottery_loss_choice']


# --- SECTION 2: GAIN LOTTERY ---

class Section2Instructions(Page):
    """Gain lottery instructions"""
    pass


class Section2Task(Page):
    form_model = 'player'
    form_fields = ['lottery_gain_choice']


# --- SECTION 3: ELLSBERG AMBIGUITY ---

class Section3Instructions(Page):
    """Ellsberg two-urn instructions"""
    pass


class Section3CompCheck(Page):
    form_model = 'player'
    form_fields = ['comp_check_ellsberg']

    @staticmethod
    def error_message(player, values):
        if values['comp_check_ellsberg'] != 2:
            return 'Risposta non corretta. La differenza è che nell\'Urna A conosci la composizione (50 rosse, 50 nere), mentre nell\'Urna B non la conosci.'


class Section3Task(Page):
    form_model = 'player'
    form_fields = ['ellsberg_choice']


# --- SECTION 4: CRSD FIRST (depends on treatment) ---

class Section4Instructions(Page):
    """CRSD instructions - first risk level based on treatment"""
    
    @staticmethod
    def vars_for_template(player):
        if player.treatment == 'HR_LR':
            return dict(
                disaster_numbers="da 1 a 9",
                safe_number="10",
                risk_description="Se il numero estratto va da 1 a 9"
            )
        else:  # LR_HR
            return dict(
                disaster_numbers="da 1 a 6",
                safe_number="da 7 a 10",
                risk_description="Se il numero estratto va da 1 a 6"
            )


class Section4CompCheck(Page):
    form_model = 'player'
    form_fields = ['comp_check_crsd']

    @staticmethod
    def error_message(player, values):
        if values['comp_check_crsd'] != 2:
            return 'Risposta non corretta. Se il fondo comune non raggiunge 600€ e viene estratto un numero nel range di rischio, tutti perdono tutto.'


class Section4Task(Page):
    form_model = 'player'
    
    @staticmethod
    def get_form_fields(player):
        if player.treatment == 'HR_LR':
            return ['contribution_high_risk', 'belief_personal_hr', 'belief_empirical_hr', 'belief_normative_hr']
        else:
            return ['contribution_low_risk', 'belief_personal_lr', 'belief_empirical_lr', 'belief_normative_lr']
    
    @staticmethod
    def vars_for_template(player):
        if player.treatment == 'HR_LR':
            return dict(
                disaster_numbers="da 1 a 9",
                safe_number="10",
                section_number=4
            )
        else:
            return dict(
                disaster_numbers="da 1 a 6",
                safe_number="da 7 a 10",
                section_number=4
            )


# --- SECTION 5: CRSD SECOND (depends on treatment) ---

class Section5Instructions(Page):
    """CRSD instructions - second risk level based on treatment"""
    
    @staticmethod
    def vars_for_template(player):
        if player.treatment == 'HR_LR':
            return dict(
                disaster_numbers="da 1 a 6",
                safe_number="da 7 a 10",
                risk_description="Se il numero estratto va da 1 a 6"
            )
        else:  # LR_HR
            return dict(
                disaster_numbers="da 1 a 9",
                safe_number="10",
                risk_description="Se il numero estratto va da 1 a 9"
            )


class Section5Task(Page):
    form_model = 'player'
    
    @staticmethod
    def get_form_fields(player):
        if player.treatment == 'HR_LR':
            return ['contribution_low_risk', 'belief_personal_lr', 'belief_empirical_lr', 'belief_normative_lr']
        else:
            return ['contribution_high_risk', 'belief_personal_hr', 'belief_empirical_hr', 'belief_normative_hr']
    
    @staticmethod
    def vars_for_template(player):
        if player.treatment == 'HR_LR':
            return dict(
                disaster_numbers="da 1 a 6",
                safe_number="da 7 a 10",
                section_number=5
            )
        else:
            return dict(
                disaster_numbers="da 1 a 9",
                safe_number="10",
                section_number=5
            )


# --- SECTION 6: CRSD AMBIGUOUS ---

class Section6Instructions(Page):
    """CRSD ambiguous risk instructions"""
    pass


class Section6Task(Page):
    form_model = 'player'
    form_fields = ['contribution_ambiguous', 'belief_personal_amb', 'belief_empirical_amb', 'belief_normative_amb']


# --- SECTION 7: QUESTIONNAIRE ---

class Questionnaire1(Page):
    """Demographics"""
    form_model = 'player'
    form_fields = ['age', 'gender', 'residence_comune', 'residence_regione', 'education', 'employment']


class Questionnaire2(Page):
    """Trust, time preference, risk"""
    form_model = 'player'
    form_fields = ['trust_general', 'time_preference', 'risk_self_report']


class Questionnaire3(Page):
    """Big Five personality"""
    form_model = 'player'
    form_fields = [
        'big5_reserved', 'big5_trusting', 'big5_lazy', 'big5_relaxed', 'big5_artistic',
        'big5_outgoing', 'big5_fault_finding', 'big5_thorough', 'big5_nervous', 'big5_imaginative'
    ]


class Questionnaire4(Page):
    """Wellbeing"""
    form_model = 'player'
    form_fields = [
        'wellbeing_like_life', 'wellbeing_happy_person', 'wellbeing_satisfied',
        'wellbeing_life_happy', 'wellbeing_life_is_happy', 'wellbeing_wonderful', 'wellbeing_feel_good'
    ]


class Questionnaire5(Page):
    """Perceived Stress Scale"""
    form_model = 'player'
    form_fields = [
        'pss_upset', 'pss_unable_control', 'pss_nervous', 'pss_confident', 'pss_going_well',
        'pss_could_not_cope', 'pss_control_irritations', 'pss_on_top', 'pss_angered', 'pss_difficulties_piling'
    ]


class QuestionnaireLocation(Page):
    """Location question to determine if bradyseism questions shown"""
    form_model = 'player'
    form_fields = ['location']


class QuestionnaireBradyseism(Page):
    """Bradyseism experience - only for Pozzuoli residents"""
    form_model = 'player'
    form_fields = ['years_in_area', 'experienced_1982', 'experienced_evacuation']

    @staticmethod
    def is_displayed(player):
        return player.location == 'pozzuoli'


class ThankYou(Page):
    @staticmethod
    def before_next_page(player, timeout_happened):
        player.end_time = datetime.now().isoformat()
        if player.start_time:
            start = datetime.fromisoformat(player.start_time)
            end = datetime.fromisoformat(player.end_time)
            player.duration_minutes = (end - start).total_seconds() / 60
        player.participant.finished = True


page_sequence = [
    Welcome,
    GeneralInstructions,
    # Section 1: Loss Lottery
    Section1Instructions,
    Section1CompCheck,
    Section1Task,
    # Section 2: Gain Lottery
    Section2Instructions,
    Section2Task,
    # Section 3: Ellsberg
    Section3Instructions,
    Section3CompCheck,
    Section3Task,
    # Section 4: CRSD First
    Section4Instructions,
    Section4CompCheck,
    Section4Task,
    # Section 5: CRSD Second
    Section5Instructions,
    Section5Task,
    # Section 6: CRSD Ambiguous
    Section6Instructions,
    Section6Task,
    # Section 7: Questionnaire
    Questionnaire1,
    Questionnaire2,
    Questionnaire3,
    Questionnaire4,
    Questionnaire5,
    QuestionnaireLocation,
    QuestionnaireBradyseism,
    ThankYou,
]
