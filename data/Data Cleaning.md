# Data Cleaning — Pipeline complet (GDELT Bénin 2025)

Ce document décrit **tout le process de nettoyage** et de désambiguïsation que nous avons mis en place pour passer d’un export GDELT “brut” à un dataset **100% centré sur le Bénin (pays)**, prêt pour l’analyse et le dashboard.

---

## 1) Objectif

- Construire un corpus d’événements GDELT 2025 **qualifié “Bénin”**, exploitable pour l’analyse (perception, diplomatie, sécurité, attractivité).
- Réduire le bruit régional (événements hors scope) et surtout résoudre le piège récurrent : **Benin (pays)** vs **Benin City (Nigéria)**.

---

## 2) Lineage des fichiers (de bout en bout)

- `GDELT_events_benin_2025.csv`
  - Export des événements GDELT 2025 après filtre “Bénin” (scope géo + acteurs).

- `copy_events_benin_2025_labeled.csv`
  - Dataset enrichi avec des **labels lisibles** (pays, types d’acteurs, événements CAMEO, QuadClass).
  - Généré par `add_labels.py` ou `add_labels_pure.py` + dictionnaires CAMEO (`CAMEO.*.txt`).

- `copy_events_benin_2025_labeled_url_flagged.csv`
  - Dataset “labeled” + colonnes de QA URL (`SuspectUrl`, `BeninMentioned`, `BeninCityMentioned`, `BeninRepublicMentioned`, `RemoveReason`).

- `copy_events_benin_2025_labeled_url_filtered.csv`
  - Dataset filtré (suppression des URLs identifiées comme **hors Bénin** ou **Benin City / Nigéria** selon règles ci-dessous).

- `copy_events_benin_2025_labeled_url_flagged_v2.csv`
  - Version “flagged” mise à jour après correction du **sous-filtrage Nigeria** (certains médias .com, etc. passaient en `SuspectUrl=False`).

- `copy_events_benin_2025_labeled_url_filtered_v2.csv`
  - Version “filtered” mise à jour après correction Nigeria (cible uniquement : `SuspectUrl=False` → pattern Nigeria → re-check contenu).

- `GDELT_events_benin_2025_cleaned.csv`
  - Résultat final consolidé du pipeline, utilisé pour l'analyse et le dashboard.

---

## 3) Étape A — Extraction / constitution du scope “Bénin”

### A1. Filtre strict “Bénin” (géo + acteurs)

La logique de scope est explicitée dans le notebook d’extraction BigQuery (`GDELT_Benin_BigQuery.ipynb`) :

- Année : **2025**
- Conserver les événements si **au moins une** des conditions suivantes est vraie :
  - `ActionGeo_CountryCode = 'BN'`
  - `Actor1Geo_CountryCode = 'BN'`
  - `Actor2Geo_CountryCode = 'BN'`
  - `Actor1CountryCode = 'BEN'`
  - `Actor2CountryCode = 'BEN'`

Cette étape est la base du “Strict AND Filter” : on ne fait pas une analyse “Afrique de l’Ouest”, on veut un dataset **ultra focalisé** sur le Bénin.

### A2. Colonnes utiles retenues

Le dataset de travail conserve notamment :

- Identifiants : `GLOBALEVENTID`
- Temps : `SQLDATE`, `MonthYear`
- Acteurs : `Actor1Name`, `Actor1CountryCode`, `Actor1Type1Code`, `Actor2Name`, `Actor2CountryCode`, `Actor2Type1Code`
- CAMEO : `EventCode`, `EventBaseCode`, `EventRootCode`, `QuadClass`
- Scores : `GoldsteinScale`, `AvgTone`, `NumMentions`, `NumSources`, `NumArticles`
- Géographie : `ActionGeo_*`
- Source : `SOURCEURL`

---

## 4) Étape B — Enrichissement CAMEO → labels lisibles

### B1. Problème

GDELT encode énormément d’information sous forme de **codes** (pays, types d’acteurs, événements). Pour analyser et raconter des insights, il faut rendre ces codes lisibles.

### B2. Solution

Nous avons enrichi `copy_events_benin_2025.csv` en injectant des colonnes labels adjacentes, via :

- `add_labels.py` (version pandas) ou `add_labels_pure.py` (version `csv` pure)
- Dictionnaires CAMEO : `CAMEO.country.txt`, `CAMEO.type.txt`, `CAMEO.eventcodes.txt`

Colonnes ajoutées (si présentes dans le fichier) :

- `Actor1CountryLabel` après `Actor1CountryCode`
- `Actor1Type1Label` après `Actor1Type1Code`
- `Actor2CountryLabel` après `Actor2CountryCode`
- `Actor2Type1Label` après `Actor2Type1Code`
- `EventLabel` après `EventCode`
- `EventBaseLabel` après `EventBaseCode`
- `EventRootLabel` après `EventRootCode`
- `QuadClassLabel` après `QuadClass`

### B3. Détail important (bug “zéros initiaux”)

Les `EventRootCode` peuvent être inconsistants (ex. `2` vs `02`).

