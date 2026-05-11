# data_loader.py

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


@st.cache_data(show_spinner=False)
def load_csv(path_or_file) -> pd.DataFrame:
    return pd.read_csv(path_or_file)


def find_file(input_dir: str, filename: str):
    file_path = Path(input_dir) / filename
    if file_path.exists():
        return str(file_path)
    return None


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean column names and standardize important fields.

    This function makes sure columns like TestName / PayorName
    become testname / payorname so the rest of the code is consistent.
    """
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
            df[col] = df[col].replace(
                {
                    "nan": np.nan,
                    "None": np.nan,
                    "": np.nan,
                }
            )

    return df


def load_dataset(input_dir: str, filename: str, uploaded_file=None):
    """
    Load dataset either from uploaded Streamlit file or from local folder.
    Uploaded file takes priority.
    """
    try:
        if uploaded_file is not None:
            return clean_columns(load_csv(uploaded_file))

        local_path = find_file(input_dir, filename)
        if local_path:
            return clean_columns(load_csv(local_path))

        return None

    except Exception as e:
        st.sidebar.error(f"Could not load {filename}: {e}")
        return None


def validate_columns(df: pd.DataFrame, required_cols: set, file_name: str) -> bool:
    """
    Validate required columns exist in dataframe.
    """
    if df is None:
        return False

    missing_cols = required_cols - set(df.columns)

    if missing_cols:
        st.error(f"{file_name} is missing required columns: {sorted(missing_cols)}")
        return False

    return True