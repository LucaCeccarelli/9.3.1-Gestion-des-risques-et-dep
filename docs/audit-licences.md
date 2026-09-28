# TP4 — Audit de conformité des licences

Projet audité : l'API météo des TP1 à TP3 (Python, `uv`). Aucune dépendance n'a été ajoutée : le scanner est lancé avec `uvx`, dans un environnement jetable, et lit l'environnement du projet via `--python`.

## 1. Scan

```bash
uv sync --frozen
uvx pip-licenses@5.5.5 --python .venv/bin/python --from=mixed --format=markdown --output-file licenses.md
```

Résultat brut : [`licenses.md`](../licenses.md). Il couvre les 58 paquets installés : 3 dépendances directes (`dependency-injector`, `fastapi[standard]`, `httpx`), 2 dépendances de développement directes (`pytest`, `pytest-playwright`) et toutes leurs dépendances transitives. `--from=mixed` lit les classifiers PyPI, puis `License-Expression`, puis le champ `License`.

Seul `colorama` (BSD-3-Clause, dépendance de `click` et `pytest` sous Windows uniquement) figure dans `uv.lock` sans être installé sous Linux, donc sans apparaître dans le scan.

Position dans l'arbre : `uv tree --invert --package <nom>`. Profondeur 1 = dépendance directe de `meteo`.

## 2. Classification

