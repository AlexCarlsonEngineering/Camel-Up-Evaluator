# Camel Up Evaluator
Probablistic evaluation of game states for the board game Camel Up

## Files

- `app.py`: Streamlit UI entrypoint that runs the interactive simulator and ties together UI and analytics.
- `ui.py`: Streamlit UI components and Plotly visualization helpers used by `app.py`.
- `analytics.py`: Exact enumeration and probability logic for end-of-round metrics and prediction EV calculations.
- `simulation.py`: Monte Carlo simulation routines to estimate race outcomes from a given state.
- `game_logic.py`: Deterministic rules for applying a draw (piece movement, stacking, and state transitions).
- `models.py`: Data model classes (`GameState`, `RaceState`) and cloning utilities.
- `config.py`: Game constants and UI/runtime configuration (pieces, tiers, thresholds, colors, simulation counts).
- `README.md`: This project overview and file index.

## Quick start

1. Create and activate a Python virtual environment (Python 3.13 recommended).
2. Install dependencies (e.g. `streamlit`, `pandas`, `plotly`).
3. Run the app: `streamlit run app.py`.

