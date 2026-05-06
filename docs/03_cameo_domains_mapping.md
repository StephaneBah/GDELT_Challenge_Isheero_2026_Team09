# Mapping CAMEO → domaines de risque

Référence d'équipe pour le principe « domains, not codes » de la doctrine.
Le mapping est implémenté dans [`src/config.py`](../src/config.py) (`CAMEO_TO_DOMAIN`).

---

## Les 5 domaines retenus pour Phase 1

| Domaine | Description | Public concerné |
|---|---|---|
| **securitaire** | Posture militaire, coercition, assauts, combats, violences de masse | ONG sécurité, ambassades, assureurs |
| **politique** | Déclarations, désaccords, sanctions verbales, manifestations | Journalistes politiques, observateurs |
| **economique** | Coopération matérielle, échanges commerciaux | Investisseurs, chambres de commerce |
| **humanitaire** | Aide, dons, soutien matériel | ONG humanitaires, agences UN |
| **informationnel** | Production de discours public (subset à isoler en sub-codes) | Analystes médias |

> Phase 2 pourra raffiner avec **environnemental** et **infrastructurel** (sub-codes spécifiques).

---

## Mapping par CAMEO Root Code

| Root | Description CAMEO | Domaine retenu | Justification |
|------|------|------|------|
| 01 | MAKE PUBLIC STATEMENT | politique | Posture publique |
| 02 | APPEAL | politique | Demande politique |
| 03 | EXPRESS INTENT TO COOPERATE | politique | Intention diplomatique |
| 04 | CONSULT | politique | Consultation |
| 05 | ENGAGE IN DIPLOMATIC COOPERATION | politique | Diplomatie |
| 06 | ENGAGE IN MATERIAL COOPERATION | **economique** | Coopération matérielle = échange économique principalement |
| 07 | PROVIDE AID | **humanitaire** | Aide |
| 08 | YIELD | politique | Concession |
| 09 | INVESTIGATE | politique | Enquête |
| 10 | DEMAND | politique | Exigence |
| 11 | DISAPPROVE | politique | Désaccord verbal |
| 12 | REJECT | politique | Rejet |
| 13 | THREATEN | politique | Menace verbale (avant escalade militaire = sécuritaire) |
| 14 | PROTEST | politique | Manifestation civile |
| 15 | EXHIBIT FORCE POSTURE | **securitaire** | Posture militaire |
| 16 | REDUCE RELATIONS | politique | Recul diplomatique |
| 17 | COERCE | **securitaire** | Coercition matérielle |
| 18 | ASSAULT | **securitaire** | Assaut |
| 19 | FIGHT | **securitaire** | Combat armé |
| 20 | USE UNCONVENTIONAL MASS VIOLENCE | **securitaire** | Violence de masse |

---

## Cas d'arbitrage à raffiner par sub-codes

Certains root codes méritent d'être éclatés au niveau du `EventCode` (3-4 chiffres) pour gagner en précision :

- **06** (Material cooperation) — peut couvrir économique (commerce) ou militaire (coopération sécuritaire). À splitter sur sub-codes.
- **07** (Provide aid) — humanitaire, mais 0712 = « aide militaire » → bascule sécuritaire.
- **13** (Threaten) — verbal politique, mais 138x peut indiquer une escalade militaire imminente.

**Recommandation Phase 1** : utiliser le mapping root simple. Mentionner ces nuances dans la slide Méthodologie.
**Phase 2** : raffinement par sub-codes si finaliste.

---

## Validation prévue

- **Audit** sur 100 events tirés au hasard : le label automatique correspond-il au sens de l'event ? Cible : ≥85% d'accord.
- **Métrique de stabilité** : la distribution des domaines est-elle cohérente entre BN, UV, NG ?
