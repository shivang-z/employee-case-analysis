import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# Streamlit App: Employee Case Analysis Explorer
# ============================================================
# Files used:
#
# 1. historical_combo.csv
#    Used for employee-level historical analytics.
#
# 2. recency_recommendations.csv
#    Used in place of the normal employee_recommendations.csv.
#    This recommendation file should include recency-based recommendation outputs.
#
# Expected folder structure:
# employee_case_analysis_outputs/
#   - historical_combo.csv
#   - recency_recommendations.csv
#
# Run:
# pip install streamlit pandas numpy
# streamlit run app.py
# ============================================================


st.set_page_config(
    page_title="Employee Case Analysis",
    page_icon="📊",
    layout="wide",
)


# -----------------------------
# Config
# -----------------------------

DEFAULT_INPUT_DIR = "employee_case_analysis_outputs"
HISTORICAL_FILE = "historical_combo.csv"
RECOMMENDATIONS_FILE = "recency_recommendations.csv"

# These are the recency recommendation columns.
# If your file uses slightly different names, the code below has fallback handling.
PRIMARY_SCORE_COL = "recency_recommendation_score"
PRIMARY_RANK_COL = "employee_recency_rank_for_combo"
PRIMARY_AVG_COL = "recency_weighted_avg_cases"


# -----------------------------
# Helper functions
# -----------------------------

@st.cache_data(show_spinner=False)
def load_csv(path_or_file):
    return pd.read_csv(path_or_file)


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Clean column names and standardize key fields."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    rename_map = {
        "TestName": "testname",
        "TESTNAME": "testname",
        "PayorName": "payorname",
        "PAYORNAME": "payorname",
        "Matched_Employee_Name": "matched_employee_name",
        "MATCHED_EMPLOYEE_NAME": "matched_employee_name",
        "Matched_Email": "matched_email",
        "MATCHED_EMAIL": "matched_email",
        "Matched_Shore": "matched_shore",
        "MATCHED_SHORE": "matched_shore",
    }

    df = df.rename(columns={c: rename_map.get(c, c) for c in df.columns})

    text_cols = [
        "matched_employee_name",
        "matched_email",
        "matched_shore",
        "testname",
        "payorname",
    ]

    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": np.nan, "None": np.nan, "": np.nan})

    return df


def find_file(input_dir: str, filename: str):
    file_path = Path(input_dir) / filename
    if file_path.exists():
        return str(file_path)
    return None


def format_num(value, decimals=2):
    if pd.isna(value):
        return "-"
    try:
        return f"{float(value):,.{decimals}f}"
    except Exception:
        return str(value)


