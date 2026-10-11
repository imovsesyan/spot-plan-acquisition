# Interface du planificateur d'acquisition SPOT
# lancement :  streamlit run interface.py
#
# L'interface ne contient pas de modele : elle lance spotProba.py avec le fichier de donnees
# choisi en parametre (exactement comme "python spotProba.py <fichier>"), puis affiche le plan.
# Toute modification du modele (contraintes, fonction objectif) apparait donc ici automatiquement.
# L'apparence (taille du texte, couleurs) est reglee dans .streamlit/config.toml

import os
import sys
import runpy
import tempfile
import pandas as pd
import altair as alt
import streamlit as st

dossier = os.path.dirname(os.path.abspath(__file__))   # dossier du projet
nomsInstruments = ["0 (avant)", "1 (nadir)", "2 (arrière)"]
couleurs = {"mono": "#2457A6", "stéréo": "#B45309"}     # bleu / orange
largeurFenetre = 300            # secondes visibles quand le chronogramme defile
dureeMaxSansDefilement = 450    # au-dela, le chronogramme defile au lieu de tout afficher

st.set_page_config(page_title="Plan d'acquisition SPOT", layout="wide")   # toute la largeur de l'ecran


# 1. choix du fichier de donnees
################################

st.sidebar.header("Jeu de données")
jeuxFournis = sorted(f for f in os.listdir(dossier)
                     if f.startswith("spotProba") and f not in ("spotProba.py", "spotProbaPartial.py"))
choix = st.sidebar.selectbox("Jeu fourni", jeuxFournis)
fichierImporte = st.sidebar.file_uploader("Ou importer un fichier (.py)", type="py")

if fichierImporte is not None:
    # le fichier importe est enregistre dans un dossier temporaire pour etre passe en parametre
    cheminJeu = os.path.join(tempfile.gettempdir(), fichierImporte.name)
    with open(cheminJeu, "wb") as f:
        f.write(fichierImporte.getbuffer())
else:
    cheminJeu = os.path.join(dossier, choix)


# 2. resolution : on lance spotProba.py avec le fichier en parametre
####################################################################

sys.argv = ["spotProba.py", cheminJeu]
try:
    with st.spinner("Résolution avec SCIP..."):
        r = runpy.run_path(os.path.join(dossier, "spotProba.py"))   # variables de spotProba.py
except Exception as erreur:
    st.error("Ce fichier ne peut pas être lu : " + str(erreur) + ". Il doit définir les mêmes "
             "variables que les jeux fournis (nbImages, TY, PA, PM, DD, AN, DU, VI, PMmax...).")
    st.stop()

mymodel, selection, assignedTo = r["mymodel"], r["selection"], r["assignedTo"]
nbImages, nbInstruments, TY, PA, PM, PMmax = r["nbImages"], r["nbInstruments"], r["TY"], r["PA"], r["PM"], r["PMmax"]
DD, AN, DU, VI = r["DD"], r["AN"], r["DU"], r["VI"]

if mymodel.getStatus() != "optimal":
    st.warning("Le solveur n'a pas trouvé de plan optimal (statut : " + mymodel.getStatus() + ").")
    st.stop()


# 3. affichage des resultats
############################

st.title("Plan d'acquisition SPOT")
st.caption("Jeu de données : " + os.path.basename(cheminJeu))

selectionnees = [i for i in range(nbImages) if mymodel.getVal(selection[i]) > 0.5]
nonRetenues = [i for i in range(nbImages) if i not in selectionnees]
memoire = sum(PM[i] for i in selectionnees)

col1, col2, col3 = st.columns(3)
col1.metric("Gain espéré", "{:g}".format(round(mymodel.getObjVal(), 3)))   # valeur de l'objectif ; 70 et non 70.0
col2.metric("Images retenues", str(len(selectionnees)) + " / " + str(nbImages))
col3.metric("Mémoire", str(memoire) + " / " + str(PMmax))

