# Pokémon TCG Deck Builder

This project builds competitive Pokémon TCG decks for the **Standard format**
using only the card data stored locally in `data/`.

## Data

- `data/cards_full.json` is the list of every tournament-eligible card printing
  (regulation marks H, I, J, plus Basic Energy and 30th Celebration).
  Each card has: `id`, `name`, `category` (Pokemon / Trainer / Energy),
  `stage`, `evolveFrom`, `hp`, `types`, `abilities`, `attacks` (with `cost`,
  `damage`, `effect`), `weaknesses`, `retreat`, `trainerType`, `energyType`,
  `effect`, `rarity`, `regulationMark`.
- If `data/cards_unique.json` or `data/cards_compact.txt` exist, prefer them for
  browsing (one entry per distinct card). `cards_full.json` is the source of truth.
- The data is large. Search it with `grep` or short Python scripts instead of
  reading it all at once.
- Card names may be codes (for example `PKM-0412`). Treat them exactly like
  real names and never guess what they stand for.

## Ground rules

- **Only use cards that exist in `data/`.** Copy names exactly as written there.
- **Base every choice on the card text in `data/`.** Do not rely on remembered
  decklists, tournament results or card text from memory, and do not browse
  the web.
- When a name has several versions with different text (for example several
  different "Pikachu" cards), give the `id` of the version you mean.

## Deck rules (Standard)

1. Exactly **60 cards**.
2. At most **4 copies of any card with the same name**, counting all versions
   together. Basic Energy is exempt and can be played in any number.
3. At least **1 Basic Pokémon**.
4. At most **1 ACE SPEC** card in the whole deck.
5. Every Stage 1 needs its Basic in the deck; every Stage 2 needs its Stage 1
   (or its Basic plus a card that skips the Stage 1, such as Rare Candy).
6. The deck must be able to pay its attackers' Energy costs.

## How to build a deck

1. Read the request: the required Pokémon, any style asked for, and any limits.
2. Find the required cards in `data/` and read their full text.
3. Work out what the deck needs to function: an attacker plan, energy, a way to
   find and evolve Pokémon, draw, switching, recovery, and ways to disrupt the
   opponent. Search the data for the best cards for each job. Then run the
   "Hidden-synergy search" below before choosing the 60.
