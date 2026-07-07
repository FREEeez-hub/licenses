import unittest
from datetime import date, datetime
from unittest import mock

from tradingpop.memory import Memoire
from tradingpop.recap import AVERTISSEMENT, construire_recap, recap_du_matin

ANALYSE = {
    "situation": "Divergence baissière RSI/prix.",
    "action": "prudence",
    "suggestion": "Prudence, volatilité anormale sur la paire.",
    "confiance": 60,
    "justification": "Actualité BCE imminente.",
}


class TestRecap(unittest.TestCase):
    def setUp(self):
        self.memoire = Memoire(":memory:")

    def tearDown(self):
        self.memoire.fermer()

    def test_recap_vide(self):
        recap = construire_recap(self.memoire, "2026-07-06")
        self.assertIn("Aucune suggestion enregistrée", recap)
        self.assertIn(AVERTISSEMENT, recap)

    def test_recap_avec_suggestions_et_resultats(self):
        t0 = datetime(2026, 7, 6, 9, 30, 0)
        sid = self.memoire.enregistrer_suggestion(
            "EUR/USD", 1.0000, {}, ANALYSE, [1], quand=t0
        )
        self.memoire.enregistrer_resultat(sid, 1, 0.9950)
        recap = construire_recap(self.memoire, "2026-07-06")
        self.assertIn("EUR/USD", recap)
        self.assertIn("Prudence", recap)
        self.assertIn("-0.50 %", recap)
        self.assertIn("09:30", recap)

    def test_recap_du_matin_une_seule_fois_par_jour(self):
        aujourdhui = date(2026, 7, 7)
        with mock.patch("tradingpop.recap.envoyer_email_recap") as envoi:
            premier = recap_du_matin(self.memoire, aujourdhui)
            self.assertIsNotNone(premier)
            self.assertIn("2026-07-06", premier)
            envoi.assert_called_once()
            # Deuxième appel le même jour : rien.
            self.assertIsNone(recap_du_matin(self.memoire, aujourdhui))
        # Le lendemain, le récap repart.
        with mock.patch("tradingpop.recap.envoyer_email_recap"):
            self.assertIsNotNone(recap_du_matin(self.memoire, date(2026, 7, 8)))

    def test_echec_email_n_empeche_pas_affichage(self):
        with mock.patch(
            "tradingpop.recap.envoyer_email_recap", side_effect=RuntimeError("brevo down")
        ):
            recap = recap_du_matin(self.memoire, date(2026, 7, 7))
        self.assertIsNotNone(recap)
        self.assertIn("Envoi email échoué", recap)


if __name__ == "__main__":
    unittest.main()
