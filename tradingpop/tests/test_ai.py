import unittest

from tradingpop.ai import (
    _extraire_json,
    construire_prompt_analyse,
    normaliser_analyse,
)


class TestNormalisation(unittest.TestCase):
    def test_analyse_complete(self):
        brut = {
            "situation": " Cassure de range. ",
            "action": "OPPORTUNITE_ACHAT",
            "suggestion": "Opportunité d'achat possible.",
            "confiance": "72",
            "justification": "MACD haussier.",
        }
        analyse = normaliser_analyse(brut)
        self.assertEqual(analyse["action"], "opportunite_achat")
        self.assertEqual(analyse["confiance"], 72)
        self.assertEqual(analyse["situation"], "Cassure de range.")

    def test_action_inconnue_devient_attendre(self):
        analyse = normaliser_analyse({"action": "yolo", "confiance": 150})
        self.assertEqual(analyse["action"], "attendre")
        self.assertEqual(analyse["confiance"], 100)

    def test_confiance_illisible(self):
        analyse = normaliser_analyse({"confiance": "beaucoup"})
        self.assertEqual(analyse["confiance"], 0)


class TestExtractionJson(unittest.TestCase):
    def test_json_pur(self):
        self.assertEqual(_extraire_json('{"a": 1}'), {"a": 1})

    def test_json_entoure_de_markdown(self):
        texte = 'Voici :\n```json\n{"action": "attendre"}\n```\nVoilà.'
        self.assertEqual(_extraire_json(texte), {"action": "attendre"})


class TestPrompt(unittest.TestCase):
    def test_prompt_contient_tout(self):
        bougies = [
            {"datetime": "2026-07-06 10:00", "open": 1, "high": 2, "low": 0.5, "close": 1.5}
        ] * 30
        structure = {"tendance": "haussière", "evenement": "BOS haussier"}
        patterns = [{"nom": "Marteau", "datetime": "2026-07-06 10:00"}]
        prompt = construire_prompt_analyse(
            "EUR/USD",
            bougies,
            {"rsi_14": 55.2},
            structure,
            patterns,
            "BCE : statu quo.",
            "- hier : attendre",
        )
        self.assertIn("EUR/USD", prompt)
        self.assertIn("rsi_14", prompt)
        self.assertIn("BOS haussier", prompt)
        self.assertIn("Marteau", prompt)
        self.assertIn("BCE", prompt)
        self.assertIn("hier : attendre", prompt)
        # Seules les 20 dernières bougies partent dans le prompt.
        self.assertEqual(prompt.count('"datetime"'), 21)  # 20 bougies + 1 pattern

    def test_prompt_sans_rien(self):
        prompt = construire_prompt_analyse("AAPL", [], {}, None, None, None, None)
        self.assertIn("aucune actualité disponible", prompt)
        self.assertIn("aucun historique", prompt)
        self.assertIn("structure non calculable", prompt)
        self.assertIn("aucune figure de bougie détectée", prompt)


if __name__ == "__main__":
    unittest.main()
