# Drop tables from the supplied Mod 15 disc

Open this folder as a mod in FM Editor, or load it as a mod in the PC port.
The mod contains only drop-table changes relative to this workspace's retail game.
It does not change decks, cards, scripts, or the number of cards awarded per win.

`drops.csv` contains every nonzero drop weight in all 120 pools: 39 named
opponents plus the unused slot, with POW, B/C/D and TEC pools for each.
Card IDs are the disc's 1-based IDs. Opponent labels are the editor's retail
slot names. Both disc and retail card names are included for mapping.
Each pool totals 2048; probability per draw is weight / 2048.
117 pools differ from retail. No normalization or inferred decoding was needed.
The saved mod was reopened and all 120 pools compared exactly with the source.

`extraction-report.json` records source fingerprints and verification results.
The supplied filename is not independent confirmation of the mod's release:
these are verified tables from this disc, not a comparison with TEA Online.
The disc also changes 39 deck pools and 28 card records; those are not included.
