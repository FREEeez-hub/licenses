"""Détection de figures de bougies classiques (doji, marteau, avalement...).

Comme pour la structure de marché (structure.py), ces figures sont détectées
par calcul sur les prix réels, pas devinées par l'IA — elle les commente avec
un vocabulaire de trader, sans avoir à halluciner leur présence.
"""

from __future__ import annotations


def _metriques(bougie: dict) -> tuple[float, float, float, float]:
    corps = abs(bougie["close"] - bougie["open"])
    amplitude = bougie["high"] - bougie["low"]
    meche_haute = bougie["high"] - max(bougie["open"], bougie["close"])
    meche_basse = min(bougie["open"], bougie["close"]) - bougie["low"]
    return corps, amplitude, meche_haute, meche_basse


def _est_doji(bougie: dict) -> bool:
    corps, amplitude, _, _ = _metriques(bougie)
    return amplitude > 0 and corps <= 0.1 * amplitude


def _est_marteau(bougie: dict) -> bool:
    corps, amplitude, meche_haute, meche_basse = _metriques(bougie)
    return amplitude > 0 and corps > 0 and meche_basse >= 2 * corps and meche_haute <= corps


def _est_etoile_filante(bougie: dict) -> bool:
    corps, amplitude, meche_haute, meche_basse = _metriques(bougie)
    return amplitude > 0 and corps > 0 and meche_haute >= 2 * corps and meche_basse <= corps


def _est_avalement_haussier(precedente: dict, courante: dict) -> bool:
    return (
        precedente["close"] < precedente["open"]
        and courante["close"] > courante["open"]
        and courante["open"] <= precedente["close"]
        and courante["close"] >= precedente["open"]
    )


def _est_avalement_baissier(precedente: dict, courante: dict) -> bool:
    return (
        precedente["close"] > precedente["open"]
        and courante["close"] < courante["open"]
        and courante["open"] >= precedente["close"]
        and courante["close"] <= precedente["open"]
    )


def detecter_patterns_bougies(bougies: list[dict], n: int = 5) -> list[dict]:
    """Repère les figures de bougies classiques sur les `n` dernières bougies."""
    if not bougies:
        return []
    recentes = bougies[-n:]
    resultats = []
    for i, bougie in enumerate(recentes):
        if _est_doji(bougie):
            resultats.append(
                {
                    "nom": "Doji",
                    "datetime": bougie["datetime"],
                    "description": "corps très petit — indécision entre acheteurs et vendeurs",
                }
            )
        elif _est_marteau(bougie):
            resultats.append(
                {
                    "nom": "Marteau",
                    "datetime": bougie["datetime"],
                    "description": "mèche basse longue, petit corps — rejet des vendeurs",
                }
            )
        elif _est_etoile_filante(bougie):
            resultats.append(
                {
                    "nom": "Étoile filante",
                    "datetime": bougie["datetime"],
                    "description": "mèche haute longue, petit corps — rejet des acheteurs",
                }
            )
        if i > 0:
            precedente = recentes[i - 1]
            if _est_avalement_haussier(precedente, bougie):
                resultats.append(
                    {
                        "nom": "Avalement haussier",
                        "datetime": bougie["datetime"],
                        "description": "la bougie haussière englobe totalement la précédente baissière",
                    }
                )
            elif _est_avalement_baissier(precedente, bougie):
                resultats.append(
                    {
                        "nom": "Avalement baissier",
                        "datetime": bougie["datetime"],
                        "description": "la bougie baissière englobe totalement la précédente haussière",
                    }
                )
    return resultats
