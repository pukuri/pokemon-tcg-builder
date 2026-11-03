#!/usr/bin/env python3
"""
Check a Pokémon TCG deck file against the Standard deck rules and the local
card data.

Usage:
    python3 check_deck.py decks/my-deck.json
    python3 check_deck.py decks/my-deck.json --cards data/cards_full.json
    python3 check_deck.py decks/my-deck.json --strict    # warnings also fail

Errors (the deck is illegal or unusable):
    - total is not exactly 60
    - a card is not in the eligible card data
    - more than 4 copies of one name (Basic Energy exempt)
    - no Basic Pokémon
    - more than 1 ACE SPEC
    - a malformed entry (missing name, bad count)
    - a missing write-up: a card without a "role", no "strategy", fewer than
      3 "synergies", not exactly 3 "rejected" cards, or no "main_resource"
      (skip with --rules-only)

Warnings (legal, but probably a mistake):
    - a name has several different versions and no "id" says which one
    - an evolution card whose previous stage is missing
    - an attacker whose attacks the deck's energy can't pay for
    - a card that is in no synergy group (unless its entry has "standalone": true)
    - a card_text entry whose "quoted" words are not in that card's text in data/
    - a main_resource card that is not in the deck

Exit code: 0 when the deck passes, 1 when it fails, 2 for bad input files.
Python 3.8+, no extra packages.
"""

import argparse
import difflib
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

DEFAULT_CARD_FILES = ["data/pokemon_standard/cards_full.json", "data/cards_full.json", "data/cards_unique.json"]


# ---------- helpers ----------

def norm(text):
    """Compare names loosely: ignore case, accents, curly quotes and extra spaces."""
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("’", "'").replace("‘", "'")
    return " ".join(text.casefold().split())


def stage_of(card):
    return norm(card.get("stage")).replace(" ", "")  # "basic", "stage1", "stage2", ...


def is_pokemon(card):
    return norm(card.get("category")) in ("pokemon", "pokémon")


def is_basic_pokemon(card):
    return is_pokemon(card) and stage_of(card) == "basic"


def is_basic_energy(card):
    return norm(card.get("category")) == "energy" and norm(card.get("energyType")) in ("normal", "basic")


def is_ace_spec(card):
    return "ace spec" in norm(card.get("rarity")) or "ace spec" in norm(card.get("trainerType"))


def text_signature(card):
    """Cards with the same name and the same signature are reprints of one card."""
    parts = [norm(card.get("effect"))]
    for a in card.get("abilities") or []:
        parts.append("A:" + norm(a.get("name")) + norm(a.get("effect")))
    for a in card.get("attacks") or []:
        parts.append("K:" + norm(a.get("name")) + norm(a.get("damage")) + norm(a.get("effect")))
    parts.append(str(card.get("hp") or ""))
    return "|".join(parts)


def load_cards(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):  # allow {"cards": [...]} too
        data = data.get("cards") or data.get("data") or list(data.values())
    by_id, by_name = {}, defaultdict(list)
    for card in data:
        if not isinstance(card, dict) or not card.get("name"):
            continue
        if card.get("id"):
            by_id[norm(card["id"])] = card
        by_name[norm(card["name"])].append(card)
    return by_id, by_name


def load_deck(path):
    with open(path, encoding="utf-8") as f:
        deck = json.load(f)
    entries = deck if isinstance(deck, list) else deck.get("cards")
    if not isinstance(entries, list):
        raise ValueError('deck file needs a "cards" list')
    return deck if isinstance(deck, dict) else {"cards": entries}, entries


# ---------- checks ----------