# une ligne par acquisition (une image stereo donne deux acquisitions : avant et arriere)
acquisitions = []
for i in selectionnees:
    for j in range(nbInstruments):
        if mymodel.getVal(assignedTo[i][j]) > 0.5:
            acquisitions.append({"Image": i, "Type": "mono" if TY[i] == 1 else "stéréo",
                                 "Instrument": nomsInstruments[j], "Début": DD[i][j],
                                 "Fin": DD[i][j] + DU, "Milieu": DD[i][j] + DU / 2, "Angle": AN[i][j]})
acq = pd.DataFrame(acquisitions)

ongletChrono, ongletPlan, ongletDonnees = st.tabs(["Chronogramme", "Plan", "Données"])

# chronogramme : une barre par acquisition, de DD (debut) a DD + DU (fin), sur chaque instrument
with ongletChrono:
    if acq.empty:
        st.info("Aucune image retenue : choisissez un autre jeu de données.")
    else:
        debutMin, finMax = int(acq["Début"].min()) - 10, int(acq["Fin"].max()) + 10
        if finMax - debutMin > dureeMaxSansDefilement:
            # trop long pour tout afficher lisiblement : on fait defiler une fenetre de 300 s
            debut = st.slider("Faire défiler (secondes)", debutMin, finMax - largeurFenetre, debutMin, step=10)
            fenetre = [debut, debut + largeurFenetre]
        else:
            fenetre = [debutMin, finMax]

        echelleX = alt.X("Début:Q", title="temps depuis le début de la révolution (s)",
                         scale=alt.Scale(domain=fenetre))
        axeY = alt.Y("Instrument:N", sort=nomsInstruments, title=None,
                     scale=alt.Scale(domain=nomsInstruments))   # les 3 instruments, meme sans image
        barres = alt.Chart(acq).mark_bar(clip=True, height=50).encode(
            x=echelleX, x2="Fin:Q", y=axeY,
            color=alt.Color("Type:N", title=None,
                            scale=alt.Scale(domain=list(couleurs), range=list(couleurs.values())),
                            legend=alt.Legend(orient="top")),
            tooltip=["Image", "Type", "Instrument", "Début", "Fin", "Angle"])
        numeros = alt.Chart(acq).mark_text(clip=True, color="white", fontSize=20, fontWeight="bold").encode(
            x=alt.X("Milieu:Q", scale=alt.Scale(domain=fenetre)), y=axeY, text="Image:N")
        graphe = (barres + numeros).properties(height=360).configure_axis(
            labelFontSize=20, titleFontSize=20).configure_legend(labelFontSize=20, symbolSize=300)
        st.altair_chart(graphe)
        st.caption("Une barre = une acquisition de " + str(DU) + " s ; le nombre est le numéro de l'image.")

# tableau du plan : seulement les images retenues
with ongletPlan:
    lignes = []
    for i in selectionnees:
        instruments = [j for j in range(nbInstruments) if mymodel.getVal(assignedTo[i][j]) > 0.5]
        lignes.append({"Image": i, "Type": "mono" if TY[i] == 1 else "stéréo", "Prix (PA)": PA[i],
                       "Instrument(s)": ", ".join(nomsInstruments[j] for j in instruments),
                       "Début (s)": ", ".join(str(DD[i][j]) for j in instruments)})
    st.dataframe(pd.DataFrame(lignes), hide_index=True, row_height=48)
    if nonRetenues:
        st.write("Images non retenues : " + ", ".join(str(i) for i in nonRetenues))
    else:
        st.write("Toutes les images sont retenues.")

# donnees brutes du jeu (dont les donnees d'incertitude, pas encore utilisees par l'objectif)
with ongletDonnees:
    st.write("DU = " + str(DU) + " s, VI = " + str(VI) + " deg/s, PMmax = " + str(PMmax)
             + ", Failure = " + str(r["Failure"]))
    st.dataframe(pd.DataFrame({
        "Image": range(nbImages), "TY": TY, "PA": PA, "PM": PM,
        "DD": [str(DD[i]) for i in range(nbImages)],
        "AN": [str(AN[i]) for i in range(nbImages)],
        "ProbaInf": r["ProbaInf"], "ProbaSup": r["ProbaSup"],
    }), hide_index=True, row_height=48)
