"""Client Twelve Data : bougies et prix spot pour actions et paires forex.

Twelve Data accepte les symboles actions ("AAPL") et forex ("EUR/USD") avec la
même API, ce qui couvre toute la watchlist sans compte broker.
"""

from __future__ import annotations

import os

import requests

BASE_URL = "https://api.twelvedata.com"
TIMEOUT = 30


class MarketDataError(RuntimeError):
    """Erreur renvoyée par l'API de données de marché."""


def _cle_api() -> str:
    cle = os.environ.get("TWELVEDATA_API_KEY")
    if not cle:
        raise MarketDataError("TWELVEDATA_API_KEY manquante dans l'environnement")
    return cle


def _get(endpoint: str, params: dict) -> dict:
    params = {**params, "apikey": _cle_api()}
    reponse = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=TIMEOUT)
    reponse.raise_for_status()
    donnees = reponse.json()
    if isinstance(donnees, dict) and donnees.get("status") == "error":
        raise MarketDataError(donnees.get("message", "erreur Twelve Data inconnue"))
    return donnees


def recuperer_bougies(
    symbole: str, intervalle: str = "5min", nombre: int = 120
) -> list[dict]:
    """Retourne les bougies OHLC du plus ancien au plus récent.

    Chaque bougie : {"datetime", "open", "high", "low", "close"} (floats).
    """
    donnees = _get(
        "time_series",
        {"symbol": symbole, "interval": intervalle, "outputsize": nombre},
    )
    valeurs = donnees.get("values") or []
    bougies = []
    for v in reversed(valeurs):  # Twelve Data renvoie du plus récent au plus ancien
        bougies.append(
            {
                "datetime": v["datetime"],
                "open": float(v["open"]),
                "high": float(v["high"]),
                "low": float(v["low"]),
                "close": float(v["close"]),
            }
        )
    if not bougies:
        raise MarketDataError(f"Aucune bougie reçue pour {symbole}")
    return bougies


def recuperer_prix(symbole: str) -> float:
    """Prix spot courant, utilisé pour évaluer les suggestions passées."""
    donnees = _get("price", {"symbol": symbole})
    try:
        return float(donnees["price"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MarketDataError(f"Prix illisible pour {symbole} : {donnees}") from exc
