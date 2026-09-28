# TP4 — Audit de conformité des licences

Projet audité : l'API météo des TP1 à TP3 (Python, `uv`). Aucune dépendance n'a été ajoutée : le scanner est lancé avec `uvx`, dans un environnement jetable, et lit l'environnement du projet via `--python`.

## 1. Scan

```bash
uv sync --frozen
uvx pip-licenses@5.5.5 --python .venv/bin/python --from=mixed --format=markdown --output-file licenses.md
```

Résultat brut : [`licenses.md`](../licenses.md). Il couvre les 49 paquets installés : 3 dépendances directes (`dependency-injector`, `fastapi[standard]`, `httpx`), 1 dépendance de développement directe (`pytest`) et toutes leurs dépendances transitives. `--from=mixed` lit les classifiers PyPI, puis `License-Expression`, puis le champ `License`.

Seul `colorama` (BSD-3-Clause, dépendance de `click` et `pytest` sous Windows uniquement) figure dans `uv.lock` sans être installé sous Linux, donc sans apparaître dans le scan.

Position dans l'arbre : `uv tree --invert --package <nom>`. Profondeur 1 = dépendance directe de `meteo`.

Le premier scan (58 paquets) contenait aussi `pytest-playwright` et 8 dépendances transitives, dont `text-unidecode` (GPL). Leur retrait est décrit dans la fiche correspondante (section 3).

## 2. Classification

| Licence (telle que rapportée) | Famille | Paquets |
|---|---|---|
| MIT, MIT License | permissive | agent-detector, annotated-doc, annotated-types, anyio, fastapi, fastapi-cli, fastapi-cloud-cli, fastar, h11, httptools, iniconfig, markdown-it-py, mdurl, pluggy, pydantic, pydantic-core, pydantic-extra-types, pydantic-settings, PyYAML, pytest, rich, rich-toolkit, rignore, sentry-sdk, typer, typing-inspection, urllib3, watchfiles |
| BSD-2-Clause, BSD-3-Clause | permissive | click, httpcore, idna, MarkupSafe, Pygments, python-dotenv, starlette, uvicorn, websockets |
| BSD License (variante non précisée) | permissive | dependency-injector, httpx, Jinja2. Fichier `LICENSE` vérifié : BSD-3-Clause pour les trois |
| 0BSD | permissive | detect-installer |
| ISC License (ISCL) | permissive | dnspython, shellingham |
| Apache-2.0 | permissive | python-multipart |
| Apache Software License; MIT License | permissive (double) | uvloop |
| Apache-2.0 OR BSD-2-Clause | permissive (choix) | packaging |
| PSF-2.0 | permissive | typing_extensions |
| The Unlicense | permissive (domaine public) | email-validator |
| **MPL-2.0** | **copyleft faible** (par fichier) | **certifi** |
| propriétaire | — | aucun |
| non identifiée | — | aucune : tous les paquets déclarent une licence ; seule la variante BSD manquait pour trois paquets (vérifiée ci-dessus) |

Signalements actuels : **certifi** (MPL-2.0, copyleft faible). Aucune GPL, AGPL ni LGPL. Deux cas du premier scan ont été résolus par retrait : **text-unidecode** (GPL, via une double licence) et **pytest-base-url** (MPL-2.0).

## 3. Fiches de décision

### text-unidecode 1.3 — Artistic License OU GPLv2+ (résolu : retiré)

- **Position (avant retrait)** : transitive, profondeur 3, groupe `dev` uniquement : `meteo` → `pytest-playwright` → `python-slugify` → `text-unidecode`. Jamais importé par `meteo/`. Absent de l'image Docker.
- **Stratégie retenue** : **réécrire**. `pytest-playwright` ne fournissait que deux fixtures (`playwright`, `base_url`) aux 4 tests e2e, et ceux-ci n'utilisaient que l'API `request` de Playwright (du HTTP, sans navigateur). Ils utilisent désormais un `httpx.Client`, qui était déjà une dépendance directe du projet. Aucune dépendance n'est ajoutée, et 9 paquets sortent de l'arbre : `playwright`, `pytest-playwright`, `pytest-base-url`, `python-slugify`, `text-unidecode`, `greenlet`, `pyee`, `requests`, `charset-normalizer`.
- **Justification** : l'option Artistic suffisait juridiquement pour une dépendance de dev non distribuée. Elle imposait en revanche une exception permanente dans la CI, épinglée à une version. La réécriture coûte quelques lignes de test et supprime l'exception : la liste blanche s'applique maintenant sans dérogation. Côté architecture, le changement reste dans `tests/`. `meteo/` n'est pas touché, et les tests e2e ne dépendent que du contrat HTTP public de l'API, c'est-à-dire de sa boundary.
- **Décision initiale, remplacée** : licence alternative (Artistic), avec l'exception CI `--ignore-packages text-unidecode:1.3`.

