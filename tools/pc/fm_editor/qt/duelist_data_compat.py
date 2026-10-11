"""Retail duelist-rule constants for the PySide compatibility layer."""

# How each duelist plays: game/ai_opponent_data.c gDuel_aOpponentData, nine
# bytes a duelist (notes/more-duelists.md "The nine bytes").
AI_ROWS = [
    (5, 20, 10, 1, 1, 0, 0, 25, 50), (5, 20, 10, 1, 1, 0, 0, 25, 50), (5, 30, 20, 1, 2, 0, 0, 25, 25),
    (5, 10, 5, 2, 1, 0, 0, 25, 75), (5, 20, 10, 2, 2, 1, 1, 25, 50), (5, 30, 20, 3, 1, 1, 1, 25, 75),
    (5, 10, 5, 1, 3, 1, 1, 25, 25), (10, 20, 10, 3, 3, 2, 2, 50, 50), (20, 20, 10, 2, 2, 3, 3, 75, 50),
    (8, 10, 5, 3, 2, 2, 2, 25, 75), (8, 10, 5, 2, 3, 2, 2, 25, 50), (10, 20, 10, 3, 3, 2, 2, 75, 25),
    (12, 20, 10, 2, 2, 2, 2, 50, 50), (12, 30, 20, 2, 2, 2, 2, 50, 25), (14, 20, 10, 3, 3, 3, 3, 75, 25),
    (16, 20, 10, 3, 3, 3, 3, 75, 0), (16, 20, 10, 3, 3, 3, 3, 75, 25), (16, 20, 10, 3, 3, 3, 3, 75, 50),
    (12, 10, 5, 1, 1, 1, 1, 25, 75), (10, 10, 5, 1, 2, 1, 1, 25, 75), (10, 30, 20, 2, 1, 1, 1, 25, 25),
    (14, 10, 5, 2, 2, 2, 2, 50, 50), (16, 20, 10, 2, 3, 3, 3, 50, 25), (14, 10, 5, 2, 2, 2, 2, 50, 50),
    (16, 20, 10, 3, 3, 3, 3, 50, 25), (14, 10, 5, 3, 2, 2, 2, 50, 50), (16, 20, 10, 3, 3, 3, 3, 50, 25),
    (14, 10, 5, 2, 2, 2, 2, 50, 50), (16, 20, 10, 2, 3, 3, 3, 50, 25), (14, 10, 5, 3, 2, 2, 2, 50, 50),
    (16, 20, 10, 3, 3, 3, 3, 50, 25), (16, 20, 10, 3, 3, 3, 3, 75, 75), (18, 10, 5, 1, 2, 3, 3, 50, 25),
    (20, 10, 5, 2, 2, 3, 3, 50, 50), (20, 30, 20, 2, 1, 3, 3, 50, 75), (20, 20, 10, 2, 2, 3, 3, 75, 0),
    (20, 20, 10, 2, 2, 4, 4, 75, 0), (20, 20, 10, 2, 2, 5, 5, 50, 0), (20, 10, 5, 2, 2, 5, 5, 75, 0),
    (15, 20, 10, 3, 3, 5, 5, 50, 25)]
AI_FIELDS = 9                       # DUELIST_AI_FIELDS
AI_SEARCH = (5, 20)                 # byte 0, held there by settle_ai
AI_FIELD_LABELS = ("Deck search", "LP threshold ÷100", "Low-deck threshold", "Fusion depth", "Second depth",
                   "Byte 5 (unread)", "Byte 6 (unread)", "Duster / hold %", "Blind attack %")
# The six the AI script lets read face-down cards (duelists.c Duelists_HidesFaceDown).
SIGHT_DUELISTS = (8, 15, 35, 36, 37, 38)    # Heishin, Pegasus, Heishin 2nd, Seto 3rd, DarkNite, Nitemare

# How a duel is scored (tables.c rank_rule_names), each rule five
# [threshold, change] pairs; the disc's rows, the same for every duelist
# (notes/research/the-game.md, tests/pc/rank_test.c). The last threshold is
# "and above": the game makes it 32767 whatever is written.
RANK_RULES = ("turns", "effective attacks", "defensive wins", "face-down plays", "pure magic",
              "traps triggered", "cards used", "remaining lp", "initiate fusion", "equip magic")
RANK_STEPS = 5
RANK_ABOVE = 0x7FFF
RANK_RETAIL = (
    ((5, 12), (9, 8), (29, 0), (33, -8), (RANK_ABOVE, -12)),
    ((2, 4), (4, 2), (10, 0), (20, -2), (RANK_ABOVE, -4)),
    ((2, 0), (6, -10), (10, -20), (15, -30), (RANK_ABOVE, -40)),
    ((1, 0), (11, -2), (21, -4), (31, -6), (RANK_ABOVE, -8)),
    ((1, 2), (4, -4), (7, -8), (10, -12), (RANK_ABOVE, -16)),
    ((1, 2), (3, -8), (5, -16), (7, -24), (RANK_ABOVE, -32)),
    ((9, 15), (13, 12), (33, 0), (37, -5), (RANK_ABOVE, -7)),
    ((100, -7), (1000, -5), (7000, 0), (8000, 4), (RANK_ABOVE, 6)),
    ((1, 4), (5, 0), (10, -4), (15, -8), (RANK_ABOVE, -12)),
    ((1, 4), (5, 0), (10, -4), (15, -8), (RANK_ABOVE, -12)))
# "unlock": {"story": 0x6E0 + n} is "duelist n is unlocked in Free Duel".
STORY_FREE_DUEL = 0x6E0

__all__ = ("AI_ROWS", "AI_FIELDS", "AI_SEARCH", "AI_FIELD_LABELS",
           "SIGHT_DUELISTS", "RANK_RULES", "RANK_STEPS", "RANK_ABOVE",
           "RANK_RETAIL", "STORY_FREE_DUEL")
