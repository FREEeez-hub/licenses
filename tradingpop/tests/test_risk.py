import unittest

from tradingpop.risk import calculer_position


class TestCalculerPosition(unittest.TestCase):
    def test_calcul_standard(self):
        resultat = calculer_position(
            prix_actuel=100.0,
            niveau_invalidation=98.0,
            capital_reference=10000.0,
            risque_max_pct_par_trade=1.0,
        )
        self.assertEqual(resultat["distance_stop"], 2.0)
        self.assertEqual(resultat["risque_montant"], 100.0)  # 1 % de 10 000
        self.assertEqual(resultat["taille_position"], 50.0)  # 100 / 2
        self.assertAlmostEqual(resultat["distance_stop_pct"], 2.0)

    def test_aucun_niveau_invalidation(self):
        self.assertIsNone(
            calculer_position(100.0, None, 10000.0, 1.0)
        )

    def test_prix_egal_au_niveau(self):
        self.assertIsNone(
            calculer_position(100.0, 100.0, 10000.0, 1.0)
        )

    def test_risque_proportionnel_au_pourcentage(self):
        resultat_1pct = calculer_position(100.0, 90.0, 10000.0, 1.0)
        resultat_2pct = calculer_position(100.0, 90.0, 10000.0, 2.0)
        self.assertEqual(resultat_2pct["risque_montant"], resultat_1pct["risque_montant"] * 2)
        self.assertEqual(resultat_2pct["taille_position"], resultat_1pct["taille_position"] * 2)


if __name__ == "__main__":
    unittest.main()
