# config.py

from pathlib import Path


DEFAULT_INPUT_DIR = "employee_case_analysis_outputs"

HISTORICAL_FILE = "historical_combo.csv"
RECOMMENDATIONS_FILE = "recency_recommendations.csv"


# Main score columns expected in recency_recommendations.csv
RECENCY_SCORE_COL = "recency_recommendation_score"
RECENCY_RANK_COL = "employee_recency_rank_for_combo"
RECENCY_AVG_CASES_COL = "recency_weighted_avg_cases"


# Opportunity Finder thresholds
# These can be tuned later based on business preference.
HIGH_SCORE_PERCENTILE = 0.75
LOW_USAGE_PERCENTILE = 0.35

LOW_OBSERVED_DAYS_THRESHOLD = 10
MEDIUM_OBSERVED_DAYS_THRESHOLD = 30


# Streamlit app settings
APP_TITLE = "Employee Case Analysis Explorer"
APP_ICON = "📊"