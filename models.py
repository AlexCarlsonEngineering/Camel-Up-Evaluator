"""
Data models and state representations.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from config import PIECES


@dataclass
class GameState:
    """State for a single-round or generic within-round view."""
    values: Dict[str, int]              # piece -> value
    stacks: Dict[int, List[str]]        # stack_value -> [bottom,...,top]

    def clone(self) -> "GameState":
        return GameState(
            values=self.values.copy(),
            stacks={v: lst[:] for v, lst in self.stacks.items()},
        )


@dataclass
class RaceState(GameState):
    """Extends GameState with per-round info for race-to-THRESHOLD."""
    draws_used_in_round: int = 0
    remaining_in_round: List[str] = field(default_factory=list)

    def clone(self) -> "RaceState":
        return RaceState(
            values=self.values.copy(),
            stacks={v: lst[:] for v, lst in self.stacks.items()},
            draws_used_in_round=self.draws_used_in_round,
            remaining_in_round=self.remaining_in_round[:],
        )