- Le script force un format `zfill(2)` côté pandas et applique une correction côté CSV pure.

Output : `copy_events_benin_2025_labeled.csv`

---

## 5) Étape C — URL Quality Check (v1) : filtrer le bruit hors-Bénin

### C1. Problème

Même avec un filtre strict “Bénin”, certaines URLs/articulations restent bruitées :

- pages qui ne mentionnent pas le Bénin (erreurs de jointure/mention)
- confusion “Benin City” (Nigéria) vs République du Bénin

### C2. Approche (flag → fetch → validation contextuelle)

- **Flag URL (heuristique)** : marquer `SuspectUrl=True` si l’URL contient des marqueurs Nigeria (TLD `.ng`, mots-clés `naira/naija/nigeria`, etc.).
- **Fetch & parsing** : télécharger le HTML, retirer `script/style/tags`, normaliser en ASCII, passer en lowercase.
- **Règles de suppression (RemoveReason)** : si le texte **ne contient pas** `benin` → `RemoveReason = "Benin not mentioned"` ; si le texte contient `Benin City` (ou marqueurs similaires) **sans** marqueurs République du Bénin → `RemoveReason = "Benin City (Nigeria)"`.
- **Sorties** : `copy_events_benin_2025_labeled_url_flagged.csv` (avec colonnes QA) et `copy_events_benin_2025_labeled_url_filtered.csv` (les URLs à delete sont exclues).

### C3. Gestion des pages non scrapables

Quand `fetch_text()` échoue (paywall, non-HTML, blocage…), on marque :

- `BeninMentioned = Unknown`, etc.
- `RemoveReason = Unknown`

Par défaut, ces lignes **ne sont pas supprimées** automatiquement : elles restent dans le filtré, car on ne peut pas trancher sans information.

---

## 6) Étape D — Correctif Nigeria (v2) : re-filtrer les Nigeria passés en `SuspectUrl=False`

### D1. Problème

Beaucoup de médias nigérians utilisent des domaines qui **ne finissent pas** par `.ng` et n’ont pas forcément de mots-clés évidents dans l’URL.
Résultat : une partie du bruit Nigeria est passée en **`SuspectUrl=False`**, donc jamais scrapée en v1.

### D2. Solution

Nous avons élargi la détection Nigeria avec un pattern dédié :

```text
NIGERIAN_DOMAINS_PATTERN = (
    r"\.ng$|punchng|nigerianobserver|thisdaylive|saharareporters|"
    r"premiumtimesng|thenationonlineng|nationalguideng|dailytrust|"
    r"naijanews|nigerianeye|withinnigeria|nigeriasun|vanguardngr|"
    r"channelstv|opinionnigeria|informationng|thenewsnigeria|"
    r"tribuneonlineng|theeagleonline|blueprint\.ng|thecable\.ng|"
    r"legit\.ng|naija247|pulse\.ng|thenigerianvoice|bellanaija|"
    r"nationalaccord|prompnewsonline|thesun\.ng|guardian\.ng|"
    r"leadership\.ng|quicknews|myjoyonline"
)
```

### D3. Stratégie “ciblée / incremental” (sans refaire tout le process)

Au lieu de re-scraper tout le dataset :

- On prend **uniquement** les lignes qui étaient `SuspectUrl=False`
- On applique `NIGERIAN_DOMAINS_PATTERN` pour identifier les URLs Nigeria “ratées”
- On re-scrape seulement ces URLs et on applique **exactement les mêmes règles** “Benin not mentioned” / “Benin City (Nigeria)” via `fetch_text()`

Outputs :

- `copy_events_benin_2025_labeled_url_flagged_v2.csv`
- `copy_events_benin_2025_labeled_url_filtered_v2.csv`

---

## 7) Challenges & solutions (récap)

- **Lisibilité / opacité CAMEO** → mapping via dictionnaires + insertion de labels à côté des codes.
- **Zéros initiaux** (`EventRootCode`) → normalisation (`zfill(2)`) pour que le mapping soit correct.
- **Bruit régional** → filtre strict géo+acteurs (BN/BEN) dès l’extraction.
- **Désambiguïsation “Benin City”** → heuristique URL + validation contextuelle dans le texte scrapé.
- **Sous-couverture Nigeria** (domaines .com etc.) → `NIGERIAN_DOMAINS_PATTERN` + re-filtrage ciblé sur le bucket `SuspectUrl=False`.
- **Web scraping imparfait** (paywalls, non-text, erreurs) → gestion `Unknown` (conservé par défaut) + possibilité d’arbitrer ensuite.

---

## 8) Où est implémentée chaque étape (dans le repo)

- Extraction (BigQuery) : `notebooks/1_GDELT_Benin_Collect_From_BigQuery.ipynb`
- Enrichissement CAMEO : `data/scripts/add_labels.py` / `data/scripts/add_labels_pure.py`
- URL QA (script) : `data/scripts/url_quality_check.py`
- URL QA (notebook + correctif v2 ciblé) : `notebooks/2_Data_Cleaning.ipynb`
