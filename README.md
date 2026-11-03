# Pokémon TCG Deck Builder

A toolkit for building, validating and testing competitive **Standard-format**
Pokémon TCG decks using only locally stored card data. A code agent
builds the decks following the rules in [AGENTS.md](AGENTS.md); the Python scripts
check them, simulate them, and pit them against each other; a small Node web app
shows the finished decks with card images.

Everything is dependency-free: Python 3.8+ and Node.js, no `pip install` or `npm install`.

## What it can do

- **Download card data** – fetch every Standard-eligible card (regulation marks
  H, I, J, Basic Energy and 30th Celebration) from [TCGdex](https://tcgdex.net).
- **Build decks** – an agent writes `decks/<name>.json` plus a `decks/<name>.md`
  explanation, with card roles, synergies, rejected cards and consistency checks.
- **Validate decks** – enforce the rules: 60 cards, max 4 copies per name, at least
  1 Basic, max 1 ACE SPEC, evolution lines complete, and synergy quotes that match
  the real card text.
- **Test consistency** – shuffle a deck thousands of times and measure how often
  it hits setup goals (turn-1 Basic, attacker ready, Energy, ...).
- **Duel two decks** – simulate head-to-head matches and report win rates,
  first/second split, game length and mulligan rates.
- **Browse decks in a browser** – local viewer with card images for `decks/` and
  the tournament-style lists in `example/`.

## Commands

### 1. Get the card data (first time only)

```bash
python3 fetch_standard_cards.py --out data/pokemon_standard
```

Options: `--marks H,I,J`, `--extra-sets 30th`, `--workers 4`, `--refresh` (ignore the cache).
Reruns only download new cards.

### 2. Validate a deck

```bash
python3 check_deck.py decks/mega-darkrai-poison.json
python3 check_deck.py decks/mega-darkrai-poison.json --strict       # warnings fail too
python3 check_deck.py decks/mega-darkrai-poison.json --rules-only   # skip synergy checks

python3 deck_guard.py                    # check every deck in decks/
python3 deck_guard.py decks/foo.json     # check specific decks
```

### 3. Test consistency

```bash
python3 simulate_deck.py decks/mega-darkrai-poison.json --games 10000
python3 simulate_deck.py --help          # format of "consistency_checks"
```

### 4. Duel two decks

```bash
python3 compare_decks.py decks/mega-darkrai-poison.json example/dragapult.json --games 5000 --seed 1
```

### 5. Build a new deck with a code agent

Open the project in any code agent that reads `AGENTS.md` (Claude Code, Codex,
Cursor, Gemini CLI, ...) and describe the deck you want, for example
*"Build a Dragapult ex deck"*. The agent follows `AGENTS.md`, saves the deck to
`decks/`, and runs the checker and simulator.

## Web viewer

Start the server (no install step needed):

```bash
npm start
# or
node server.js
```

Then open **http://localhost:3000** in your browser.

To use another port:

```bash
PORT=8080 npm start     # then open http://localhost:8080
```

The server reads `decks/*.json` ("Your decks") and `example/*.json` ("Examples"),
resolves each card from `data/pokemon_standard/cards_full.json`, and serves the
page from `public/`. Card images are loaded from TCGdex, so the browser needs
internet access. Stop the server with `Ctrl+C`.
