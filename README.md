# classroom-experiments
instructions and code for classroom experiments used in a principles of microeconomics course. each experiment is available in two versions: a pen and paper (card game) version and a computerized version built with oTree.

the textbook used for the course is CORE Econ The Economy 2.0: Microeconomics (https://books.core-econ.org/the-economy/microeconomics/0-3-contents.html).

each experiment, with the exception of experiment 5, was conducted before theory lectures covering the concepts faced in the experiments.

the idea is to have an experiment for each unit covered. however, for unit 1 and 2 there is no experiment. the first experiment, the guessing game, was conducted on the first day of class to introduce the idea of experiments to the students.

## repository structure

```
├── instructions/   pen and paper versions
├── otree/          computerized versions (oTree)
└── README.md
```

### instructions/
step-by-step instructions for running each experiment in class with pen and paper or cards.

### otree/
the oTree project containing computerized versions of the same experiments. the games are designed to match the pen and paper versions, so the two formats can be used interchangeably or compared.

the folder is a complete, self-contained oTree project:

- `settings.py` defines the session configurations, one for each experiment, and is what oTree reads to know which experiments are available
- each experiment is its own app (a subfolder containing the pages, templates, and game logic)
- `requirements.txt` lists the python packages needed

to use the experiments:

1. install oTree (https://otree.readthedocs.io) and python
2. download or clone this repository
3. open a terminal inside the `otree` folder (oTree commands must be run from the folder that contains `settings.py`)
4. install the requirements with `pip install -r requirements.txt`
5. run `otree devserver` to test locally, then open http://localhost:8000 in a browser
6. to run the experiments with students, host the project on your own server (see the oTree documentation on deployment) and share the session links with participants

you are free to edit the apps, change the parameters (payoffs, number of rounds, group sizes) in `settings.py` or in each app, and adapt them to your own course.

## how the experiments were used in the course
1. experiment 1 - guessing game - class intro and introduction to "thinking about what others are thinking"
2. experiment 2 - allocation task - textbook unit 3 allocation task, card game (before unit 3 theory)
3. experiment 3 - prisoner's dilemma (Holt and Capra 2000) - card game (before unit 4 theory)
4. experiment 4 - ultimatum and impunity game (Güth et al. 1982, Forsythe et al. 1994) - card game (before unit 5 theory)
5. experiment 5 - strategic price setting - textbook unit 7 (after unit 7 theory)
6. experiment 6 - pit market (Holt 1996) - card game (before unit 8 theory)
7. experiment 7 - public goods game and collective-risk social dilemma (Holt and Laury 1997, Milinski et al. 2008) - card game (before unit 10 theory)
