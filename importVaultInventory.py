"""Importe l'inventaire depuis la note vault WAT-Inventaire-Warframe.md vers inventory.db.

La note vault est la source de vérité (mise à jour incrémentale par capture d'écran,
voir la procédure dans la note). Ce script la resynchronise vers la table `inventory` :
upsert par slug — met à jour la quantité si l'item existe, l'insère sinon.
Les items du tableau absents de la base sont ajoutés avec purchasePrice=0 (farm, pas achat).

Usage :
    python importVaultInventory.py [--dry-run] [chemin/vers/la/note.md]
"""

import re
import sqlite3
import sys

import AccessingWFMarket as wfm

DEFAULT_NOTE = "/data/obsidian-vault/01 - Pro/Projets/WAT-Inventaire-Warframe.md"


def parseVaultTable(path):
    """Extrait (nom affiché, quantité) du tableau pièces (6 colonnes).

    Le tableau rivens (4 colonnes) est ignoré : WAT ne trade pas les rivens.
    """
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) != 6:
                continue
            name, qty = cells[0], cells[1]
            if name in ("Item", "") or set(name) <= {"-"}:
                continue
            if not re.fullmatch(r"\d+", qty):
                raise ValueError(f"Quantité illisible pour {name!r} : {qty!r}")
            items.append((name, int(qty)))
    return items


def resolveSlug(name, nameToSlug):
    """Nom affiché -> slug WFM. Les parts de warframe s'appellent 'X Blueprint'
    en jeu mais 'X' sur warframe.market (et inversement pour certains items)."""
    if name in nameToSlug:
        return nameToSlug[name]
    if name.endswith(" Blueprint") and name[: -len(" Blueprint")] in nameToSlug:
        return nameToSlug[name[: -len(" Blueprint")]]
    if f"{name} Blueprint" in nameToSlug:
        return nameToSlug[f"{name} Blueprint"]
    return None


def main():
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dryRun = "--dry-run" in sys.argv[1:]
    notePath = args[0] if args else DEFAULT_NOTE

    items = parseVaultTable(notePath)
    nameToSlug = wfm.getNameToSlug()

    resolved, unmatched = [], []
    for name, qty in items:
        slug = resolveSlug(name, nameToSlug)
        (resolved if slug else unmatched).append((name, slug, qty))

    for name, slug, qty in resolved:
        print(f"  {name}  ->  {slug}  x{qty}")
    if unmatched:
        print(f"\n{len(unmatched)} item(s) SANS slug WFM (rien n'est écrit tant que ça n'est pas résolu) :")
        for name, _, qty in unmatched:
            print(f"  ?? {name} x{qty}")
        sys.exit(1)

    print(f"\n{len(resolved)} items mappés, {sum(q for _, _, q in resolved)} unités au total.")
    if dryRun:
        print("--dry-run : base non modifiée.")
        return

    con = sqlite3.connect("inventory.db")
    cur = con.cursor()
    inserted = updated = 0
    for _, slug, qty in resolved:
        exists = cur.execute("SELECT COUNT(*) FROM inventory WHERE name=?", (slug,)).fetchone()[0]
        if exists:
            cur.execute("UPDATE inventory SET number=? WHERE name=?", (qty, slug))
            updated += 1
        else:
            cur.execute(
                "INSERT INTO inventory (name, purchasePrice, number) VALUES (?, 0, ?)",
                (slug, qty),
            )
            inserted += 1
    con.commit()
    con.close()
    print(f"inventory.db : {inserted} insérés, {updated} mis à jour.")


if __name__ == "__main__":
    main()
