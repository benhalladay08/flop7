from dataclasses import dataclass


@dataclass
class Card:
    """Base dataclass for all Flip 7 cards."""
    name: str
    abbrv: str
    num_in_deck: int
    points: int
    bustable: bool
    score_priority: int = 0  # Higher means applied later in the scoring process
    score_modifier: callable | None = None


# Number Cards (0-12)
ZERO = Card(name="0", abbrv="0", num_in_deck=1, points=0, bustable=True)
ONE = Card(name="1", abbrv="1", num_in_deck=1, points=1, bustable=True)
TWO = Card(name="2", abbrv="2", num_in_deck=2, points=2, bustable=True)
THREE = Card(name="3", abbrv="3", num_in_deck=3, points=3, bustable=True)
FOUR = Card(name="4", abbrv="4", num_in_deck=4, points=4, bustable=True)
FIVE = Card(name="5", abbrv="5", num_in_deck=5, points=5, bustable=True)
SIX = Card(name="6", abbrv="6", num_in_deck=6, points=6, bustable=True)
SEVEN = Card(name="7", abbrv="7", num_in_deck=7, points=7, bustable=True)
EIGHT = Card(name="8", abbrv="8", num_in_deck=8, points=8, bustable=True)
NINE = Card(name="9", abbrv="9", num_in_deck=9, points=9, bustable=True)
TEN = Card(name="10", abbrv="10", num_in_deck=10, points=10, bustable=True)
ELEVEN = Card(name="11", abbrv="11", num_in_deck=11, points=11, bustable=True)
TWELVE = Card(name="12", abbrv="12", num_in_deck=12, points=12, bustable=True)

# Action Cards
FLIP_THREE = Card(name="Flip Three", abbrv="F", num_in_deck=3, points=0, bustable=False)
FREEZE = Card(name="Freeze", abbrv="Z", num_in_deck=3, points=0, bustable=False)
SECOND_CHANCE = Card(name="Second Chance", abbrv="C", num_in_deck=3, points=0, bustable=False)

# Score Modifier Cards
PLUS_TWO = Card(name="+2", abbrv="+2", num_in_deck=1, points=2, bustable=False, score_priority=2, score_modifier=lambda score: score + 2)
PLUS_FOUR = Card(name="+4", abbrv="+4", num_in_deck=1, points=4, bustable=False, score_priority=2, score_modifier=lambda score: score + 4)
PLUS_SIX = Card(name="+6", abbrv="+6", num_in_deck=1, points=6, bustable=False, score_priority=2, score_modifier=lambda score: score + 6)
PLUS_EIGHT = Card(name="+8", abbrv="+8", num_in_deck=1, points=8, bustable=False, score_priority=2, score_modifier=lambda score: score + 8)
PLUS_TEN = Card(name="+10", abbrv="+10", num_in_deck=1, points=10, bustable=False, score_priority=2, score_modifier=lambda score: score + 10)
TIMES_TWO = Card(name="x2", abbrv="X", num_in_deck=1, points=0, bustable=False, score_priority=1, score_modifier=lambda score: score * 2)

# List of all card types
ALL_CARDS = [
    ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT, NINE, TEN, ELEVEN, TWELVE,
    FLIP_THREE, FREEZE, SECOND_CHANCE,
    PLUS_TWO, PLUS_FOUR, PLUS_SIX, PLUS_EIGHT, PLUS_TEN, TIMES_TWO
]

# Map abbreviations to card objects for easy lookup
CARD_MAP = {card.abbrv: card for card in ALL_CARDS}

# Total cards in deck: 79 (number cards) + 9 (action, 3×3) + 6 (modifiers, 6×1) = 94
