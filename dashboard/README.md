# Observatoire Médiatique du Bénin 2025

## 📖 Présentation
L'Observatoire Médiatique du Bénin est un tableau de bord interactif conçu pour les décideurs. Basé sur l'analyse massive des données de la base mondiale GDELT, il permet de comprendre **comment le Bénin est raconté dans les médias internationaux en 2025**. 

L'outil dépasse la simple volumétrie d'articles pour décrypter le **sentiment** (tonalité) et l'**impact géopolitique** (stabilité) de l'actualité. Il met en lumière les dynamiques de coopération, d'économie et de diplomatie qui façonnent la perception et l'attractivité du pays.

## 🚀 Fonctionnalités Clés
- **Score d'Attractivité Composite** : Un indicateur exclusif sur 100 qui pondère la coopération (35%), l'économie (25%), la stabilité géopolitique (25%) et le sentiment médiatique (15%).
- **Filtres Intelligents (Portée)** : Naviguez de la couverture globale à des axes très spécifiques (*Économique, Diplomatique, Coopération, Conflits*) de manière fluide. Les codes CAMEO complexes sont gérés en arrière-plan.
- **Analyse Thématique Avancée** : Cartographie des "Event Roots" pour visualiser précisément les thèmes qui génèrent de la stabilité ou de la tension.
- **Rythme et Tonalité** : Suivi de l'évolution temporelle croisant le volume d'événements, le sentiment moyen (*AvgTone*) et le signal de stabilité (*GoldsteinScale*).

## 📊 Ce que le Dashboard permet de voir
- **L'image internationale globale** : Identifiez rapidement si la couverture médiatique penche vers la coopération, l'économie ou le conflit.
- **Les leviers d'attractivité** : Repérez, via le graphique croisé "Perception vs Stabilité", les sujets porteurs qui rassurent les investisseurs et améliorent l'image du pays (quadrant supérieur droit).
- **Les principaux partenaires** : Visualisez sur une carte interactive les pays qui interagissent le plus avec le Bénin et la tonalité de ces relations.

## ⚙️ Mode d'emploi
1. **Sélectionnez votre Portée (Filtre principal)** : Utilisez le menu déroulant en haut à gauche pour choisir votre angle d'analyse. Tous les KPIs et graphiques s'adapteront instantanément à la thématique choisie.
2. **Affinez par Types d'événements** : Filtrez sur des familles d'actions précises (ex: *Appels / Demandes*, *Consultations / Visites*) selon la nomenclature GDELT. Laissez vide pour inclure tous les types.
3. **Ajustez le Temps & l'Espace** : Zoomez sur une période précise ou un pays partenaire en particulier via les curseurs de la barre latérale.
4. **Explorez (Interactivité)** : Survolez les graphiques avec votre souris pour lire le détail des statistiques, l'outil est pensé pour l'exploration visuelle.

## 🛠️ Installation et Lancement

Le tableau de bord nécessite le fichier de données nettoyé à l'emplacement suivant :
`../data/GDELT_events_benin_2025_cleaned.csv`

Pour lancer l'application (depuis le dossier `dashboard`) :
```bash
streamlit run app.py
```
