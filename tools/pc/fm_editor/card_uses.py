"""What the mod does with a card: every rule, pool, deck and pack naming it.

No window of either kind here (`card_links.py` is the Tk one's menus and its
Where it's used window; `qt/cards.py` has the modern one's), so the list is
read the same way whichever window asks for it."""
from __future__ import annotations

from . import fixed_decks, packs as packmath, starter_pools, validate
from .gamedata import DUELIST_NAMES, POOL_LABELS, POOL_TOTAL, POOLS, TYPE_EQUIP
from .model import fusion_pairs


def plural(n: int, one: str, many: str = None) -> str:
    return f"{n} {one if n == 1 else many or one + 's'}"


def where_used(project, cid) -> list:
    """[(where, what, target)] of everything in the mod naming the card, with
    `target` naming the place rather than how to go there: a frontend turns
    one into the move its own pages take (open_target below for the Tk
    window). A target of None is a place neither window edits."""
    p = project
    lines = []

    def add(where, what, target):
        lines.append((where, what, target))

    for other, added in sorted(p.added.items()):
        if added.base == cid and other != cid:
            add("Cards", f"Copy of it: {p.card_label(other)}", ("card", other))
    # What the game plays for each pair, as the Fusions tab shows it.
    own, pairs = fusion_pairs(p)
    material = made = 0
    for pair in pairs:
        result = own.get(pair)
        result = result if result is not None else p.fusions.get(pair)
        if result:
            material += cid in pair
            made += result == cid
    if material or made:
        add("Fusions", f"Material in {plural(material, 'fusion')}; made by {plural(made, 'fusion')}",
            ("fusions", cid))
    if p.cards[cid].type == TYPE_EQUIP:
        add("Equips", f"Equips {plural(len(p.equip_targets(cid)), 'monster')}", ("equips", cid))
    else:
        for equip in p.equip_cards():
            if equip in p.cards and cid in p.equip_targets(equip):
                add("Equips", f"Equipped by {p.card_label(equip)}", ("equips", equip))
    for ritual in sorted(set(p.ritual_cards()) | set(p.rituals)):
        if ritual not in p.cards:
            continue
        recipe = list(p.rituals.get(ritual) or ())
        tributes = recipe[:3] + [req.get("card") for req in p.ritual_requirements.get(ritual, [])]
        target = ("rituals", ritual)
        if ritual == cid:
            add("Rituals", "Its ritual", target)
        if cid in tributes:
            add("Rituals", f"Tribute for {p.card_label(ritual)}", target)
        if len(recipe) > 3 and recipe[3] == cid:
            add("Rituals", f"Summoned by {p.card_label(ritual)}", target)
    for d, pools in enumerate(p.pools):
        name = DUELIST_NAMES[d] if d < len(DUELIST_NAMES) else str(d)
        if name == "Unused":    # duelist 0: no duel deals or drops its pools
            continue
        deck = fixed_decks.deck_of(p, d)
        for pool in POOLS:
            if pool == "deck" and deck is not None:
                copies = deck.cards.get(cid, 0)
                if copies:
                    add("Duelists", f"{name}: fixed deck, {plural(copies, 'copy', 'copies')}",
                        ("pool", d, "deck", cid))
                continue
            weight = pools[pool].get(cid, 0)
            if weight:
                add("Duelists", f"{name}: {POOL_LABELS[pool]}, {weight * 100 / POOL_TOTAL:.2f}%",
                    ("pool", d, pool, cid))
    for i, deck in enumerate(p.starter):
        copies = deck.cards.get(cid, 0)
        if copies:
            add("Starter decks", f"{deck.name or '(unnamed)'}: {plural(copies, 'copy', 'copies')}",
                ("starter", i, cid))
    resolve = validate.pack_resolver(p)
    for i, entry in enumerate(p.packs):
        if not isinstance(entry, dict):
            continue
        for tier, pool in packmath.tiers_of(entry):
            if any(resolve(ref) == cid for ref, _ in packmath.pool_items(pool.get("cards", []))):
                name = entry.get("name", packmath.pack_id(entry))
                add("Packs", name + (f" (tier {tier})" if tier != "cards" else ""), ("pack", i))
        unlock = entry.get("unlock")
        if isinstance(unlock, dict) and "card" in unlock and resolve(unlock["card"]) == cid:
            add("Packs", entry.get("name", packmath.pack_id(entry)) + ": unlocked by owning it", ("pack", i))
    # No Tk tab edits "starter_pools" (kept as written in mod.json): listed,
    # no link there; the Qt window has a page for them.
    for i, pool in enumerate(starter_pools.state(p)):
        weight = pool.cards.get(cid, 0)
        if weight:
            add("Starter pools", f"{pool.name or f'pool {i + 1}'}: weight {weight} (mod.json only)", None)
    return lines
