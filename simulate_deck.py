#!/usr/bin/env python3
"""
Shuffle a deck thousands of times and measure how often it finds the cards it
needs by a given turn.

Usage:
    python3 simulate_deck.py decks/my-deck.json
    python3 simulate_deck.py decks/my-deck.json --games 20000 --seed 1
    python3 simulate_deck.py decks/my-deck.json --extra-per-turn 1

What it models (keep this in mind when reading the results):
  - Draw 7. If there's no Basic Pokémon, shuffle and redraw (a mulligan).
  - Set aside 6 Prize cards.
  - Draw 1 card at the start of each turn (both players draw on turn 1).
  - "By turn N" means the opening hand plus N draws, so turn 0 = opening hand.
  - It does NOT play search or draw cards. Count those as "outs" in a check
    instead (a card that searches for a Pokémon is a way to find that Pokémon).
    --extra-per-turn N adds N extra cards seen per turn, a rough stand-in for
    draw Abilities. The results are an approximation for comparing versions
    of a deck, not exact odds.

Checks live in the deck file under "consistency_checks":

  "consistency_checks": [
    {
      "name": "Main Basic on turn 1",
      "by_turn": 1,
      "target": 0.85,
      "need": [
        {"any_of": ["Basic A", "Search Card B", "Search Card C"]}
      ]
    },
    {
      "name": "Basic and Stage 1 by turn 2",
      "by_turn": 2,
      "target": 0.70,
      "need": [
        {"any_of": ["Basic A", "Search Card B"]},
        {"any_of": ["Stage 1 A", "Search Card C"], "at_least": 1}
      ]
    }
  ]

Every item in "need" must be met in the same game, each by different cards:
one search card can't count for two items at once. "at_least" asks for that
many different cards from the list (default 1).

Special names you can use in "any_of":
  @basic          any Basic Pokémon
  @pokemon        any Pokémon
  @energy         any Energy card
  @energy:Fire    Basic Fire Energy (works for any type)
  @supporter  @item  @stadium  @tool   Trainer cards of that kind

Always reported:
  - mulligan rate (opening hands with no Basic Pokémon)
  - for cards with 1 or 2 copies, how often every copy is in the Prizes

Exit code: 0 when every check meets its target, 1 when any check is below
target or a check names a card that isn't in the deck, 2 for bad input.
Python 3.8+, no extra packages.
"""

import argparse
import json
import os
import random
import sys
import unicodedata
from collections import Counter, defaultdict

DEFAULT_CARD_FILES = ["data/pokemon_standard/cards_full.json", "data/cards_full.json", "data/cards_unique.json"]
HAND, PRIZES = 7, 6


