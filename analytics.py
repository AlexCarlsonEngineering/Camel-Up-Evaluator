"""
Game analytics: ranking, statistics, and probability calculations.
"""

from typing import Dict, List, Tuple
from itertools import permutations, product
from fractions import Fraction
from collections import defaultdict

from config import (
    PIECES,
    RANK_PIECES,
    ROLL_VALUES,
    DRAWS_PER_ROUND,
    PRED_TIERS_ROUND,
    PRED_TIERS_RACE,
    THRESHOLD,
)
from models import GameState, RaceState
from game_logic import apply_draw
from simulation import simulate_race_from_state, evaluate_loser_from_state



def rank_pieces_single_round(state: GameState) -> List[str]:
    """
    Rank Red, Blue, Green, Orange, Purple from best to worst:
      1) Higher value,
      2) Tie-break by who is higher on the stack at that value.
    Gray is ignored for ranking.
    """
    info = {}
    for p in RANK_PIECES:
        v = state.values[p]

        # Find stack whose key is v and contains p
        stack_list = None
        for sv, lst in state.stacks.items():
            if sv == v and p in lst:
                stack_list = lst
                break

        if stack_list is None:
            height = -1
        else:
            height = stack_list.index(p)

        info[p] = (v, height)

    ranked = sorted(
        RANK_PIECES,
        key=lambda p: (info[p][0], info[p][1]),
        reverse=True,
    )
    return ranked


def compute_end_of_round_stats_from_racestate(
    rs: RaceState,
) -> Tuple[Dict[str, Fraction], Dict[str, Fraction], Dict[str, Fraction], Dict[int, Dict[str, Fraction]]]:
    """
    Exact enumeration of all ways to finish the *current* round from the given RaceState.
    Returns:
      - ev: expected piece values at end of this round (Fractions) for all PIECES
      - first_probs: P(1st) for Red,Blue,Green,Orange,Purple
      - second_probs: P(2nd) for Red,Blue,Green,Orange,Purple
      - prediction_ev_round: EV of short-term predictions per tier for Red,Blue,Green,Orange,Purple
    """
    draws_done = rs.draws_used_in_round
    draws_left = DRAWS_PER_ROUND - draws_done

    base_state = GameState(
        values=rs.values.copy(),
        stacks={v: lst[:] for v, lst in rs.stacks.items()},
    )

    total_worlds = 0
    value_sums = defaultdict(int)
    first_counts = {p: 0 for p in RANK_PIECES}
    second_counts = {p: 0 for p in RANK_PIECES}

    if draws_left <= 0:
        # Round is already complete: deterministic outcome
        total_worlds = 1
        for p in PIECES:
            value_sums[p] = base_state.values[p]

        ranking = rank_pieces_single_round(base_state)
        if len(ranking) >= 2:
            first_counts[ranking[0]] = 1
            second_counts[ranking[1]] = 1
    else:
        remaining_pieces = rs.remaining_in_round[:]

        # Enumerate all sequences of which pieces are drawn (order matters) and roll sequences
        for draws_seq in permutations(remaining_pieces, draws_left):
            for base_rolls in product(ROLL_VALUES, repeat=draws_left):
                state = base_state.clone()
                for piece, base_r in zip(draws_seq, base_rolls):
                    # Non-Gray pieces move forward; Gray moves backward
                    actual_roll = -base_r if piece == "Gray" else base_r
                    apply_draw(state, piece, actual_roll)

                for p in PIECES:
                    value_sums[p] += state.values[p]

                ranking = rank_pieces_single_round(state)
                if len(ranking) >= 2:
                    first_counts[ranking[0]] += 1
                    second_counts[ranking[1]] += 1

                total_worlds += 1

    # Convert to Fractions
    ev = {p: Fraction(value_sums[p], total_worlds) for p in PIECES}
    first_probs = {
        p: Fraction(first_counts[p], total_worlds) for p in RANK_PIECES
    }
    second_probs = {
        p: Fraction(second_counts[p], total_worlds) for p in RANK_PIECES
    }

    # Prediction EVs for the single-round model
    # score_T(p) = T*P1 + 1*P2 - 1*(1 - P1 - P2)
    #             = (T+1)*P1 + 2*P2 - 1
    prediction_ev_round: Dict[int, Dict[str, Fraction]] = {T: {} for T in PRED_TIERS_ROUND}
    for p in RANK_PIECES:
        p1 = first_probs[p]
        p2 = second_probs[p]
        for T in PRED_TIERS_ROUND:
            prediction_ev_round[T][p] = (T + 1) * p1 + 2 * p2 - 1

    return ev, first_probs, second_probs, prediction_ev_round

