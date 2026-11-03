#!/usr/bin/env python3
"""
Simulate a simplified head-to-head match between two Pokémon TCG decks.

Usage:
    python3 duel_decks.py decks/foo.json example/bar.json
    python3 duel_decks.py decks/foo.json example/bar.json --games 5000 --seed 1
    python3 duel_decks.py decks/foo.json example/bar.json --extra-per-turn 1

The two decks actually play each other, game after game. Each game:

  1. Both decks are shuffled. Each player mulligans until their opening hand
     of 7 has a Basic Pokémon, then sets 6 Prize cards aside.
  2. The player going first alternates each game. The first player cannot
     attack on their first turn (the real rule); the second player can.
  3. Each turn a player: draws 1 card, plays Basic Pokémon onto the Bench,
     evolves (Stage 1 then Stage 2) wherever the pre-evolution is in play,
     attaches 1 Basic Energy to their Active Pokémon, then attacks with the
     Active using its highest-damage affordable attack.
  4. Damage is applied to the opponent's Active. Weakness (x2) and Resistance
     (-30) are read from the card data. When an Active is Knocked Out, its
     owner promotes their strongest Benched Pokémon (most Energy, then HP) and
     the attacker draws a Prize.
  5. A game ends when one side takes its 6th Prize, or the opponent has no
     Pokémon in play, or the opponent decks out trying to draw.

Approximations (this is a tactical model, not a rules-complete referee):
  - Trainer cards, Abilities and Special Energy are NOT played literally. Use
    --extra-per-turn N to stand in for a deck's draw/search engine (N extra
    cards seen per turn).
  - An attack's damage is its printed base number. The "+" and "x" modifiers
    are ignored, and an attack with no printed damage deals 0.
  - Only Basic Energy cards attach, one per turn. Special Energy is ignored.
  - There is no retreat, switching, Status condition, Bench damage from spread
    attacks, or hand/deck manipulation; the Active is fixed until it is Knocked
    Out.

Reported: A wins / B wins (win rate), the split by who went first, average
game length, and each deck's mulligan rate.

Exit code: 0 done, 2 for bad input or missing card data.
Python 3.8+, no extra packages.
"""

import argparse
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict

import check_deck

HAND, PRIZES = 7, 6
MAX_BENCH = 5          # 1 Active + 5 Bench
MULLIGAN_CAP = 50      # give up on a deck with no playable Basic
COLORED_TYPES = ("grass", "fire", "water", "lightning", "psychic",
                 "fighting", "darkness", "metal")


def norm(text):
    return check_deck.norm(text)


def energy_color(card):
    """The colour a Basic Energy provides, or None for a non-standard name."""
    n = norm(card.get("name"))
    for t in COLORED_TYPES:
        if n in (t + " energy", "basic " + t + " energy"):
            return t
    return None


def parse_damage(damage):
    if isinstance(damage, (int, float)):
        return int(damage)
    m = re.match(r"\d+", str(damage or ""))
    return int(m.group()) if m else 0


def build_model(card):
    cat = norm(card.get("category"))
    m = {"key": norm(card["name"]), "name": card["name"], "category": cat}
    if cat == "pokemon":
        stage = norm(card.get("stage")).replace(" ", "")
        m.update({
            "stage": stage,
            "evolve_from": norm(card["evolveFrom"]) if card.get("evolveFrom") else None,
            "hp": int(card.get("hp") or 0),
            "types": [norm(t) for t in (card.get("types") or [])],
            "weaknesses": {norm(w["type"]): w.get("value")
                           for w in (card.get("weaknesses") or [])},
            "resistances": {norm(r["type"]): r.get("value")
                            for r in (card.get("resistances") or [])},
            "attacks": [{"name": a.get("name"),
                         "cost": [norm(t) for t in (a.get("cost") or [])],
                         "damage": parse_damage(a.get("damage"))}
                        for a in (card.get("attacks") or [])],
        })
    elif cat == "energy":
        m["basic"] = norm(card.get("energyType")) in ("normal", "basic")
        m["color"] = energy_color(card) if m["basic"] else None
    return m


