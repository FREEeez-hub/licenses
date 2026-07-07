"""Point d'entrée : `python -m tradingpop` depuis le dossier du projet."""

from __future__ import annotations

import sys

from .config import charger_config, charger_dotenv, verifier_env


def main() -> int:
    charger_dotenv()
    manquantes = verifier_env(email_requis=False)
    if manquantes:
        print(
            "Variables d'environnement manquantes : " + ", ".join(manquantes),
            file=sys.stderr,
        )
        print("Voir .env.example pour la liste complète.", file=sys.stderr)
        return 1
    manquantes_email = verifier_env(email_requis=True)
    if manquantes_email:
        print(
            "Attention : envoi email du récap désactivé, variables manquantes : "
            + ", ".join(manquantes_email),
            file=sys.stderr,
        )
    config = charger_config()

    # Import tardif : tkinter n'est requis que pour lancer réellement le popup.
    from .app import PopupTradingPop

    PopupTradingPop(config).lancer()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
