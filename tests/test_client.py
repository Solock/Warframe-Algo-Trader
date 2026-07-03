"""
Tests offline du client AccessingWFMarket (aucun appel réseau).
Lancer depuis la racine du repo : .venv/bin/python -m unittest discover tests -v
"""
import math
import unittest

import AccessingWFMarket as wfm


class TestNormalisation(unittest.TestCase):
    def test_toBool(self):
        self.assertIs(wfm._toBool(True), True)
        self.assertIs(wfm._toBool(False), False)
        # héritage v1 : les call sites passaient str(True)/str(False)
        self.assertIs(wfm._toBool("True"), True)
        self.assertIs(wfm._toBool("False"), False)
        self.assertIs(wfm._toBool("true"), True)
        self.assertIs(wfm._toBool("false"), False)
        self.assertIs(wfm._toBool(1), True)
        self.assertIs(wfm._toBool(0), False)

    def test_toRank(self):
        self.assertIsNone(wfm._toRank(None))
        self.assertIsNone(wfm._toRank(float("nan")))
        self.assertEqual(wfm._toRank(5.0), 5)
        # régression : rank 0 est un rang valide, il ne doit PAS être omis
        # (la v2 exige rank pour tout item à rangs)
        self.assertEqual(wfm._toRank(0), 0)
        self.assertEqual(wfm._toRank(0.0), 0)


class TestCompactOrderToLegacy(unittest.TestCase):
    def test_mapping(self):
        v2Order = {
            "id": "abc123",
            "type": "sell",
            "platinum": 42,
            "quantity": 3,
            "visible": True,
            "rank": 10,
            "itemId": "54c6855ee779891362942572",
        }
        legacy = wfm._compactOrderToLegacy(
            v2Order, {"54c6855ee779891362942572": "primed_continuity"}
        )
        self.assertEqual(legacy["id"], "abc123")
        self.assertEqual(legacy["platinum"], 42)
        self.assertEqual(legacy["quantity"], 3)
        self.assertIs(legacy["visible"], True)
        self.assertEqual(legacy["mod_rank"], 10)
        self.assertEqual(legacy["item"]["url_name"], "primed_continuity")
        self.assertEqual(legacy["item"]["id"], "54c6855ee779891362942572")

    def test_mapping_sans_rank(self):
        v2Order = {
            "id": "x",
            "type": "buy",
            "platinum": 1,
            "quantity": 1,
            "visible": False,
            "itemId": "inconnu",
        }
        legacy = wfm._compactOrderToLegacy(v2Order, {})
        self.assertIsNone(legacy["mod_rank"])
        # slug inconnu : on retombe sur l'itemId plutôt que de crasher
        self.assertEqual(legacy["item"]["url_name"], "inconnu")


class TestDryRun(unittest.TestCase):
    """En dry-run, aucune écriture ne doit partir sur le réseau."""

    def setUp(self):
        self._orig = wfm.isDryRun
        wfm.isDryRun = lambda: True
        # si un appel réseau part quand même, il explose immédiatement
        self._origRequest = wfm.warframeApi.request
        def _forbidden(*args, **kwargs):
            raise AssertionError("appel réseau parti en mode dry-run !")
        wfm.warframeApi.request = _forbidden

    def tearDown(self):
        wfm.isDryRun = self._orig
        wfm.warframeApi.request = self._origRequest

    def test_postOrder(self):
        r = wfm.postOrder("54aae292e7798909064f1575", "buy", 5, 1, "False", 0, "secura_dual_cestra")
        self.assertEqual(r.status_code, 200)
        order = r.json()["data"]
        self.assertTrue(order["id"].startswith("dryrun-"))
        self.assertEqual(order["platinum"], 5)
        self.assertEqual(order["rank"], 0)
        self.assertIs(order["visible"], False)

    def test_updateListing(self):
        self.assertTrue(wfm.updateListing("id1", 10, 1, "True", "item", "sell"))

    def test_deleteOrder(self):
        self.assertEqual(wfm.deleteOrder("id1").status_code, 200)

    def test_closeOrder(self):
        self.assertEqual(wfm.closeOrder("id1", 1).status_code, 200)


if __name__ == "__main__":
    unittest.main()
