# app.py

import numpy as np
import pandas as pd
import streamlit as st

from config import (
    APP_ICON,
    APP_TITLE,
    DEFAULT_INPUT_DIR,
    HISTORICAL_FILE,
    RECOMMENDATIONS_FILE,
)

from data_loader import (
    load_dataset,
    validate_columns,
)

from analytics import (
    prepare_recommendations,
    get_score_col,
    get_rank_col,
    build_employee_summary,
    create_opportunity_finder,
    create_combo_coverage_summary,
)

from ui_helpers import (
    format_num,
    existing_cols,
    download_df,
    safe_top_n_selector,
    apply_shore_filter,
    show_loaded_file_status,
)


# ============================================================
# Page config
# ============================================================

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
)


# ============================================================
# Sidebar data loading
# ============================================================

st.sidebar.title("Data")

input_dir = st.sidebar.text_input(
    "Input folder",
    value=DEFAULT_INPUT_DIR,
)

st.sidebar.caption("Upload files only if they are not available locally.")

uploaded_hist = st.sidebar.file_uploader(
    "Upload historical_combo.csv",
    type=["csv"],
)

uploaded_recs = st.sidebar.file_uploader(
    "Upload recency_recommendations.csv",
    type=["csv"],
)


historical_combo = load_dataset(
    input_dir=input_dir,
    filename=HISTORICAL_FILE,
    uploaded_file=uploaded_hist,
)

recommendations = load_dataset(
    input_dir=input_dir,
    filename=RECOMMENDATIONS_FILE,
    uploaded_file=uploaded_recs,
)

if recommendations is not None:
    recommendations = prepare_recommendations(recommendations)


show_loaded_file_status(historical_combo, HISTORICAL_FILE)
show_loaded_file_status(recommendations, RECOMMENDATIONS_FILE)


# ============================================================
# Header
# ============================================================

st.title(APP_TITLE)

st.write(
    "This app helps review employee-level performance, recommendation rankings, "
    "and hidden opportunity areas across TestName / PayorName combinations."
)


if historical_combo is None and recommendations is None:
    st.error(
        "No data loaded. Please place the CSV files in the input folder "
        "or upload them from the sidebar."
    )
    st.stop()


# ============================================================
# Global filters
# ============================================================

shore_values = set()

for df in [historical_combo, recommendations]:
    if df is not None and "matched_shore" in df.columns:
        shore_values.update(df["matched_shore"].dropna().astype(str).unique())


selected_shore = "All"

if shore_values:
    selected_shore = st.sidebar.selectbox(
        "Shore filter",
        ["All"] + sorted(shore_values),
    )


historical_combo_filtered = apply_shore_filter(historical_combo, selected_shore)
recommendations_filtered = apply_shore_filter(recommendations, selected_shore)


# ============================================================
# Tabs
# ============================================================

tab_employee, tab_combo, tab_opportunity, tab_coverage = st.tabs(
    [
        "Employee Deep-Dive",
        "Best Employees by Test / Payor",
        "Opportunity Finder",
        "Coverage Risk",
    ]
)


# ============================================================
# TAB 1: Employee Deep-Dive
# ============================================================

