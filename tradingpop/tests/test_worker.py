import queue
import unittest
from datetime import datetime, timedelta
from unittest import mock

from tradingpop.config import Config
from tradingpop.memory import Memoire
from tradingpop.worker import Worker

BOUGIES = [
    {"datetime": f"2026-07-06 {h:02d}:00", "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0 + h * 0.001}
    for h in range(24)
]

ANALYSE = {
    "situation": "Range étroit.",
    "action": "attendre",
    "suggestion": "Attendre une cassure confirmée.",
    "confiance": 40,
    "justification": "Pas de signal clair.",
}


class TestWorker(unittest.TestCase):
    def setUp(self):
        self.config = Config(watchlist=["EUR/USD"], news_every_n_cycles=1)
        self.memoire = Memoire(":memory:")
        self.file = queue.Queue()
        self.worker = Worker(self.config, self.memoire, self.file)

    def tearDown(self):
        self.memoire.fermer()

    def _messages(self):
        messages = []
        while not self.file.empty():
            messages.append(self.file.get_nowait())
        return messages

    def test_cycle_complet_enregistre_et_emet(self):
        with mock.patch(
            "tradingpop.worker.market_data.recuperer_bougies", return_value=BOUGIES
        ), mock.patch(
            "tradingpop.worker.news.rechercher_actualites", return_value="BCE : statu quo."
        ), mock.patch(
            "tradingpop.worker.ai.analyser", return_value=ANALYSE
        ) as analyser:
            self.worker._analyser_instrument("EUR/USD")

        # L'actualité et l'historique (None au premier cycle) sont transmis à l'IA.
        _, args, _ = analyser.mock_calls[0]
        self.assertEqual(args[1], "EUR/USD")
        self.assertEqual(args[4], "BCE : statu quo.")
        self.assertIsNone(args[5])

        # La suggestion est en mémoire avec ses échéances d'évaluation.
        self.assertEqual(len(self.memoire.suggestions_du_jour(datetime.now().strftime("%Y-%m-%d"))), 1)
        dues = self.memoire.evaluations_dues(datetime.now() + timedelta(hours=25))
        self.assertEqual({d["horizon_heures"] for d in dues}, {1, 24})

        # L'UI reçoit un message d'analyse.
        types = [m["type"] for m in self._messages()]
        self.assertIn("analyse", types)

    def test_erreur_reseau_n_arrete_pas_la_boucle(self):
        with mock.patch(
            "tradingpop.worker.market_data.recuperer_bougies",
            side_effect=RuntimeError("API down"),
        ):
            self.worker._analyser_instrument("EUR/USD")
        types = [m["type"] for m in self._messages()]
        self.assertIn("erreur", types)

    def test_evaluation_des_suggestions_dues(self):
        t0 = datetime.now() - timedelta(hours=2)
        self.memoire.enregistrer_suggestion("EUR/USD", 1.0, {}, ANALYSE, [1], quand=t0)
        with mock.patch(
            "tradingpop.worker.market_data.recuperer_prix", return_value=1.05
        ):
            self.worker._evaluer_suggestions_passees()
        resume = self.memoire.resume_historique("EUR/USD")
        self.assertIn("+5.00 %", resume)


if __name__ == "__main__":
    unittest.main()