def existing_cols(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [c for c in cols if c in df.columns]


def download_df(df: pd.DataFrame, filename: str, label: str):
    st.download_button(
        label=label,
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
    )


def apply_shore_filter(df: pd.DataFrame, selected_shore: str) -> pd.DataFrame:
    if selected_shore != "All" and "matched_shore" in df.columns:
        return df[df["matched_shore"] == selected_shore].copy()
    return df.copy()


def safe_top_n_selector(label: str, total_rows: int, default_n: int = 20) -> int:
    """Avoid Streamlit slider error when there are very few rows."""
    if total_rows <= 0:
        return 0
    if total_rows == 1:
        st.caption("Only 1 row is available for the selected filters.")
        return 1

    max_value = min(100, total_rows)
    min_value = 1
    value = min(default_n, max_value)

    return st.slider(
        label,
        min_value=min_value,
        max_value=max_value,
        value=value,
    )


def get_score_col(df: pd.DataFrame) -> str | None:
    """Return the best available score column."""
    for col in [
        "recency_recommendation_score",
        "recency_score",
        "recommendation_score",
    ]:
        if col in df.columns:
            return col
    return None


def get_rank_col(df: pd.DataFrame) -> str | None:
    """Return the best available rank column."""
    for col in [
        "employee_recency_rank_for_combo",
        "employee_rank_for_combo",
    ]:
        if col in df.columns:
            return col
    return None


def get_avg_col(df: pd.DataFrame) -> str | None:
    """Return the best available average productivity column."""
    for col in [
        "recency_weighted_avg_cases",
        "avg_daily_unique_cases",
    ]:
        if col in df.columns:
            return col
    return None


def add_confidence_label(df: pd.DataFrame) -> pd.DataFrame:
    """Add confidence label based on observed_days."""
    df = df.copy()

    if "observed_days" not in df.columns:
        df["confidence_level"] = "Not available"
        return df

    def label(days):
        if pd.isna(days):
            return "Not available"
        if days >= 30:
            return "High"
        if days >= 10:
            return "Medium"
        return "Low"

    df["confidence_level"] = df["observed_days"].apply(label)
    return df


def add_recommendation_reason(df: pd.DataFrame) -> pd.DataFrame:
    """Create a simple reason code for why a recency recommendation ranks well."""
    df = df.copy()

    reasons = []

    for _, row in df.iterrows():
        row_reasons = []

        if "recency_avg_cases_norm" in df.columns and row.get("recency_avg_cases_norm", 0) >= 0.75:
            row_reasons.append("strong recent productivity")
        elif "recency_avg_norm" in df.columns and row.get("recency_avg_norm", 0) >= 0.75:
            row_reasons.append("strong recent productivity")
        elif "avg_cases_norm" in df.columns and row.get("avg_cases_norm", 0) >= 0.75:
            row_reasons.append("high average productivity")

        if "max_cases_norm" in df.columns and row.get("max_cases_norm", 0) >= 0.75:
            row_reasons.append("strong peak performance")

        if "evidence_norm" in df.columns and row.get("evidence_norm", 0) >= 0.75:
            row_reasons.append("strong historical evidence")

        if "consistency_norm" in df.columns and row.get("consistency_norm", 0) >= 0.75:
            row_reasons.append("stable performance")

        if not row_reasons:
            row_reasons.append("balanced recommendation profile")

        reasons.append(" + ".join(row_reasons))

    df["recommendation_reason"] = reasons
    return df


def prepare_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    """Add helpful interpretation columns to recency_recommendations.csv."""
    df = df.copy()
    df = add_confidence_label(df)
    # df = add_recommendation_reason(df)
    return df


# -----------------------------
# Sidebar: Load data
# -----------------------------

st.sidebar.title("Data")
input_dir = st.sidebar.text_input("Input folder", value=DEFAULT_INPUT_DIR)

st.sidebar.caption("Upload files only if they are not available locally.")
uploaded_hist = st.sidebar.file_uploader("Upload historical_combo.csv", type=["csv"])
uploaded_recs = st.sidebar.file_uploader("Upload recency_recommendations.csv", type=["csv"])

historical_path = find_file(input_dir, HISTORICAL_FILE)
recommendations_path = find_file(input_dir, RECOMMENDATIONS_FILE)

historical_combo = None
recommendations = None

try:
    if uploaded_hist is not None:
        historical_combo = clean_columns(load_csv(uploaded_hist))
    elif historical_path:
        historical_combo = clean_columns(load_csv(historical_path))
except Exception as e:
    st.sidebar.error(f"Could not load {HISTORICAL_FILE}: {e}")

try:
    if uploaded_recs is not None:
        recommendations = clean_columns(load_csv(uploaded_recs))
    elif recommendations_path:
        recommendations = clean_columns(load_csv(recommendations_path))
except Exception as e:
    st.sidebar.error(f"Could not load {RECOMMENDATIONS_FILE}: {e}")

if recommendations is not None:
    recommendations = prepare_recommendations(recommendations)

if historical_combo is not None:
    st.sidebar.success("Loaded historical_combo.csv")
else:
    st.sidebar.warning("historical_combo.csv not loaded")

if recommendations is not None:
    st.sidebar.success("Loaded recency_recommendations.csv")
else:
    st.sidebar.warning("recency_recommendations.csv not loaded")


# -----------------------------
# Header
# -----------------------------

st.title("Employee Case Analysis Explorer")
st.write(
    "Use this app to review employee-level performance and recency-based recommendation rankings "
    "for TestName / PayorName combinations."
)

if historical_combo is None and recommendations is None:
    st.error("No data loaded. Please place the CSV files in the input folder or upload them from the sidebar.")
    st.stop()


# -----------------------------
# Global shore filter
# -----------------------------

shore_values = set()
for df in [historical_combo, recommendations]:
    if df is not None and "matched_shore" in df.columns:
        shore_values.update(df["matched_shore"].dropna().astype(str).unique())

selected_shore = "All"
if shore_values:
    selected_shore = st.sidebar.selectbox("Shore filter", ["All"] + sorted(shore_values))

if historical_combo is not None:
    historical_combo = apply_shore_filter(historical_combo, selected_shore)

if recommendations is not None:
    recommendations = apply_shore_filter(recommendations, selected_shore)


# -----------------------------
# Tabs
# -----------------------------

tab_employee, tab_combo, tab_model = st.tabs(
    [
        "Employee Deep-Dive",
        "Best Employees by Test / Payor",
        "Recommendation Model Summary",
    ]
)


# ============================================================
# TAB 1: Employee Deep-Dive
# Uses historical_combo.csv + recency_recommendations.csv
# ============================================================

with tab_employee:
    st.header("Employee Deep-Dive")
    st.write(
        "Select one employee to review historical performance and recency-based recommended combinations."
    )

    employee_source = None
    if historical_combo is not None and "matched_employee_name" in historical_combo.columns:
        employee_source = historical_combo
    elif recommendations is not None and "matched_employee_name" in recommendations.columns:
        employee_source = recommendations

    if employee_source is None:
        st.warning("No employee field found in the loaded files.")
    else:
        employee_list = sorted(employee_source["matched_employee_name"].dropna().astype(str).unique())

        if not employee_list:
            st.warning("No employees found after applying filters.")
        else:
            selected_employee = st.selectbox("Select employee", employee_list)

            # -----------------------------
            # Historical section
            # -----------------------------
            if historical_combo is not None:
                required_cols = {"matched_employee_name", "testname", "payorname"}
                missing_cols = required_cols - set(historical_combo.columns)

                if missing_cols:
                    st.error(f"historical_combo.csv is missing required columns: {sorted(missing_cols)}")
                else:
                    emp_hist = historical_combo[
                        historical_combo["matched_employee_name"].astype(str) == selected_employee
                    ].copy()

                    if not emp_hist.empty:
                        st.subheader("Historical Performance Summary")

                        total_cases = emp_hist["historical_total_unique_cases"].sum() if "historical_total_unique_cases" in emp_hist.columns else np.nan
                        total_touches = emp_hist["historical_total_touches"].sum() if "historical_total_touches" in emp_hist.columns else np.nan
                        best_avg_cases = emp_hist["avg_daily_unique_cases"].max() if "avg_daily_unique_cases" in emp_hist.columns else np.nan
                        best_peak_cases = emp_hist["max_daily_unique_cases"].max() if "max_daily_unique_cases" in emp_hist.columns else np.nan
                        combo_count = emp_hist[["testname", "payorname"]].drop_duplicates().shape[0]

                        c1, c2, c3, c4, c5 = st.columns(5)
                        c1.metric("Total Unique Cases", format_num(total_cases, 0))
                        c2.metric("Total Touches", format_num(total_touches, 0))
                        c3.metric("Best Avg Daily Cases", format_num(best_avg_cases, 2))
                        c4.metric("Best Peak Daily Cases", format_num(best_peak_cases, 0))
                        c5.metric("Combos Worked", format_num(combo_count, 0))

                        sort_options = existing_cols(
                            emp_hist,
                            [
                                "avg_daily_unique_cases",
                                "historical_total_unique_cases",
                                "max_daily_unique_cases",
                                "active_days",
                                "avg_touches_per_case",
                                "consistency_cv_cases",
                            ],
                        )

                        if sort_options:
                            sort_metric = st.selectbox("Sort historical combinations by", sort_options)
                            ascending = sort_metric in ["avg_touches_per_case", "consistency_cv_cases"]
                            emp_hist_sorted = emp_hist.sort_values(sort_metric, ascending=ascending).reset_index(drop=True)
                        else:
                            emp_hist_sorted = emp_hist.copy()

                        hist_display_cols = existing_cols(
                            emp_hist_sorted,
                            [
                                "testname",
                                "payorname",
                                "matched_shore",
                                "active_days",
                                "historical_total_unique_cases",
                                "historical_total_touches",
                                "avg_daily_unique_cases",
                                "median_daily_unique_cases",
                                "max_daily_unique_cases",
                                "std_daily_unique_cases",
                                "consistency_cv_cases",
                                "avg_touches_per_case",
                            ],
                        )

                        st.dataframe(emp_hist_sorted[hist_display_cols], width="stretch", hide_index=True)
                        download_df(emp_hist_sorted, f"{selected_employee}_historical_performance.csv", "Download historical performance")

                    else:
                        st.info("No historical rows found for this employee.")

            st.divider()

            # -----------------------------
            # Recency recommendation section for selected employee
            # -----------------------------
            st.subheader("Recency-Based Recommended TestName / PayorName Combinations")

            if recommendations is None:
                st.warning("recency_recommendations.csv is required to show recommendations.")
            else:
                required_cols = {"matched_employee_name", "testname", "payorname"}
                missing_cols = required_cols - set(recommendations.columns)

                if missing_cols:
                    st.error(f"recency_recommendations.csv is missing required columns: {sorted(missing_cols)}")
                else:
                    emp_recs = recommendations[
                        recommendations["matched_employee_name"].astype(str) == selected_employee
                    ].copy()

                    if emp_recs.empty:
                        st.info("No recommendation rows found for this employee.")
                    else:
                        score_col = get_score_col(emp_recs)
                        rank_col = get_rank_col(emp_recs)
                        avg_col = get_avg_col(emp_recs)

                        if rank_col:
                            emp_recs = emp_recs.sort_values(rank_col, ascending=True)
                        elif score_col:
                            emp_recs = emp_recs.sort_values(score_col, ascending=False)

                        top_n_recs = safe_top_n_selector("Number of recommendations to show", len(emp_recs), default_n=10)

                        rec_display_cols = existing_cols(
                            emp_recs,
                            [
                                rank_col,
                                "testname",
                                "payorname",
                                "matched_shore",
                                "observed_days",
                                "confidence_level",
                                # "recency_weighted_avg_cases",
                                # "avg_daily_unique_cases",
                                # "max_daily_unique_cases",
                                # "avg_daily_touches",
                                # "max_daily_touches",
                                "consistency_score",
                                "evidence_score",
                                score_col,
                                "recommendation_reason",
                            ],
                        )

                        st.dataframe(emp_recs.head(top_n_recs)[rec_display_cols], width="stretch", hide_index=True)
                        download_df(emp_recs, f"{selected_employee}_recency_recommendations.csv", "Download employee recency recommendations")

                        if score_col:
                            st.subheader("Recency Recommendation Score Chart")
                            chart_recs = emp_recs.head(top_n_recs).copy()
                            chart_recs["combo"] = chart_recs["testname"].astype(str) + " / " + chart_recs["payorname"].astype(str)
                            chart_recs = chart_recs[["combo", score_col]].set_index("combo")
                            st.bar_chart(chart_recs)

                        top_row = emp_recs.iloc[0]
                        st.info(
                            f"For **{selected_employee}**, the top recency-based recommended combination is "
                            f"**{top_row['testname']} / {top_row['payorname']}**. "
                            "This recommendation gives higher importance to recent performance while still considering overall productivity, peak output, evidence, and consistency."
                        )


# ============================================================
# TAB 2: Best Employees by TestName / PayorName
# Uses recency_recommendations.csv
# ============================================================

with tab_combo:
    st.header("Best Employees by TestName / PayorName")
    st.write(
        "Select a TestName / PayorName combination to see which employees are recommended for that work type."
    )

    if recommendations is None:
        st.warning("recency_recommendations.csv is required for combination-level ranking.")
    else:
        required_cols = {"matched_employee_name", "testname", "payorname"}
        missing_cols = required_cols - set(recommendations.columns)

        if missing_cols:
            st.error(f"recency_recommendations.csv is missing required columns: {sorted(missing_cols)}")
        else:
            tests = sorted(recommendations["testname"].dropna().astype(str).unique())

            if not tests:
                st.warning("No TestName values found after applying filters.")
            else:
                col1, col2, col3 = st.columns(3)

                with col1:
                    selected_test = st.selectbox("Select TestName", tests)

                payors = sorted(
                    recommendations.loc[
                        recommendations["testname"].astype(str) == selected_test,
                        "payorname",
                    ].dropna().astype(str).unique()
                )

                if not payors:
                    st.warning("No PayorName values found for this TestName.")
                else:
                    with col2:
                        selected_payor = st.selectbox("Select PayorName", payors)

                    combo_df = recommendations[
                        (recommendations["testname"].astype(str) == selected_test)
                        & (recommendations["payorname"].astype(str) == selected_payor)
                    ].copy()

                    if combo_df.empty:
                        st.warning("No employees found for this combination.")
                    else:
                        score_col = get_score_col(combo_df)
                        rank_col = get_rank_col(combo_df)
                        avg_col = get_avg_col(combo_df)

                        metric_options = existing_cols(
                            combo_df,
                            [
                                score_col,
                                "recency_weighted_avg_cases",
                                "avg_daily_unique_cases",
                                "max_daily_unique_cases",
                                "observed_days",
                                "consistency_score",
                                "evidence_score",
                            ],
                        )

                        if not metric_options:
                            st.error("No ranking metrics found in recency_recommendations.csv.")
                            st.stop()

                        default_index = metric_options.index(score_col) if score_col in metric_options else 0

                        with col3:
                            ranking_metric = st.selectbox("Rank employees by", metric_options, index=default_index)

                        combo_df = combo_df.sort_values(ranking_metric, ascending=False).reset_index(drop=True)
                        combo_df.insert(0, "rank_for_selected_combo", np.arange(1, len(combo_df) + 1))

                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Employees Found", format_num(combo_df["matched_employee_name"].nunique(), 0))

                        if score_col:
                            c2.metric("Top Recency Score", format_num(combo_df[score_col].max(), 3))
                        else:
                            c2.metric("Top Recency Score", "-")

                        if avg_col:
                            c3.metric("Best Recent/Avg Cases", format_num(combo_df[avg_col].max(), 2))
                        else:
                            c3.metric("Best Recent/Avg Cases", "-")

                        if "max_daily_unique_cases" in combo_df.columns:
                            c4.metric("Best Peak Daily Cases", format_num(combo_df["max_daily_unique_cases"].max(), 0))
                        else:
                            c4.metric("Best Peak Daily Cases", "-")

                        st.divider()

                        st.subheader(f"Recommended Employees for {selected_test} / {selected_payor}")

                        top_n = safe_top_n_selector("Number of employees to show", len(combo_df), default_n=20)

                        display_cols = existing_cols(
                            combo_df,
                            [
                                "rank_for_selected_combo",
                                rank_col,
                                "matched_employee_name",
                                "matched_email",
                                "matched_shore",
                                "observed_days",
                                "confidence_level",
                                "recency_weighted_avg_cases",
                                "avg_daily_unique_cases",
                                "max_daily_unique_cases",
                                "avg_daily_touches",
                                "max_daily_touches",
                                "consistency_score",
                                "evidence_score",
                                score_col,
                                "recommendation_reason",
                            ],
                        )

                        st.dataframe(combo_df.head(top_n)[display_cols], width="stretch", hide_index=True)

                        download_df(
                            combo_df,
                            f"recency_recommended_employees_{selected_test}_{selected_payor}.csv",
                            "Download selected-combo recommendations",
                        )

                        st.subheader("Recommendation Chart")
                        chart_df = combo_df.head(top_n).copy()
                        chart_df = chart_df[["matched_employee_name", ranking_metric]].set_index("matched_employee_name")
                        st.bar_chart(chart_df)

                        top_employee = combo_df.iloc[0]
                        st.info(
                            f"For **{selected_test} / {selected_payor}**, the top recommended employee based on `{ranking_metric}` is "
                            f"**{top_employee['matched_employee_name']}**. "
                            "This ranking uses the recency-based recommendation output."
                        )


# ============================================================
# TAB 3: Recommendation Model Summary
# ============================================================

with tab_model:
    st.header("Recommendation Model Summary")

    st.write(
        "This app is using `recency_recommendations.csv` in place of the normal recommendation output. "
        "The goal is to show recommendations that give more importance to recent performance while still keeping the model explainable."
    )

    st.subheader("Expected Recommendation Columns")

    expected_cols = pd.DataFrame(
        [
            {
                "Column": "recency_recommendation_score",
                "Meaning": "Final recommendation score after including recency-weighted performance.",
            },
            {
                "Column": "employee_recency_rank_for_combo",
                "Meaning": "Rank of each TestName / PayorName recommendation within an employee.",
            },
            {
                "Column": "recency_weighted_avg_cases",
                "Meaning": "Average daily unique cases after giving more importance to recent days.",
            },
            {
                "Column": "observed_days",
                "Meaning": "Number of days the employee worked that TestName / PayorName combination.",
            },
            {
                "Column": "confidence_level",
                "Meaning": "High / Medium / Low confidence based on observed days.",
            },
        ]
    )

    st.dataframe(expected_cols, width="stretch", hide_index=True)

    st.subheader("How to Interpret")
    st.markdown(
        """
- A higher recency recommendation score means the employee is a stronger current fit for that TestName / PayorName combination.
- Recent performance receives more importance than older historical performance.
- `confidence_level` helps show whether the recommendation is based on enough observed days.
- The app still shows historical performance separately so users can compare long-term performance with recommendation ranking.
        """
    )