with tab_employee:
    st.header("Employee Deep-Dive")

    st.write(
        "Select one employee to review historical performance and recommended combinations."
    )

    employee_source = None

    if (
        historical_combo_filtered is not None
        and "matched_employee_name" in historical_combo_filtered.columns
    ):
        employee_source = historical_combo_filtered

    elif (
        recommendations_filtered is not None
        and "matched_employee_name" in recommendations_filtered.columns
    ):
        employee_source = recommendations_filtered

    if employee_source is None:
        st.warning("No employee field found in the loaded files.")

    else:
        employee_list = sorted(
            employee_source["matched_employee_name"].dropna().astype(str).unique()
        )

        if not employee_list:
            st.warning("No employees found after applying filters.")

        else:
            selected_employee = st.selectbox(
                "Select employee",
                employee_list,
            )

            # -----------------------------
            # Historical summary
            # -----------------------------

            if historical_combo_filtered is not None:
                required_cols = {
                    "matched_employee_name",
                    "testname",
                    "payorname",
                }

                if validate_columns(
                    historical_combo_filtered,
                    required_cols,
                    HISTORICAL_FILE,
                ):
                    emp_hist = historical_combo_filtered[
                        historical_combo_filtered["matched_employee_name"].astype(str)
                        == selected_employee
                    ].copy()

                    if not emp_hist.empty:
                        st.subheader("Historical Performance Summary")

                        summary = build_employee_summary(
                            historical_combo_filtered,
                            selected_employee,
                        )

                        c1, c2, c3, c4, c5 = st.columns(5)

                        c1.metric(
                            "Total Unique Cases",
                            format_num(summary.get("total_unique_cases"), 0),
                        )

                        c2.metric(
                            "Total Touches",
                            format_num(summary.get("total_touches"), 0),
                        )

                        c3.metric(
                            "Best Avg Daily Cases",
                            format_num(summary.get("best_avg_daily_cases"), 2),
                        )

                        c4.metric(
                            "Best Peak Daily Cases",
                            format_num(summary.get("best_peak_daily_cases"), 0),
                        )

                        c5.metric(
                            "Combos Worked",
                            format_num(summary.get("combos_worked"), 0),
                        )

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
                            sort_metric = st.selectbox(
                                "Sort historical combinations by",
                                sort_options,
                            )

                            ascending = sort_metric in [
                                "avg_touches_per_case",
                                "consistency_cv_cases",
                            ]

                            emp_hist = emp_hist.sort_values(
                                sort_metric,
                                ascending=ascending,
                            ).reset_index(drop=True)

                        hist_display_cols = existing_cols(
                            emp_hist,
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

                        st.dataframe(
                            emp_hist[hist_display_cols],
                            width="stretch",
                            hide_index=True,
                        )

                        download_df(
                            emp_hist,
                            f"{selected_employee}_historical_performance.csv",
                            "Download historical performance",
                        )

                    else:
                        st.info("No historical rows found for this employee.")

            st.divider()

            # -----------------------------
            # Recommendations for employee
            # -----------------------------

            st.subheader("Recommended TestName / PayorName Combinations")

            if recommendations_filtered is None:
                st.warning("recency_recommendations.csv is required to show recommendations.")

            else:
                required_cols = {
                    "matched_employee_name",
                    "testname",
                    "payorname",
                }

                if validate_columns(
                    recommendations_filtered,
                    required_cols,
                    RECOMMENDATIONS_FILE,
                ):
                    emp_recs = recommendations_filtered[
                        recommendations_filtered["matched_employee_name"].astype(str)
                        == selected_employee
                    ].copy()

                    if emp_recs.empty:
                        st.info("No recommendation rows found for this employee.")

                    else:
                        score_col = get_score_col(emp_recs)
                        rank_col = get_rank_col(emp_recs)

                        if rank_col:
                            emp_recs = emp_recs.sort_values(
                                rank_col,
                                ascending=True,
                            )

                        elif score_col:
                            emp_recs = emp_recs.sort_values(
                                score_col,
                                ascending=False,
                            )

                        top_n = safe_top_n_selector(
                            "Number of recommendations to show",
                            len(emp_recs),
                            default_n=10,
                        )

                        rec_display_cols = existing_cols(
                            emp_recs,
                            [
                                rank_col,
                                "testname",
                                "payorname",
                                "matched_shore",
                                "observed_days",
                                "confidence_level",
                                "recency_weighted_avg_cases",
                                "avg_daily_unique_cases",
                                "max_daily_unique_cases",
                                "consistency_score",
                                score_col,
                                "recommendation_reason",
                            ],
                        )

                        st.dataframe(
                            emp_recs.head(top_n)[rec_display_cols],
                            width="stretch",
                            hide_index=True,
                        )

                        if score_col:
                            chart_df = emp_recs.head(top_n).copy()
                            chart_df["combo"] = (
                                chart_df["testname"].astype(str)
                                + " / "
                                + chart_df["payorname"].astype(str)
                            )

                            chart_df = chart_df[["combo", score_col]].set_index("combo")
                            st.bar_chart(chart_df)

                        download_df(
                            emp_recs,
                            f"{selected_employee}_recommendations.csv",
                            "Download employee recommendations",
                        )


# ============================================================
# TAB 2: Best Employees by Test / Payor
# ============================================================

with tab_combo:
    st.header("Best Employees by TestName / PayorName")

    st.write(
        "Select a TestName / PayorName combination to see which employees are recommended."
    )

    if recommendations_filtered is None:
        st.warning("recency_recommendations.csv is required for combination-level ranking.")

    else:
        required_cols = {
            "matched_employee_name",
            "testname",
            "payorname",
        }

        if validate_columns(
            recommendations_filtered,
            required_cols,
            RECOMMENDATIONS_FILE,
        ):
            tests = sorted(
                recommendations_filtered["testname"].dropna().astype(str).unique()
            )

            if not tests:
                st.warning("No TestName values found after filters.")

            else:
                col1, col2, col3 = st.columns(3)

                with col1:
                    selected_test = st.selectbox(
                        "Select TestName",
                        tests,
                    )

                payors = sorted(
                    recommendations_filtered.loc[
                        recommendations_filtered["testname"].astype(str)
                        == selected_test,
                        "payorname",
                    ]
                    .dropna()
                    .astype(str)
                    .unique()
                )

                with col2:
                    selected_payor = st.selectbox(
                        "Select PayorName",
                        payors,
                    )

                combo_df = recommendations_filtered[
                    (
                        recommendations_filtered["testname"].astype(str)
                        == selected_test
                    )
                    & (
                        recommendations_filtered["payorname"].astype(str)
                        == selected_payor
                    )
                ].copy()

                if combo_df.empty:
                    st.warning("No employees found for this combination.")

                else:
                    score_col = get_score_col(combo_df)

                    metric_options = existing_cols(
                        combo_df,
                        [
                            score_col,
                            "recency_weighted_avg_cases",
                            "avg_daily_unique_cases",
                            "max_daily_unique_cases",
                            "observed_days",
                            "consistency_score",
                        ],
                    )

                    if not metric_options:
                        st.error("No ranking metric found.")
                        st.stop()

                    with col3:
                        ranking_metric = st.selectbox(
                            "Rank employees by",
                            metric_options,
                        )

                    combo_df = combo_df.sort_values(
                        ranking_metric,
                        ascending=False,
                    ).reset_index(drop=True)

                    combo_df.insert(
                        0,
                        "rank_for_selected_combo",
                        np.arange(1, len(combo_df) + 1),
                    )

                    c1, c2, c3, c4 = st.columns(4)

                    c1.metric(
                        "Employees Found",
                        format_num(combo_df["matched_employee_name"].nunique(), 0),
                    )

                    if score_col:
                        c2.metric(
                            "Top Score",
                            format_num(combo_df[score_col].max(), 3),
                        )
                    else:
                        c2.metric("Top Score", "-")

                    if "recency_weighted_avg_cases" in combo_df.columns:
                        c3.metric(
                            "Best Recent Avg Cases",
                            format_num(combo_df["recency_weighted_avg_cases"].max(), 2),
                        )
                    else:
                        c3.metric("Best Recent Avg Cases", "-")

                    if "max_daily_unique_cases" in combo_df.columns:
                        c4.metric(
                            "Best Peak Daily Cases",
                            format_num(combo_df["max_daily_unique_cases"].max(), 0),
                        )
                    else:
                        c4.metric("Best Peak Daily Cases", "-")

                    top_n = safe_top_n_selector(
                        "Number of employees to show",
                        len(combo_df),
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
                            "confidence_level",
                            "recency_weighted_avg_cases",
                            "avg_daily_unique_cases",
                            "max_daily_unique_cases",
                            "consistency_score",
                            score_col,
                            "recommendation_reason",
                        ],
                    )

                    st.dataframe(
                        combo_df.head(top_n)[display_cols],
                        width="stretch",
                        hide_index=True,
                    )

                    chart_df = combo_df.head(top_n).copy()
                    chart_df = chart_df[
                        ["matched_employee_name", ranking_metric]
                    ].set_index("matched_employee_name")

                    st.bar_chart(chart_df)

                    download_df(
                        combo_df,
                        f"recommended_employees_{selected_test}_{selected_payor}.csv",
                        "Download selected-combo recommendations",
                    )


