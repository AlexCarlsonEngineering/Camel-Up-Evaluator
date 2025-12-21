"""
Game configuration and constants.
"""

# Piece names
PIECES = ["Red", "Blue", "Green", "Orange", "Purple", "Gray"]
RANK_PIECES = ["Red", "Blue", "Green", "Orange", "Purple"]  # eligible for placement & winning

# Game mechanics
ROLL_VALUES = [1, 2, 3]
THRESHOLD = 16  # Race-to-N threshold
DRAWS_PER_ROUND = 5

# Prediction tiers
# Single-round prediction tiers: 1st payout, 2nd = +1, others = -1
PRED_TIERS_ROUND = [5, 3, 2]

# Race prediction tiers: 1st payout, non-win = -1
PRED_TIERS_RACE = [8, 5, 3]

# Colors for plotting
COLOR_MAP = {
    "Red": "#e41a1c",      # red
    "Blue": "#377eb8",     # blue
    "Green": "#4daf4a",    # green
    "Orange": "#ff7f00",   # orange
    "Purple": "#984ea3",   # purple
    "Gray": "#999999",     # gray
}

# UI Settings
MONTE_CARLO_SIMULATIONS = 500
MONTE_CARLO_SIMULATIONS_DRAW = 100  # sims per branch when valuing a draw action
