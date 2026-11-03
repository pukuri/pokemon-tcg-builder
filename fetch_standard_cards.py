#!/usr/bin/env python3
"""
Step 1: download every Standard-eligible Pokemon TCG card from TCGdex.

A card counts as eligible if:
  - its regulation mark is H, I or J (change with --marks), or
  - it is a Basic Energy (these have no mark and are always legal), or
  - it belongs to an extra set you allow (default: 30th Celebration main set,
    which TCGdex leaves unmarked but Limitless treats as Standard legal).

TCGdex's own "legal.standard" flag is NOT trusted, because it is wrong for
some cards (for example the whole 30th Celebration set).

Free API, no key needed. Python 3.8+, no extra packages.

Usage:
    python3 fetch_standard_cards.py
    python3 fetch_standard_cards.py --marks H,I,J --extra-sets 30th
    python3 fetch_standard_cards.py --extra-sets ""        # leave 30th Celebration out
    python3 fetch_standard_cards.py --extra-sets 30th,30th-c  # also Classic Collection
    python3 fetch_standard_cards.py --refresh               # re-download everything

Output (in ./pokemon_standard/ by default):
    cards_full.json      every eligible printing with all TCGdex fields
    eligible_cards.csv   one row per printing, for a quick look in a spreadsheet
    cache/               one JSON file per card, so reruns only fetch new cards
"""

import argparse
import csv
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://api.tcgdex.net/v2/en"
HEADERS = {"User-Agent": "standard-card-list/1.0 (personal deckbuilding)",
           "Accept": "application/json"}

SSL_HELP = """
Python could not verify TCGdex's HTTPS certificate because it can't find your
computer's trusted certificates. Fix it with ONE of these, then run again:

  1. Install the certifi package (works everywhere; this script uses it automatically):
         python3 -m pip install certifi
     (on Windows: py -m pip install certifi)

  2. macOS with Python from python.org: open Finder > Applications > Python 3.x
     and double-click "Install Certificates.command".
"""


def make_ssl_context():
    """Use certifi's certificate bundle if installed, else the system default."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


SSL_CONTEXT = make_ssl_context()


def is_cert_error(err):
    reason = getattr(err, "reason", err)
    return isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(err)


def get(path, params=None, retries=4):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == retries - 1:
                raise
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if is_cert_error(e):
                sys.exit(SSL_HELP)  # retrying won't help
            if attempt == retries - 1:
                raise
        time.sleep(1.5 * (attempt + 1))


def collect_ids(marks, extra_sets):
    """Return {card_id: reason} for everything that might be eligible."""
    found = {}
    for m in marks:
        cards = get("/cards", {"regulationMark": m}) or []
        print(f"  mark {m}: {len(cards)} printings")
        for c in cards:
            found.setdefault(c["id"], f"mark {m}")

    # TCGdex's legality flag is only used to discover Basic Energy printings;
    # they are confirmed by their details later.
    legal = get("/cards", {"legal.standard": "true"}) or []
    extra = [c for c in legal if c["id"] not in found]
    print(f"  possible Basic Energy (no mark): {len(extra)} printings")
    for c in extra:
        found.setdefault(c["id"], "basic energy")

    for s in extra_sets:
        data = get(f"/sets/{s}")
        if not data:
            print(f"  WARNING: set '{s}' not found on TCGdex, skipped")
            continue
        print(f"  extra set {s} ({data.get('name')}): {len(data.get('cards', []))} printings")
        for c in data.get("cards", []):
            found[c["id"]] = f"extra set {s}"
    return found


def fetch_details(ids, cache_dir, workers, refresh):
    os.makedirs(cache_dir, exist_ok=True)
    details, todo = {}, []
    for cid in ids:
        path = os.path.join(cache_dir, f"{cid}.json")
        if not refresh and os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                details[cid] = json.load(f)
        else:
            todo.append(cid)
    print(f"  {len(details)} from cache, {len(todo)} to download")

    failed = []

    def one(cid):
        time.sleep(0.05)  # stay polite
        return cid, get("/cards/" + urllib.parse.quote(cid, safe=""))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(one, cid) for cid in todo]
        for i, fut in enumerate(as_completed(futures), 1):
            try:
                cid, data = fut.result()
            except Exception as e:  # noqa: BLE001
                failed.append(str(e))
                continue
            if data:
                details[cid] = data
                with open(os.path.join(cache_dir, f"{cid}.json"), "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
            if i % 200 == 0 or i == len(todo):
                print(f"    downloaded {i}/{len(todo)}")
    if failed:
        print(f"  WARNING: {len(failed)} cards failed to download. Run again to retry them.")
    return details


def is_eligible(card, marks, extra_sets):
    mark = (card.get("regulationMark") or "").upper()
    set_id = (card.get("set") or {}).get("id", "")
    if mark in marks:
        return f"mark {mark}"
    if card.get("category") == "Energy" and card.get("energyType") == "Normal":
        return "basic energy"
    if set_id in extra_sets:
        return f"extra set {set_id}"
    return None


def sort_key(card):
    local = str(card.get("localId", ""))
    digits = "".join(ch for ch in local if ch.isdigit())
    return ((card.get("set") or {}).get("id", ""), int(digits) if digits else 0, local)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--marks", default="H,I,J", help="regulation marks to allow")
    ap.add_argument("--extra-sets", default="30th",
                    help="comma-separated TCGdex set ids to allow regardless of mark")
    ap.add_argument("--out", default="pokemon_standard", help="output folder")
    ap.add_argument("--workers", type=int, default=4, help="parallel downloads (keep it low)")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache")
    a = ap.parse_args()

    marks = {m.strip().upper() for m in a.marks.split(",") if m.strip()}
    extra_sets = {s.strip() for s in a.extra_sets.split(",") if s.strip()}
    os.makedirs(a.out, exist_ok=True)

    print(f"Finding eligible cards (marks {', '.join(sorted(marks))}"
          f"{'; extra sets ' + ', '.join(sorted(extra_sets)) if extra_sets else ''})")
    try:
        ids = collect_ids(sorted(marks), sorted(extra_sets))
        print(f"Downloading card details for {len(ids)} printings")
        details = fetch_details(ids, os.path.join(a.out, "cache"), a.workers, a.refresh)
    except Exception as e:  # noqa: BLE001
        sys.exit(f"Could not reach TCGdex: {e}")

    cards = []
    for card in details.values():
        reason = is_eligible(card, marks, extra_sets)
        if reason:
            card["eligibility"] = reason
            cards.append(card)
    cards.sort(key=sort_key)

    with open(os.path.join(a.out, "cards_full.json"), "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=1)

    with open(os.path.join(a.out, "eligible_cards.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "set", "number", "name", "category", "stage / trainer type",
                    "types", "hp", "regulation mark", "rarity", "eligible because"])
        for c in cards:
            w.writerow([
                c.get("id"), (c.get("set") or {}).get("name", ""), c.get("localId"),
                c.get("name"), c.get("category"),
                c.get("stage") or c.get("trainerType") or c.get("energyType") or "",
                ", ".join(c.get("types") or []), c.get("hp") or "",
                c.get("regulationMark") or "", c.get("rarity") or "", c.get("eligibility"),
            ])

    by_reason = {}
    for c in cards:
        by_reason[c["eligibility"]] = by_reason.get(c["eligibility"], 0) + 1
    print(f"\nDone: {len(cards)} eligible printings, {len({c['name'] for c in cards})} unique names")
    for r, n in sorted(by_reason.items()):
        print(f"  {r}: {n}")
    print(f"Saved to {os.path.abspath(a.out)}")


if __name__ == "__main__":
    main()