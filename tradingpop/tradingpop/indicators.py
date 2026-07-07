"""Indicateurs techniques standards, en Python pur (pas de dépendance numpy).

Toutes les fonctions prennent une liste de prix de clôture, du plus ancien au
plus récent, et retournent soit une valeur, soit une série alignée sur la fin
de la liste d'entrée.
"""

from __future__ import annotations


def sma(prix: list[float], periode: int) -> float | None:
    """Moyenne mobile simple sur les `periode` derniers prix."""
    if len(prix) < periode or periode <= 0:
        return None
    return sum(prix[-periode:]) / periode


def ema_serie(prix: list[float], periode: int) -> list[float]:
    """Série EMA complète (première valeur = SMA d'amorçage)."""
    if len(prix) < periode or periode <= 0:
        return []
    k = 2 / (periode + 1)
    valeurs = [sum(prix[:periode]) / periode]
    for p in prix[periode:]:
        valeurs.append(p * k + valeurs[-1] * (1 - k))
    return valeurs


def ema(prix: list[float], periode: int) -> float | None:
    serie = ema_serie(prix, periode)
    return serie[-1] if serie else None


def rsi(prix: list[float], periode: int = 14) -> float | None:
    """RSI de Wilder (lissage exponentiel des gains/pertes)."""
    if len(prix) < periode + 1:
        return None
    gains, pertes = 0.0, 0.0
    for i in range(1, periode + 1):
        delta = prix[i] - prix[i - 1]
        if delta >= 0:
            gains += delta
        else:
            pertes -= delta
    gain_moy, perte_moy = gains / periode, pertes / periode
    for i in range(periode + 1, len(prix)):
        delta = prix[i] - prix[i - 1]
        gain_moy = (gain_moy * (periode - 1) + max(delta, 0)) / periode
        perte_moy = (perte_moy * (periode - 1) + max(-delta, 0)) / periode
    if perte_moy == 0:
        return 100.0
    rs = gain_moy / perte_moy
    return 100 - 100 / (1 + rs)


def macd(
    prix: list[float], rapide: int = 12, lente: int = 26, signal: int = 9
) -> dict | None:
    """MACD classique : ligne MACD, ligne signal et histogramme."""
    if len(prix) < lente + signal:
        return None
    ema_rapide = ema_serie(prix, rapide)
    ema_lente = ema_serie(prix, lente)
    # Aligne les deux séries sur leur fin commune.
    n = min(len(ema_rapide), len(ema_lente))
    ligne_macd = [ema_rapide[-n + i] - ema_lente[-n + i] for i in range(n)]
    ligne_signal = ema_serie(ligne_macd, signal)
    if not ligne_signal:
        return None
    return {
        "macd": ligne_macd[-1],
        "signal": ligne_signal[-1],
        "histogramme": ligne_macd[-1] - ligne_signal[-1],
    }


def calculer_indicateurs(clotures: list[float]) -> dict:
    """Calcule le jeu d'indicateurs transmis à l'IA pour une série de clôtures."""
    resultat = {
        "dernier_prix": clotures[-1] if clotures else None,
        "sma_20": sma(clotures, 20),
        "sma_50": sma(clotures, 50),
        "ema_20": ema(clotures, 20),
        "rsi_14": rsi(clotures, 14),
        "macd": macd(clotures),
    }
    if len(clotures) >= 2 and clotures[-2]:
        resultat["variation_derniere_bougie_pct"] = (
            (clotures[-1] - clotures[-2]) / clotures[-2] * 100
        )
    return resultat
