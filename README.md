# Plan d'acquisition d'un satellite SPOT

Étude de cas « Décider sous probabilités imprécises » — M2 Informatique, IA et Décision, Toulouse, 2026-2027.

**Auteurs :** Inesa Movsesyan, Zhanna Minasyan

Pour une révolution du satellite, le programme choisit quelles images acquérir et avec quel instrument (avant, nadir, arrière), en maximisant le gain espéré malgré l'incertitude sur les nuages et les pannes d'instruments. Le modèle est un programme linéaire en nombres entiers résolu par SCIP (PySCIPOpt).

## Contenu

| Fichier | Rôle |
|---|---|
| `spotProba.py` | Modèle : variables, contraintes et fonction objectif |
| `interface.py` | Interface : choix du jeu de données, plan obtenu, chronogramme par instrument |
| `spotProba1.py` … `spotProba5.py` | Jeux de données fournis |
| `spotProba1_*.py` | Les 4 cas d'incertitude donnés en commentaire dans `spotProba1.py` |
| `requirements.txt` | Dépendances Python |
| `.streamlit/config.toml` | Apparence de l'interface |

## Lancement

```bash
pip install -r requirements.txt
python spotProba.py spotProba4.py    # n'importe quel fichier de données ; spotProba1.py par défaut
streamlit run interface.py           # interface dans le navigateur
```

## Modèle

Variables binaires : `selection[i]` (image *i* retenue) et `assignedTo[i][j]` (image *i* prise par l'instrument *j* : 0 avant, 1 nadir, 2 arrière).

Contraintes :
1. **Mémoire** : Σᵢ PM[i] · selection[i] ≤ PMmax (PM est déjà doublée pour les images stéréo).
2. **Non-chevauchement** : pour deux images *a*, *b* et un instrument *j*, si |DD[a][j] − DD[b][j]| · VI < DU · VI + |AN[a][j] − AN[b][j]|, alors assignedTo[a][j] + assignedTo[b][j] ≤ 1.
3. **Image mono** (TY = 1) : Σⱼ assignedTo[i][j] = selection[i].
   **Image stéréo** (TY = 2) : assignedTo[i][0] = assignedTo[i][2] = selection[i] et assignedTo[i][1] = 0.
4. **Exclusivité** : impliquée par la contrainte 2 (deux acquisitions simultanées se chevauchent).

Fonction objectif — gain espéré, critère pessimiste (probabilité de nuage = ProbaSup) :
- image mono prise par l'instrument *j* : PA[i] · (1 − ProbaSup[i]) · (1 − Failure[j])
- image stéréo, comptée une seule fois et perdue si l'un des deux instruments tombe en panne : PA[i] · (1 − ProbaSup[i]) · (1 − Failure[0]) · (1 − Failure[2])

## Résultats

Jeux de test (valeurs de référence de l'énoncé) :

| Fichier | Nuage | Pannes | Attendu | Obtenu |
|---|---|---|---|---|
| `spotProba1.py` | aucun | aucune | 70 | 70 |
| `spotProba2.py` | aucun | aucune | 60 | 60 |
| `spotProba3.py` | aucun | aucune | 60 | 60 |
| `spotProba1_nuage10.py` | 0,1 | aucune | 63 | 63 |
| `spotProba1_nuage10a30.py` | entre 0,1 et 0,3 | aucune | 49 | 49 |
| `spotProba1_panne_nadir.py` | aucun | nadir : 1 | 60 | 60 |
| `spotProba1_combine.py` | jusqu'à 0,1 / 0,5 / 0,9 | 0,01 ; 0,9 ; 0,01 | 14,661 | 14,661 |

Jeux principaux (critère pessimiste) :

| Fichier | Gain espéré | Images retenues | Mémoire |
|---|---|---|---|
| `spotProba4.py` | 333 | 14 / 20 | 140 / 150 |
| `spotProba5.py` | 553,646 | 27 / 40 | 300 / 300 |