# ============================================================
# TAB 3: Opportunity Finder
# ============================================================

with tab_opportunity:
    st.header("Opportunity Finder")

    st.write(
        "This view identifies employees who have strong recommendation scores "
        "but relatively low usage/exposure. These may represent hidden strengths "
        "or underutilized capacity."
    )

    if recommendations_filtered is None:
        st.warning("recency_recommendations.csv is required for Opportunity Finder.")

    else:
        required_cols = {
            "matched_employee_name",
            "testname",
            "payorname",
            "observed_days",
        }

        if validate_columns(
            recommendations_filtered,
            required_cols,
            RECOMMENDATIONS_FILE,
        ):
            try:
                opportunity_df = create_opportunity_finder(recommendations_filtered)

                high_opp_df = opportunity_df[
                    opportunity_df["opportunity_label"] == "High Opportunity"
                ].copy()

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    "Total Opportunities",
                    format_num(len(high_opp_df), 0),
                )

                c2.metric(
                    "Employees with Opportunities",
                    format_num(high_opp_df["matched_employee_name"].nunique(), 0),
                )

                c3.metric(
                    "Combos with Opportunities",
                    format_num(
                        high_opp_df[["testname", "payorname"]]
                        .drop_duplicates()
                        .shape[0],
                        0,
                    ),
                )

                label_filter = st.selectbox(
                    "Opportunity filter",
                    [
                        "High Opportunity",
                        "Strong but already used",
                        "Low exposure",
                        "Normal",
                        "All",
                    ],
                )

                if label_filter == "All":
                    display_df = opportunity_df.copy()
                else:
                    display_df = opportunity_df[
                        opportunity_df["opportunity_label"] == label_filter
                    ].copy()

                top_n = safe_top_n_selector(
                    "Number of rows to show",
                    len(display_df),
                    default_n=25,
                )

                score_col = get_score_col(display_df)

                display_cols = existing_cols(
                    display_df,
                    [
                        "opportunity_label",
                        "opportunity_score",
                        "matched_employee_name",
                        "matched_email",
                        "matched_shore",
                        "testname",
                        "payorname",
                        "observed_days",
                        "confidence_level",
                        "recency_weighted_avg_cases",
                        "avg_daily_unique_cases",
                        "max_daily_unique_cases",
                        score_col,
                        "recommendation_reason",
                    ],
                )

                st.dataframe(
                    display_df.head(top_n)[display_cols],
                    width="stretch",
                    hide_index=True,
                )

                if not display_df.empty:
                    chart_df = display_df.head(top_n).copy()
                    chart_df["employee_combo"] = (
                        chart_df["matched_employee_name"].astype(str)
                        + " | "
                        + chart_df["testname"].astype(str)
                        + " / "
                        + chart_df["payorname"].astype(str)
                    )

                    chart_df = chart_df[
                        ["employee_combo", "opportunity_score"]
                    ].set_index("employee_combo")

                    st.bar_chart(chart_df)

                download_df(
                    display_df,
                    "opportunity_finder_output.csv",
                    "Download opportunity finder output",
                )

                st.info(
                    "Interpretation: High Opportunity means the employee has a strong "
                    "recommendation score but low observed usage. This can help identify "
                    "employees who may be underutilized for a specific TestName / PayorName."
                )

            except Exception as e:
                st.error(f"Could not create Opportunity Finder output: {e}")