def resolve_deck(path, by_id, by_name):
    """Return (models, deck_list) for one deck file."""
    with open(path, encoding="utf-8") as f:
        deck = json.load(f)
    entries = deck.get("cards") if isinstance(deck, dict) else deck
    models, deck_list = {}, []
    for e in entries:
        if not isinstance(e, dict):
            continue
        card = by_id.get(norm(e["id"])) if e.get("id") else None
        if card is None:
            versions = by_name.get(norm(e.get("name")))
            card = versions[0] if versions else None
        if card is None:
            raise ValueError(f"\"{e.get('name') or e.get('id')}\" is not in the card data")
        key = norm(card["name"])
        if key not in models:
            models[key] = build_model(card)
        deck_list += [key] * int(e.get("count") or 0)
    return models, deck_list


def deck_info(models, deck_list):
    """Precompute the lookups the engine needs."""
    keys = set(deck_list)
    pokemon = {k for k in keys if models[k]["category"] == "pokemon"}
    basics = {k for k in pokemon if models[k]["stage"] == "basic"}
    max_dmg = {k: max((a["damage"] for a in models[k]["attacks"]), default=0)
               for k in pokemon}

    stage1_of, stage2_of = defaultdict(set), defaultdict(set)
    for k in pokemon:
        ev = models[k]["evolve_from"]
        if not ev:
            continue
        if models[k]["stage"] == "stage1":
            stage1_of[ev].add(k)
        elif models[k]["stage"] == "stage2":
            stage2_of[ev].add(k)

    # Best damage a Basic can reach through its evolution line.
    def ceiling(k):
        best = max_dmg.get(k, 0)
        for s1 in stage1_of.get(k, ()):
            best = max(best, max_dmg.get(s1, 0))
            for s2 in stage2_of.get(s1, ()):
                best = max(best, max_dmg.get(s2, 0))
        return best

    return {
        "models": models, "deck_list": deck_list, "basics": basics,
        "max_dmg": max_dmg, "stage1_of": stage1_of, "stage2_of": stage2_of,
        "ceiling": {k: ceiling(k) for k in basics},
    }


def new_mon(key, model):
    return {"key": key, "model": model, "damage": 0, "energy": []}


def best_basic(candidates, info):
    return max(candidates, key=lambda k: (info["ceiling"].get(k, 0),
                                          info["models"][k]["hp"], k))


def child_value(k, info):
    best = info["max_dmg"].get(k, 0)
    for s2 in info["stage2_of"].get(k, ()):
        best = max(best, info["max_dmg"].get(s2, 0))
    return best


def can_pay(energy_colors, cost):
    if len(energy_colors) < len(cost):
        return False
    need = Counter(c for c in cost if c != "colorless")
    have = Counter(c for c in energy_colors if c)
    return all(have.get(t, 0) >= n for t, n in need.items())


def setup_board(hand, info):
    """Turn an opening hand into a board: best Basic Active, rest on Bench."""
    hand = list(hand)
    basics = [k for k in hand if k in info["basics"]]
    if not basics:
        return [], hand
    active = best_basic(basics, info)
    hand.remove(active)
    board = [new_mon(active, info["models"][active])]
    rest = sorted((k for k in hand if k in info["basics"]),
                  key=lambda k: (info["ceiling"].get(k, 0), info["models"][k]["hp"], k),
                  reverse=True)[:MAX_BENCH]
    for k in rest:
        board.append(new_mon(k, info["models"][k]))
        hand.remove(k)
    return board, hand


def evolve_board(state, info):
    for mon in state["board"]:
        kids = info["stage1_of"].get(mon["key"])
        if kids:
            mon["key"] = max(kids, key=lambda k: (child_value(k, info),
                                                  info["models"][k]["hp"], k))
            kids2 = info["stage2_of"].get(mon["key"])
            if kids2:
                mon["key"] = max(kids2, key=lambda k: (info["max_dmg"][k],
                                                       info["models"][k]["hp"], k))
            mon["model"] = info["models"][mon["key"]]


def attach_energy(state, info):
    if not state["board"]:
        return
    for i, k in enumerate(state["hand"]):
        if info["models"][k]["category"] == "energy" and info["models"][k].get("basic"):
            state["board"][0]["energy"].append(info["models"][k]["color"])
            state["hand"].pop(i)
            return


