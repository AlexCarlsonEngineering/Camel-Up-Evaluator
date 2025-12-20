"""
UI components and visualization helpers.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from config import COLOR_MAP, PIECES, RANK_PIECES, PRED_TIERS_ROUND, PRED_TIERS_RACE
from models import RaceState


def print_initial_game_state() -> None:
    """Display initial game state information."""
    st.markdown("### Initial Game State")
    st.write("Pieces: Red, Blue, Green, Orange, Purple, Gray")
    st.write("Starting values:")
    st.write("- Red: 3 (starts in its own stack at value 3)")
    st.write("- Blue: 2 (starts in its own stack at value 2)")
    st.write("- Green: 1")
    st.write("- Orange: 1")
    st.write("- Purple: 1")
    st.write("- Gray: 15 (starts in its own stack at value 15, can stack, moves backward when drawn)")

    st.write("Starting stacks by value:")
    st.write("- Stack value 1: [Green, Orange, Purple] (bottom Green → top Purple)")
    st.write("- Stack value 2: [Blue]")
    st.write("- Stack value 3: [Red]")
    st.write("- Stack value 15: [Gray]")

    st.info(
        "Gray is in a stack and interacts like others:\n"
        "- When drawn, Gray moves backwards by -1, -2, or -3, applying that negative value to itself and any pieces above it.\n"
        "- Pieces below Gray in a stack can still push Gray forward when they are drawn.\n"
        "- Gray is excluded from winning both single rounds and the full race."
    )


def render_board(state: RaceState) -> None:
    """Plot the board using Plotly: x-axis is position, stacked markers by height."""
    rows = []
    for v, stack in state.stacks.items():
        for h, piece in enumerate(stack):
            rows.append(
                {
                    "position": v,
                    "height": h,
                    "piece": piece,
                }
            )

    if not rows:
        st.info("No pieces on the board.")
        return

    df = pd.DataFrame(rows)
    min_pos = int(df["position"].min())
    max_pos = int(df["position"].max())
    min_x = min(1, min_pos)
    max_x = max(16, max_pos)

    fig = px.scatter(
        df,
        x="position",
        y="height",
        color="piece",
        color_discrete_map=COLOR_MAP,
        hover_name="piece",
    )
    fig.update_traces(marker=dict(size=18, line=dict(width=1, color="black")))
    fig.update_layout(
        xaxis=dict(
            dtick=1,
            range=[min_x - 0.5, max_x + 0.5],
            title="Track position",
        ),
        yaxis=dict(visible=False),
        height=400,
        margin=dict(l=10, r=10, t=30, b=10),
        legend_title_text="Piece",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_ev_table(rs: RaceState, ev: dict) -> None:
    """Render expected values table."""
    st.markdown("#### Expected values at end of current round")
    data_ev = []
    for p in PIECES:
        data_ev.append(
            {
                "Piece": p,
                "Current value": rs.values[p],
                "EV end-of-round": float(ev[p]),
            }
        )
    df_ev = pd.DataFrame(data_ev)
    st.dataframe(df_ev, use_container_width=True, hide_index=True)


def render_placement_and_prediction_table(
    first_probs: dict,
    second_probs: dict,
    prediction_ev_round: dict,
    label_suffix: str = "",
) -> None:
    """Render placement probabilities and prediction EV table."""
    st.markdown(f"#### End-of-round placement & short-term prediction EVs{label_suffix}")
    data_place = []
    for p in RANK_PIECES:
        row = {
            "Piece": p,
            f"P(1st @ end of round{label_suffix})": float(first_probs[p]),
            f"P(2nd @ end of round{label_suffix})": float(second_probs[p]),
        }
        for T in PRED_TIERS_ROUND:
            row[f"EV round bet (T={T})"] = float(prediction_ev_round[T][p])
        data_place.append(row)
    df_place = pd.DataFrame(data_place)
    st.dataframe(df_place, use_container_width=True, hide_index=True)


def render_race_win_probability_table(win_probs: dict) -> None:
    """Render race win probabilities and long-term prediction EV table."""
    st.markdown("#### Race win probabilities & long-term prediction EVs")
    data_race = []
    for p in RANK_PIECES:  # Gray is excluded from winning bets
        row = {
            "Piece": p,
            "P(win race)": win_probs.get(p, 0.0),
        }
        for T in PRED_TIERS_RACE:
            row[f"EV race bet (T={T})"] = (T + 1) * row["P(win race)"] - 1
        data_race.append(row)
    df_race = pd.DataFrame(data_race)
    st.dataframe(df_race, use_container_width=True, hide_index=True)


def render_race_loss_probability_table(loss_probs: dict) -> None:
    """Render race loss probabilities and long-term prediction EV table."""
    st.markdown("#### Race loss probabilities & long-term prediction EVs")
    data_race = []
    for p in RANK_PIECES:  # Gray is excluded from losing bets
        row = {
            "Piece": p,
            "P(lose race)": loss_probs.get(p, 0.0),
        }
        for T in PRED_TIERS_RACE:
            row[f"EV race bet (T={T})"] = (T + 1) * row["P(lose race)"] - 1
        data_race.append(row)
    df_race = pd.DataFrame(data_race)
    st.dataframe(df_race, use_container_width=True, hide_index=True)


def render_top_predictions(
    first_probs: dict,
    second_probs: dict,
    prediction_ev_round: dict,
    win_probs: dict,
    loss_probs: dict,
    pred_tiers_race: list,
    draw_ev: float | None = None,
) -> None:
    """Render top 10 expected value predictions across all bet types (plus draw)."""
    st.markdown("#### Top 10 Expected Value Predictions")

    predictions = []

    # Short-term predictions (round bets)
    if prediction_ev_round is not None:
        for p in RANK_PIECES:
            for T in prediction_ev_round:
                ev = prediction_ev_round[T][p]
                predictions.append(
                    {
                        "Piece": p,
                        "Bet Type": f"1st Place (T={T})",
                        "EV": float(ev),
                    }
                )

    # Long-term race win predictions
    for p in RANK_PIECES:
        for T in pred_tiers_race:
            ev = (T + 1) * win_probs.get(p, 0.0) - 1
            predictions.append(
                {
                    "Piece": p,
                    "Bet Type": f"Race Win (T={T})",
                    "EV": float(ev),
                }
            )

    # Long-term race loss predictions
    for p in RANK_PIECES:
        for T in pred_tiers_race:
            ev = (T + 1) * loss_probs.get(p, 0.0) - 1
            predictions.append(
                {
                    "Piece": p,
                    "Bet Type": f"Race Lose (T={T})",
                    "EV": float(ev),
                }
            )

    # Optional: include the "Draw next" action
    if draw_ev is not None:
        predictions.append(
            {
                "Piece": "Draw",
                "Bet Type": "Draw Next",
                "EV": float(draw_ev),
            }
        )

    # Sort by EV descending and take top 10
    df_predictions = pd.DataFrame(predictions)
    df_predictions = df_predictions.sort_values("EV", ascending=False).head(10)

    st.dataframe(df_predictions, use_container_width=True, hide_index=True)



def render_round_draw_status(state: RaceState, show_next_round: bool = False) -> None:
    """Render list of drawn and undrawn pieces for current or next round.
    
    Args:
        state: Current race state
        show_next_round: If True, show all pieces as undrawn (for next round preview)
    """
    st.markdown("#### Round Draw Status")
    
    # Calculate drawn and undrawn pieces
    if show_next_round:
        # Show all pieces as undrawn for next round
        drawn_pieces = []
        undrawn_pieces = PIECES[:]
    else:
        drawn_pieces = [p for p in PIECES if p not in state.remaining_in_round]
        undrawn_pieces = state.remaining_in_round[:]
    
    # Create two columns for drawn and undrawn
    col_drawn, col_undrawn = st.columns(2)
    
    with col_drawn:
        st.write("**Drawn Pieces:**")
        if drawn_pieces:
            for piece in drawn_pieces:
                st.write(f"✓ {piece}")
        else:
            st.write("*None yet*")
    
    with col_undrawn:
        st.write("**Undrawn Pieces:**")
        if undrawn_pieces:
            for piece in undrawn_pieces:
                st.write(f"○ {piece}")
        else:
            st.write("*All drawn*")
