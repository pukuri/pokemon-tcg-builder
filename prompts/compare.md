# Duel two decks

Pit the two deck files supplied at the end of this prompt (after "Decks:")
against each other in simulated matches, and explain which one wins and why.

## Steps

1. Run the duel simulator on the two decks:

   ```
   python3 compare_decks.py <deck-a> <deck-b> --games 5000
   ```

   Add `--extra-per-turn 1` for a second pass that gives each deck a rough
   stand-in for its draw/search engine, and `--seed N` for repeatable results.
   The script first checks both decks are legal, then plays simplified
   head-to-head matches and prints an objective report: A's win rate vs B's,
   the win rate split by who went first, average game length, and each deck's
   mulligan rate.

2. Explain the result in plain language:
   - who wins, by what margin, and whether the margin flips depending on who
     goes first;
   - the combat math behind the win: attacker damage vs the opponent's HP,
     weakness/resistance, and the prize race;
   - what card differences explain the outcome (energy counts, attacker HP and
     damage, Basic count and mulligans).

3. Quote card text where it matters, and call out anything surprising.

4. Note where the simulator is blind (see below) and say whether a real effect
   it ignores would change the verdict, with the card that causes it.

## What the simulator models and ignores

`duel_decks.py` plays a simplified tactical game: both decks mulligan to a
Basic, draw 1 per turn, play Basics, evolve, attach 1 Basic Energy per turn,
and attack with the Active's highest-damage affordable move. Weakness (×2) and
Resistance (−30) are applied, KOs draw Prizes, and the game ends at 6 Prizes,
no Pokémon, or deck-out.

It does **not** play Trainer cards, Abilities, or Special Energy (use
`--extra-per-turn` as a draw/search stand-in), and it ignores the `+`/`×` damage
modifiers, Status conditions, retreat, switching, and Bench damage from spread
attacks. Treat the win rates as a comparison between the two lists under those
rules, not a statement about real tournament results.

## Fallback

If `compare_decks.py` is missing or errors, run each deck through
`python3 check_deck.py <deck>` to confirm it is legal, then
`python3 duel_decks.py <deck-a> <deck-b> --games 5000` manually and explain the
result yourself.

## Decks

(The two deck file paths are appended below this line.)