def compute_best_prediction_ev_from_metrics(
    first_probs: Dict[str, Fraction],
    second_probs: Dict[str, Fraction],
    prediction_ev_round: Dict[int, Dict[str, Fraction]],
    win_probs: Dict[str, float],
    loss_probs: Dict[str, float],
    pred_tiers_race: List[int],
) -> float:
    """Return the maximum EV among all 'plays' (bets) given the current metrics.

    Mirrors the EV formulas used in the UI's render_top_predictions:
      * single-round bets from prediction_ev_round,
      * long-term race win bets, and
      * long-term race loss bets.
    """
    best_ev = float("-inf")

    # Short-term (round) bets
    for p in RANK_PIECES:
        for T in prediction_ev_round:
            ev = float(prediction_ev_round[T][p])
            if ev > best_ev:
                best_ev = ev

    # Long-term race win bets
    for p in RANK_PIECES:
        for T in pred_tiers_race:
            ev = (T + 1) * win_probs.get(p, 0.0) - 1
            if ev > best_ev:
                best_ev = ev

    # Long-term race loss bets
    for p in RANK_PIECES:
        for T in pred_tiers_race:
            ev = (T + 1) * loss_probs.get(p, 0.0) - 1
            if ev > best_ev:
                best_ev = ev

    if best_ev == float("-inf"):
        return 0.0
    return best_ev


def evaluate_winner_from_state(state: RaceState) -> str | None:
    """Determine the front-runner in the race for the given state.

    Winner is the piece with highest value; ties are broken by stack height
    using rank_pieces_single_round. Only Red/Blue/Green/Orange/Purple are
    eligible as race winners.
    """
    ranked = rank_pieces_single_round(state)
    return ranked[0] if ranked else None


def enumerate_next_draw_states(base_state: RaceState) -> List[Tuple[float, RaceState]]:
    """Enumerate all possible next states after a *single* draw.

    Mirrors the random behaviour of race_draw_once but returns all
    (probability, next_state) pairs deterministically.
    """
    # Decide whether the next draw starts a fresh round
    if base_state.draws_used_in_round >= DRAWS_PER_ROUND or not base_state.remaining_in_round:
        candidate_pieces = PIECES[:]  # fresh round: all pieces available

        def make_clone() -> RaceState:
            s = base_state.clone()
            s.draws_used_in_round = 0
            s.remaining_in_round = PIECES[:]
            return s
    else:
        candidate_pieces = base_state.remaining_in_round[:]

        def make_clone() -> RaceState:
            return base_state.clone()

    n_pieces = len(candidate_pieces)
    n_rolls = len(ROLL_VALUES)
    if n_pieces == 0 or n_rolls == 0:
        return []

    p_each = 1.0 / (n_pieces * n_rolls)
    outcomes: List[Tuple[float, RaceState]] = []

    for piece in candidate_pieces:
        for base_roll in ROLL_VALUES:
            s1 = make_clone()
            if piece not in s1.remaining_in_round:
                # Defensive guard; shouldn't happen if logic above is correct.
                continue

            s1.remaining_in_round.remove(piece)
            s1.draws_used_in_round += 1

            actual_roll = -base_roll if piece == "Gray" else base_roll
            apply_draw(s1, piece, actual_roll)

            outcomes.append((p_each, s1))

    return outcomes


def compute_draw_action_ev(
    base_state: RaceState,
    first_probs: Dict[str, Fraction],
    second_probs: Dict[str, Fraction],
    prediction_ev_round: Dict[int, Dict[str, Fraction]],
    win_probs: Dict[str, float],
    loss_probs: Dict[str, float],
    pred_tiers_race: List[int],
    n_race_sims_per_next: int = 2000,
) -> float:
    """Expected value of the 'Draw next' action.

    Definition:
        EV(draw) = 1 - E[ max_play_EV(next_state) - max_play_EV(current_state) ].

    Intuition:
      * 1 is the base payoff for drawing.
      * We subtract the average increase in the best available play's EV
        caused by the extra information from the draw.
    """
    # Best play EV in the current state
    current_best = compute_best_prediction_ev_from_metrics(
        first_probs,
        second_probs,
        prediction_ev_round,
        win_probs,
        loss_probs,
        pred_tiers_race,
    )

    # Enumerate all possible next states after one draw
    outcomes = enumerate_next_draw_states(base_state)
    if not outcomes:
        # No draws possible: just return baseline
        return 1.0

    expected_best_next = 0.0

    for prob, next_state in outcomes:
        # If the race is already decided after this draw, build
        # deterministic win/loss probabilities; otherwise simulate.
        max_val = max(next_state.values[p] for p in RANK_PIECES)
        if max_val >= THRESHOLD:
            winner = evaluate_winner_from_state(next_state)
            loser = evaluate_loser_from_state(next_state)
            win_probs_next = {p: 0.0 for p in PIECES}
            loss_probs_next = {p: 0.0 for p in PIECES}
            if winner is not None:
                win_probs_next[winner] = 1.0
            if loser is not None:
                loss_probs_next[loser] = 1.0
        else:
            win_probs_next, loss_probs_next, _ = simulate_race_from_state(
                next_state, n_games=n_race_sims_per_next
            )

        # Round-level stats from this new state
        _, first_next, second_next, prediction_ev_round_next = compute_end_of_round_stats_from_racestate(
            next_state
        )

        best_next = compute_best_prediction_ev_from_metrics(
            first_next,
            second_next,
            prediction_ev_round_next,
            win_probs_next,
            loss_probs_next,
            pred_tiers_race,
        )

        expected_best_next += prob * best_next

    avg_increase = expected_best_next - current_best
    draw_ev = 1.0 - avg_increase
    return draw_ev
