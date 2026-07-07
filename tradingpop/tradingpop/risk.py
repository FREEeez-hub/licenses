"""Calcul de taille de position et de risque — un calcul mathématique
transparent à partir de paramètres définis par l'utilisateur (capital de
référence, risque max par trade), pas une estimation devinée par l'IA.
"""

from __future__ import annotations


def calculer_position(
    prix_actuel: float,
    niveau_invalidation: float | None,
    capital_reference: float,
    risque_max_pct_par_trade: float,
) -> dict | None:
    """Taille de position et perte si le niveau d'invalidation est touché.

    None si aucun niveau d'invalidation fiable n'est disponible (structure
    trop incertaine) : dans ce cas, aucun calcul de risque n'est affiché.
    """
    if niveau_invalidation is None or prix_actuel == niveau_invalidation:
        return None
    distance_stop = abs(prix_actuel - niveau_invalidation)
    risque_montant = capital_reference * risque_max_pct_par_trade / 100
    return {
        "niveau_invalidation": niveau_invalidation,
        "distance_stop": distance_stop,
        "distance_stop_pct": distance_stop / prix_actuel * 100,
        "risque_montant": risque_montant,
        "taille_position": risque_montant / distance_stop,
    }
