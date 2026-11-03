# Mega Darkrai ex Poison

**Request:** the same poison deck, adjusted to the quantities that can actually be bought.

**Changes in revision 5 (this one):** Brock's Scouting removed entirely and Night Stretcher restored (1 copy). The freed slot became a 3rd Toxel. Net vs revision 4: Brock's Scouting 2 → 0, Night Stretcher 0 → 1, Toxel 2 → 3.

**Changes in revision 4:** Meowth ex removed. Brock's Scouting 3 → 2 (only one Supporter per turn). Dark Bell 3 → 2 and Night Stretcher removed to pay for Toxel ×2 and Toxtricity ×2 (Sinister Surge, `me02-067` / `me02-068`).

**Changes from the previous list:** Janine's Secret Art 4 → 2, Boss's Orders 3 → 2, Night Stretcher 2 → 1, Precious Trolley removed (too expensive). Brute Bonnet is removed (the Indonesian version needs Legacy Energy, which the deck does not run) and replaced by a 4th Pecharunt. Darkness Energy 13 → 15, and Switch 1 → 2, Dark Bell 2 → 3, Brock's Scouting 2 → 3.

## Decklist (60)

**Pokémon (21)**
- 4 Mega Darkrai ex `me05-048`
- 4 Team Rocket's Zubat `sv10-120`
- 4 Pecharunt `svp-129`
- 2 Budew `me02.5-016`
- 1 Pecharunt ex `sv06.5-039`
- 3 Toxel `me02-067`
- 2 Toxtricity `me02-068`
- 1 Shaymin `sv10-010`

**Trainers (24)**
- Supporters: 4 Lillie's Determination, 2 Janine's Secret Art, 2 Boss's Orders
- Items: 4 Poké Pad, 4 Ultra Ball, 2 Dark Bell, 1 Night Stretcher, 2 Switch
- Stadium: 3 Perilous Jungle
- No ACE SPEC (Precious Trolley is too expensive)

**Energy (15)**
- 15 Darkness Energy

## Why 15 Energy

Janine's Secret Art gives Darkrai only 1 Energy per play, and only 2 copies can be bought, so Energy has to be in your first ~10 cards. Turn-3 Abyss Eye check (20,000 games, draw-free): 13 Energy 54.6%, **15 Energy 55.2%**, 16 Energy 57.7%, 18 Energy 65.0%. 15 was chosen to avoid flooding; the 3 slots saved went to Switch, Dark Bell and Toxel. Toxtricity (below) now adds Energy on top of this.

## New cards

**Toxel ×3 + Toxtricity ×2.** Sinister Surge: "Once during your turn, you may use this Ability. Search your deck for a Basic {D} Energy card and attach it to 1 of your Benched {D} Pokémon. Then, shuffle your deck. If you attached Energy to a Pokémon in this way, place 2 damage counters on that Pokémon."
- It attaches Energy from the deck without using a hand card or the Supporter slot, so it stacks with Janine's Secret Art. With Toxtricity out on turn 2: manual attach + Janine + Surge = 3 Energy on Darkrai, a turn earlier. Two Toxtricity = 2 Surges a turn.
- The 2 damage counters land on a Benched Pokémon, which switches on Dusk Raid's +110: 220 damage with only 2 Energy.
- Limits: Toxtricity is a Stage 1 (Toxel first, so it is evolved no earlier than turn 2). The target must be a Benched {D} Pokémon (Darkrai, Zubat, Pecharunt). The counters are real damage on our side: Zubat (50 HP) survives only 2 Surges. Toxtricity has 140 HP, retreat 2 and no Switch of its own.
- Poké Pad and Ultra Ball find it. Toxel is a Basic, so mulligans fall from 8.0% to 6.2% with 3 copies.

