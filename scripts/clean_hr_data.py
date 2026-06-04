"""
clean_hr_data.py
----------------
Production-style cleaning pipeline for the Nusantara Tech HR dataset.

Reads messy CSVs from data/raw/, applies the same transformations documented
step-by-step in notebooks/01_data_cleaning.ipynb, validates referential
integrity, and writes clean CSVs to data/clean_rebuilt/.

Usage:
    python scripts/clean_hr_data.py

Design: each cleaning concern is a small, named function. main() wires them
together. This mirrors how a reusable ETL step would be structured.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT = Path(__file__).resolve().parent.parent / "data" / "clean_rebuilt"

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]
GENDER_MAP = {
    "male": "Male", "m": "Male", "l": "Male",
    "female": "Female", "f": "Female", "p": "Female",
}


# --------------------------------------------------------------------------- #
# Reusable cleaning helpers
# --------------------------------------------------------------------------- #
def clean_text(series: pd.Series) -> pd.Series:
    """Strip ends and collapse internal whitespace to single spaces."""
    return (series.astype(str)
                  .str.strip()
                  .str.replace(r"\s+", " ", regex=True))


def parse_date(value) -> pd.Timestamp:
    """Parse a date string of unknown format; return NaT if none match."""
    if pd.isna(value) or str(value).strip() == "":
        return pd.NaT
    s = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return pd.NaT


def map_gender(value):
    if pd.isna(value):
        return np.nan
    return GENDER_MAP.get(str(value).strip().lower(), np.nan)


def clean_salary(value):
    """Turn 'Rp30.100.000' / '30100000 ' / 30100000 into an int."""
    if pd.isna(value):
        return np.nan
    s = (str(value).strip()
         .replace("Rp", "").replace(".", "").replace(",", "").replace(" ", ""))
    return pd.to_numeric(s, errors="coerce")


# --------------------------------------------------------------------------- #
# Per-table cleaners
# --------------------------------------------------------------------------- #
def clean_departments(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["dept_name"] = clean_text(df["dept_name"])
    df["dept_id"] = pd.to_numeric(df["dept_id"], errors="coerce").astype("Int64")
    df["salary_band_mid"] = pd.to_numeric(df["salary_band_mid"], errors="coerce")
    return df


def clean_employees(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates().reset_index(drop=True)

    df["full_name"] = clean_text(df["full_name"]).str.title()
    df["gender"] = df["gender"].apply(map_gender)
    df["status"] = df["status"].str.strip().str.title()

    for col in ["hire_date", "termination_date"]:
        df[col] = df[col].apply(parse_date)

    df["monthly_salary_idr"] = df["monthly_salary_idr"].apply(clean_salary).astype("Int64")

    # Fill only where "unknown" is a legitimate category
    for col in ["gender", "city", "employment_type"]:
        df[col] = df[col].fillna("Unknown")
    # satisfaction_score intentionally left NaN where missing

    # Types
    for col in ["employee_id", "dept_id", "manager_id"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in ["satisfaction_score", "last_performance_score"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def clean_salaries(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["effective_date"] = df["effective_date"].apply(parse_date)
    df["change_reason"] = df["change_reason"].fillna("Unknown")
    for col in ["salary_id", "employee_id"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    df["monthly_salary_idr"] = pd.to_numeric(df["monthly_salary_idr"], errors="coerce").astype("Int64")
    return df


def clean_reviews(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates().reset_index(drop=True)
    for col in ["review_id", "employee_id"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    df["review_score"] = pd.to_numeric(df["review_score"], errors="coerce")
    df["reviewer_id"] = pd.to_numeric(df["reviewer_id"], errors="coerce").astype("Int64")
    return df


def clean_goals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["achievement_pct"] = (df["achievement_pct"].astype(str)
                             .str.replace("%", "", regex=False).str.strip())
    df["achievement_pct"] = pd.to_numeric(df["achievement_pct"], errors="coerce")
    df["weight_pct"] = pd.to_numeric(df["weight_pct"], errors="coerce")
    for col in ["goal_id", "employee_id"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate(emp, dept):
    assert emp["employee_id"].is_unique, "employee_id not unique"
    orphans = set(emp["dept_id"].dropna()) - set(dept["dept_id"].dropna())
    assert not orphans, f"employees reference missing departments: {orphans}"
    mgr = set(emp["manager_id"].dropna())
    ids = set(emp["employee_id"].dropna())
    assert mgr.issubset(ids), "manager_id values that aren't employees"
    assert set(emp["gender"].unique()).issubset({"Male", "Female", "Unknown"})
    assert (emp["monthly_salary_idr"].dropna() > 0).all(), "non-positive salary"


# --------------------------------------------------------------------------- #
def main():
    OUT.mkdir(parents=True, exist_ok=True)

    dept  = clean_departments(pd.read_csv(RAW / "departments.csv", dtype=str))
    emp   = clean_employees(pd.read_csv(RAW / "employees.csv", dtype=str))
    sal   = clean_salaries(pd.read_csv(RAW / "salaries.csv", dtype=str))
    rev   = clean_reviews(pd.read_csv(RAW / "performance_reviews.csv", dtype=str))
    goals = clean_goals(pd.read_csv(RAW / "goals.csv", dtype=str))

    validate(emp, dept)

    tables = {"departments": dept, "employees": emp, "salaries": sal,
              "performance_reviews": rev, "goals": goals}
    for name, df in tables.items():
        df.to_csv(OUT / f"{name}.csv", index=False)
        print(f"  wrote {name:22s} {df.shape}")

    print("Cleaning complete. Validation passed.")


if __name__ == "__main__":
    main()