# ============================================================
# TAB 4: Coverage Risk
# ============================================================

with tab_coverage:
    st.header("Coverage Risk")

    st.write(
        "This view shows which TestName / PayorName combinations may depend on too few strong employees."
    )

    if recommendations_filtered is None:
        st.warning("recency_recommendations.csv is required for Coverage Risk.")

    else:
        try:
            coverage_df = create_combo_coverage_summary(recommendations_filtered)

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Total Combos",
                format_num(len(coverage_df), 0),
            )

            c2.metric(
                "Critical Risk Combos",
                format_num((coverage_df["coverage_risk"] == "Critical").sum(), 0),
            )

            c3.metric(
                "Medium Risk Combos",
                format_num((coverage_df["coverage_risk"] == "Medium").sum(), 0),
            )

            risk_filter = st.selectbox(
                "Coverage risk filter",
                ["Critical", "Medium", "Low", "All"],
            )

            if risk_filter == "All":
                display_coverage = coverage_df.copy()
            else:
                display_coverage = coverage_df[
                    coverage_df["coverage_risk"] == risk_filter
                ].copy()

            st.dataframe(
                display_coverage,
                width="stretch",
                hide_index=True,
            )

            download_df(
                display_coverage,
                "coverage_risk_output.csv",
                "Download coverage risk output",
            )

            st.info(
                "Interpretation: Critical or Medium risk means there are only a few strong "
                "recommended employees for that TestName / PayorName combination. "
                "This can help prioritize backup planning and cross-training."
            )

        except Exception as e:
            st.error(f"Could not create Coverage Risk output: {e}")