**Budew ×2.** Itchy Pollen: "During your opponent's next turn, they can't play any Item cards from their hand."
- It costs no Energy, so it can attack on the first turn you're allowed to attack, even with no Energy in hand.
- It blocks Ultra Ball, Switch and Rare Candy for a turn, which slows the opponent's setup and stops Item switching out of poison.
- Retreat Cost 0: on the Darkrai turn it retreats for free and Darkrai comes Active.
- Limit: it uses your attack for the turn, so play it on turns when nothing else can poison.
- Two extra Basics lower the mulligan rate from 14.3% to 8.8%.

**Shaymin ×1.** Flower Curtain: "Prevent all damage done to your Benched Pokémon that don't have a Rule Box by attacks from your opponent's Pokémon."
- It protects the small poisoners (Zubat 50 HP, Pecharunt 80, Budew 30) from snipes in the example decks. Fezandipiti ex's Cruel Arrow (100 damage) appears in 5 of them.
- Limits:
  - It doesn't protect Darkrai, Pecharunt ex or the Active.
  - It stops damage, not placed damage counters, so Dragapult ex's Phantom Dive still gets through.

**Switch ×2.** Subjugating Chains moves only {D} Pokémon, so it can't move Budew or Shaymin ({G}). Switch covers that, and it covers games where Pecharunt ex is prized.

## Game plan

1. **Turn 1:** bench Basics with Ultra Ball or Poké Pad with Shaymin among them and a Toxel if you have one. Open with Zubat to poison, or with Budew to lock Items when you have no Energy.
2. **Turn 2:** evolve Toxel into Toxtricity and use Sinister Surge on the benched Darkrai, then Janine's Secret Art puts more Energy on it. Pecharunt's Poison Chain poisons the target and stops it retreating.
3. **Turn 2-3:** bring Darkrai Active with Subjugating Chains, Switch or Budew's free retreat. Abyss Eye Knocks Out the Active if it has any Special Condition.
4. **If they cure or switch out:** Boss's Orders, then Dark Bell, then Abyss Eye, all in the same turn.
5. **Damage over time:** with Pecharunt Active and Perilous Jungle in play, a poisoned non-{D} target takes 8 counters per Checkup. Dusk Raid finishes it.

## Consistency (20,000 games)

| Check | Draw-free | Target |
|---|---|---|
| Poisoner found on turn 1 | 93.5% | 85% ✅ |
| Mega Darkrai ex found on turn 1 | 71.3% | 85% ❌ |
| Poisoner + {D} Energy by turn 2 | 91.4% | 85% ✅ |
| Darkrai with 3 Energy by turn 3 (counts Toxtricity as an out) | 50.8% | 70% ❌ |
| Special Condition source by turn 3 | 94.9% | 85% ✅ |
| Way to bring Darkrai Active by turn 3 | 74.0% | 70% ✅ |
| Budew found on turn 1 | 59.3% | 50% ✅ |
| Toxel + Toxtricity by turn 3 | 67.2% | 50% ✅ |

Mulligan rate: **6.2%**.

**Accepted trade-offs:**
- Turn-1 Darkrai is 71.3%, below the 85% target. Removing Meowth ex and both Brock's Scouting took away the outs that were not Ultra Ball (86.0% before). The simulator doesn't play Lillie's Determination, which digs for Ultra Ball.
- The turn-3 Energy check is below target. Cause: only 2 Janine can be bought, and 15 Energy was chosen on request instead of 18 (65.0%). The simulator doesn't play draw cards or Sinister Surge (Toxtricity is counted as an out, which assumes its Toxel is found: 67.2%), and 4 Lillie's Determination help. Going back to 16-18 Energy is the fix if you want faster turn-3 Abyss Eye.

## Rejected cards

1. **Mega Dragalge ex.** It needs a Stage 1 and {W} Energy. With fewer Energy, a second type is even harder to fit.
2. **Brock's Scouting.** Removed at your request. It found 2 Basics or 1 Evolution, but only one Supporter can be played per turn. (Meowth ex was cut earlier for a similar reason: a one-time Supporter search for a Bench slot and 2 Prizes.)
3. **Munkidori.** It is {P}, so Chains can't move it, and its Ability needs {D} Energy that Darkrai wants.
