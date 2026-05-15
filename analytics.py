# analytics.py

import numpy as np
import pandas as pd

from config import (
    RECENCY_SCORE_COL,
    RECENCY_AVG_CASES_COL,
    HIGH_SCORE_PERCENTILE,
    LOW_USAGE_PERCENTILE,
    LOW_OBSERVED_DAYS_THRESHOLD,
    MEDIUM_OBSERVED_DAYS_THRESHOLD,
)


def get_score_col(df: pd.DataFrame) -> str | None:
    """
    Return the best available recommendation score column.
    """
    for col in [
        "recency_recommendation_score",
        "recency_score",
        "recommendation_score",
    ]:
        if col in df.columns:
            return col

    return None


def get_rank_col(df: pd.DataFrame) -> str | None:
    """
    Return the best available employee-level rank column.
    """
    for col in [
        "employee_recency_rank_for_combo",
        "employee_rank_for_combo",
    ]:
        if col in df.columns:
            return col

    return None


def add_confidence_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add High / Medium / Low confidence based on observed_days.
    """
    df = df.copy()

    if "observed_days" not in df.columns:
        df["confidence_level"] = "Not available"
        return df

    def label(days):
        if pd.isna(days):
            return "Not available"

        if days >= MEDIUM_OBSERVED_DAYS_THRESHOLD:
            return "High"

        if days >= LOW_OBSERVED_DAYS_THRESHOLD:
            return "Medium"

        return "Low"

    df["confidence_level"] = df["observed_days"].apply(label)

    return df


def add_recommendation_reason(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create readable explanation labels using columns that actually exist.

    This does not calculate the recommendation score.
    It only adds an explanation column for UI readability.
    """
    df = df.copy()

    reasons = []

    recency_avg_cutoff = None
    avg_cases_cutoff = None
    max_cases_cutoff = None

    if "recency_weighted_avg_cases" in df.columns:
        recency_avg_cutoff = df["recency_weighted_avg_cases"].quantile(0.75)

    if "avg_daily_unique_cases" in df.columns:
        avg_cases_cutoff = df["avg_daily_unique_cases"].quantile(0.75)

    if "max_daily_unique_cases" in df.columns:
        max_cases_cutoff = df["max_daily_unique_cases"].quantile(0.75)

    for _, row in df.iterrows():
        row_reasons = []

        if (
            recency_avg_cutoff is not None
            and row.get("recency_weighted_avg_cases", 0) >= recency_avg_cutoff
        ):
            row_reasons.append("strong recent productivity")

        elif (
            avg_cases_cutoff is not None
            and row.get("avg_daily_unique_cases", 0) >= avg_cases_cutoff
        ):
            row_reasons.append("high average productivity")

        if (
            max_cases_cutoff is not None
            and row.get("max_daily_unique_cases", 0) >= max_cases_cutoff
        ):
            row_reasons.append("strong peak performance")

        if "observed_days" in df.columns:
            observed_days = row.get("observed_days", 0)

            if observed_days >= MEDIUM_OBSERVED_DAYS_THRESHOLD:
                row_reasons.append("strong historical evidence")

            elif observed_days >= LOW_OBSERVED_DAYS_THRESHOLD:
                row_reasons.append("moderate historical evidence")

        if "consistency_score" in df.columns and row.get("consistency_score", 0) >= 0.75:
            row_reasons.append("stable performance")

        if not row_reasons:
            row_reasons.append("balanced recommendation profile")

        reasons.append(" + ".join(row_reasons))

    df["recommendation_reason"] = reasons

    return df


def prepare_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare recommendation dataframe for UI.
    """
    df = df.copy()
    df = add_confidence_label(df)
    df = add_recommendation_reason(df)
    return df


def build_employee_summary(historical_df: pd.DataFrame, employee_name: str) -> dict:
    """
    Build KPI summary for one employee.
    """
    emp_df = historical_df[
        historical_df["matched_employee_name"].astype(str) == employee_name
    ].copy()

    if emp_df.empty:
        return {}

    return {
        "total_unique_cases": (
            emp_df["historical_total_unique_cases"].sum()
            if "historical_total_unique_cases" in emp_df.columns
            else np.nan
        ),
        "total_touches": (
            emp_df["historical_total_touches"].sum()
            if "historical_total_touches" in emp_df.columns
            else np.nan
        ),
        "best_avg_daily_cases": (
            emp_df["avg_daily_unique_cases"].max()
            if "avg_daily_unique_cases" in emp_df.columns
            else np.nan
        ),
        "best_peak_daily_cases": (
            emp_df["max_daily_unique_cases"].max()
            if "max_daily_unique_cases" in emp_df.columns
            else np.nan
        ),
        "combos_worked": emp_df[["testname", "payorname"]].drop_duplicates().shape[0],
    }


# def create_opportunity_finder(recommendations_df: pd.DataFrame) -> pd.DataFrame:
#     """
#     Find hidden opportunity areas.