def check(deck_entries, by_id, by_name):
    errors, warnings = [], []
    resolved = []  # (entry_label, count, card)

    for i, entry in enumerate(deck_entries, 1):
        if not isinstance(entry, dict):
            errors.append(f"Entry {i} is not an object: {entry!r}")
            continue
        name, cid, count = entry.get("name"), entry.get("id"), entry.get("count")
        label = f"{name or '?'}" + (f" [{cid}]" if cid else "")
        if not name and not cid:
            errors.append(f"Entry {i} has no name or id")
            continue
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            errors.append(f"{label}: count must be a whole number of at least 1 (got {count!r})")
            continue

        card = None
        if cid:
            card = by_id.get(norm(cid))
            if not card:
                errors.append(f"{label}: id not found in the eligible card data")
                continue
            if name and norm(name) != norm(card["name"]):
                warnings.append(f"{label}: id belongs to \"{card['name']}\", not \"{name}\"")
        else:
            versions = by_name.get(norm(name))
            if not versions:
                close = difflib.get_close_matches(norm(name), list(by_name), n=3, cutoff=0.75)
                hint = ""
                if close:
                    hint = " Did you mean: " + ", ".join(
                        f"\"{by_name[c][0]['name']}\"" for c in close) + "?"
                errors.append(f"{label}: not found in the eligible card data.{hint}")
                continue
            card = versions[0]
            distinct = {text_signature(v): v for v in versions}
            if len(distinct) > 1 and not is_basic_energy(card):
                ids = ", ".join(v.get("id", "?") for v in list(distinct.values())[:6])
                warnings.append(f"{label}: {len(distinct)} different versions exist "
                                f"(e.g. {ids}). Add an \"id\" to say which one.")
        resolved.append((label, count, card))

    # total (cards that weren't found still count toward the 60)
    total = sum(e["count"] for e in deck_entries
                if isinstance(e, dict) and isinstance(e.get("count"), int)
                and not isinstance(e.get("count"), bool) and e["count"] >= 1)
    if total != 60:
        errors.append(f"Deck has {total} cards; it must have exactly 60")

    # copies per name
    per_name = defaultdict(int)
    display = {}
    for _, count, card in resolved:
        if not is_basic_energy(card):
            per_name[norm(card["name"])] += count
            display[norm(card["name"])] = card["name"]
    for key, n in per_name.items():
        if n > 4:
            errors.append(f"{display[key]}: {n} copies; the limit is 4 per name")

    # basic pokemon
    if resolved and not any(is_basic_pokemon(card) for _, _, card in resolved):
        errors.append("No Basic Pokémon in the deck")

    # ace spec
    ace = [(label, n) for label, n, card in resolved
           if is_ace_spec(card) or any(is_ace_spec(v) for v in by_name.get(norm(card["name"]), []))]
    if sum(n for _, n in ace) > 1:
        errors.append("More than 1 ACE SPEC: " + ", ".join(f"{n}x {l}" for l, n in ace))

    # evolutions
    names_in_deck = {norm(card["name"]) for _, _, card in resolved}
    has_candy = "rare candy" in names_in_deck
    for label, _, card in resolved:
        if not is_pokemon(card) or stage_of(card) in ("basic", ""):
            continue
        prev = card.get("evolveFrom")
        if not prev:
            continue
        if norm(prev) in names_in_deck:
            continue
        if stage_of(card) == "stage2" and has_candy:
            prev_cards = by_name.get(norm(prev), [])
            base = next((p.get("evolveFrom") for p in prev_cards if p.get("evolveFrom")), None)
            if base and norm(base) in names_in_deck:
                continue
        warnings.append(f"{label}: evolves from \"{prev}\", which is not in the deck")

    # energy
    basic_types = set()
    special_energy = False
    energy_count = 0
    for _, n, card in resolved:
        if norm(card.get("category")) == "energy":
            energy_count += n
            if is_basic_energy(card):
                for t in card.get("types") or [card["name"].replace(" Energy", "")]:
                    basic_types.add(norm(t))
            else:
                special_energy = True
    for label, _, card in resolved:
        attacks = [a for a in (card.get("attacks") or []) if a.get("cost")]
        if not is_pokemon(card) or not attacks:
            continue
        payable = False
        for a in attacks:
            needed = {norm(t) for t in a["cost"] if norm(t) != "colorless"}
            if energy_count and (needed <= basic_types or special_energy):
                payable = True
                break
        if not payable:
            needs = sorted({t for a in attacks for t in a["cost"] if norm(t) != "colorless"})
            warnings.append(f"{label}: no attack can be paid with this deck's energy"
                            + (f" (needs {', '.join(needs)})" if needs else " (deck has no energy)"))

    return errors, warnings, resolved, total


def card_text_blob(card):
    """All the text on a card, normalized, for checking quotes."""
    parts = [card.get("effect")]
    for a in (card.get("abilities") or []) + (card.get("attacks") or []):
        # "Name: effect" too, so a quote may start with the attack or Ability name
        parts += [a.get("name"), a.get("effect"), f"{a.get('name')}: {a.get('effect')}"]
    return " | ".join(norm(p) for p in parts if p)


def quote_fragments(text):
    """The parts of a card_text entry inside double quotes, split at "..."."""
    frags = []
    for q in re.findall(r'["“]([^"“”]+)["”]', str(text)):
        for f in re.split(r"\.\.\.|…", q):
            f = norm(f).strip(" .,;:")
            if f:
                frags.append(f)
    return frags


def check_quotes(deck, resolved, by_name):
    """Warn when a card_text quote isn't really on the card it names."""
    warnings = []
    in_deck = defaultdict(list)
    for _, _, card in resolved:
        in_deck[norm(card["name"])].append(card)
    for i, s in enumerate(deck.get("synergies") or [], 1):
        if not isinstance(s, dict):
            continue
        for text in s.get("card_text") or []:
            text = str(text)
            head, sep, _ = text.partition(":")
            names = [n for n in (norm(x) for x in head.split("/")) if n] if sep else []
            cards = [c for n in names for c in (in_deck.get(n) or by_name.get(n, []))]
            short = text if len(text) <= 60 else text[:57] + "..."
            if not cards:
                warnings.append(f"Synergy {i}: card_text \"{short}\" doesn't start with a card name "
                                f"from the data (write it as 'Card Name: \"quote\"')")
                continue
            frags = quote_fragments(text)
            if not frags:
                warnings.append(f"Synergy {i}: card_text \"{short}\" has no \"quoted\" card text")
                continue
            blobs = [card_text_blob(c) for c in cards]
            for f in frags:
                if not any(f in b for b in blobs):
                    warnings.append(f"Synergy {i}: \"{f}\" is not in the text of {head.strip()}")
    return warnings


