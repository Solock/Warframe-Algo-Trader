"""
Tests offline de importVaultInventory (aucun appel réseau, aucune écriture DB).
Lancer depuis la racine du repo : .venv/bin/python -m unittest discover tests -v
"""
import os
import tempfile
import unittest

import importVaultInventory as imp


NOTE_SAMPLE = """\
# Inventaire

| Item | Qté | Statut | Ducats | WTS | WTB |
|---|---|---|---|---|---|
| Braton Prime Barrel | 1 | Unvaulted | 15 | 2 | 2 |
| Sicarus Prime Barrel | 3 | Vaulted | 15 | 11 | - |

## Rivens (tableau 4 colonnes, doit être ignoré)

| Arme | Nom riven | MR | Stats |
|---|---|---|---|
| Balla | Ignitis | 15 | +7.4% Critical Damage |
"""


class TestParseVaultTable(unittest.TestCase):
    def _parse(self, content):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            path = f.name
        try:
            return imp.parseVaultTable(path)
        finally:
            os.unlink(path)

    def test_pieces_extraites_rivens_ignores(self):
        self.assertEqual(
            self._parse(NOTE_SAMPLE),
            [("Braton Prime Barrel", 1), ("Sicarus Prime Barrel", 3)],
        )

    def test_quantite_illisible_leve(self):
        casse = NOTE_SAMPLE.replace("| Braton Prime Barrel | 1 |", "| Braton Prime Barrel | ? |")
        with self.assertRaises(ValueError):
            self._parse(casse)


class TestResolveSlug(unittest.TestCase):
    NAME_TO_SLUG = {
        "Braton Prime Barrel": "braton_prime_barrel",
        # côté jeu : « Parallax Avionics », côté WFM : « ... Blueprint »
        "Parallax Avionics Blueprint": "parallax_avionics_blueprint",
        # côté jeu : « Atlas Prime Chassis Blueprint », côté WFM parfois sans suffixe
        "Mag Prime Chassis": "mag_prime_chassis",
    }

    def test_exact(self):
        self.assertEqual(
            imp.resolveSlug("Braton Prime Barrel", self.NAME_TO_SLUG),
            "braton_prime_barrel",
        )

    def test_fallback_ajout_blueprint(self):
        self.assertEqual(
            imp.resolveSlug("Parallax Avionics", self.NAME_TO_SLUG),
            "parallax_avionics_blueprint",
        )

    def test_fallback_retrait_blueprint(self):
        self.assertEqual(
            imp.resolveSlug("Mag Prime Chassis Blueprint", self.NAME_TO_SLUG),
            "mag_prime_chassis",
        )

    def test_inconnu_rend_none(self):
        self.assertIsNone(imp.resolveSlug("Item Fantôme", self.NAME_TO_SLUG))


if __name__ == "__main__":
    unittest.main()
