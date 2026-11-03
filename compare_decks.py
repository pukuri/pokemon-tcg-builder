#!/usr/bin/env python3
"""
Pit two Pokémon TCG deck files against each other in simulated matches.

First it checks both decks are legal (check_deck.py --rules-only), then it runs
duel_decks.py, which plays simplified head-to-head matches and prints the win
rates, the first/second split, average game length, and mulligan rates.

Usage:
    python3 compare_decks.py decks/foo.json example/bar.json
    python3 compare_decks.py decks/foo.json example/bar.json --games 5000 --seed 1
    python3 compare_decks.py decks/foo.json example/bar.json --extra-per-turn 1

Exit code: 0 duel done, 1 if either deck fails the rules check, 2 for bad input.
Python 3.8+, no extra packages.
"""

import argparse
import os
import subprocess
import sys

import duel_decks

ROOT = os.path.dirname(os.path.abspath(__file__))


def run_check(deck_path):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "check_deck.py"),
                        deck_path, "--rules-only"],
                       cwd=ROOT, capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout + r.stderr).strip()


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

    # --- legality guard ------------------------------------------------------
    any_fail = False
    for key, path in (("A", a.deck_a), ("B", a.deck_b)):
        code, out = run_check(path)
        if code == 0:
            continue
        any_fail = True
        if code == 2:
            print(f"{key}: could not read deck file:")
            print("  " + out.replace("\n", "\n  "))
            return 2
        print(f"{key}: illegal deck (check_deck.py --rules-only failed):")
        print("  " + out.replace("\n", "\n  "))
    if any_fail:
        print("\nFix the deck above before duelling.")
        return 1

    # --- the duel ------------------------------------------------------------
    try:
        r = duel_decks.run(a.deck_a, a.deck_b, a.games, a.extra_per_turn, a.seed)
    except (OSError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(duel_decks.format_report(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
