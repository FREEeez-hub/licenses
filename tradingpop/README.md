# TradingPop

Popup desktop always-on-top qui surveille une watchlist (actions / forex),
analyse les données de marché et l'actualité avec une IA (OpenRouter), et
affiche des **suggestions en langage humain** — jamais un ordre passé
automatiquement. Outil strictement personnel (phase 1 de la spec, test d'un
mois) ; chaque sortie est une **analyse informative, pas un conseil financier**.

TradingView reste simplement l'écran regardé à côté : aucun lien technique
avec le popup.

## Ce que fait le popup

- **Watchlist multi-instruments** : actions et paires forex suivies en
  parallèle, intervalle de rafraîchissement configurable (day trading 1-5 min
  comme swing trading 15-60 min).
- **Analyse IA libre** : l'IA reçoit bougies OHLC + indicateurs (SMA, EMA,
  RSI, MACD) et décrit ce qu'elle observe avant de suggérer. Sortie :
  situation + suggestion + confiance 0-100 + justification courte.
- **Structure de marché et figures de bougies** : la tendance, les derniers
  plus hauts/bas significatifs et les cassures (BOS, CHoCH) sont calculés en
  code à partir des prix réels (`structure.py`), tout comme les figures de
  bougies classiques — doji, marteau, étoile filante, avalements
  (`patterns.py`). L'IA commente ces faits déjà établis plutôt que de les
  deviner sur des chiffres bruts, ce qui évite qu'elle invente des cassures.
