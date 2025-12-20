"""
Race simulation and winner determination.
"""

import random
from typing import Dict, Tuple
from collections import Counter

from config import PIECES, RANK_PIECES, ROLL_VALUES, DRAWS_PER_ROUND, THRESHOLD
from models import RaceState
from game_logic import apply_draw_core


def evaluate_winner_from_draw(state: RaceState, info: Dict) -> str:
    """
    Given the info from apply_draw_core, determine if this draw produced a winner.
    Only Red,Blue,Green,Orange,Purple are eligible to win. Gray can never win.
    Returns:
      winner piece name or None.
    """
    piece = info["piece"]

    if info["in_stack"]:
        old_v = info["old_v"]
        new_v = info["new_v"]
        if old_v is not None and old_v < THRESHOLD <= new_v:
            # Stack at new_v may include Gray plus others.
            # Winner is the topmost eligible piece in that stack.
            stack_list = state.stacks[new_v]
            for p in reversed(stack_list):  # from top down
                if p in RANK_PIECES:
                    return p
    else:
        old_val = info["old_val"]
        new_val = info["new_val"]
        if piece in RANK_PIECES and old_val < THRESHOLD <= new_val:
            return piece

    return None


def evaluate_loser_from_state(state: RaceState) -> str:
    """
    Determine the loser when any piece reaches threshold.
    Loser is the piece with lowest value, or if tied, the bottom piece in the stack at that value.
    Only Red,Blue,Green,Orange,Purple are eligible to lose.
    Returns:
      loser piece name or None.
    """
    # Find the minimum value among eligible pieces
    min_val = min(state.values[p] for p in RANK_PIECES)
    
    # Find all pieces at the minimum value
    pieces_at_min = [p for p in RANK_PIECES if state.values[p] == min_val]
    
    if len(pieces_at_min) == 1:
        return pieces_at_min[0]
    
    # Tie-break: find which piece is lowest in the stack at min_val
    if min_val in state.stacks:
        stack_list = state.stacks[min_val]
        for p in stack_list:  # from bottom up
            if p in pieces_at_min:
                return p
    
    # If no pieces in stack at that value, return first piece found
    return pieces_at_min[0]


def race_draw_once(state: RaceState) -> Tuple[str, int, str]:
    """
    Perform one random draw step in the race:
      - If we've already drawn 5 this round, start a new round.
      - Sample a piece uniformly from remaining_in_round.
      - Sample a base roll in {1,2,3}:
          * Non-Gray pieces: +base_roll
          * Gray: -base_roll (moves backwards)
      - Apply to state.
      - Return (piece, actual_roll, winner_or_None).
    """
    if state.draws_used_in_round >= DRAWS_PER_ROUND or not state.remaining_in_round:
        state.draws_used_in_round = 0
        state.remaining_in_round = PIECES[:]

    piece = random.choice(state.remaining_in_round)
    state.remaining_in_round.remove(piece)
    state.draws_used_in_round += 1

    base_roll = random.choice(ROLL_VALUES)
    actual_roll = -base_roll if piece == "Gray" else base_roll
    info = apply_draw_core(state, piece, actual_roll)
    winner = evaluate_winner_from_draw(state, info)
    return piece, actual_roll, winner


def simulate_race_from_state(
    base_state: RaceState,
    n_games: int = 5000,
) -> Tuple[Dict[str, float], Dict[str, float], float]:
    """
    Monte Carlo: estimate win and loss probabilities starting from `base_state`.
    Only Red,Blue,Green,Orange,Purple can win or lose; Gray will not be reported.
    
    Returns:
      - win_probs: dict of win probabilities for each piece
      - loss_probs: dict of loss probabilities for each piece
      - avg_draws: average draws to complete race
    """
    win_counts = Counter()
    loss_counts = Counter()
    draws_sum = 0

    for _ in range(n_games):
        state = base_state.clone()
        draws = 0

        while True:
            piece, actual_roll, winner = race_draw_once(state)
            draws += 1

            if winner is not None:
                win_counts[winner] += 1
                # Find the loser at the end of the race
                loser = evaluate_loser_from_state(state)
                if loser:
                    loss_counts[loser] += 1
                draws_sum += draws
                break

    # Ensure all pieces are present; Gray's probs will be 0
    win_probs = {p: win_counts[p] / n_games for p in PIECES}
    loss_probs = {p: loss_counts[p] / n_games for p in PIECES}
    avg_draws = draws_sum / n_games if n_games > 0 else 0
    return win_probs, loss_probs, avg_draws