| Licence (telle que rapportée) | Famille | Paquets |
|---|---|---|
| MIT, MIT License | permissive | agent-detector, annotated-doc, annotated-types, anyio, charset-normalizer, fastapi, fastapi-cli, fastapi-cloud-cli, fastar, h11, httptools, iniconfig, markdown-it-py, mdurl, pluggy, pydantic, pydantic-core, pydantic-extra-types, pydantic-settings, pyee, PyYAML, pytest, python-slugify, rich, rich-toolkit, rignore, sentry-sdk, typer, typing-inspection, urllib3, watchfiles |
| BSD-2-Clause, BSD-3-Clause | permissive | click, httpcore, idna, MarkupSafe, Pygments, python-dotenv, starlette, uvicorn, websockets |
| BSD License (variante non précisée) | permissive | dependency-injector, httpx, Jinja2. Fichier `LICENSE` vérifié : BSD-3-Clause pour les trois |
| 0BSD | permissive | detect-installer |
| ISC License (ISCL) | permissive | dnspython, shellingham |
| Apache-2.0, Apache Software License | permissive | playwright, pytest-playwright, python-multipart, requests |
| Apache Software License; MIT License | permissive (double) | uvloop |
| Apache-2.0 OR BSD-2-Clause | permissive (choix) | packaging |
| PSF-2.0 | permissive | typing_extensions |
| MIT AND PSF-2.0 | permissive (cumul) | greenlet |
| The Unlicense | permissive (domaine public) | email-validator |
| **MPL-2.0** | **copyleft faible** (par fichier) | **certifi**, **pytest-base-url** |
| **Artistic License ; GPL (GPLv2+)** | **copyleft** (option GPL d'une double licence) | **text-unidecode** |
| propriétaire | — | aucun |
| non identifiée | — | aucune : tous les paquets déclarent une licence ; seule la variante BSD manquait pour trois paquets (vérifiée ci-dessus) |

Signalements : **text-unidecode** (GPL, via une double licence) ; **certifi** et **pytest-base-url** (MPL-2.0, copyleft faible). Aucune AGPL ni LGPL.

## 3. Fiches de décision

### text-unidecode 1.3 — Artistic License OU GPLv2+

- **Position** : transitive, profondeur 3, groupe `dev` uniquement : `meteo` → `pytest-playwright` → `python-slugify` → `text-unidecode`. Jamais importé par `meteo/`. Absent de l'image Docker (`uv sync --frozen --no-dev` dans le `Dockerfile`).
- **Stratégie** : **licence alternative**. Il n'y a rien à négocier : l'auteur l'accorde déjà (« under the terms of either: Artistic License […] or GPL »). Le projet retient l'Artistic License, qui n'impose aucune contrainte copyleft sur le code qui l'utilise.
- **Justification** : les obligations de la GPL naissent à la distribution, or ce paquet ne sert qu'à l'outillage de test local et CI. C'est `pytest-playwright` qui l'utilise, pour nommer ses artefacts (captures, traces) ; nos tests e2e n'utilisent que l'API `request` de Playwright, jamais de navigateur. Si l'option Artistic disparaissait d'une future version, le repli serait de **réécrire** : supprimer `pytest-playwright` et remplacer ses deux fixtures (`playwright`, `base_url`) par quelques lignes autour de `playwright.sync_api.sync_playwright()` dans `tests/test_e2e.py`. `python-slugify` et `text-unidecode` sortiraient alors de l'arbre, sans rien changer à `meteo/`.
- **CI** : exception nominative **épinglée à la version** (`--ignore-packages text-unidecode:1.3`). Une montée de version refait échouer le build et impose de relire cette fiche.

### certifi 2026.7.22 — MPL-2.0

- **Position** : transitive, profondeur 2 au plus court (`meteo` → `httpx` → `certifi`). Elle est aussi atteinte via `httpcore` (3) et, en dev, via `requests` (4). C'est une dépendance d'exécution, présente dans l'image Docker.
- **Stratégie** : **isoler derrière une interface existante**, et la conserver telle quelle.
- **Justification** : la MPL-2.0 est un copyleft **au niveau du fichier**. Seules les modifications des fichiers de `certifi` devraient être publiées sous MPL. Nous l'utilisons sans modification, et le reste du projet n'est pas contaminé. Architecturalement, `certifi` n'est atteint qu'à travers `httpx`, et `httpx` n'est connu que des adaptateurs (`meteo/adapters/`) et du conteneur, qui injecte un unique `httpx.Client`. Remplacer le magasin de certificats (par exemple par le magasin système via le paramètre `verify=` de `httpx.Client`) ne toucherait qu'une ligne de `meteo/container.py`. Le métier (`services.py`, `ports.py`) n'en sait rien.
- **CI** : MPL-2.0 ajoutée à la liste blanche, à condition de ne pas modifier les paquets concernés.

### pytest-base-url 2.1.0 — MPL-2.0

- **Position** : transitive, profondeur 2, groupe `dev` uniquement : `meteo` → `pytest-playwright` → `pytest-base-url`. Absent de l'image Docker.
- **Stratégie** : **isoler derrière une interface existante**.
- **Justification** : c'est de l'outillage de test, non distribué et non modifié. Son seul point de contact est la fixture `base_url` lue dans `pyproject.toml`, qui sert de point de couture (seam) aux tests e2e. Le même repli par **réécriture** que pour `text-unidecode` l'éliminerait.
- **CI** : couvert par l'entrée MPL-2.0 de la liste blanche.

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
          --ignore-packages text-unidecode:1.3
          --allow-only="MIT;MIT License;BSD License;BSD-2-Clause;BSD-3-Clause;0BSD;ISC License (ISCL);Apache-2.0;Apache Software License;PSF-2.0;MIT AND PSF-2.0;Apache-2.0 OR BSD-2-Clause;The Unlicense (Unlicense);MPL-2.0;Mozilla Public License 2.0 (MPL 2.0)"
```

- **Périmètre** : `uv sync --frozen` installe tous les groupes, développement compris ; tout l'arbre est donc contrôlé.
- **Règle d'échec** : `--allow-only` sort en code 1 dès qu'un paquet n'a **aucune** de ses licences dans la liste.
- **Correspondance exacte** : la comparaison est exacte (pas de `--partial-match`), ce qui explique la présence des expressions composées vérifiées (`MIT AND PSF-2.0`, `Apache-2.0 OR BSD-2-Clause`). Une correspondance partielle laisserait passer, par exemple, `MIT AND GPL-3.0` grâce à la sous-chaîne `MIT`.
- **Version de l'outil** : `pip-licenses` est épinglé en 5.5.5 pour que le résultat ne dépende pas d'une nouvelle version de l'outil.

## 5. Vérification du critère de réussite

Commande de contrôle identique à celle de la CI, lancée en local :

| Étape | Commande | Résultat |
|---|---|---|
| Arbre actuel, sans l'exception | `… --allow-only=…` | **exit 1** : `license Artistic License; GNU General Public License (GPL); GNU General Public License v2 or later (GPLv2+) not in allow-only licenses was found for package text-unidecode:1.3` |
| Arbre actuel, avec l'exception | `… --ignore-packages text-unidecode:1.3 --allow-only=…` | exit 0 |
| Ajout volontaire d'un paquet GPL | `uv add unidecode` puis contrôle | **exit 1** : `license GNU General Public License v2 or later (GPLv2+) not in allow-only licenses was found for package Unidecode:1.4.0` |
| Retrait | `uv remove unidecode` puis contrôle | exit 0 ; `pyproject.toml` et `uv.lock` redeviennent identiques |