- **Taille de position et risque** : calcul mathématique (pas une estimation
  de l'IA) de la taille de position et de la perte en cas d'invalidation, à
  partir du niveau de structure le plus proche et de deux paramètres que tu
  contrôles dans `config.json` : `capital_reference` et
  `risque_max_pct_par_trade` (`risk.py`).
- **Actualité** : recherche web ciblée avant analyse via OpenRouter (modèle à
  suffixe `:online`), mise en cache pour limiter le coût (`news_every_n_cycles`).
- **Mémoire** (pas de fine-tuning) : chaque suggestion est enregistrée en
  SQLite (`tradingpop.db`) avec suivi automatique du prix réel à T+1h et T+1j ;
  le résumé des cas passés est réinjecté dans les analyses suivantes.
- **Récap quotidien** : chaque matin, résumé de la veille envoyé par email
  (Brevo) **et** affiché à l'ouverture du popup.
- **Alertes** : sur signal fort (confiance ≥ seuil et action ≠ attendre), la
  vignette clignote et un bip sonne (`alert_sound` désactivable).
- **UI non bloquante** : tous les appels réseau/IA tournent dans un thread de
  fond ; l'UI consomme une file thread-safe.

## Hors scope (volontaire)

Pas d'exécution automatique d'ordres, pas de connexion broker, pas de
fine-tuning, pas de multi-utilisateurs, pas d'intégration TradingView.

## Installation

Prérequis : Python 3.11+ avec tkinter (inclus dans l'installeur Windows
officiel de python.org).

```bash
cd tradingpop
pip install -r requirements.txt
copy .env.example .env          # puis remplir les clés (jamais dans un chat/commit)
copy config.example.json config.json   # puis ajuster la watchlist
python -m tradingpop
```

### Variables d'environnement (`.env`)

| Variable | Rôle |
|---|---|
| `OPENROUTER_API_KEY` | Analyse IA + recherche d'actualités (réutilisée de GrantHound) |
| `TWELVEDATA_API_KEY` | Données de marché actions + forex (palier gratuit : https://twelvedata.com) |
| `BREVO_API_KEY` | Envoi email du récap (réutilisée de GrantHound) |
| `TRADINGPOP_EMAIL_DESTINATAIRE` | Adresse qui reçoit le récap quotidien |
| `TRADINGPOP_EMAIL_EXPEDITEUR` | Adresse expéditrice validée dans Brevo |

Sans les variables email, le popup démarre quand même : seul l'envoi du récap
est désactivé (il reste affiché à l'ouverture).

### Configuration (`config.json`)

| Clé | Défaut | Rôle |
|---|---|---|
| `watchlist` | `["EUR/USD"]` | Instruments suivis (symboles Twelve Data : `"AAPL"`, `"EUR/USD"`...) |
| `refresh_minutes` | `5` | Intervalle entre deux cycles d'analyse |
| `candle_interval` / `candle_count` | `"5min"` / `120` | Granularité et profondeur des bougies |
| `news_every_n_cycles` | `3` | Fréquence de la recherche d'actualités (1 = à chaque cycle) |
| `recap_hour` | `8` | Heure à partir de laquelle le récap est dû si le popup tourne déjà |
| `alert_confidence_threshold` | `75` | Seuil de confiance déclenchant l'alerte visuelle/sonore |
| `alert_sound` | `true` | Bip sur signal fort |
| `model` | `anthropic/claude-sonnet-5` | Modèle OpenRouter pour l'analyse |
| `news_model` | `anthropic/claude-haiku-4.5:online` | Modèle avec recherche web pour l'actualité |
| `outcome_horizons_hours` | `[1, 24]` | Horizons d'évaluation du prix réel après suggestion |
| `history_limit` | `8` | Nombre de cas passés réinjectés dans le prompt |
| `db_path` | `tradingpop.db` | Emplacement de la base SQLite |
| `swing_lookback` | `3` | Nombre de bougies de chaque côté pour détecter un plus haut/bas significatif |
| `capital_reference` | `10000.0` | Capital de référence pour le calcul de taille de position (à ajuster à ta situation) |
| `risque_max_pct_par_trade` | `1.0` | % maximum du capital risqué par trade — modifiable à tout moment |

## Architecture

```
tradingpop/
  __main__.py    point d'entrée (python -m tradingpop), vérifie env + config
  config.py      config.json + .env, valeurs par défaut
  market_data.py client Twelve Data (bougies, prix spot)
  indicators.py  SMA / EMA / RSI / MACD en Python pur
  structure.py   swings, tendance, BOS/CHoCH — calculés à partir des prix réels
  patterns.py    figures de bougies classiques (doji, marteau, avalements...)
  risk.py        taille de position et perte en cas d'invalidation (calcul, pas l'IA)
  news.py        recherche web d'actualités via OpenRouter :online + cache
  ai.py          prompt d'analyse, appel OpenRouter, validation JSON
  memory.py      SQLite : suggestions, résultats T+1h/T+1j, méta (thread-safe)
  recap.py       construction du récap + envoi Brevo + déduplication quotidienne
  worker.py      thread de fond : collecte → analyse → mémoire → file UI
  app.py         popup Tkinter always-on-top (seul module qui importe tkinter)
```

Flux d'un cycle : bougies Twelve Data → indicateurs + structure + figures de
bougies → actualité (cache) → résumé de l'historique en mémoire → analyse IA
(qui commente la structure/les figures déjà calculées, sans les inventer) →
calcul de taille de position → enregistrement SQLite + affichage. En début de
cycle, les suggestions arrivées à échéance sont évaluées au prix spot courant.

## Tests

```bash
python -m unittest discover -s tests
```

42 tests, sans réseau ni tkinter (indicateurs, structure de marché, figures de
bougies, calcul de risque, mémoire, récap, normalisation de la sortie IA,
câblage du worker avec réseau mocké).

## Sécurité et cadre légal (phase 1)

- Chaque affichage porte la mention « analyses informatives, pas des conseils
  financiers » ; le récap email inclut le même avertissement.
- Aucune exécution automatique : le popup suggère, l'utilisateur décide et
  exécute ailleurs (compte **démo** recommandé pendant le test).
- La taille de position affichée est un **calcul mathématique** (capital ×
  risque configuré ÷ distance au niveau d'invalidation), jamais une
  estimation de l'IA — elle reste dépendante des paramètres que tu contrôles
  dans `config.json`, pas une recommandation d'investissement.
- Aucun secret en dur : tout passe par les variables d'environnement ;
  `.env`, `config.json` et `*.db` sont exclus du dépôt via `.gitignore`.
- La phase 2 (produit public) exigera de re-creuser MiFID II / FSMA avant tout
  lancement — rien ici n'est construit pour ça, volontairement.

## Critères de succès du test d'un mois (rappel spec)

1. Le popup tourne sans plantage sur la durée.
2. Suggestions cohérentes et justifiées (l'IA ne doit pas inventer d'actualité
   — le prompt le lui interdit explicitement, à vérifier à l'usage).
3. Récap quotidien fiable, par email et à l'ouverture.
4. La mémoire s'accumule et est réutilisée (le raisonnement doit référencer
   des cas passés après quelques jours).
