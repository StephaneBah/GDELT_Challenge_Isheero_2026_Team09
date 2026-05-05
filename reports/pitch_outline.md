# Pitch — Bénin Risk Map (3 minutes)

**Hackathon iSHEERO × DataCamp Donates 2026 · Équipe Team09**

> Trame de pitch vidéo de 3 minutes pour la soumission Phase 1.
> Chaque section indique le timing, le message clé et l'asset visuel à montrer.

---

## Structure et timing

| Section | Timing | Message |
|---|---|---|
| 1. Hook | 0:00 → 0:30 | Le fait choc qui accroche |
| 2. Cadrage | 0:30 → 1:00 | Le problème et notre angle |
| 3. Démarche | 1:00 → 1:30 | Méthode + pipeline + équipe |
| 4. Insights | 1:30 → 2:30 | Les 3 résultats les plus marquants |
| 5. Impact | 2:30 → 3:00 | À qui ça sert · appel à l'action |

---

## 1. Hook (0:00 → 0:30) — Le fait choc

**Personne qui parle** : Data Scientist (Anchor narratif).

> « En 2025, un event sécuritaire au Bénin a généré en moyenne __X__ fois
> moins de mentions médiatiques mondiales qu'un event comparable au Burkina
> Faso. Pourtant, les chiffres que nous avons extraits de la base GDELT
> montrent que la trajectoire sécuritaire béninoise suit celle de ses voisins
> sahéliens — avec __Y__ mois de décalage. Le Bénin est un angle mort. »

**Visuel** : carte choroplèthe des 3 pays avec intensité de couverture
médiatique colorée (insight 1 du one-pager).

---

## 2. Cadrage (0:30 → 1:00) — Le problème et notre angle

**Voix off** :

> « Notre équipe Team09 a passé une semaine sur GDELT — la plus grosse base
> mondiale d'événements géopolitiques — pour répondre à une question simple :
> que voit-on, et que ne voit-on pas, du Bénin en 2025 ? Nous avons construit
> Bénin Risk Map, le premier outil départemental de cartographie du risque
> opérationnel béninois, fondé sur 12 mois de signaux médiatiques mondiaux. »

**Visuel** : titre du projet · logo · capture d'écran du dashboard.

---

## 3. Démarche (1:00 → 1:30) — Méthode et pipeline

**Voix off** :

> « Concrètement : nous avons extrait l'année 2025 complète depuis BigQuery,
> filtrée sur trois pays — Bénin, Burkina, Niger. Nous avons regroupé les
> events bruts en *stories* pour éliminer le bruit GDELT. Nous avons
> reclassé les codes CAMEO en cinq domaines de risque lisibles. Nous avons
> entraîné un modèle xlm-roberta multilingue pour valider le ton. Nous avons
> validé nos résultats croisés sur ACLED. Tout est reproductible : `git
> clone`, `make extract`, `make process`, `make dashboard`. »

**Visuel** : schéma à 4 couches (pipeline → analytics/ml/viz → questions →
consommateurs) · une capture du Makefile.

---

## 4. Insights (1:30 → 2:30) — Les 3 plus marquants

> **Insight 1 — Carte du risque** (1:30 → 1:50)
> « Premier insight : la carte du risque sécuritaire opérationnel se
> concentre à __Y%__ dans les départements de l'Atacora et de l'Alibori,
> directement frontaliers du Burkina Faso et du Niger. Ce sont les zones où
> les ONG et les ambassades doivent calibrer leur exposition. »
> *Visuel* : carte choroplèthe Bénin par département.

> **Insight 2 — Bascule narrative** (1:50 → 2:10)
> « Deuxième insight : le ton médiatique mondial sur le Bénin connaît
> __N__ ruptures statistiques en 2025. La plus marquée est attribuable à
> __[story]__. Notre dashboard permet de cliquer sur chaque rupture pour
> identifier le narratif qui l'a déclenchée. »
> *Visuel* : courbe de ton avec lignes verticales aux ruptures + pop-up sur
> une rupture montrant les top stories antérieures.

> **Insight 3 — Recomposition diplomatique** (2:10 → 2:30)
> « Troisième insight : depuis juillet 2023, la co-occurrence médiatique
> Bénin–Niger a chuté de __X%__, tandis que Bénin–__[acteur Y]__ a doublé.
> La position diplomatique observable du Bénin se cristallise autour
> d'un nouveau pôle. »
> *Visuel* : graphe d'acteurs avant/après.

---

## 5. Impact et appel (2:30 → 3:00)

**Voix off** :

> « Bénin Risk Map sert quatre publics : ONG sécurité, presse, décideurs
> publics, assureurs-pays. Le dashboard est en ligne, le code est sur GitHub
> sous licence MIT. En Phase 2, nous voulons ajouter un service d'alertes
> personnalisées — *« Bénin Watch »* — pour notifier un journaliste ou un
> décideur quand un événement matchant ses critères surgit dans les médias
> mondiaux. Merci. »

**Visuel** : URL du dashboard + URL du repo + email de contact.

---

## Notes de production

- **Voix** : un seul narrateur (Data Scientist) pour la cohérence vocale.
- **Sous-titres** : générés en français + anglais pour accessibilité.
- **Format** : 1080p · 30 fps · MP4 · H.264 · stéréo · 3 minutes ± 5s.
- **Hébergement** : YouTube non listé + Google Drive (cf. consignes).
- **Outils** : enregistrement écran via OBS · capture dashboard en live ·
  voix off enregistrée séparément (qualité audio prioritaire).
- **À éviter** : musique de fond bruyante · transitions superflues · jargon
  technique non expliqué (CAMEO, GCAM, Goldstein → à traduire en français).

---

## Checklist tournage (à valider la veille)

- [ ] Dashboard déployé en ligne et fonctionnel
- [ ] Les 5 insights ont des chiffres réels (pas de placeholders __X__)
- [ ] Captures d'écran HD pré-générées si live trop risqué
- [ ] Script lu à voix haute → durée totale 2:55–3:05
- [ ] Sous-titres relus
- [ ] URL repo et URL dashboard accessibles publiquement
