import unittest
from datetime import datetime, timedelta

from tradingpop.memory import Memoire

ANALYSE = {
    "situation": "Cassure du range haussier avec volume.",
    "action": "opportunite_achat",
    "suggestion": "Opportunité d'achat possible au-dessus de 1.0850.",
    "confiance": 70,
    "justification": "RSI en zone neutre, MACD croise à la hausse.",
}


class TestMemoire(unittest.TestCase):
    def setUp(self):
        self.memoire = Memoire(":memory:")

    def tearDown(self):
        self.memoire.fermer()

    def test_enregistrement_et_evaluation(self):
        t0 = datetime(2026, 7, 6, 10, 0, 0)
        sid = self.memoire.enregistrer_suggestion(
            "EUR/USD", 1.0850, {"indicateurs": {}}, ANALYSE, [1, 24], quand=t0
        )
        # Avant l'échéance : rien à évaluer.
        self.assertEqual(self.memoire.evaluations_dues(t0), [])
        # Après 1h : l'horizon 1h est dû, pas le 24h.
        dues = self.memoire.evaluations_dues(t0 + timedelta(hours=2))
        self.assertEqual(len(dues), 1)
        self.assertEqual(dues[0]["horizon_heures"], 1)

        self.memoire.enregistrer_resultat(sid, 1, 1.0900, quand=t0 + timedelta(hours=2))
        self.assertEqual(self.memoire.evaluations_dues(t0 + timedelta(hours=2)), [])

    def test_resume_historique_reinjecte_les_resultats(self):
        t0 = datetime(2026, 7, 6, 10, 0, 0)
        sid = self.memoire.enregistrer_suggestion(
            "EUR/USD", 1.0000, {}, ANALYSE, [1], quand=t0
        )
        self.assertIsNone(self.memoire.resume_historique("EUR/USD"))
        self.memoire.enregistrer_resultat(sid, 1, 1.0200)
        resume = self.memoire.resume_historique("EUR/USD")
        self.assertIn("opportunite_achat", resume)
        self.assertIn("+2.00 %", resume)
        # L'historique est propre à l'instrument.
        self.assertIsNone(self.memoire.resume_historique("AAPL"))

    def test_suggestions_du_jour(self):
        t0 = datetime(2026, 7, 6, 10, 0, 0)
        self.memoire.enregistrer_suggestion("AAPL", 210.0, {}, ANALYSE, [1], quand=t0)
        self.assertEqual(len(self.memoire.suggestions_du_jour("2026-07-06")), 1)
        self.assertEqual(self.memoire.suggestions_du_jour("2026-07-05"), [])

    def test_action_invalide_refusee(self):
        mauvaise = {**ANALYSE, "action": "acheter_tout"}
        with self.assertRaises(ValueError):
            self.memoire.enregistrer_suggestion("AAPL", 210.0, {}, mauvaise, [1])

    def test_meta(self):
        self.assertIsNone(self.memoire.lire_meta("dernier_recap"))
        self.memoire.ecrire_meta("dernier_recap", "2026-07-07")
        self.assertEqual(self.memoire.lire_meta("dernier_recap"), "2026-07-07")
        self.memoire.ecrire_meta("dernier_recap", "2026-07-08")
        self.assertEqual(self.memoire.lire_meta("dernier_recap"), "2026-07-08")


if __name__ == "__main__":
    unittest.main()
