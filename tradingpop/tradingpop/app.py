"""Popup Tkinter : compact, toujours au premier plan, positionnable à côté de
TradingView. L'UI ne fait aucun appel réseau elle-même : elle consomme la file
remplie par le thread Worker et se rafraîchit via `after()`.
"""

from __future__ import annotations

import queue
import tkinter as tk
from datetime import datetime

from .config import Config
from .memory import Memoire
from .recap import AVERTISSEMENT, LIBELLES_ACTION, recap_du_matin
from .worker import Worker

COULEURS_ACTION = {
    "attendre": "#8a8f98",
    "opportunite_achat": "#2ecc71",
    "opportunite_vente": "#e74c3c",
    "prudence": "#f1c40f",
}
FOND = "#14161a"
FOND_LIGNE = "#1d2026"
TEXTE = "#e8eaed"
TEXTE_SECONDAIRE = "#9aa0a6"
INTERVALLE_POLL_MS = 200


class LignesInstrument:
    """Une vignette par instrument : prix, badge d'action, suggestion, confiance."""

    def __init__(self, parent: tk.Widget, symbole: str):
        self.symbole = symbole
        self.details = ""
        self.cadre = tk.Frame(parent, bg=FOND_LIGNE, padx=8, pady=6)
        self.cadre.pack(fill="x", padx=6, pady=3)

        haut = tk.Frame(self.cadre, bg=FOND_LIGNE)
        haut.pack(fill="x")
        tk.Label(
            haut, text=symbole, bg=FOND_LIGNE, fg=TEXTE, font=("Segoe UI", 10, "bold")
        ).pack(side="left")
        self.lbl_prix = tk.Label(
            haut, text="—", bg=FOND_LIGNE, fg=TEXTE, font=("Segoe UI", 10)
        )
        self.lbl_prix.pack(side="right")

        self.lbl_action = tk.Label(
            self.cadre,
            text="En attente de la première analyse…",
            bg=FOND_LIGNE,
            fg=TEXTE_SECONDAIRE,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        self.lbl_action.pack(fill="x", pady=(3, 0))

        self.lbl_suggestion = tk.Label(
            self.cadre,
            text="",
            bg=FOND_LIGNE,
            fg=TEXTE,
            font=("Segoe UI", 9),
            anchor="w",
            wraplength=300,
            justify="left",
        )
        self.lbl_suggestion.pack(fill="x")

        self.lbl_structure = tk.Label(
            self.cadre, text="", bg=FOND_LIGNE, fg=TEXTE_SECONDAIRE,
            font=("Segoe UI", 8), anchor="w", wraplength=300, justify="left",
        )
        self.lbl_structure.pack(fill="x")

        self.lbl_risque = tk.Label(
            self.cadre, text="", bg=FOND_LIGNE, fg=TEXTE_SECONDAIRE,
            font=("Segoe UI", 8), anchor="w", wraplength=300, justify="left",
        )
        self.lbl_risque.pack(fill="x")

        self.lbl_meta = tk.Label(
            self.cadre, text="", bg=FOND_LIGNE, fg=TEXTE_SECONDAIRE,
            font=("Segoe UI", 8), anchor="w",
        )
        self.lbl_meta.pack(fill="x")

        for widget in (
            self.cadre, self.lbl_action, self.lbl_suggestion,
            self.lbl_structure, self.lbl_risque, self.lbl_meta,
        ):
            widget.bind("<Button-1>", self._afficher_details)

    def mettre_a_jour(
        self, prix: float, analyse: dict, structure: dict | None, risque: dict | None
    ) -> None:
        couleur = COULEURS_ACTION.get(analyse["action"], TEXTE_SECONDAIRE)
        libelle = LIBELLES_ACTION.get(analyse["action"], analyse["action"])
        self.lbl_prix.config(text=f"{prix:g}")
        self.lbl_action.config(
            text=f"{libelle} — confiance {analyse['confiance']}/100", fg=couleur
        )
        self.lbl_suggestion.config(text=analyse["suggestion"])

        if structure:
            evenement = structure.get("evenement") or "pas de cassure nette"
            texte_structure = f"Structure : {structure['tendance']} — {evenement}"
        else:
            texte_structure = "Structure : indéterminée (historique insuffisant)"
        self.lbl_structure.config(text=texte_structure)

        if risque:
            texte_risque = (
                f"Taille sugg. : {risque['taille_position']:.2f} u. "
                f"(stop {risque['niveau_invalidation']:g}, "
                f"risque {risque['risque_montant']:.2f})"
            )
        else:
            texte_risque = "Taille de position : pas de niveau de stop fiable pour l'instant"
        self.lbl_risque.config(text=texte_risque)

        self.lbl_meta.config(text=datetime.now().strftime("analysé à %H:%M:%S"))
        self.details = (
            f"{self.symbole} — {libelle} (confiance {analyse['confiance']}/100)\n\n"
            f"Situation observée :\n{analyse['situation']}\n\n"
            f"Justification :\n{analyse['justification']}\n\n"
            f"{texte_structure}\n{texte_risque}\n\n{AVERTISSEMENT}"
        )

    def afficher_erreur(self, texte: str) -> None:
        self.lbl_meta.config(text=f"erreur : {texte[:80]}")

    def clignoter(self, fois: int = 6) -> None:
        """Alerte visuelle sur signal fort : la vignette clignote brièvement."""
        if fois <= 0:
            self.cadre.config(bg=FOND_LIGNE)
            return
        nouvelle = "#3d3115" if fois % 2 else FOND_LIGNE
        self.cadre.config(bg=nouvelle)
        self.cadre.after(250, lambda: self.clignoter(fois - 1))

    def _afficher_details(self, _evt) -> None:
        if self.details:
            FenetreTexte(self.cadre, f"Détail — {self.symbole}", self.details)


class FenetreTexte(tk.Toplevel):
    """Petite fenêtre de texte (détails d'analyse, récap quotidien)."""

    def __init__(self, parent: tk.Widget, titre: str, contenu: str):
        super().__init__(parent, bg=FOND)
        self.title(titre)
        self.attributes("-topmost", True)
        zone = tk.Text(
            self, bg=FOND, fg=TEXTE, font=("Segoe UI", 9), wrap="word",
            width=52, height=20, padx=10, pady=10, relief="flat",
        )
        zone.insert("1.0", contenu)
        zone.config(state="disabled")
        zone.pack(fill="both", expand=True)
        tk.Button(self, text="Fermer", command=self.destroy).pack(pady=4)


class PopupTradingPop:
    """Fenêtre principale : assemble worker, mémoire et vignettes."""

    def __init__(self, config: Config):
        self.config = config
        self.memoire = Memoire(config.db_path)
        self.file: queue.Queue = queue.Queue()
        self.worker = Worker(config, self.memoire, self.file)

        self.racine = tk.Tk()
        self.racine.title("TradingPop")
        self.racine.configure(bg=FOND)
        self.racine.attributes("-topmost", True)
        self.racine.geometry("340x560+40+40")
        self.racine.protocol("WM_DELETE_WINDOW", self.quitter)

        tk.Label(
            self.racine,
            text="TradingPop — analyses informatives, pas des conseils financiers",
            bg=FOND, fg=TEXTE_SECONDAIRE, font=("Segoe UI", 7), wraplength=320,
        ).pack(fill="x", padx=6, pady=(4, 0))

        conteneur = tk.Frame(self.racine, bg=FOND)
        conteneur.pack(fill="both", expand=True)
        self.lignes = {
            symbole: LignesInstrument(conteneur, symbole)
            for symbole in config.watchlist
        }

        self.lbl_statut = tk.Label(
            self.racine, text="Démarrage…", bg=FOND, fg=TEXTE_SECONDAIRE,
            font=("Segoe UI", 8), anchor="w",
        )
        self.lbl_statut.pack(fill="x", padx=6, pady=(0, 4))

    # -- Cycle de vie ----------------------------------------------------------

    def lancer(self) -> None:
        self.worker.start()
        self.racine.after(INTERVALLE_POLL_MS, self._consommer_file)
        self.racine.after(500, self._verifier_recap)
        self.racine.after(60_000, self._tic_horaire)
        self.racine.mainloop()

    def quitter(self) -> None:
        self.worker.stopper()
        self.racine.destroy()
        self.memoire.fermer()

    # -- File worker → UI ---------------------------------------------------------

    def _consommer_file(self) -> None:
        try:
            while True:
                message = self.file.get_nowait()
                self._traiter_message(message)
        except queue.Empty:
            pass
        self.racine.after(INTERVALLE_POLL_MS, self._consommer_file)

    def _traiter_message(self, message: dict) -> None:
        genre = message.get("type")
        if genre == "statut":
            self.lbl_statut.config(text=message["texte"])
        elif genre == "analyse":
            ligne = self.lignes.get(message["symbole"])
            if ligne:
                ligne.mettre_a_jour(
                    message["prix"],
                    message["analyse"],
                    message.get("structure"),
                    message.get("risque"),
                )
                if (
                    message["analyse"]["confiance"]
                    >= self.config.alert_confidence_threshold
                    and message["analyse"]["action"] != "attendre"
                ):
                    ligne.clignoter()
                    if self.config.alert_sound:
                        self.racine.bell()
            self.lbl_statut.config(
                text=f"Dernière analyse : {message['symbole']} "
                f"({datetime.now().strftime('%H:%M:%S')})"
            )
        elif genre == "erreur":
            ligne = self.lignes.get(message.get("symbole", ""))
            if ligne:
                ligne.afficher_erreur(message["texte"])
            self.lbl_statut.config(text=f"Erreur {message.get('symbole')} — voir vignette")

    # -- Récap quotidien -----------------------------------------------------------

    def _verifier_recap(self) -> None:
        """À l'ouverture puis chaque minute : génère/affiche le récap si dû."""
        recap = recap_du_matin(self.memoire)
        if recap:
            FenetreTexte(self.racine, "Récap quotidien", recap)

    def _tic_horaire(self) -> None:
        if datetime.now().hour >= self.config.recap_hour:
            self._verifier_recap()
        self.racine.after(60_000, self._tic_horaire)
