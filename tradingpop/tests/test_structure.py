import unittest

from tradingpop.structure import detecter_structure, swings


def _bougie(dt, valeur):
    return {"datetime": dt, "open": valeur, "high": valeur + 0.1, "low": valeur - 0.1, "close": valeur}


# Deux jambes haussières (plus haut et plus bas de la 2e jambe > 1re jambe),
# suivies d'une bougie qui casse nettement au-dessus du dernier plus haut.
VALEURS_HAUSSE_AVEC_BOS = [
    100.0, 100.3, 100.6, 100.8, 101.0,  # 0-4 : monte vers le 1er plus haut (idx4)
    100.8, 100.5, 100.2, 99.8, 99.5,  # 5-9 : descend vers le 1er plus bas (idx9)
    99.8, 100.1, 100.4, 100.7, 102.0,  # 10-14 : monte vers le 2e plus haut, plus élevé (idx14)
    101.7, 101.4, 101.1, 100.7, 100.3,  # 15-19 : descend vers le 2e plus bas, plus élevé (idx19)
    100.5, 100.6,  # 20-21 : contexte nécessaire pour confirmer le pivot idx19
    105.0,  # 22 : cassure nette au-dessus du plus haut (102.0) -> BOS haussier
]


def _serie_haussiere_avec_bos():
    return [_bougie(f"t{i}", v) for i, v in enumerate(VALEURS_HAUSSE_AVEC_BOS)]


class TestSwings(unittest.TestCase):
    def test_pas_assez_de_bougies(self):
        self.assertEqual(swings([_bougie("t0", 100)], lookback=3), [])

    def test_detecte_des_pivots(self):
        points = swings(_serie_haussiere_avec_bos(), lookback=2)
        self.assertTrue(any(p["type"] == "haut" for p in points))
        self.assertTrue(any(p["type"] == "bas" for p in points))


class TestDetecterStructure(unittest.TestCase):
    def test_historique_insuffisant(self):
        bougies = [_bougie(f"t{i}", 100) for i in range(4)]
        resultat = detecter_structure(bougies, lookback=3)
        self.assertEqual(resultat["tendance"], "indéterminée")
        self.assertIsNone(resultat["evenement"])
        self.assertIsNone(resultat["niveau_invalidation"])

    def test_tendance_haussiere_et_bos_detectes(self):
        resultat = detecter_structure(_serie_haussiere_avec_bos(), lookback=2)
        self.assertEqual(resultat["tendance"], "haussière")
        self.assertIn("BOS haussier", resultat["evenement"])
        self.assertEqual(resultat["niveau_invalidation"], 100.2)  # low de la bougie idx19 (100.3 - 0.1)

    def test_choc_baissier_apres_tendance_haussiere(self):
        bougies = _serie_haussiere_avec_bos()
        # Remplace la bougie de cassure par une chute sous le dernier plus bas (100.3).
        bougies[-1] = _bougie("t_choch", 95.0)
        resultat = detecter_structure(bougies, lookback=2)
        self.assertEqual(resultat["tendance"], "haussière")
        self.assertIn("CHoCH baissier", resultat["evenement"])


if __name__ == "__main__":
    unittest.main()
