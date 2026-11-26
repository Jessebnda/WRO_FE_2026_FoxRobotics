"""Restricciones del sorteo para el mapa parcial de la primera vuelta."""

from functools import lru_cache
from itertools import combinations, permutations

import numpy as np

from .wro_field import (CARDS, CARD_SINGLE_GREEN, CARD_SINGLE_RED,
                        PARKING_FORBIDDEN_SEATS, REQUIRED_CARDS, SEATS,
                        SECTIONS_CW, _valid_zones)

_COLORS = ("", "Green", "Red")
_CARD_VALUES = np.array(
    [[_COLORS.index(dict(card).get(seat, "")) for seat in SEATS] for card in CARDS],
    dtype=np.uint8,
)
_SEAT_INDEX = {seat: idx for idx, seat in enumerate(SEATS)}
_SECTION_INDEX = {sec: idx for idx, sec in enumerate(SECTIONS_CW)}


@lru_cache(maxsize=2)
def _layouts(direction):
    """Filas de cuatro IDs de carta. Los duplicados conservan su ID de sorteo."""
    legal = set()
    zones = [_valid_zones(n, direction) for n in range(1, len(CARDS) + 1)]
    # La carta única designada y la requerida son distintas de las otras dos.
    # El sorteo no descarta que una de las otras dos tenga también esos rasgos.
    for single in (CARD_SINGLE_GREEN, CARD_SINGLE_RED):
        for required in REQUIRED_CARDS:
            pool = [n for n in range(1, len(CARDS) + 1) if n not in (single, required)]
            for extra in combinations(pool, 2):
                cards = (single, required, *extra)
                values = [color for n in cards for _, color in CARDS[n - 1]]
                if len(values) < 5 or abs(values.count("Green") - values.count("Red")) > 1:
                    continue
                if any(zones[n - 1] for n in cards):
                    legal.add(tuple(sorted(n - 1 for n in cards)))
    return np.asarray([row for cards in sorted(legal) for row in permutations(cards)], dtype=np.uint8)


@lru_cache(maxsize=128)
def _possible(direction, parking, confirmed, empty):
    allowed = np.ones((len(SECTIONS_CW), len(CARDS)), dtype=bool)
    for (section, seat), color in (*confirmed, *((key, "") for key in empty)):
        allowed[_SECTION_INDEX[section]] &= _CARD_VALUES[:, _SEAT_INDEX[seat]] == _COLORS.index(color)
    park_idx = _SECTION_INDEX[parking]
    forbidden = [_SEAT_INDEX[seat] for seat in PARKING_FORBIDDEN_SEATS]
    allowed[park_idx] &= ~np.any(_CARD_VALUES[:, forbidden], axis=1)
    layouts = _layouts(direction)
    layouts = layouts[np.all(allowed[np.arange(len(SECTIONS_CW)), layouts], axis=1)]
    if not len(layouts):
        return None
    result = {}
    for idx, section in enumerate(SECTIONS_CW):
        values = _CARD_VALUES[np.unique(layouts[:, idx])]
        for col, seat in enumerate(SEATS):
            result[section, seat] = frozenset(_COLORS[v] for v in np.unique(values[:, col]) if v)
    return result


def possible_colors(direction, parking, confirmed, empty):
    """Colores con soporte en algún acomodo, o None si la visión es inconsistente."""
    known = tuple(sorted((key, val) for key, val in confirmed.items()
                         if key[0] in _SECTION_INDEX and key[1] in _SEAT_INDEX and val in _COLORS[1:]))
    absent = tuple(sorted(key for key in empty - confirmed.keys()
                          if key[0] in _SECTION_INDEX and key[1] in _SEAT_INDEX))
    return _possible(direction, parking, known, absent)