def norm(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("’", "'").replace("‘", "'")
    return " ".join(text.casefold().split())


def load_cards(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("cards") or data.get("data") or list(data.values())
    by_id, by_name = {}, defaultdict(list)
    for card in data:
        if isinstance(card, dict) and card.get("name"):
            if card.get("id"):
                by_id[norm(card["id"])] = card
            by_name[norm(card["name"])].append(card)
    return by_id, by_name


def tags_for(card):
    tags = set()
    cat = norm(card.get("category"))
    if cat == "pokemon":
        tags.add("@pokemon")
        if norm(card.get("stage")).replace(" ", "") == "basic":
            tags.add("@basic")
    elif cat == "trainer":
        kind = norm(card.get("trainerType"))
        for t in ("supporter", "item", "stadium", "tool"):
            if t in kind:
                tags.add("@" + t)
    elif cat == "energy":
        tags.add("@energy")
        if norm(card.get("energyType")) in ("normal", "basic"):
            kind = norm(card["name"]).replace(" energy", "")
            tags.add("@energy:" + kind)
    return tags


def build_deck(entries, by_id, by_name):
    """Return (list of card keys, display names, tags per key)."""
    deck, display, tags = [], {}, defaultdict(set)
    for e in entries:
        if not isinstance(e, dict):
            raise ValueError(f"bad card entry: {e!r}")
        card = by_id.get(norm(e.get("id"))) if e.get("id") else None
        if card is None:
            versions = by_name.get(norm(e.get("name")))
            card = versions[0] if versions else None
        if card is None:
            raise ValueError(f"\"{e.get('name') or e.get('id')}\" is not in the card data "
                             "(run check_deck.py first)")
        count = e.get("count")
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise ValueError(f"bad count for {card['name']}: {count!r}")
        key = norm(card["name"])
        display[key] = card["name"]
        tags[key] |= tags_for(card)
        deck += [key] * count
    return deck, display, tags


def resolve(item, keys, tags):
    item_n = norm(item)
    if item_n.startswith("@"):
        return {k for k in keys if item_n in tags[k]}
    return {k for k in keys if k == item_n}


def can_meet(slots, seen):
    """Can every slot be filled by a different seen card? (bipartite matching)"""
    owner = [-1] * len(seen)

    def assign(s, visited):
        for p, card in enumerate(seen):
            if card in slots[s] and p not in visited:
                visited.add(p)
                if owner[p] == -1 or assign(owner[p], visited):
                    owner[p] = s
                    return True
        return False

    return all(assign(s, set()) for s in range(len(slots)))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", help="deck JSON file")
    ap.add_argument("--cards", help="card data file (default: data/cards_full.json)")
    ap.add_argument("--games", type=int, default=10000, help="number of games (default 10000)")
    ap.add_argument("--extra-per-turn", type=int, default=0,
                    help="extra cards seen per turn from draw effects (default 0)")
    ap.add_argument("--seed", type=int, help="random seed, for repeatable results")
    a = ap.parse_args()

    cards_path = a.cards or next((p for p in DEFAULT_CARD_FILES if os.path.exists(p)), None)
    if not cards_path or not os.path.exists(cards_path):
        print("Card data not found. Put cards_full.json in data/ or pass --cards.")
        sys.exit(2)
    try:
        by_id, by_name = load_cards(cards_path)
        with open(a.deck, encoding="utf-8") as f:
            deck_file = json.load(f)
        entries = deck_file.get("cards") if isinstance(deck_file, dict) else deck_file
        deck, display, tags = build_deck(entries or [], by_id, by_name)
    except (OSError, ValueError) as e:
        print(f"Could not read input: {e}")
        sys.exit(2)

    checks = deck_file.get("consistency_checks", []) if isinstance(deck_file, dict) else []
    keys = set(deck)
    counts = Counter(deck)
    if not any("@basic" in tags[k] for k in keys):
        print("The deck has no Basic Pokémon, so every hand is a mulligan.")
        sys.exit(2)

    # Resolve checks once.
    problems, prepared = [], []
    for i, c in enumerate(checks, 1):
        name = c.get("name") or f"check {i}"
        slots = []
        for req in c.get("need") or []:
            pool = set()
            for item in req.get("any_of") or []:
                found = resolve(item, keys, tags)
                if not found:
                    problems.append(f"{name}: \"{item}\" matches nothing in the deck")
                pool |= found
            slots += [pool] * max(1, int(req.get("at_least", 1)))
        if not slots:
            problems.append(f"{name}: has no \"need\" list")
            continue
        relevant = set().union(*slots)
        prepared.append({"name": name, "turn": int(c.get("by_turn", 1)),
                         "target": c.get("target"), "slots": slots,
                         "relevant": relevant, "hits": 0})

    rng = random.Random(a.seed)
    is_basic = {k: "@basic" in tags[k] for k in keys}
    low_copies = [k for k in keys if counts[k] <= 2]
    prized_all = Counter()
    mulligan_games = 0
    max_turn = max([p["turn"] for p in prepared] + [0])
    per_turn = 1 + max(0, a.extra_per_turn)
    cards = list(deck)

    for _ in range(a.games):
        mulligans = 0
        while True:
            rng.shuffle(cards)
            if any(is_basic[c] for c in cards[:HAND]):
                break
            mulligans += 1
        if mulligans:
            mulligan_games += 1
        prizes = Counter(cards[HAND:HAND + PRIZES])
        for k in low_copies:
            if prizes[k] == counts[k]:
                prized_all[k] += 1
        start = HAND + PRIZES
        for p in prepared:
            seen = cards[:HAND] + cards[start:start + p["turn"] * per_turn]
            seen = [c for c in seen if c in p["relevant"]]
            if len(seen) >= len(p["slots"]) and can_meet(p["slots"], seen):
                p["hits"] += 1

    # Report
    title = deck_file.get("deck_name") if isinstance(deck_file, dict) else None
    print(f"{title or os.path.basename(a.deck)}: {a.games:,} games, opening hand + "
          f"{per_turn} card(s) seen per turn")
    print(f"\nMulligan rate (no Basic in opening hand): {mulligan_games / a.games:.1%}")

    if low_copies:
        print("\nChance every copy is in the Prizes:")
        for k in sorted(low_copies, key=lambda k: (counts[k], display[k])):
            print(f"  {counts[k]}x {display[k]}: {prized_all[k] / a.games:.1%}")

    failed = bool(problems)
    if prepared:
        print("\nChecks (by turn N = opening hand + N turns of draws):")
        for p in prepared:
            rate = p["hits"] / a.games
            target = p["target"]
            if isinstance(target, (int, float)):
                ok = rate >= target
                failed |= not ok
                verdict = f"target {target:.0%}  {'OK' if ok else 'BELOW TARGET'}"
            else:
                verdict = "no target"
            print(f"  {rate:6.1%}  turn {p['turn']}  {p['name']}  ({verdict})")
    else:
        print("\nNo \"consistency_checks\" in the deck file. Add some to test the deck's setup.")

    for msg in problems:
        print(f"  PROBLEM  {msg}")
    print("\nFAIL" if failed else "\nPASS")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