def ko(attacker, defender):
    """Resolve a Knock Out. Return the winner label, or None."""
    defender["board"].pop(0)
    attacker["prizes"] -= 1
    if attacker["prizes"] <= 0:
        return attacker["label"]
    if not defender["board"]:
        return attacker["label"]
    # Promote strongest Bench: most Energy, then HP.
    defender["board"].sort(key=lambda m: (len(m["energy"]), m["model"]["hp"]),
                           reverse=True)
    return None


def attack(attacker, defender):
    """Attack with the Active. Return a winner label or None."""
    if not attacker["board"]:
        return None
    if not defender["board"]:
        return attacker["label"]
    atk = attacker["board"][0]
    atk_model = atk["model"]
    defn = defender["board"][0]
    best = None
    for a in atk_model["attacks"]:
        if can_pay(atk["energy"], a["cost"]):
            if best is None or a["damage"] > best["damage"]:
                best = a
    if best is None:
        return None

    dmg = best["damage"]
    types = atk_model.get("types") or []
    if types:
        t = types[0]
        if t in defn["model"].get("weaknesses", {}):
            dmg *= 2
        if t in defn["model"].get("resistances", {}):
            dmg = max(0, dmg - 30)
    defn["damage"] += dmg
    if defn["damage"] >= defn["model"]["hp"]:
        return ko(attacker, defender)
    return None


def make_player(label, info, rng, mull_counter):
    deck = list(info["deck_list"])
    mulligans = 0
    while True:
        rng.shuffle(deck)
        if any(k in info["basics"] for k in deck[:HAND]):
            break
        mulligans += 1
        if mulligans >= MULLIGAN_CAP:
            break
    mull_counter[0] += mulligans
    if mulligans:
        mull_counter[1] += 1
    draw_pile = deck[HAND + PRIZES:]
    board, hand = setup_board(deck[:HAND], info)
    return {"label": label, "draw_pile": draw_pile, "hand": hand,
            "prizes": PRIZES, "board": board, "turns": 0}


def play_game(info_a, info_b, rng, first_is_a, extra):
    a_mull, b_mull = [0, 0], [0, 0]
    A = make_player("A", info_a, rng, a_mull)
    B = make_player("B", info_b, rng, b_mull)
    players = {"A": A, "B": B}
    first, second = ("A", "B") if first_is_a else ("B", "A")
    order = [first, second]
    turns = 0
    while True:
        turns += 1
        for p in order:
            state = players[p]
            opp = players["B" if p == "A" else "A"]
            state["turns"] += 1
            info = info_a if p == "A" else info_b
            # 1. Draw.
            if not state["draw_pile"]:
                return ("B" if p == "A" else "A"), turns, a_mull, b_mull
            state["hand"].append(state["draw_pile"].pop())
            for _ in range(max(0, extra)):
                if state["draw_pile"]:
                    state["hand"].append(state["draw_pile"].pop())
            # 2. Play Basics onto the Bench.
            if len(state["board"]) < 1 + MAX_BENCH:
                avail = sorted((k for k in state["hand"] if k in info["basics"]),
                               key=lambda k: (info["ceiling"].get(k, 0),
                                              info["models"][k]["hp"], k),
                               reverse=True)
                for k in avail:
                    if len(state["board"]) >= 1 + MAX_BENCH:
                        break
                    state["board"].append(new_mon(k, info["models"][k]))
                    state["hand"].remove(k)
            # 3. Evolve.
            evolve_board(state, info)
            # 4. Attach Energy to the Active.
            attach_energy(state, info)
            # 5. Attack (first player's first turn is skipped).
            if not (p == first and state["turns"] == 1):
                winner = attack(state, opp)
                if winner:
                    return winner, turns, a_mull, b_mull
    # unreachable