#     Logic:
#     A high-opportunity row means:
#     - employee has a high recommendation score
#     - but observed usage/exposure is relatively low

#     In simple terms:
#     This employee appears strong for this combo, but may not be used enough there.
#     """
#     df = recommendations_df.copy()

#     score_col = get_score_col(df)

#     if score_col is None:
#         raise ValueError(
#             "No recommendation score column found. Expected recency_recommendation_score, recency_score, or recommendation_score."
#         )

#     if "observed_days" not in df.columns:
#         raise ValueError("observed_days column is required for Opportunity Finder.")

#     # High score cutoff based on top 25 percent of recommendation scores
#     high_score_cutoff = df[score_col].quantile(HIGH_SCORE_PERCENTILE)

#     # Low usage cutoff based on lower 35 percent of observed days
#     low_usage_cutoff = df["observed_days"].quantile(LOW_USAGE_PERCENTILE)

#     df["high_score_flag"] = df[score_col] >= high_score_cutoff
#     df["low_usage_flag"] = df["observed_days"] <= low_usage_cutoff

#     df["opportunity_flag"] = df["high_score_flag"] & df["low_usage_flag"]

#     # Opportunity score rewards high recommendation score and low usage.
#     # Lower observed_days means more potential opportunity.
#     max_observed_days = df["observed_days"].max()

#     if pd.isna(max_observed_days) or max_observed_days == 0:
#         df["usage_gap_score"] = 0
#     else:
#         df["usage_gap_score"] = 1 - (df["observed_days"] / max_observed_days)

#     df["opportunity_score"] = df[score_col] * df["usage_gap_score"]

#     def opportunity_label(row):
#         if row["opportunity_flag"]:
#             return "High Opportunity"

#         if row["high_score_flag"]:
#             return "Strong but already used"

#         if row["low_usage_flag"]:
#             return "Low exposure"

#         return "Normal"

#     df["opportunity_label"] = df.apply(opportunity_label, axis=1)

#     opportunity_df = df.sort_values(
#         ["opportunity_flag", "opportunity_score", score_col],
#         ascending=[False, False, False],
#     ).reset_index(drop=True)

#     return opportunity_df

def create_opportunity_finder(recommendations_df: pd.DataFrame) -> pd.DataFrame:
    """
    Find hidden opportunity areas using combo-specific logic.

    Logic:
    A high-opportunity row means:
    - employee is strong compared to other employees within the same TestName / PayorName
    - but has relatively low usage/exposure within that same TestName / PayorName

    In simple terms:
    This employee appears strong for this specific combo, but may not be used enough there.
    """
    df = recommendations_df.copy()

    score_col = get_score_col(df)

    if score_col is None:
        raise ValueError(
            "No recommendation score column found. Expected recency_recommendation_score, recency_score, or recommendation_score."
        )

    required_cols = {
        "matched_employee_name",
        "testname",
        "payorname",
        "observed_days",
    }

    missing_cols = required_cols - set(df.columns)

    if missing_cols:
        raise ValueError(f"Missing required columns for Opportunity Finder: {missing_cols}")

    # Make sure observed_days is numeric
    df["observed_days"] = pd.to_numeric(df["observed_days"], errors="coerce").fillna(0)

    combo_cols = ["testname", "payorname"]

    # ------------------------------------------------------------
    # 1. Combo-specific score percentile
    # ------------------------------------------------------------
    # For each TestName / PayorName combination:
    # - rank employees by recommendation score
    # - convert rank into percentile
    # - employees in the top 25% for that combo are treated as high-score candidates
    # ------------------------------------------------------------

    df["combo_score_percentile"] = (
        df.groupby(combo_cols)[score_col]
        .rank(pct=True, ascending=True, method="average")
    )

    df["high_score_flag"] = df["combo_score_percentile"] >= HIGH_SCORE_PERCENTILE

    # ------------------------------------------------------------
    # 2. Combo-specific low usage cutoff
    # ------------------------------------------------------------
    # Instead of checking low observed_days globally, we check whether the employee
    # has low exposure compared to other employees for the same TestName / PayorName.
    # ------------------------------------------------------------

    df["combo_low_usage_cutoff"] = (
        df.groupby(combo_cols)["observed_days"]
        .transform(lambda s: s.quantile(LOW_USAGE_PERCENTILE))
    )

    df["combo_min_observed_days"] = (
        df.groupby(combo_cols)["observed_days"]
        .transform("min")
    )

    df["combo_max_observed_days"] = (
        df.groupby(combo_cols)["observed_days"]
        .transform("max")
    )

    # This avoids incorrectly flagging everyone as low usage when all employees
    # have the same observed_days for a combo.
    df["combo_usage_has_variation"] = (
        df["combo_max_observed_days"] > df["combo_min_observed_days"]
    )

    df["low_usage_flag"] = (
        (df["observed_days"] <= df["combo_low_usage_cutoff"])
        & df["combo_usage_has_variation"]
    )

    # ------------------------------------------------------------
    # 3. Opportunity flag
    # ------------------------------------------------------------
    # A true opportunity means:
    # strong within this combo AND underused within this combo.
    # ------------------------------------------------------------

    df["opportunity_flag"] = df["high_score_flag"] & df["low_usage_flag"]

    # ------------------------------------------------------------
    # 4. Usage gap score
    # ------------------------------------------------------------
    # Lower observed_days compared to the max observed_days in the same combo
    # means higher potential opportunity.
    # ------------------------------------------------------------

    df["usage_gap_score"] = np.where(
        df["combo_max_observed_days"] > 0,
        1 - (df["observed_days"] / df["combo_max_observed_days"]),
        0,
    )

    df["usage_gap_score"] = df["usage_gap_score"].clip(lower=0, upper=1)

    # ------------------------------------------------------------
    # 5. Opportunity score
    # ------------------------------------------------------------
    # We use combo_score_percentile instead of raw score so the opportunity score
    # is fairer across combinations with different score distributions.
    # ------------------------------------------------------------

    df["opportunity_score"] = (
        df["combo_score_percentile"].fillna(0)
        * df["usage_gap_score"].fillna(0)
    )

    # ------------------------------------------------------------
    # 6. Human-readable label
    # ------------------------------------------------------------

    def opportunity_label(row):
        if row["opportunity_flag"]:
            return "High Opportunity"

        if row["high_score_flag"]:
            return "Strong but already used"

        if row["low_usage_flag"]:
            return "Low exposure"

        return "Normal"

    df["opportunity_label"] = df.apply(opportunity_label, axis=1)

    # ------------------------------------------------------------
    # 7. Sort most useful opportunities to the top
    # ------------------------------------------------------------

    opportunity_df = (
        df.sort_values(
            [
                "opportunity_flag",
                "opportunity_score",
                "combo_score_percentile",
                score_col,
            ],
            ascending=[False, False, False, False],
        )
        .reset_index(drop=True)
    )

    return opportunity_df


