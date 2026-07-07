"""Chargement de la configuration (config.json) et des variables d'environnement.

Aucun secret n'est jamais stocké dans le code ni dans config.json : les clés
API vivent exclusivement dans l'environnement (ou un fichier .env local non
versionné, chargé ici sans dépendance externe).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAUTS = {
    "watchlist": ["EUR/USD"],
    "refresh_minutes": 5,
    "candle_interval": "5min",
    "candle_count": 120,
    "news_every_n_cycles": 3,
    "recap_hour": 8,
    "alert_confidence_threshold": 75,
    "alert_sound": True,
    "model": "anthropic/claude-sonnet-5",
    "news_model": "anthropic/claude-haiku-4.5:online",
    "outcome_horizons_hours": [1, 24],
    "history_limit": 8,
    "db_path": "tradingpop.db",
    "swing_lookback": 3,
    "capital_reference": 10000.0,
    "risque_max_pct_par_trade": 1.0,
}

VARS_ENV_REQUISES = [
    "OPENROUTER_API_KEY",
    "TWELVEDATA_API_KEY",
]

VARS_ENV_EMAIL = [
    "BREVO_API_KEY",
    "TRADINGPOP_EMAIL_DESTINATAIRE",
    "TRADINGPOP_EMAIL_EXPEDITEUR",
]


@dataclass
class Config:
    watchlist: list[str] = field(default_factory=lambda: list(DEFAUTS["watchlist"]))
    refresh_minutes: int = DEFAUTS["refresh_minutes"]
    candle_interval: str = DEFAUTS["candle_interval"]
    candle_count: int = DEFAUTS["candle_count"]
    news_every_n_cycles: int = DEFAUTS["news_every_n_cycles"]
    recap_hour: int = DEFAUTS["recap_hour"]
    alert_confidence_threshold: int = DEFAUTS["alert_confidence_threshold"]
    alert_sound: bool = DEFAUTS["alert_sound"]
    model: str = DEFAUTS["model"]
    news_model: str = DEFAUTS["news_model"]
    outcome_horizons_hours: list[int] = field(
        default_factory=lambda: list(DEFAUTS["outcome_horizons_hours"])
    )
    history_limit: int = DEFAUTS["history_limit"]
    db_path: str = DEFAUTS["db_path"]
    swing_lookback: int = DEFAUTS["swing_lookback"]
    capital_reference: float = DEFAUTS["capital_reference"]
    risque_max_pct_par_trade: float = DEFAUTS["risque_max_pct_par_trade"]


def charger_dotenv(chemin: str | Path = ".env") -> None:
    """Charge un fichier .env minimaliste (KEY=VALUE) sans écraser l'existant."""
    p = Path(chemin)
    if not p.is_file():
        return
    for ligne in p.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        cle, valeur = cle.strip(), valeur.strip().strip("'\"")
        if cle and cle not in os.environ:
            os.environ[cle] = valeur


def charger_config(chemin: str | Path = "config.json") -> Config:
    """Charge config.json en complétant avec les valeurs par défaut."""
    donnees: dict = {}
    p = Path(chemin)
    if p.is_file():
        donnees = json.loads(p.read_text(encoding="utf-8"))
    inconnues = set(donnees) - set(DEFAUTS)
    if inconnues:
        raise ValueError(f"Clés de configuration inconnues : {sorted(inconnues)}")
    fusion = {**DEFAUTS, **donnees}
    return Config(**fusion)


def verifier_env(email_requis: bool = True) -> list[str]:
    """Retourne la liste des variables d'environnement manquantes."""
    requises = list(VARS_ENV_REQUISES)
    if email_requis:
        requises += VARS_ENV_EMAIL
    return [v for v in requises if not os.environ.get(v)]
