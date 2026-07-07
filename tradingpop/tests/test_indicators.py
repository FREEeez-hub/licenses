import math
import unittest

from tradingpop.indicators import calculer_indicateurs, ema, macd, rsi, sma


class TestIndicateurs(unittest.TestCase):
    def test_sma(self):
        self.assertEqual(sma([1, 2, 3, 4], 2), 3.5)
        self.assertIsNone(sma([1, 2], 5))

    def test_ema_converge_vers_constante(self):
        serie = [10.0] * 50
        self.assertAlmostEqual(ema(serie, 20), 10.0)

    def test_rsi_bornes(self):
        hausse = list(range(1, 40))
        self.assertAlmostEqual(rsi([float(x) for x in hausse]), 100.0)
        baisse = [float(x) for x in range(40, 1, -1)]
        self.assertLess(rsi(baisse), 1.0)
        self.assertIsNone(rsi([1.0, 2.0]))

    def test_rsi_valeur_connue(self):
        # Série alternée : le RSI doit rester strictement entre 0 et 100.
        prix = [10 + (0.5 if i % 2 else -0.3) * i for i in range(30)]
        valeur = rsi(prix)
        self.assertTrue(0 < valeur < 100)

    def test_macd_structure(self):
        prix = [100 + math.sin(i / 5) * 3 + i * 0.1 for i in range(80)]
        resultat = macd(prix)
        self.assertIsNotNone(resultat)
        self.assertAlmostEqual(
            resultat["histogramme"], resultat["macd"] - resultat["signal"]
        )
        self.assertIsNone(macd([1.0] * 10))

    def test_calculer_indicateurs_complet(self):
        prix = [100.0 + i * 0.2 for i in range(120)]
        indicateurs = calculer_indicateurs(prix)
        self.assertEqual(indicateurs["dernier_prix"], prix[-1])
        self.assertIsNotNone(indicateurs["sma_20"])
        self.assertIsNotNone(indicateurs["sma_50"])
        self.assertIsNotNone(indicateurs["rsi_14"])
        self.assertIsNotNone(indicateurs["macd"])
        self.assertAlmostEqual(
            indicateurs["variation_derniere_bougie_pct"],
            (prix[-1] - prix[-2]) / prix[-2] * 100,
        )

    def test_series_trop_courtes(self):
        indicateurs = calculer_indicateurs([1.0, 2.0])
        self.assertIsNone(indicateurs["sma_20"])
        self.assertIsNone(indicateurs["rsi_14"])
        self.assertIsNone(indicateurs["macd"])


if __name__ == "__main__":
    unittest.main()
