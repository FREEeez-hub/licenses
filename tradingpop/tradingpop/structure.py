"""Détection de structure de marché : swings, BOS et CHoCH.

Ces événements sont calculés directement à partir des prix (pas devinés par
l'IA) pour que les schémas nommés dans l'analyse correspondent à des
cassures réellement mesurées, et non à une estimation visuelle sujette à
hallucination.

Vocabulaire :
- Swing high/low : un plus haut ou plus bas local (pivot) sur une fenêtre de
  bougies.
- BOS (Break of Structure) : cassure du dernier swing dans le sens de la
  tendance en cours — continuation probable.
- CHoCH (Change of Character) : cassure du dernier swing à l'opposé de la
  tendance en cours — retournement potentiel.
"""

from __future__ import annotations


def swings(bougies: list[dict], lookback: int = 3) -> list[dict]:
    """Détecte les pivots (swing highs/lows) sur `lookback` bougies de chaque côté."""
    points = []
    n = len(bougies)
    for i in range(lookback, n - lookback):
        fenetre = bougies[i - lookback : i + lookback + 1]
        haut, bas = bougies[i]["high"], bougies[i]["low"]
        if haut == max(b["high"] for b in fenetre):
            points.append(
                {"type": "haut", "prix": haut, "datetime": bougies[i]["datetime"]}
            )
        elif bas == min(b["low"] for b in fenetre):
            points.append(
                {"type": "bas", "prix": bas, "datetime": bougies[i]["datetime"]}
            )
    return points


def detecter_structure(bougies: list[dict], lookback: int = 3) -> dict:
    """Résume la structure récente : tendance, derniers swings, BOS/CHoCH éventuel.

    Le résultat sert à la fois de contexte pour le prompt IA (des faits à
    commenter, pas à deviner) et de niveau d'invalidation pour le calcul de
    taille de position.
    """
    points = swings(bougies, lookback)
    hauts = [p for p in points if p["type"] == "haut"]
    bas = [p for p in points if p["type"] == "bas"]

    resultat_vide = {
        "tendance": "indéterminée",
        "evenement": None,
        "dernier_swing_haut": hauts[-1] if hauts else None,
        "dernier_swing_bas": bas[-1] if bas else None,
        "niveau_invalidation": None,
    }
    if len(hauts) < 2 or len(bas) < 2:
        return resultat_vide

    dernier_haut, avant_haut = hauts[-1], hauts[-2]
    dernier_bas, avant_bas = bas[-1], bas[-2]

    if dernier_haut["prix"] > avant_haut["prix"] and dernier_bas["prix"] > avant_bas["prix"]:
        tendance = "haussière"
    elif dernier_haut["prix"] < avant_haut["prix"] and dernier_bas["prix"] < avant_bas["prix"]:
        tendance = "baissière"
    else:
        tendance = "range"

    prix_actuel = bougies[-1]["close"]
    evenement: str | None = None

    if tendance == "haussière":
        if prix_actuel > dernier_haut["prix"]:
            evenement = "BOS haussier (cassure du dernier plus haut, continuation probable)"
            niveau_invalidation = dernier_bas["prix"]
        elif prix_actuel < dernier_bas["prix"]:
            evenement = "CHoCH baissier (cassure du dernier plus bas, tendance potentiellement retournée)"
            niveau_invalidation = dernier_haut["prix"]
        else:
            niveau_invalidation = dernier_bas["prix"]
    elif tendance == "baissière":
        if prix_actuel < dernier_bas["prix"]:
            evenement = "BOS baissier (cassure du dernier plus bas, continuation probable)"
            niveau_invalidation = dernier_haut["prix"]
        elif prix_actuel > dernier_haut["prix"]:
            evenement = "CHoCH haussier (cassure du dernier plus haut, tendance potentiellement retournée)"
            niveau_invalidation = dernier_bas["prix"]
        else:
            niveau_invalidation = dernier_haut["prix"]
    else:
        niveau_invalidation = (
            dernier_bas["prix"] if prix_actuel >= dernier_bas["prix"] else dernier_haut["prix"]
        )

    return {
        "tendance": tendance,
        "evenement": evenement,
        "dernier_swing_haut": dernier_haut,
        "dernier_swing_bas": dernier_bas,
        "niveau_invalidation": niveau_invalidation,
    }
