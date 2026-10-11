# Variante de spotProba1 (cas donne en commentaire dans spotProba1.py)
# Maximum value of the objective : 60  (no cloud; instrument 2 is down )
#  no image is assigned on instrument 2 ;

nbImages = 3

TY = [1, 2, 1]

PM = [10, 20, 10]

PA = [10, 20, 40]

nbInstruments = 3

DD = [[130, 230, 330], [150, 0, 350], [220, 320, 420]]

AN = [[10, 10, 10], [5, 0, 5], [20, 20, 20]]

DU = 20

VI = 1

PMmax = 50

# Probability of Cloudy Weather
ProbaInf = [0, 0, 0]
ProbaSup = [0, 0, 0]
# proba of failure of each instrument
Failure = [0, 1, 0]
