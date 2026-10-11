# Resolution d'un problème de planification de prise de vue sous incertitude
# Helene Fargier, oct 2025



# on charge le solveur lineaire
from pyscipopt import Model, quicksum
from itertools import product
import sys       
import runpy     

# on charge les données
# le fichier de donnees est passe en parametre (et non plus fixe en dur a spotProba1) :
# n'importe quel fichier au format des jeux fournis (chemin complet possible, ".py" facultatif)
cheminJeu = "spotProba1.py"
if len(sys.argv) > 1:
    cheminJeu = sys.argv[1]
if not cheminJeu.endswith(".py"):
    cheminJeu = cheminJeu + ".py"
jeu = runpy.run_path(cheminJeu)   # dictionnaire {nom de variable : valeur} du fichier de donnees
nbImages, nbInstruments, PA, DD, AN, VI, DU = jeu["nbImages"], jeu["nbInstruments"], jeu["PA"], jeu["DD"], jeu["AN"], jeu["VI"], jeu["DU"]
TY, PM, PMmax, Failure, ProbaInf, ProbaSup = jeu["TY"], jeu["PM"], jeu["PMmax"], jeu["Failure"], jeu["ProbaInf"], jeu["ProbaSup"]
print("Jeu de donnees : " + cheminJeu)



# creation du modele lineaire
#model
mymodel = Model()

# pour chaque image i ,  le solveur doit affecter la variable booleen selection[i) à 1 ssi  l'image i est selectionnée
selection = {}
for i in range(nbImages):
    selection[i] = mymodel.addVar(vtype='B', name='select' + str(i))

# pour chaque image i ,  le solveur doit affecter la variable booleen 
# assignedTo[i][j] à 1 ssi  l'image i est attribuée à l'instrument j
assignedTo = {}
for i in range(nbImages):
    ass_i = {}
    for j in range(nbInstruments):
        ass_i[j] = mymodel.addVar(vtype='B', name='assignto' + str(i) + '_' + str(j))
    assignedTo[i] = ass_i

# fonction objectif : maximiser le gain espéré total des images sélectionnées
# en tenant compte des incertitudes liées aux conditions météorologiques
# et aux pannes des instruments (critère pessimiste : probabilité de nuage = ProbaSup).
# - image mono prise par l'instrument j : PA * (1-ProbaSup) * (1-Failure[j])
# - image stereo : comptée une seule fois (avec selection[i]), et seulement si les
#   instruments 0 ET 2 fonctionnent : PA * (1-ProbaSup) * (1-Failure[0]) * (1-Failure[2])
mymodel.setObjective(quicksum(
    (1-ProbaSup[i])*(1-Failure[j])*
    assignedTo[i][j]*PA[i]
     for i in range(nbImages) if TY[i] == 1
     for j in range(nbInstruments))
  + quicksum(
    (1-ProbaSup[i])*(1-Failure[0])*(1-Failure[2])*
    selection[i]*PA[i]
     for i in range(nbImages) if TY[i] == 2),
sense='maximize')

# ajout des contraintes au modele

# la contrainte de non chevauchement
# considérons un instrument
# si, sur cet insrument, le temps de transition entre 2 images ima1 et ima2
# ne tient pas entre la fin de ima1 et le debut de ima2
# alors une seule de ces deux images au plus peut etre assignée à l'instrument

for ima1,ima2 in product(range(nbImages), range(nbImages)):
    if ima1 < ima2:
        for ins in range(nbInstruments):
            if  abs(DD[ima1][ins] - DD[ima2][ins]) * VI < DU * VI + abs(AN[ima1][ins] - AN[ima2][ins]):
                mymodel.addCons(assignedTo[ima1][ins] + assignedTo[ima2][ins] <= 1)


# la contrainte de memoire
# la memoire consommee par les images selectionnees ne depasse pas PMmax
# (PM[i] est deja doublee pour une image stereo : on ne la double pas une seconde fois)
mymodel.addCons(quicksum(PM[i] * selection[i] for i in range(nbImages)) <= PMmax)

# les contraintes d'affectation des images aux instruments
for i in range(nbImages):
    if TY[i] == 1:
        # image mono : si elle est selectionnee, elle est prise par exactement un des 3 instruments,
        # sinon par aucun
        mymodel.addCons(quicksum(assignedTo[i][j] for j in range(nbInstruments)) == selection[i])
    elif TY[i] == 2:
        # image stereo : si elle est selectionnee, elle est prise par l'instrument avant (0)
        # ET par l'instrument arriere (2), jamais par le nadir (1) ; sinon par aucun
        mymodel.addCons(assignedTo[i][0] == selection[i])
        mymodel.addCons(assignedTo[i][2] == selection[i])
        mymodel.addCons(assignedTo[i][1] == 0)



# resolution et affichage des resulats

# visualiser le problem lineaire cree
mymodel.writeProblem("pb.cip")

# lancer l'optimisation
print("Resolution")
mymodel.hideOutput(False)
mymodel.optimize()

# afficiher  les resultats mode "scip"
print('statut ' + mymodel.getStatus())
print("solution", end='\t')
print(mymodel.getBestSol())

# afficher les resultats proprement
if mymodel.getStatus() == 'optimal':
    print("\n\nProblème resolu, valeur de l'objectif " + str(mymodel.getObjVal()))
    sol=mymodel.getBestSol()
    for ima in range(nbImages):
        for ins in range(nbInstruments):
            if (mymodel.getVal(assignedTo[ima][ins]) > 0.5):  
                typeIma = "mono" if TY[ima] == 1 else "stereo"
                print("Image" + str(ima) + " (" + typeIma + ") selectionnée et  assignée à  " + str(ins) + "  (debut à " + str( DD[ima][ins]) + ")")
    # memoire utilisee par le plan
    memoire = sum(PM[i] for i in range(nbImages) if mymodel.getVal(selection[i]) > 0.5)
    print("Memoire utilisee : " + str(memoire) + " / " + str(PMmax))