def run(path_a, path_b, games, extra, seed):
    cards_path = next((p for p in check_deck.DEFAULT_CARD_FILES
                       if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), p))), None)
    if not cards_path:
        raise RuntimeError("card data not found (looked for data/cards_full.json etc.)")
    by_id, by_name = check_deck.load_cards(cards_path)
    models_a, list_a = resolve_deck(path_a, by_id, by_name)
    models_b, list_b = resolve_deck(path_b, by_id, by_name)
    if not (models_a and models_b):
        raise ValueError("a deck has no cards")
    info_a = deck_info(models_a, list_a)
    info_b = deck_info(models_b, list_b)
    if not info_a["basics"]:
        raise ValueError("deck A has no Basic Pokémon")
    if not info_b["basics"]:
        raise ValueError("deck B has no Basic Pokémon")

    name_a = os.path.splitext(os.path.basename(path_a))[0]
    name_b = os.path.splitext(os.path.basename(path_b))[0]

    rng = random.Random(seed)
    a_wins = b_wins = total_turns = 0
    a_first_games = b_first_games = 0
    a_first_wins = a_second_wins = b_first_wins = b_second_wins = 0
    a_mull_games = b_mull_games = 0

    for i in range(games):
        first_is_a = (i % 2 == 0)
        winner, turns, a_m, b_m = play_game(info_a, info_b, rng, first_is_a, extra)
        total_turns += turns
        a_mull_games += (1 if a_m[1] else 0)
        b_mull_games += (1 if b_m[1] else 0)
        if first_is_a:
            a_first_games += 1
        else:
            b_first_games += 1
        if winner == "A":
            a_wins += 1
            if first_is_a:
                a_first_wins += 1
            else:
                a_second_wins += 1
        else:
            b_wins += 1
            if first_is_a:
                b_second_wins += 1
            else:
                b_first_wins += 1

    return {
        "name_a": name_a, "name_b": name_b, "path_a": path_a, "path_b": path_b,
        "games": games, "extra": extra,
        "a_wins": a_wins, "b_wins": b_wins,
        "a_first_wins": a_first_wins, "a_second_wins": a_second_wins,
        "b_first_wins": b_first_wins, "b_second_wins": b_second_wins,
        "a_first_games": a_first_games, "b_first_games": b_first_games,
        "avg_turns": total_turns / games,
        "a_mulligan": a_mull_games / games,
        "b_mulligan": b_mull_games / games,
    }


def format_report(r):
    g = r["games"]
    lines = []
    lines.append("=" * 78)
    lines.append(f" Head-to-head duel: {r['name_a']}  vs  {r['name_b']}")
    lines.append(f" {g:,} games" + (f", --extra-per-turn {r['extra']}" if r["extra"] else ""))
    lines.append("=" * 78)
    lines.append("")
    lines.append(f"  {r['name_a']}  wins:  {r['a_wins']:,}  ({r['a_wins'] / g:.1%})")
    lines.append(f"  {r['name_b']}  wins:  {r['b_wins']:,}  ({r['b_wins'] / g:.1%})")
    lines.append("")
    lines.append("  Win rate by who went first:")
    lines.append(f"    {r['name_a']} going first:  {r['a_first_wins'] / r['a_first_games']:.1%}  "
                 f"| going second: {r['a_second_wins'] / r['b_first_games']:.1%}")
    lines.append(f"    {r['name_b']} going first:  {r['b_first_wins'] / r['b_first_games']:.1%}  "
                 f"| going second: {r['b_second_wins'] / r['a_first_games']:.1%}")
    lines.append("")
    lines.append(f"  Average game length: {r['avg_turns']:.1f} turns")
    lines.append(f"  Mulligan rate — {r['name_a']}: {r['a_mulligan']:.1%}   "
                 f"{r['name_b']}: {r['b_mulligan']:.1%}")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck_a", help="first deck JSON file")
    ap.add_argument("deck_b", help="second deck JSON file")
    ap.add_argument("--games", type=int, default=5000, help="matches to simulate (default 5000)")
    ap.add_argument("--extra-per-turn", type=int, default=0,
                    help="extra cards seen per turn, a stand-in for draw/search (default 0)")
    ap.add_argument("--seed", type=int, help="random seed for repeatable results")
    a = ap.parse_args()
    try:
        r = run(a.deck_a, a.deck_b, a.games, a.extra_per_turn, a.seed)
    except (OSError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(format_report(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
