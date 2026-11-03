# Generate a deck

Build a Pokémon TCG deck for the **Standard format** that satisfies the user's
criteria, which are supplied at the end of this prompt (after "Criteria:").

Use only the card data stored locally in `data/`. Search it with `grep` or
short Python scripts — never read it all at once, never rely on memory or the
web, and never browse the internet for card text or decklists. Copy card names
exactly as written. Card names may be codes (for example `PKM-0412`); treat
them exactly like real names. When a name has several versions with different
text, give the `id` of the version you mean.

## Workflow

1. Read the criteria and identify the required Pokémon, any style asked for,
   and any limits.
2. Find the required cards in `data/` and read their full text.
3. Work out what the deck needs to function: an attacker plan, energy, a way to
   find and evolve Pokémon, draw, switching, recovery, and disruption. Search
   `data/` for the best card for each job, and for each key job (draw, Pokémon
   search, gusting, switching, energy) compare the 2–3 best candidates across
   the whole game before choosing.
4. Look for synergies starting from the win condition: write the main attack's
   damage (or the win condition) as a formula and name the number it depends on
   (hand size, Energy, Bench size, damage counters, discard count). Record it
   under `main_resource` and list every card that changes that number with its
   net effect. Then give synergy groups for the engine's cost, the card
   restrictions, and coverage — see `AGENTS.md` for the full rules. Note the
   strongest cards you considered but left out, and why.
5. Write the deck to `decks/<deck-name>.json` (short lowercase name, hyphenated,
   based on the main attacker; add a number if the file already exists) and
   explain it in `decks/<deck-name>.md`.
6. Run `python3 check_deck.py decks/<deck-name>.json` and fix every error,
   rerunning until it reports PASS.
7. Add at least 4 `consistency_checks` (see `python3 simulate_deck.py --help`):
   turn-1 main Basic, main attacker ready, each attacker's Energy, and the
   condition of every conditional card. Run
   `python3 simulate_deck.py decks/<deck-name>.json --games 10000` and fix
   anything below target (never lower a target just to pass).

Full rules and deckbuilding principles are in `AGENTS.md`. Follow them.

## Output format

Save decks as JSON:

```json
{
  "deck_name": "Short name",
  "requirements": "The request this deck answers",
  "cards": [
    { "name": "Card Name", "count": 4, "id": "set-number", "role": "Why it is in the deck and why this many" }
  ],
  "strategy": "How the deck wins, in 3 to 6 sentences",
  "main_resource": {
    "resource": "The number the main attack or win condition depends on",
    "formula": "How damage follows from it, with thresholds (e.g. 11 cards = 220)",
    "cards": [
      { "name": "Card A", "effect": "+2 (draws 3, spends itself)" }
    ]
  },
  "synergies": [
    {
      "cards": ["Card A", "Card B"],
      "card_text": ["Card A: \"exact quote from data/\"", "Card B: \"exact quote\""],
      "how_they_interact": "What happens during a game when these are used together, with numbers"
    }
  ],
  "rejected": [
    { "name": "Card Name", "reason": "Why it was left out" }
  ]
}
```

- `name` and `count` are required for every entry. `id` is optional unless the
  name has several versions. `role` is short and specific.
- List Pokémon first, then Trainers, then Energy. Counts must add to exactly 60.
- `main_resource` is required. Its `cards` must all be in the deck.
- `synergies` needs at least 3 groups and `rejected` exactly 3 cards. Each
  `card_text` entry starts with the card's exact name, a colon, then the quote
  in double quotes (exact wording from `data/`, "..." allowed to skip words).
- Every card (except Basic Energy) appears in some synergy's `cards`, or its
  entry has `"standalone": true`. `example/alakazam.json` shows the format.

## Deliverables

For every deck, reply with:
1. The decklist grouped as Pokémon, Trainers and Energy with counts.
2. The role of every card (one specific line each).
3. The main resource (the formula and every card that changes it), then the
   synergies with exact card-text quotes, numbers, and how they interact.
4. The 3 rejected cards and why each lost its place.
5. The final `check_deck.py` PASS output.

## Criteria

(The user's request is appended below this line.)
