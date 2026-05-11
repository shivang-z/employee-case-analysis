# ui_helpers.py

import pandas as pd
import streamlit as st


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


def safe_top_n_selector(label: str, total_rows: int, default_n: int = 20) -> int:
    """
    Avoid Streamlit slider error when total rows are less than the slider minimum.
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


def apply_shore_filter(df: pd.DataFrame, selected_shore: str) -> pd.DataFrame:
    if df is None:
        return None

    if selected_shore != "All" and "matched_shore" in df.columns:
        return df[df["matched_shore"] == selected_shore].copy()

    return df.copy()


def show_loaded_file_status(df, file_name: str):
    if df is not None:
        st.sidebar.success(f"Loaded {file_name}")
    else:
        st.sidebar.warning(f"{file_name} not loaded")