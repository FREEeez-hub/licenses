"""Mémoire des suggestions en SQLite locale (pas de fine-tuning, décision de spec).

Chaque analyse est enregistrée avec son contexte de marché ; un suivi
automatique note le prix réel aux horizons configurés (T+1h, T+1j...) et le
résultat est réinjecté dans les analyses suivantes sous forme de résumé texte.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta

from .ai import ACTIONS_VALIDES

SCHEMA = """
CREATE TABLE IF NOT EXISTS suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cree_le TEXT NOT NULL,               -- ISO 8601, heure locale
    symbole TEXT NOT NULL,
    prix REAL NOT NULL,                  -- prix au moment de la suggestion
    contexte TEXT NOT NULL,              -- JSON : indicateurs + extrait actu
    situation TEXT NOT NULL,
    action TEXT NOT NULL,
    suggestion TEXT NOT NULL,
    confiance INTEGER NOT NULL,
    justification TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_suggestions_symbole ON suggestions (symbole, cree_le);

CREATE TABLE IF NOT EXISTS resultats (
    suggestion_id INTEGER NOT NULL REFERENCES suggestions (id),
    horizon_heures INTEGER NOT NULL,
    echeance TEXT NOT NULL,              -- ISO 8601 : quand évaluer
    prix_constate REAL,                  -- NULL tant que non évalué
    variation_pct REAL,
    evalue_le TEXT,
    PRIMARY KEY (suggestion_id, horizon_heures)
);

CREATE TABLE IF NOT EXISTS meta (
    cle TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);
