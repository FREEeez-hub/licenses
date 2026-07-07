"""Analyse IA via OpenRouter (même clé que GrantHound : OPENROUTER_API_KEY).

L'IA reçoit les données de marché, les indicateurs, l'actualité récente et un
résumé de ses suggestions passées, puis raisonne librement — aucune stratégie
à règles fixes n'est imposée. La sortie est structurée en JSON pour affichage
et enregistrement en mémoire.
"""

from __future__ import annotations

import json
import os

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT = 120

ACTIONS_VALIDES = {"attendre", "opportunite_achat", "opportunite_vente", "prudence"}

PROMPT_SYSTEME = """Tu es l'analyste de TradingPop, un assistant personnel d'observation \
des marchés. Tu produis des analyses informatives, jamais des conseils financiers \
réglementés et jamais d'ordres à exécuter.

Écris comme un trader expérimenté qui commente un graphique : nomme les mouvements, \
les fluctuations et les figures avec un vocabulaire précis (structure de marché, \
cassures, figures de bougies), pas juste "le prix a monté".

À chaque analyse :
1. DÉCRIS d'abord concrètement ce que tu observes dans les données (choc de prix, \
cassure de range, divergence RSI/prix, croisement de moyennes, volatilité anormale...). \
Ne saute jamais directement au verdict.
2. Une structure de marché (tendance, dernier plus haut/bas significatif, événement \
BOS/CHoCH éventuel) et des figures de bougies sont fournies plus bas, déjà calculées \
à partir des prix réels. Réfère-toi à ces éléments par leur nom exact s'ils sont \
pertinents. N'invente JAMAIS de cassure ou de figure supplémentaire que celles \
fournies — si aucun événement n'est indiqué, dis simplement que la structure ne \
montre pas de cassure nette en ce moment.
3. Intègre l'actualité fournie si elle est pertinente. N'invente JAMAIS de fait \
d'actualité : si l'actualité fournie est vide ou hors sujet, dis-le et raisonne \
uniquement sur les données.
4. Tiens compte de tes suggestions passées sur cet instrument et de leur résultat \
réel pour ajuster ton raisonnement (ex. "la dernière fois que ce schéma est apparu, \
le prix a fait X").
5. Ne calcule et ne mentionne JAMAIS de taille de position ou de montant à risquer : \
ce calcul est fait séparément par l'application, à partir de paramètres que \
l'utilisateur contrôle. Reste sur la description du marché.

Réponds UNIQUEMENT avec un objet JSON (aucun texte autour) au format :
{
  "situation": "description concrète de ce qui est observé, 2-4 phrases",
  "action": "attendre" | "opportunite_achat" | "opportunite_vente" | "prudence",
  "suggestion": "la suggestion en une phrase de langage humain",
  "confiance": entier 0-100,
  "justification": "justification courte (1-2 phrases)"
}"""


class AIError(RuntimeError):
    """Erreur de l'appel IA (réseau, quota, sortie illisible)."""


def _cle_api() -> str:
    cle = os.environ.get("OPENROUTER_API_KEY")
    if not cle:
        raise AIError("OPENROUTER_API_KEY manquante dans l'environnement")
    return cle


def appel_openrouter(model: str, messages: list[dict], **extra) -> str:
    """Appel brut OpenRouter, retourne le texte de la première réponse."""
    reponse = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {_cle_api()}",
            "Content-Type": "application/json",
            "X-Title": "TradingPop",
        },
        json={"model": model, "messages": messages, **extra},
        timeout=TIMEOUT,
    )
    reponse.raise_for_status()
    donnees = reponse.json()
    try:
        return donnees["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise AIError(f"Réponse OpenRouter illisible : {donnees}") from exc


def _extraire_json(texte: str) -> dict:
    """Extrait l'objet JSON de la réponse, même entouré de texte ou de ```."""
    texte = texte.strip()
    debut, fin = texte.find("{"), texte.rfind("}")
    if debut == -1 or fin <= debut:
        raise AIError(f"Pas de JSON dans la réponse IA : {texte[:200]}")
    return json.loads(texte[debut : fin + 1])


def construire_prompt_analyse(
    symbole: str,
    bougies: list[dict],
    indicateurs: dict,
    structure: dict | None,
    patterns: list[dict] | None,
    actualites: str | None,
    historique: str | None,
) -> str:
    """Assemble le message utilisateur transmis au modèle."""
    dernieres = bougies[-20:]
    parties = [
        f"Instrument : {symbole}",
        "",
        "## 20 dernières bougies (OHLC, de la plus ancienne à la plus récente)",
        json.dumps(dernieres, ensure_ascii=False),
        "",
        "## Indicateurs techniques calculés sur la série complète",
        json.dumps(indicateurs, ensure_ascii=False),
        "",
        "## Structure de marché calculée (faits, pas une estimation de ta part)",
        json.dumps(structure, ensure_ascii=False) if structure else "(structure non calculable, historique insuffisant)",
        "",
        "## Figures de bougies détectées sur les dernières bougies",
        json.dumps(patterns, ensure_ascii=False) if patterns else "(aucune figure de bougie détectée)",
        "",
        "## Actualité récente (résumé de recherche web)",
        actualites.strip() if actualites else "(aucune actualité disponible pour ce cycle)",
        "",
        "## Tes suggestions passées sur cet instrument et leur résultat réel",
        historique.strip() if historique else "(aucun historique pour l'instant)",
    ]
    return "\n".join(parties)


def analyser(
    model: str,
    symbole: str,
    bougies: list[dict],
    indicateurs: dict,
    structure: dict | None,
    patterns: list[dict] | None,
    actualites: str | None,
    historique: str | None,
) -> dict:
    """Lance une analyse et retourne le JSON validé/normalisé."""
    contenu = appel_openrouter(
        model,
        [
            {"role": "system", "content": PROMPT_SYSTEME},
            {
                "role": "user",
                "content": construire_prompt_analyse(
                    symbole, bougies, indicateurs, structure, patterns, actualites, historique
                ),
            },
        ],
    )
    brut = _extraire_json(contenu)
    return normaliser_analyse(brut)


def normaliser_analyse(brut: dict) -> dict:
    """Valide et normalise la sortie IA (champs requis, bornes de confiance)."""
    action = str(brut.get("action", "attendre")).strip().lower()
    if action not in ACTIONS_VALIDES:
        action = "attendre"
    try:
        confiance = max(0, min(100, int(brut.get("confiance", 0))))
    except (TypeError, ValueError):
        confiance = 0
    return {
        "situation": str(brut.get("situation", "")).strip(),
        "action": action,
        "suggestion": str(brut.get("suggestion", "")).strip(),
        "confiance": confiance,
        "justification": str(brut.get("justification", "")).strip(),
    }
