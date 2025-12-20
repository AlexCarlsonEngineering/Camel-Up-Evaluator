"""
Core game logic and state initialization.
"""

from typing import Dict

from config import PIECES
from models import GameState, RaceState


def make_initial_gamestate() -> GameState:
    """Initial stacks & values for both single-round and race, with modified rules."""
    values = {p: 0 for p in PIECES}
    # Starting values
    values["Red"] = 3
    values["Blue"] = 2
    values["Green"] = 1
    values["Orange"] = 1
    values["Purple"] = 1
    values["Gray"] = 15

    stacks = {
        1: ["Green", "Orange", "Purple"],   # bottom Green, then Orange, then Purple (top)
        2: ["Blue"],
        3: ["Red"],
        15: ["Gray"],
    }

    return GameState(values=values, stacks=stacks)


def make_initial_racestate() -> RaceState:
    """Create initial race state with all pieces ready for first round."""
    base = make_initial_gamestate()
    return RaceState(
        values=base.values,
        stacks=base.stacks,
        draws_used_in_round=0,
        remaining_in_round=PIECES[:],
    )


def apply_draw_core(state: GameState, piece: str, roll: int) -> Dict:
    """
    Core draw logic:
      - Applies a draw of `piece` with numeric increment `roll` to `state`.
      - `roll` may be positive (normal) or negative (Gray moving backwards).
      - Returns info about the transition (for race threshold checks).
    """
    info = {
        "piece": piece,
        "roll": roll,
        "in_stack": False,
        "old_v": None,
        "new_v": None,
        "affected": [],
        "old_val": state.values.get(piece, 0),
        "new_val": None,
    }

    # Check if the piece is in any stack
    in_stack = False
    stack_v = None
    stack_idx = None

    for v, stack_list in list(state.stacks.items()):
        if piece in stack_list:
            in_stack = True
            stack_v = v
            stack_idx = stack_list.index(piece)
            break

    if in_stack:
        info["in_stack"] = True
        info["old_v"] = stack_v
        info["old_val"] = state.values[piece]

        stack_list = state.stacks[stack_v]
        affected = stack_list[stack_idx:]
        info["affected"] = affected[:]

        # Add roll (possibly negative) to all affected pieces
        for p in affected:
            state.values[p] += roll

        # Remove affected from old stack
        remaining = stack_list[:stack_idx]
        if remaining:
            state.stacks[stack_v] = remaining
        else:
            del state.stacks[stack_v]

        # Move affected block to new stack at value (stack_v + roll)
        new_v = stack_v + roll
        state.stacks.setdefault(new_v, []).extend(affected)
        info["new_v"] = new_v
        info["new_val"] = state.values[piece]
    else:
        # Plain piece: just add its own (possibly negative) roll
        old_val = state.values[piece]
        new_val = old_val + roll
        state.values[piece] = new_val
        info["old_val"] = old_val
        info["new_val"] = new_val

    return info


def apply_draw(state: GameState, piece: str, roll: int) -> None:
    """Convenience wrapper when you don't need the extra info."""
    apply_draw_core(state, piece, roll)