"""


class Memoire:
    """Accès thread-safe à la base tradingpop.db (UI + thread de fond)."""

    def __init__(self, chemin_db: str):
        self._verrou = threading.Lock()
        self._conn = sqlite3.connect(chemin_db, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._verrou:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def fermer(self) -> None:
        with self._verrou:
            self._conn.close()

    # -- Enregistrement --------------------------------------------------

    def enregistrer_suggestion(
        self,
        symbole: str,
        prix: float,
        contexte: dict,
        analyse: dict,
        horizons_heures: list[int],
        quand: datetime | None = None,
    ) -> int:
        """Enregistre une analyse et planifie l'évaluation à chaque horizon."""
        if analyse["action"] not in ACTIONS_VALIDES:
            raise ValueError(f"Action inconnue : {analyse['action']}")
        quand = quand or datetime.now()
        with self._verrou:
            curseur = self._conn.execute(
                "INSERT INTO suggestions (cree_le, symbole, prix, contexte,"
                " situation, action, suggestion, confiance, justification)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    quand.isoformat(timespec="seconds"),
                    symbole,
                    prix,
                    json.dumps(contexte, ensure_ascii=False),
                    analyse["situation"],
                    analyse["action"],
                    analyse["suggestion"],
                    analyse["confiance"],
                    analyse["justification"],
                ),
            )
            suggestion_id = curseur.lastrowid
            for heures in horizons_heures:
                echeance = quand + timedelta(hours=heures)
                self._conn.execute(
                    "INSERT INTO resultats (suggestion_id, horizon_heures, echeance)"
                    " VALUES (?, ?, ?)",
                    (suggestion_id, heures, echeance.isoformat(timespec="seconds")),
                )
            self._conn.commit()
        return suggestion_id

    # -- Suivi des résultats ----------------------------------------------

    def evaluations_dues(self, maintenant: datetime | None = None) -> list[dict]:
        """Résultats arrivés à échéance et pas encore évalués."""
        maintenant = maintenant or datetime.now()
        with self._verrou:
            lignes = self._conn.execute(
                "SELECT r.suggestion_id, r.horizon_heures, s.symbole, s.prix"
                " FROM resultats r JOIN suggestions s ON s.id = r.suggestion_id"
                " WHERE r.prix_constate IS NULL AND r.echeance <= ?",
                (maintenant.isoformat(timespec="seconds"),),
            ).fetchall()
        return [dict(l) for l in lignes]

    def enregistrer_resultat(
        self,
        suggestion_id: int,
        horizon_heures: int,
        prix_constate: float,
        quand: datetime | None = None,
    ) -> None:
        quand = quand or datetime.now()
        with self._verrou:
            ligne = self._conn.execute(
                "SELECT prix FROM suggestions WHERE id = ?", (suggestion_id,)
            ).fetchone()
            if ligne is None:
                return
            prix_initial = ligne["prix"]
            variation = (
                (prix_constate - prix_initial) / prix_initial * 100
                if prix_initial
                else None
            )
            self._conn.execute(
                "UPDATE resultats SET prix_constate = ?, variation_pct = ?,"
                " evalue_le = ? WHERE suggestion_id = ? AND horizon_heures = ?",
                (
                    prix_constate,
                    variation,
                    quand.isoformat(timespec="seconds"),
                    suggestion_id,
                    horizon_heures,
                ),
            )
            self._conn.commit()

    # -- Réinjection dans les analyses -------------------------------------

    def resume_historique(self, symbole: str, limite: int = 8) -> str | None:
        """Résumé texte des dernières suggestions évaluées, pour le prompt IA."""
        with self._verrou:
            lignes = self._conn.execute(
                "SELECT s.cree_le, s.prix, s.action, s.suggestion, s.confiance,"
                " r.horizon_heures, r.variation_pct"
                " FROM suggestions s JOIN resultats r ON r.suggestion_id = s.id"
                " WHERE s.symbole = ? AND r.prix_constate IS NOT NULL"
                " ORDER BY s.cree_le DESC, r.horizon_heures ASC LIMIT ?",
                (symbole, limite * 3),
            ).fetchall()
        if not lignes:
            return None
        par_suggestion: dict[str, dict] = {}
        for l in lignes:
            entree = par_suggestion.setdefault(
                l["cree_le"],
                {
                    "cree_le": l["cree_le"],
                    "action": l["action"],
                    "suggestion": l["suggestion"],
                    "confiance": l["confiance"],
                    "resultats": [],
                },
            )
            entree["resultats"].append(
                f"T+{l['horizon_heures']}h : {l['variation_pct']:+.2f} %"
            )
        parties = []
        for entree in list(par_suggestion.values())[:limite]:
            parties.append(
                f"- {entree['cree_le']} — action \"{entree['action']}\" "
                f"(confiance {entree['confiance']}) : {entree['suggestion']} "
                f"→ résultat réel : {', '.join(entree['resultats'])}"
            )
        return "\n".join(parties)

    # -- Récap quotidien ----------------------------------------------------

    def suggestions_du_jour(self, jour: str) -> list[dict]:
        """Toutes les suggestions d'une date (YYYY-MM-DD), avec leurs résultats."""
        with self._verrou:
            suggestions = self._conn.execute(
                "SELECT * FROM suggestions WHERE cree_le LIKE ? ORDER BY cree_le",
                (f"{jour}%",),
            ).fetchall()
            resultats = {}
            for s in suggestions:
                resultats[s["id"]] = [
                    dict(r)
                    for r in self._conn.execute(
                        "SELECT horizon_heures, variation_pct, prix_constate"
                        " FROM resultats WHERE suggestion_id = ?"
                        " AND prix_constate IS NOT NULL ORDER BY horizon_heures",
                        (s["id"],),
                    ).fetchall()
                ]
        return [{**dict(s), "resultats": resultats[s["id"]]} for s in suggestions]

    # -- Méta (déduplication du récap, etc.) ---------------------------------

    def lire_meta(self, cle: str) -> str | None:
        with self._verrou:
            ligne = self._conn.execute(
                "SELECT valeur FROM meta WHERE cle = ?", (cle,)
            ).fetchone()
        return ligne["valeur"] if ligne else None

    def ecrire_meta(self, cle: str, valeur: str) -> None:
        with self._verrou:
            self._conn.execute(
                "INSERT INTO meta (cle, valeur) VALUES (?, ?)"
                " ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
                (cle, valeur),
            )
            self._conn.commit()
