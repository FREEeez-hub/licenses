"""Boucle de fond : collecte, analyse, mémoire, suivi des résultats.

Tourne dans un thread séparé de l'UI ; chaque résultat est poussé dans une
file thread-safe que le popup consomme, pour que l'interface ne se fige
jamais pendant un appel réseau ou IA.
"""

from __future__ import annotations

import queue
import threading
import time
import traceback

from . import ai, market_data, news, patterns, risk, structure
from .config import Config
from .memory import Memoire


class Worker(threading.Thread):
    """Thread de surveillance : un cycle = toute la watchlist analysée."""

    def __init__(self, config: Config, memoire: Memoire, sortie: queue.Queue):
        super().__init__(daemon=True, name="tradingpop-worker")
        self.config = config
        self.memoire = memoire
        self.sortie = sortie  # messages {"type": ..., ...} vers l'UI
        self.arret = threading.Event()
        self.cache_actualites = news.CacheActualites(
            duree_vie_s=config.news_every_n_cycles * config.refresh_minutes * 60
        )
        self._cycle = 0

    # -- Boucle principale ---------------------------------------------------

    def run(self) -> None:
        while not self.arret.is_set():
            debut = time.time()
            self._evaluer_suggestions_passees()
            for symbole in self.config.watchlist:
                if self.arret.is_set():
                    return
                self._analyser_instrument(symbole)
            self._cycle += 1
            # Attente jusqu'au prochain cycle, interruptible immédiatement.
            restant = self.config.refresh_minutes * 60 - (time.time() - debut)
            if restant > 0:
                self.arret.wait(restant)

    def stopper(self) -> None:
        self.arret.set()

    # -- Un instrument ---------------------------------------------------------

    def _analyser_instrument(self, symbole: str) -> None:
        self._emettre({"type": "statut", "texte": f"Analyse de {symbole}…"})
        try:
            bougies = market_data.recuperer_bougies(
                symbole, self.config.candle_interval, self.config.candle_count
            )
            clotures = [b["close"] for b in bougies]
            from .indicators import calculer_indicateurs

            indicateurs = calculer_indicateurs(clotures)
            structure_marche = structure.detecter_structure(
                bougies, self.config.swing_lookback
            )
            patterns_bougies = patterns.detecter_patterns_bougies(bougies)

            actualites = None
            if self._cycle % max(1, self.config.news_every_n_cycles) == 0:
                actualites = news.rechercher_actualites(
                    self.config.news_model, symbole, self.cache_actualites
                )
            else:
                actualites = self.cache_actualites.obtenir(symbole)

            historique = self.memoire.resume_historique(
                symbole, self.config.history_limit
            )
            analyse = ai.analyser(
                self.config.model,
                symbole,
                bougies,
                indicateurs,
                structure_marche,
                patterns_bougies,
                actualites,
                historique,
            )
            risque = risk.calculer_position(
                clotures[-1],
                structure_marche["niveau_invalidation"],
                self.config.capital_reference,
                self.config.risque_max_pct_par_trade,
            )
            contexte = {
                "indicateurs": indicateurs,
                "structure": structure_marche,
                "patterns": patterns_bougies,
                "risque": risque,
                "actualites": (actualites or "")[:500],
            }
            self.memoire.enregistrer_suggestion(
                symbole,
                clotures[-1],
                contexte,
                analyse,
                self.config.outcome_horizons_hours,
            )
            self._emettre(
                {
                    "type": "analyse",
                    "symbole": symbole,
                    "prix": clotures[-1],
                    "analyse": analyse,
                    "structure": structure_marche,
                    "risque": risque,
                }
            )
        except Exception as exc:  # noqa: BLE001 — un instrument en échec ne stoppe pas la boucle
            self._emettre(
                {
                    "type": "erreur",
                    "symbole": symbole,
                    "texte": f"{type(exc).__name__} : {exc}",
                    "trace": traceback.format_exc(),
                }
            )

    # -- Suivi des suggestions passées -----------------------------------------

    def _evaluer_suggestions_passees(self) -> None:
        """Note le prix réel pour chaque suggestion arrivée à échéance."""
        try:
            dues = self.memoire.evaluations_dues()
        except Exception:  # noqa: BLE001
            return
        prix_cache: dict[str, float] = {}
        for due in dues:
            symbole = due["symbole"]
            try:
                if symbole not in prix_cache:
                    prix_cache[symbole] = market_data.recuperer_prix(symbole)
                self.memoire.enregistrer_resultat(
                    due["suggestion_id"], due["horizon_heures"], prix_cache[symbole]
                )
            except Exception:  # noqa: BLE001 — réessaiera au prochain cycle
                continue

    # -- Communication UI ---------------------------------------------------------

    def _emettre(self, message: dict) -> None:
        self.sortie.put(message)