def create_combo_coverage_summary(recommendations_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create a simple coverage summary by TestName / PayorName.

    This is useful for leadership because it shows where only a few employees
    have strong recommendation scores.
    """
    df = recommendations_df.copy()

    score_col = get_score_col(df)

    if score_col is None:
        raise ValueError("No recommendation score column found.")

    required_cols = {"testname", "payorname", "matched_employee_name"}
    missing_cols = required_cols - set(df.columns)

    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # strong_cutoff = df[score_col].quantile(0.75)
    # df["strong_candidate_flag"] = df[score_col] >= strong_cutoff
    # ------------------------------------------------------------
    # Combo-specific strong candidate logic
    # ------------------------------------------------------------
    # For each TestName / PayorName combination:
    # - rank employees by recommendation score
    # - convert rank into percentile
    # - top 25% employees for that combo are marked as strong candidates
    # ------------------------------------------------------------

    df["combo_score_percentile"] = (
        df.groupby(["testname", "payorname"])[score_col]
        .rank(pct=True, ascending=True)
    )

    df["strong_candidate_flag"] = df["combo_score_percentile"] >= 0.75

    

    # Combo-level aggregation
    # ------------------------------------------------------------

    coverage = (
        df.groupby(["testname", "payorname"], dropna=False)
        .agg(
            total_employees=("matched_employee_name", "nunique"),
            strong_employees=("strong_candidate_flag", "sum"),
            avg_score=(score_col, "mean"),
            max_score=(score_col, "max"),
            min_score=(score_col, "min"),
            median_score=(score_col, "median"),
        )
        .reset_index()
    )

    # Strong employee percentage
    coverage["strong_employee_pct"] = (
        coverage["strong_employees"]
        / coverage["total_employees"].replace(0, np.nan)
    )

    def risk_level(row):
        strong_count = row["strong_employees"]

        if strong_count <= 1:
            return "Critical"

        if strong_count <= 3:
            return "Medium"

        return "Low"

    coverage["coverage_risk"] = coverage.apply(risk_level, axis=1)

    # Proper sorting order: Critical -> Medium -> Low
    risk_order = {
        "Critical": 1,
        "Medium": 2,
        "Low": 3,
    }

    coverage["risk_order"] = coverage["coverage_risk"].map(risk_order)

    coverage = (
        coverage.sort_values(
            ["risk_order", "strong_employees", "max_score"],
            ascending=[True, True, False],
        )
        .drop(columns=["risk_order"])
        .reset_index(drop=True)
    )

    # coverage = coverage.sort_values(
    #     ["coverage_risk", "strong_employees", "max_score"],
    #     ascending=[True, True, False],
    # ).reset_index(drop=True)

    return coverage