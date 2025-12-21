"""
Main Streamlit application.
"""

import streamlit as st

from config import (
    PIECES,
    RANK_PIECES,
    DRAWS_PER_ROUND,
    MONTE_CARLO_SIMULATIONS,
    MONTE_CARLO_SIMULATIONS_DRAW,
    PRED_TIERS_ROUND,
    PRED_TIERS_RACE,
)
from models import RaceState
from game_logic import make_initial_racestate
from simulation import race_draw_once, simulate_race_from_state
from analytics import compute_end_of_round_stats_from_racestate, compute_draw_action_ev

from ui import (
    print_initial_game_state,
    render_board,
    render_ev_table,
    render_placement_and_prediction_table,
    render_race_win_probability_table,
    render_race_loss_probability_table,
    render_round_draw_status,
    render_top_predictions,
)


def run_app() -> None:
    """Run the main Streamlit application."""
    st.set_page_config(page_title="Camel Stack Race Simulator", layout="wide")
    st.title("Camel Stack Race Simulator")

    # Initialize session state
    if "race_state" not in st.session_state:
        st.session_state["race_state"] = make_initial_racestate()
        st.session_state["num_draws"] = 0
        st.session_state["last_draw"] = None
        st.session_state["race_winner"] = None

    rs: RaceState = st.session_state["race_state"]

    with st.expander("Game rules & starting configuration", expanded=False):
        print_initial_game_state()

    # Pre-compute draw EV for display next to button
    race_winner = st.session_state["race_winner"]
    
    # Compute basic stats needed for draw EV
    ev_round, first_probs, second_probs, prediction_ev_round = compute_end_of_round_stats_from_racestate(rs)
    sims = MONTE_CARLO_SIMULATIONS
    if race_winner is not None:
        win_probs = {p: 0.0 for p in PIECES}
        win_probs[race_winner] = 1.0
        loss_probs = {p: 0.0 for p in PIECES}
    else:
        win_probs, loss_probs, _ = simulate_race_from_state(rs, n_games=sims)
    
    # Check if current round is complete early to determine which state to use for draw EV
    round_complete = rs.draws_used_in_round >= DRAWS_PER_ROUND or not rs.remaining_in_round
    
    # Pre-compute next round state and stats if round is complete
    next_round_state = None
    ev_next = None
    first_probs_next = None
    second_probs_next = None
    prediction_ev_next = None
    
    if round_complete:
        next_round_state = RaceState(
            values=rs.values.copy(),
            stacks={v: lst[:] for v, lst in rs.stacks.items()},
            draws_used_in_round=0,
            remaining_in_round=PIECES[:],
        )
        ev_next, first_probs_next, second_probs_next, prediction_ev_next = compute_end_of_round_stats_from_racestate(
            next_round_state
        )
    
    # Compute draw EV if race is not already won
    draw_ev_display = None
    if race_winner is None:
        if round_complete:
            # For next round, use pre-computed state
            draw_ev_display = compute_draw_action_ev(
                next_round_state,
                first_probs_next,
                second_probs_next,
                prediction_ev_next,
                win_probs,
                loss_probs,
                PRED_TIERS_RACE,
                n_race_sims_per_next=MONTE_CARLO_SIMULATIONS_DRAW,
            )
        else:
            # For current round
            draw_ev_display = compute_draw_action_ev(
                rs,
                first_probs,
                second_probs,
                prediction_ev_round,
                win_probs,
                loss_probs,
                PRED_TIERS_RACE,
                n_race_sims_per_next=MONTE_CARLO_SIMULATIONS_DRAW,
            )

    # Controls
    col_draw, col_draw_ev, col_reset = st.columns([1, 1, 1])

    with col_draw:
        if st.button("🎲 Draw next"):
            if st.session_state["race_winner"] is None:
                piece, roll, winner = race_draw_once(rs)
                st.session_state["num_draws"] += 1
                st.session_state["last_draw"] = (piece, roll, winner)
                st.session_state["race_state"] = rs
                if winner is not None:
                    st.session_state["race_winner"] = winner
            else:
                st.warning(f"Race is already over! Winner: {st.session_state['race_winner']}")

    with col_draw_ev:
        if draw_ev_display is not None:
            st.metric("Draw EV", f"{draw_ev_display:.3f}")
        else:
            st.metric("Draw EV", "—", help="Race already won")

    with col_reset:
        if st.button("🔁 Reset game"):
            st.session_state["race_state"] = make_initial_racestate()
            st.session_state["num_draws"] = 0
            st.session_state["last_draw"] = None
            st.session_state["race_winner"] = None
            rs = st.session_state["race_state"]

    # Last draw info
    if st.session_state["last_draw"] is not None:
        piece, roll, winner = st.session_state["last_draw"]
        msg = f"Last draw: **{piece}** with roll **{roll:+d}**"
        if winner is not None:
            msg += f" → 🎉 **Winner: {winner}**"
        st.markdown(msg)

    # Layout: board + dashboards
    board_col, metrics_col = st.columns([1.2, 1.8])

    with board_col:
        st.subheader("Board")
        render_board(rs)
        render_round_draw_status(rs, show_next_round=(rs.draws_used_in_round >= DRAWS_PER_ROUND or not rs.remaining_in_round))
        st.write("Current values:")
        st.json(rs.values)

    with metrics_col:
        st.subheader("Dashboards")

        # Check if current round is complete
        round_complete = rs.draws_used_in_round >= DRAWS_PER_ROUND or not rs.remaining_in_round

        if round_complete and race_winner is None:
            # Round is complete, show next round odds
            st.info(f"✅ Round complete! ({DRAWS_PER_ROUND}/{DRAWS_PER_ROUND} draws)")
            st.markdown("---")
            st.markdown("### Odds for Next Round")

            # next_round_state and stats already computed above for draw EV display
            # Defensive: if they weren't computed earlier (possible rerun timing), compute them now
            if next_round_state is None or first_probs_next is None:
                next_round_state = RaceState(
                    values=rs.values.copy(),
                    stacks={v: lst[:] for v, lst in rs.stacks.items()},
                    draws_used_in_round=0,
                    remaining_in_round=PIECES[:],
                )
                ev_next, first_probs_next, second_probs_next, prediction_ev_next = compute_end_of_round_stats_from_racestate(
                    next_round_state
                )

            # ---- Top 10 predictions ----
            render_top_predictions(
                first_probs_next,
                second_probs_next,
                prediction_ev_next,
                win_probs,
                loss_probs,
                PRED_TIERS_RACE,
                draw_ev=draw_ev_display,
            )

            # ---- Short-term placement & prediction EV for next round ----
            render_placement_and_prediction_table(
                first_probs_next,
                second_probs_next,
                prediction_ev_next,
                label_suffix=" (next round)",
            )

            # ---- Race win probabilities & long-term prediction EV ----
            render_race_win_probability_table(win_probs)

            # ---- Race loss probabilities & long-term prediction EV ----
            render_race_loss_probability_table(loss_probs)

            # ---- Next round EV table (at bottom) ----
            st.markdown("#### Expected values at end of next round")
            import pandas as pd
            data_ev = []
            for p in PIECES:
                data_ev.append(
                    {
                        "Piece": p,
                        "Current value": rs.values[p],
                        "EV end-of-next-round": float(ev_next[p]),
                    }
                )
            df_ev = pd.DataFrame(data_ev)
            st.dataframe(df_ev, width="stretch", hide_index=True)

            st.caption(f"Next round stats estimated via Monte Carlo with {sims} simulations from current state.")
        else:
            # Round is in progress, show current round odds

            # ---- Top 10 predictions ----
            render_top_predictions(
                first_probs,
                second_probs,
                prediction_ev_round,
                win_probs,
                loss_probs,
                PRED_TIERS_RACE,
                draw_ev=draw_ev_display,
            )


            # ---- Short-term placement & prediction EV ----
            render_placement_and_prediction_table(first_probs, second_probs, prediction_ev_round)

            # ---- Race win probabilities & long-term prediction EV ----
            render_race_win_probability_table(win_probs)

            # ---- Race loss probabilities & long-term prediction EV ----
            render_race_loss_probability_table(loss_probs)

            # ---- Expected values (at bottom) ----
            render_ev_table(rs, ev_round)

            st.caption(f"Race stats estimated via Monte Carlo with {sims} simulations from current state.")


if __name__ == "__main__":
    run_app()
