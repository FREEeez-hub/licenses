import unittest

from tradingpop.patterns import detecter_patterns_bougies


def _b(dt, o, h, l, c):
    return {"datetime": dt, "open": o, "high": h, "low": l, "close": c}


class TestPatternsBougies(unittest.TestCase):
    def test_liste_vide(self):
        self.assertEqual(detecter_patterns_bougies([]), [])

    def test_doji(self):
        # Corps quasi nul par rapport à l'amplitude totale.
        bougies = [_b("t0", 100.0, 101.0, 99.0, 100.02)]
        resultats = detecter_patterns_bougies(bougies)
        self.assertEqual(resultats[0]["nom"], "Doji")

    def test_marteau(self):
        # Corps en haut de la bougie, longue mèche basse, pas de mèche haute.
        bougies = [_b("t0", 100.0, 100.5, 97.0, 100.5)]
        resultats = detecter_patterns_bougies(bougies)
        self.assertEqual(resultats[0]["nom"], "Marteau")

    def test_etoile_filante(self):
        # Corps en bas de la bougie, longue mèche haute, pas de mèche basse.
        bougies = [_b("t0", 100.0, 103.0, 99.5, 99.5)]
        resultats = detecter_patterns_bougies(bougies)
        self.assertEqual(resultats[0]["nom"], "Étoile filante")

    def test_avalement_haussier(self):
        bougies = [
            _b("t0", 101.0, 101.2, 99.5, 99.8),  # baissière
            _b("t1", 99.5, 102.0, 99.3, 101.8),  # haussière, englobe la précédente
        ]
        resultats = detecter_patterns_bougies(bougies)
        self.assertTrue(any(r["nom"] == "Avalement haussier" for r in resultats))

    def test_avalement_baissier(self):
        bougies = [
            _b("t0", 99.5, 101.2, 99.3, 101.0),  # haussière
            _b("t1", 101.8, 102.0, 98.5, 99.0),  # baissière, englobe la précédente
        ]
        resultats = detecter_patterns_bougies(bougies)
        self.assertTrue(any(r["nom"] == "Avalement baissier" for r in resultats))

    def test_bougie_neutre_sans_figure(self):
        # Corps et mèches équilibrés : aucune figure classique ne doit matcher.
        bougies = [_b("t0", 100.0, 100.6, 99.4, 100.5)]
        resultats = detecter_patterns_bougies(bougies)
        self.assertEqual(resultats, [])


if __name__ == "__main__":
    unittest.main()
