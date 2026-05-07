import os
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# Streamlit App: Employee Case Analysis Explorer
# ============================================================
# Simple version based on only 2 files:
#
# 1. employee_recommendations.csv
#    Used for TestName / PayorName combo analysis.
#    This tells us which employees are best for a selected combo.
#
# 2. historical_combo.csv
#    Used for employee-level analytics.
#    This gives summarized historical performance for each employee.
#
# Expected folder structure:
# employee_case_analysis_outputs/
#   - employee_recommendations.csv
#   - historical_combo.csv
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
RECOMMENDATIONS_FILE = "employee_recommendations.csv"
HISTORICAL_FILE = "historical_combo.csv"


# -----------------------------
# Helper functions
# -----------------------------

@st.cache_data(show_spinner=False)
def load_csv(path_or_file):
    return pd.read_csv(path_or_file)


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Clean column names and standardize important fields."""
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

    for col in ["matched_employee_name", "matched_email", "matched_shore", "testname", "payorname"]:
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
    """
    Safe selector for top N rows.

    Streamlit slider fails when min_value == max_value.
    This function avoids that issue when only a few rows exist.
    """
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


# -----------------------------
# Sidebar: Load data
# -----------------------------

st.sidebar.title("Data")

input_dir = st.sidebar.text_input("Input folder", value=DEFAULT_INPUT_DIR)

st.sidebar.caption("Upload files only if they are not available locally.")
uploaded_recs = st.sidebar.file_uploader("Upload employee_recommendations.csv", type=["csv"])
uploaded_hist = st.sidebar.file_uploader("Upload historical_combo.csv", type=["csv"])

recommendations_path = find_file(input_dir, RECOMMENDATIONS_FILE)
historical_path = find_file(input_dir, HISTORICAL_FILE)

employee_recommendations = None
historical_combo = None

try:
    if uploaded_recs is not None:
        employee_recommendations = clean_columns(load_csv(uploaded_recs))
    elif recommendations_path:
        employee_recommendations = clean_columns(load_csv(recommendations_path))
except Exception as e:
    st.sidebar.error(f"Could not load {RECOMMENDATIONS_FILE}: {e}")

try:
    if uploaded_hist is not None:
        historical_combo = clean_columns(load_csv(uploaded_hist))
    elif historical_path:
        historical_combo = clean_columns(load_csv(historical_path))
except Exception as e:
    st.sidebar.error(f"Could not load {HISTORICAL_FILE}: {e}")

if employee_recommendations is not None:
    st.sidebar.success("Loaded employee_recommendations.csv")
else:
    st.sidebar.warning("employee_recommendations.csv not loaded")

if historical_combo is not None:
    st.sidebar.success("Loaded historical_combo.csv")
else:
    st.sidebar.warning("historical_combo.csv not loaded")


# -----------------------------
# Header
# -----------------------------

st.title("Employee Case Analysis Explorer")
st.write(
    "A simple app to review individual employee performance and find the best employees "
    "for each TestName / PayorName combination."
)

if employee_recommendations is None and historical_combo is None:
    st.error(
        "No data loaded. Please place the CSV files in the input folder or upload them from the sidebar."
    )
    st.stop()


# -----------------------------
# Global filter
# -----------------------------

shore_values = set()
for df in [employee_recommendations, historical_combo]:
    if df is not None and "matched_shore" in df.columns:
        shore_values.update(df["matched_shore"].dropna().astype(str).unique())

selected_shore = "All"
if shore_values:
    selected_shore = st.sidebar.selectbox("Shore filter", ["All"] + sorted(shore_values))

if employee_recommendations is not None:
    employee_recommendations = apply_shore_filter(employee_recommendations, selected_shore)

if historical_combo is not None:
    historical_combo = apply_shore_filter(historical_combo, selected_shore)


# -----------------------------
# Tabs
# -----------------------------

tab_employee, tab_combo = st.tabs([
    "Employee Deep-Dive",
    "Best Employees by Test / Payor",
])


# ============================================================
# TAB 1: Employee Deep-Dive
# Uses historical_combo.csv
# ============================================================

with tab_employee:
    st.header("Employee Deep-Dive")
    st.write(
        "Use this section to understand how one employee has performed historically "
        "across TestName / PayorName combinations."
    )

    if historical_combo is None:
        st.warning("historical_combo.csv is required for employee-level analytics.")
    else:
        required_cols = {"matched_employee_name", "testname", "payorname"}
        missing_cols = required_cols - set(historical_combo.columns)

        if missing_cols:
            st.error(f"historical_combo.csv is missing required columns: {sorted(missing_cols)}")
        else:
            employee_list = sorted(
                historical_combo["matched_employee_name"].dropna().astype(str).unique()
            )

            if not employee_list:
                st.warning("No employees found after applying the filters.")
            else:
                selected_employee = st.selectbox("Select employee", employee_list)

                emp_df = historical_combo[
                    historical_combo["matched_employee_name"].astype(str) == selected_employee
                ].copy()

                if emp_df.empty:
                    st.warning("No data found for this employee.")
                else:
                    # -----------------------------
                    # KPI cards
                    # -----------------------------
                    total_cases = emp_df["historical_total_unique_cases"].sum() if "historical_total_unique_cases" in emp_df.columns else np.nan
                    total_touches = emp_df["historical_total_touches"].sum() if "historical_total_touches" in emp_df.columns else np.nan
                    best_avg_cases = emp_df["avg_daily_unique_cases"].max() if "avg_daily_unique_cases" in emp_df.columns else np.nan
                    best_peak_cases = emp_df["max_daily_unique_cases"].max() if "max_daily_unique_cases" in emp_df.columns else np.nan
                    combo_count = emp_df[["testname", "payorname"]].drop_duplicates().shape[0]

                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Total Unique Cases", format_num(total_cases, 0))
                    c2.metric("Total Touches", format_num(total_touches, 0))
                    c3.metric("Best Avg Daily Cases", format_num(best_avg_cases, 2))
                    c4.metric("Best Peak Daily Cases", format_num(best_peak_cases, 0))
                    c5.metric("Combos Worked", format_num(combo_count, 0))

                    st.divider()

                    # -----------------------------
                    # Main employee table
                    # -----------------------------
                    st.subheader("Employee Performance by TestName / PayorName")

                    sort_options = existing_cols(
                        emp_df,
                        [
                            "avg_daily_unique_cases",
                            "historical_total_unique_cases",
                            "max_daily_unique_cases",
                            "active_days",
                            "avg_touches_per_case",
                            "consistency_cv_cases",
                        ],
                    )

                    if not sort_options:
                        st.error("No sortable metric columns were found in historical_combo.csv.")
                        st.stop()

                    sort_metric = st.selectbox("Sort by", sort_options)
                    ascending = True if sort_metric in ["avg_touches_per_case", "consistency_cv_cases"] else False

                    emp_sorted = emp_df.sort_values(sort_metric, ascending=ascending).reset_index(drop=True)

                    display_cols = existing_cols(
                        emp_sorted,
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

                    st.dataframe(emp_sorted[display_cols], width="stretch", hide_index=True)

                    download_df(
                        emp_sorted,
                        f"{selected_employee}_employee_deep_dive.csv",
                        "Download employee deep-dive CSV",
                    )

                    # -----------------------------
                    # Simple visuals
                    # -----------------------------
                    st.subheader("Quick Visual Summary")

                    visual_metric_options = existing_cols(
                        emp_sorted,
                        [
                            "avg_daily_unique_cases",
                            "historical_total_unique_cases",
                            "max_daily_unique_cases",
                            "active_days",
                        ],
                    )

                    if visual_metric_options:
                        visual_metric = st.selectbox("Chart metric", visual_metric_options)
                        top_n = safe_top_n_selector(
                            "Number of combinations to show",
                            total_rows=len(emp_sorted),
                            default_n=10,
                        )

                        chart_df = emp_sorted.head(top_n).copy()
                        chart_df["combo"] = chart_df["testname"].astype(str) + " / " + chart_df["payorname"].astype(str)
                        chart_df = chart_df[["combo", visual_metric]].set_index("combo")

                        st.bar_chart(chart_df)
                    else:
                        st.info("No numeric metric found for charting.")

                    # -----------------------------
                    # Short interpretation
                    # -----------------------------
                    st.subheader("Quick Interpretation")

                    best_row = emp_sorted.iloc[0]
                    st.info(
                        f"For {selected_employee}, the strongest combination based on `{sort_metric}` is "
                        f"**{best_row['testname']} / {best_row['payorname']}**. "
                        "Use the table above to compare their volume, average productivity, peak productivity, "
                        "and consistency across combinations."
                    )


# ============================================================
# TAB 2: Best Employees by TestName / PayorName
# Uses employee_recommendations.csv
# ============================================================

with tab_combo:
    st.header("Best Employees by TestName / PayorName")
    st.write(
        "Use this section to select a TestName / PayorName combination and see which employees "
        "are recommended or ranked highest for that combination."
    )

    if employee_recommendations is None:
        st.warning("employee_recommendations.csv is required for combination-level employee ranking.")
    else:
        required_cols = {"matched_employee_name", "testname", "payorname"}
        missing_cols = required_cols - set(employee_recommendations.columns)

        if missing_cols:
            st.error(f"employee_recommendations.csv is missing required columns: {sorted(missing_cols)}")
        else:
            tests = sorted(employee_recommendations["testname"].dropna().astype(str).unique())

            if not tests:
                st.warning("No TestName values found after applying the filters.")
            else:
                selected_test = st.selectbox("Select TestName", tests)

                payors = sorted(
                    employee_recommendations.loc[
                        employee_recommendations["testname"].astype(str) == selected_test,
                        "payorname",
                    ].dropna().astype(str).unique()
                )

                if not payors:
                    st.warning("No PayorName values found for this TestName.")
                else:
                    selected_payor = st.selectbox("Select PayorName", payors)

                    combo_df = employee_recommendations[
                        (employee_recommendations["testname"].astype(str) == selected_test)
                        & (employee_recommendations["payorname"].astype(str) == selected_payor)
                    ].copy()

                    if combo_df.empty:
                        st.warning("No employees found for this combination.")
                    else:
                        # Ranking metric: recommendation_score is the default because this file is for recommendations
                        metric_options = existing_cols(
                            combo_df,
                            [
                                "recommendation_score",
                                "avg_daily_unique_cases",
                                "max_daily_unique_cases",
                                "observed_days",
                                "consistency_score",
                                "evidence_score",
                            ],
                        )

                        if not metric_options:
                            st.error("No ranking metric columns were found in employee_recommendations.csv.")
                            st.stop()

                        default_index = metric_options.index("recommendation_score") if "recommendation_score" in metric_options else 0
                        ranking_metric = st.selectbox("Rank employees by", metric_options, index=default_index)

                        combo_df = combo_df.sort_values(ranking_metric, ascending=False).reset_index(drop=True)
                        combo_df.insert(0, "rank_for_selected_combo", np.arange(1, len(combo_df) + 1))

                        # -----------------------------
                        # KPI cards
                        # -----------------------------
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Employees Found", format_num(combo_df["matched_employee_name"].nunique(), 0))

                        if "recommendation_score" in combo_df.columns:
                            c2.metric("Top Recommendation Score", format_num(combo_df["recommendation_score"].max(), 3))
                        else:
                            c2.metric("Top Recommendation Score", "-")

                        if "avg_daily_unique_cases" in combo_df.columns:
                            c3.metric("Best Avg Daily Cases", format_num(combo_df["avg_daily_unique_cases"].max(), 2))
                        else:
                            c3.metric("Best Avg Daily Cases", "-")

                        if "max_daily_unique_cases" in combo_df.columns:
                            c4.metric("Best Peak Daily Cases", format_num(combo_df["max_daily_unique_cases"].max(), 0))
                        else:
                            c4.metric("Best Peak Daily Cases", "-")

                        st.divider()

                        # -----------------------------
                        # Main ranking table
                        # -----------------------------
                        st.subheader(f"Top Employees for {selected_test} / {selected_payor}")

                        top_n = safe_top_n_selector(
                            "Number of employees to show",
                            total_rows=len(combo_df),
                            default_n=20,
                        )

                        display_cols = existing_cols(
                            combo_df,
                            [
                                "rank_for_selected_combo",
                                "matched_employee_name",
                                "matched_email",
                                "matched_shore",
                                "observed_days",
                                "avg_daily_unique_cases",
                                "max_daily_unique_cases",
                                "avg_daily_touches",
                                "max_daily_touches",
                                "consistency_score",
                                "evidence_score",
                                "recommendation_score",
                                "employee_rank_for_combo",
                            ],
                        )

                        st.dataframe(combo_df.head(top_n)[display_cols], width="stretch", hide_index=True)

                        download_df(
                            combo_df,
                            f"best_employees_{selected_test}_{selected_payor}.csv",
                            "Download full selected-combo ranking CSV",
                        )

                        # -----------------------------
                        # Simple visual
                        # -----------------------------
                        st.subheader("Top Employees Chart")

                        chart_df = combo_df.head(top_n).copy()
                        chart_df = chart_df[["matched_employee_name", ranking_metric]].set_index("matched_employee_name")
                        st.bar_chart(chart_df)

                        # -----------------------------
                        # Short interpretation
                        # -----------------------------
                        top_employee = combo_df.iloc[0]
                        st.info(
                            f"For **{selected_test} / {selected_payor}**, the top employee based on `{ranking_metric}` is "
                            f"**{top_employee['matched_employee_name']}**. "
                            "The ranking is based on the recommendation output, which combines productivity, peak performance, "
                            "evidence, and consistency depending on the selected metric."
                        )
