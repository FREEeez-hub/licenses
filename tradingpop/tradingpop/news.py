"""Recherche d'actualités ciblée avant analyse.

Implémentation : un appel OpenRouter avec un modèle à suffixe ":online"
(plugin de recherche web d'OpenRouter). Même clé API que l'analyse, aucun
service supplémentaire à configurer — cohérent avec la décision de ne pas
prendre d'API de calendrier économique pour la phase de test.

Les résumés sont mis en cache par instrument : la recherche ne tourne que
tous les `news_every_n_cycles` cycles (configurable) pour limiter le coût.
"""

from __future__ import annotations

import time

from .ai import appel_openrouter

PROMPT_NEWS = """Fais une recherche web sur l'actualité récente concernant \
l'instrument financier "{symbole}" (ex. décisions de banques centrales, résultats \
d'entreprise, données macro, événements géopolitiques qui l'affectent aujourd'hui).

Résume en 3 à 6 puces factuelles, en français, avec les dates quand tu les connais. \
Si tu ne trouves rien de significatif ou de récent, réponds exactement : \
"Rien de significatif trouvé." N'invente aucun fait."""


class CacheActualites:
    """Cache mémoire {symbole: (timestamp, résumé)} avec durée de vie en secondes."""

    def __init__(self, duree_vie_s: float):
        self.duree_vie_s = duree_vie_s
        self._cache: dict[str, tuple[float, str]] = {}

    def obtenir(self, symbole: str) -> str | None:
        entree = self._cache.get(symbole)
        if entree and time.time() - entree[0] < self.duree_vie_s:
            return entree[1]
        return None

    def enregistrer(self, symbole: str, resume: str) -> None:
        self._cache[symbole] = (time.time(), resume)


def rechercher_actualites(
    news_model: str, symbole: str, cache: CacheActualites | None = None
) -> str | None:
    """Retourne un résumé d'actualité pour l'instrument, ou None en cas d'échec.

    Un échec de recherche d'actualités ne doit jamais bloquer l'analyse :
    l'appelant transmet alors None et l'IA raisonne sur les seules données.
    """
    if cache:
        en_cache = cache.obtenir(symbole)
        if en_cache is not None:
            return en_cache
    try:
        resume = appel_openrouter(
            news_model,
            [{"role": "user", "content": PROMPT_NEWS.format(symbole=symbole)}],
        ).strip()
    except Exception:  # noqa: BLE001 — la news ne bloque jamais l'analyse
        return None
    if cache and resume:
        cache.enregistrer(symbole, resume)
    return resume or None