def check_write_up(deck, entries, resolved, by_name):
    """The explanation parts AGENTS.md asks for. Missing parts are errors;
    weak parts (uncovered cards, quotes not on the card) are warnings."""
    errors, warnings = [], []
    no_role = [e.get("name") or e.get("id") or "?" for e in entries
               if isinstance(e, dict) and not str(e.get("role") or "").strip()]
    if no_role:
        errors.append(f"{len(no_role)} card(s) have no \"role\": " + ", ".join(map(str, no_role[:8])))
    if not str(deck.get("strategy") or "").strip():
        errors.append("Missing \"strategy\"")
    syn = deck.get("synergies")
    if not isinstance(syn, list) or len(syn) < 3:
        errors.append("\"synergies\" needs at least 3 groups")
    else:
        for i, s in enumerate(syn, 1):
            if not (isinstance(s, dict) and s.get("cards") and s.get("card_text")
                    and str(s.get("how_they_interact") or "").strip()):
                errors.append(f"Synergy {i} needs \"cards\", \"card_text\" and \"how_they_interact\"")
    rej = deck.get("rejected")
    if not isinstance(rej, list) or len(rej) != 3:
        errors.append("\"rejected\" needs exactly 3 cards")
    else:
        for i, r in enumerate(rej, 1):
            if not (isinstance(r, dict) and r.get("name") and str(r.get("reason") or "").strip()):
                errors.append(f"Rejected card {i} needs \"name\" and \"reason\"")

    names_in_deck = {norm(card["name"]) for _, _, card in resolved}
    res = deck.get("main_resource")
    if not (isinstance(res, dict) and str(res.get("resource") or "").strip()
            and str(res.get("formula") or "").strip() and res.get("cards")):
        errors.append("Missing \"main_resource\": needs \"resource\", \"formula\" and \"cards\"")
    else:
        for c in res["cards"]:
            if not (isinstance(c, dict) and c.get("name") and str(c.get("effect") or "").strip()):
                errors.append("Each main_resource card needs \"name\" and \"effect\"")
            elif norm(c["name"]) not in names_in_deck:
                warnings.append(f"main_resource: \"{c['name']}\" is not in the deck")

    if isinstance(syn, list):
        covered = {norm(n) for s in syn if isinstance(s, dict) for n in (s.get("cards") or [])}
        standalone = {norm(e.get("name")) for e in entries
                      if isinstance(e, dict) and e.get("standalone")}
        missing = sorted({card["name"] for _, _, card in resolved
                          if norm(card["name"]) not in covered | standalone
                          and not is_basic_energy(card)})
        if missing:
            warnings.append(f"{len(missing)} card(s) are in no synergy group (add them to one, "
                            f"or set \"standalone\": true and say why in the role): "
                            + ", ".join(missing))
        warnings += check_quotes(deck, resolved, by_name)
    return errors, warnings


def summarize(resolved):
    groups = defaultdict(int)
    for _, n, card in resolved:
        cat = norm(card.get("category"))
        groups["Pokémon" if cat in ("pokemon", "pokémon") else card.get("category") or "Other"] += n
    return ", ".join(f"{k} {v}" for k, v in groups.items())


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck", help="deck JSON file")
    ap.add_argument("--cards", help="card data file (default: data/cards_full.json)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--rules-only", action="store_true",
                    help="check only the deck rules, not roles/synergies/rejected cards")
    a = ap.parse_args()

    cards_path = a.cards or next((p for p in DEFAULT_CARD_FILES if os.path.exists(p)), None)
    if not cards_path or not os.path.exists(cards_path):
        print("Card data not found. Put cards_full.json in data/ or pass --cards.")
        sys.exit(2)
    try:
        by_id, by_name = load_cards(cards_path)
        deck, entries = load_deck(a.deck)
    except (OSError, ValueError) as e:
        print(f"Could not read input: {e}")
        sys.exit(2)

    errors, warnings, resolved, total = check(entries, by_id, by_name)
    if not a.rules_only:
        more_errors, more_warnings = check_write_up(deck, entries, resolved, by_name)
        errors += more_errors
        warnings += more_warnings

    title = deck.get("deck_name") or os.path.basename(a.deck)
    print(f"{title}: {total} cards ({summarize(resolved)})")
    for e in errors:
        print(f"  ERROR    {e}")
    for w in warnings:
        print(f"  WARNING  {w}")

    failed = bool(errors) or (a.strict and bool(warnings))
    print("FAIL" if failed else ("PASS" + (" (with warnings)" if warnings else "")))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
