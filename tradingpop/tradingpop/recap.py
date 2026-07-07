"""Récap quotidien : construit le résumé de la veille, l'envoie par email
(Brevo, même compte que GrantHound) ET le fournit au popup pour affichage à
l'ouverture — les deux canaux, conformément à la spec.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import requests

from .memory import Memoire

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
TIMEOUT = 30

LIBELLES_ACTION = {
    "attendre": "Attendre",
    "opportunite_achat": "Opportunité d'achat possible",
    "opportunite_vente": "Opportunité de vente possible",
    "prudence": "Prudence",
}

AVERTISSEMENT = (
    "Analyse informative générée automatiquement — ceci n'est pas un conseil "
    "financier. Aucun ordre n'est passé automatiquement."
)


def construire_recap(memoire: Memoire, jour: str) -> str:
    """Récap texte d'une journée : suggestions données et résultats constatés."""
    suggestions = memoire.suggestions_du_jour(jour)
    lignes = [f"Récap TradingPop — journée du {jour}", ""]
    if not suggestions:
        lignes.append("Aucune suggestion enregistrée ce jour-là.")
    else:
        par_symbole: dict[str, list[dict]] = {}
        for s in suggestions:
            par_symbole.setdefault(s["symbole"], []).append(s)
        for symbole, liste in par_symbole.items():
            lignes.append(f"## {symbole} ({len(liste)} analyse(s))")
            for s in liste:
                heure = s["cree_le"][11:16]
                libelle = LIBELLES_ACTION.get(s["action"], s["action"])
                lignes.append(
                    f"- {heure} — {libelle} (confiance {s['confiance']}) : "
                    f"{s['suggestion']}"
                )
                if s["resultats"]:
                    details = ", ".join(
                        f"T+{r['horizon_heures']}h : {r['variation_pct']:+.2f} %"
                        for r in s["resultats"]
                    )
                    lignes.append(f"  Résultat réel : {details}")
                else:
                    lignes.append("  Résultat réel : pas encore évalué")
            lignes.append("")
    lignes.append(AVERTISSEMENT)
    return "\n".join(lignes).strip()


def envoyer_email_recap(recap: str, jour: str) -> None:
    """Envoie le récap via l'API Brevo. Lève en cas d'échec (l'appelant loggue)."""
    cle = os.environ.get("BREVO_API_KEY")
    destinataire = os.environ.get("TRADINGPOP_EMAIL_DESTINATAIRE")
    expediteur = os.environ.get("TRADINGPOP_EMAIL_EXPEDITEUR")
    if not (cle and destinataire and expediteur):
        raise RuntimeError(
            "BREVO_API_KEY / TRADINGPOP_EMAIL_DESTINATAIRE /"
            " TRADINGPOP_EMAIL_EXPEDITEUR requis pour l'envoi du récap"
        )
    corps_html = "<pre style='font-family:monospace'>" + (
        recap.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    ) + "</pre>"
    reponse = requests.post(
        BREVO_URL,
        headers={"api-key": cle, "Content-Type": "application/json"},
        json={
            "sender": {"name": "TradingPop", "email": expediteur},
            "to": [{"email": destinataire}],
            "subject": f"Récap TradingPop — {jour}",
            "htmlContent": corps_html,
            "textContent": recap,
        },
        timeout=TIMEOUT,
    )
    reponse.raise_for_status()


def recap_du_matin(memoire: Memoire, aujourdhui: date | None = None) -> str | None:
    """Génère et envoie le récap de la veille, une seule fois par jour.

    Retourne le texte du récap s'il vient d'être généré (à afficher dans le
    popup), None s'il a déjà été traité aujourd'hui. L'échec de l'email ne
    bloque pas l'affichage : le texte est retourné avec une note d'erreur.
    """
    aujourdhui = aujourdhui or date.today()
    if memoire.lire_meta("dernier_recap") == aujourdhui.isoformat():
        return None
    veille = (aujourdhui - timedelta(days=1)).isoformat()
    recap = construire_recap(memoire, veille)
    try:
        envoyer_email_recap(recap, veille)
    except Exception as exc:  # noqa: BLE001 — l'affichage prime sur l'email
        recap += f"\n\n[Envoi email échoué : {exc}]"
    memoire.ecrire_meta("dernier_recap", aujourdhui.isoformat())
    return recap