### certifi 2026.7.22 — MPL-2.0

- **Position** : transitive, profondeur 2 au plus court (`meteo` → `httpx` → `certifi`), également atteinte via `httpcore` (3). Dépendance d'exécution, présente dans l'image Docker.
- **Stratégie** : **isoler derrière une interface existante**, et la conserver telle quelle.
- **Justification** : la MPL-2.0 est un copyleft **au niveau du fichier**. Seules les modifications des fichiers de `certifi` devraient être publiées sous MPL ; nous l'utilisons sans modification, et le reste du projet n'est pas contaminé. Architecturalement, `certifi` n'est atteint qu'à travers `httpx`, et `httpx` n'est connu que des adaptateurs (`meteo/adapters/`) et du conteneur, qui injecte un unique `httpx.Client`. Remplacer le magasin de certificats (par exemple par le magasin système, via le paramètre `verify=` de `httpx.Client`) ne toucherait qu'une ligne de `meteo/container.py`. Le métier (`services.py`, `ports.py`) n'en sait rien.
- **CI** : MPL-2.0 figure dans la liste blanche, à condition de ne pas modifier les paquets concernés.

### pytest-base-url 2.1.0 — MPL-2.0 (résolu : retiré)

- **Position (avant retrait)** : transitive, profondeur 2, groupe `dev` uniquement : `meteo` → `pytest-playwright` → `pytest-base-url`.
- **Stratégie retenue** : **réécrire**, par la même opération que pour `text-unidecode`. La fixture `base_url` et la clé `base_url` de `pyproject.toml` sont remplacées par la constante `BASE_URL` de `tests/test_e2e.py`.

## 4. Intégration continue

`.github/workflows/licences.yml` :

```yaml
name: licences

on:
  push:
  pull_request:

jobs:
  licences:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv sync --frozen
      - name: Liste blanche des licences
        run: >-
          uvx pip-licenses@5.5.5 --python .venv/bin/python --from=mixed
          --allow-only="MIT;MIT License;BSD License;BSD-2-Clause;BSD-3-Clause;0BSD;ISC License (ISCL);Apache-2.0;Apache Software License;PSF-2.0;Apache-2.0 OR BSD-2-Clause;The Unlicense (Unlicense);MPL-2.0;Mozilla Public License 2.0 (MPL 2.0)"
```

- **Périmètre** : `uv sync --frozen` installe tous les groupes, développement compris ; tout l'arbre est donc contrôlé.
- **Règle d'échec** : `--allow-only` sort en code 1 dès qu'un paquet n'a **aucune** de ses licences dans la liste.
- **Correspondance exacte** : la comparaison est exacte, sans `--partial-match`, d'où la présence de l'expression composée vérifiée `Apache-2.0 OR BSD-2-Clause`. Une correspondance partielle laisserait passer, par exemple, `MIT AND GPL-3.0` grâce à la sous-chaîne `MIT`.
- **Épinglage** : `pip-licenses` est épinglé en 5.5.5 pour que le résultat ne dépende pas d'une nouvelle version de l'outil.
- **Exceptions** : aucune.

## 5. Vérification du critère de réussite

Commande de contrôle identique à celle de la CI, lancée en local :

| Étape | Commande | Résultat |
|---|---|---|
| Premier scan, avant le retrait de Playwright | `… --allow-only=…` | **exit 1** : `license Artistic License; GNU General Public License (GPL); GNU General Public License v2 or later (GPLv2+) not in allow-only licenses was found for package text-unidecode:1.3` |
| Arbre actuel, sans aucune exception | `… --allow-only=…` | exit 0 |
| Ajout volontaire d'un paquet GPL | `uv add unidecode` puis contrôle | **exit 1** : `license GNU General Public License v2 or later (GPLv2+) not in allow-only licenses was found for package Unidecode:1.4.0` |
| Retrait | `uv remove unidecode` puis contrôle | exit 0 ; `pyproject.toml` et `uv.lock` redeviennent identiques |