4. Look for synergies, starting from the win condition:
   - **The main resource.** Write the main attack's damage (or the win
     condition) as a formula and name the number it depends on (hand
     size, Energy attached, Bench size, damage counters, discard count).
     Record it under `main_resource` and list every card in the deck that
     changes that number, with its net effect (e.g. "Gwynn: +3 cards").
     The first synergy group covers these cards.
   - **The engine's cost.** Name what the strategy uses up (deck size
     from heavy draw, Prizes from self-KOs, discarded Energy, Bench
     space). Do the math (e.g. "47 cards, ~12 drawn per big turn = 4
     turns") and give a synergy group for the cards that make up for it.
   - **Limits count.** Quote the restrictions as well as the benefit
     ("can't evolve this turn", "you may", "during your opponent's
     turn") and explain how they change the play.
   - **Coverage.** Every card must appear in at least one synergy group.
     A card that truly works alone gets `"standalone": true` and a role
     that says why.
   - **Numbers and order of play.** Use numbers in every
     `how_they_interact` (damage thresholds, cards gained, turns), and
     give the order to play cards on the key turn when it matters.
5. Note the strongest cards you considered but left out, and why.
6. Write the deck to `decks/<deck-name>.json` in the format below.
7. Run the checker and fix every error, then rerun until it passes:
   ```
   python3 check_deck.py decks/<deck-name>.json
   ```
   Also fix every synergy warning: a card in no synergy group, a quote
   that isn't in the card's text in `data/`, or a `main_resource` card
   that isn't in the deck.
8. Reply with everything listed under "What every deck request delivers".

## Hidden-synergy search

Do this before choosing the 60. A card can fit the main attacker without
belonging to the deck's stated plan (for example a Toxtricity that feeds a
poison deck's Darkrai Energy and damage counters). Build the plan from the
attacker's text, not only from the request's theme.

1. Read the main attacker's text and list its **inputs**: Energy count and
   type, damage counters on the Bench, hand size, Bench size, Special
   Conditions it needs, cards in the discard pile. Note the attacker's own type.
2. For each input, search `data/` for cards that **produce** it. Use a short
   script that matches effect text (for example "attach", "Energy", "damage
   counters", "Benched"). Do not rely on memory. Include Pokémon Abilities and
   attacks, not only Trainers.
3. Filter to the attacker's type first, since same-type Pokémon often
   synergize. Then widen to Colorless Pokémon and Trainers.
4. Write one line per hit: what it adds, what it costs (Bench slot, HP, a
   Stage 1 setup, extra Prizes, damage to your own Pokémon), and which card it
   competes with.
5. Put the best 2-3 hits in the deck or in `rejected`, each with a reason. A
   strong card that fits the attacker but not the main plan still gets judged.
6. If the simulator cannot play the card (for example an Ability), say so.
   Count it as an out or add a manual check, and state the assumption next to
   the result. Also report what the card cost in the other checks.

## What every deck request delivers

Do all of this for every deck request, even when the request doesn't ask:

1. **The deck file**, saved to `decks/<deck-name>.json` in the format below.
   Use a short lowercase name with hyphens, based on the main attacker
   (for example `decks/dragapult.json`). If that file already exists, add a
   number (`decks/dragapult-2.json`) instead of overwriting it.
2. **A passing check.** `check_deck.py` must report PASS. Show its final output.
3. **The role of every card**: one specific line per card saying what job it
   does in this deck and why this many copies.
4. **The synergies**: first the main resource (the formula and every card
   that changes it), then each group of cards that work together. Quote the
   relevant card text from `data/` word for word (keep each quote short, just
   the part that matters, and use "..." to skip words) and explain exactly how
   the cards interact during a game, with numbers.
5. **3 rejected cards**: the 3 strongest cards you considered but left out,
   and why each one lost its place.

In the reply, show the decklist grouped as Pokémon, Trainers and Energy with
counts, then the strategy, the synergies and the rejected cards.

## Output format

Save decks as JSON:

```json
{
  "deck_name": "Short name for the deck",
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
  name has several versions with different text. `role` is short and specific.
- List Pokémon first, then Trainers, then Energy.
- The counts must add up to exactly 60.
- `synergies` needs at least 3 groups and `rejected` exactly 3 cards.
- `main_resource` is required. Its `cards` must all be in the deck.
- Each `card_text` entry starts with the card's exact name, then a colon,
  then the quote in double quotes. Several cards with the same text can share
  one entry: `"Boss's Orders / Prime Catcher: \"...\""`.
- Every card (except Basic Energy) appears in some synergy's `cards`, or its
  entry has `"standalone": true`.
- `example/alakazam.json` shows `main_resource` and synergies written this way.
- explain the deck in a <deck_name>.md file

## Deckbuilding principles

1. **Conditions must be met.** If a card only works when something is true
   (an Energy type attached, a Pokémon Knocked Out, behind on Prizes), make
   sure the deck makes it true often. Count the cards that help.
2. **Don't undercut the engine.** Before adding a card, check it doesn't
   stop another card from doing its job (for example, skipping an evolution
   stage whose Ability is the deck's draw engine).
3. **Count outs, not just copies.** For each key job (finding a Basic on
   turn 1, evolving, finding the attacker's Energy), count every card that can
   do it. Cards needed early or every game want 4 copies or several outs.
4. **Fewer cards, more copies.** Prefer 3–4 copies of reliable cards over many
   1-ofs. Use single copies only for situational cards and say why.
5. **Opening hand.** Play enough Basic Pokémon that the opening hand almost
   always has one, and make sure the Pokémon you'd hate to start with can
   retreat or be switched out.
6. **Limits aren't targets.** "At most 3" means up to 3 if they help, not
   as few as possible. Use the allowance when the cards are worth it.
7. **Justify every 2-Prize Pokémon.** Each Rule Box Pokémon must bring enough
   to be worth giving up 2 Prize cards.
8. **Pick the ACE SPEC last.** Compare every eligible ACE SPEC against the
   deck's biggest weakness and explain the choice.
9. **Cover every job.** Before saving, list how many cards do each job:
   search, draw, switching, recovery, gusting, Energy. A job with 0–1 cards
   needs a reason.
10. **Compare before choosing.** For each key job (draw, Pokémon search,
    gusting, switching, Energy), list the 2–3 best candidates from data/ and
    compare them across the whole game:
    - when each can be used (going first or second, early or late game),
    - how many cards or how much value it gives,
    - what it costs (discarding, Prize cards, using your Supporter for the turn),
    - how likely you are to have it when you need it.
    Pick the card that's better on more turns, not the one that wins a single
    situation. Record the comparison in the deck file under "comparisons".
      
## Consistency testing

After check_deck.py passes, test how reliably the deck sets up:

1. Add "consistency_checks" to the deck file (see
   `python3 simulate_deck.py --help` for the format). Write at least 4
   checks, covering:
   - finding the main attacker's Basic on turn 1,
   - the main attacker ready to attack by the turn the strategy needs,
   - each attacker's Energy, by the turn it is needed,
   - the condition of every conditional card (Deckbuilding principle 1).
2. List every card that can do the job as an out, including search cards,
   but only if it can really find that card in this deck.
3. Give each check a target and say why. As a rough guide: turn-1 needs
   85%+, the main setup 70%+.
4. Run: python3 simulate_deck.py decks/<deck-name>.json --games 10000
5. If a check is below target, change the deck (more copies, more outs,
   cut cards that don't help) and run both scripts again. Never lower a
   target just to pass; if one truly can't be met, keep it and explain
   the trade-off.
6. When unsure between two card choices, simulate both and keep the
   version with better odds on the most important checks.
7. Report the mulligan rate but don't aim for a fixed number: decks with
   few Basics mulligan often, and that can be a fair price.

## Example decks

`example/` holds real tournament lists in the same format as your decks.
Use them to learn what strong decks look like: how many copies of key
cards, how many Supporters and Energy, and which staples appear in many
decks. Don't copy a list. If an example uses the same main attacker as
the request, still build from the card data and explain every difference
from the example.
