# Cleaning Notebook — Line-by-Line Learning Guide

A walkthrough of `notebooks/01_data_cleaning.ipynb`. The notebook and the
production script (`scripts/clean_hr_data.py`) apply the **same fixes**, but the
notebook is structured for *exploration and learning*, so it has extra steps the
script doesn't.

This guide explains those differences and every new piece of syntax. If you've
already read `CLEANING_EXPLAINED.md` (the script guide), this focuses on what's
**new or different** here rather than repeating shared concepts.

> Companion file: `docs/CLEANING_EXPLAINED.md` covers the shared building blocks
> (`.apply`, `pd.to_numeric`, `.fillna`, `assert`, etc.) in depth.

---

## Notebook vs. script — the key differences

| Aspect | Notebook | Script |
|--------|----------|--------|
| **Path** | `../data/raw` (runs from inside `notebooks/`) | `data/raw` resolved from project root |
| **Output folder** | `../data/clean_rebuilt` | `data/clean_rebuilt` |
| **Structure** | Linear: load → look → fix one issue → verify → next issue | Functions called from `main()` |
| **Extra steps** | "Show the problem" cells (`.head()`, `value_counts()`) before each fix | None — goes straight to the clean result |
| **Variables** | One DataFrame per table (`emp`, `dept`…) modified in place across cells | Each cleaner takes a df and returns a new one |
| **Purpose** | Teach & demonstrate reasoning | Re-run the pipeline reliably |

The notebook's "look before you fix" rhythm *is* the real analyst workflow:
you inspect, decide, fix, then confirm. The script is what you write **after**
you've figured out the steps.

---

## Setup cell — the path difference explained

```python
import pandas as pd
import numpy as np
from pathlib import Path

RAW = Path("../data/raw")
OUT = Path("../data/clean_rebuilt")
OUT.mkdir(parents=True, exist_ok=True)
```

- `Path("../data/raw")` — the `..` means **"go up one folder"**. The notebook
  lives in `notebooks/`, so `../data/raw` climbs out of `notebooks/` and into
  `data/raw`. The script instead computes the path from the file's location with
  `Path(__file__).resolve().parent.parent` — more robust, but `..` is fine and
  readable in a notebook you run interactively.
- `OUT.mkdir(parents=True, exist_ok=True)` — same as the script: create the
  output folder, making parents if needed, and don't error if it exists.

```python
emp   = pd.read_csv(RAW / "employees.csv", dtype=str)
dept  = pd.read_csv(RAW / "departments.csv", dtype=str)
sal   = pd.read_csv(RAW / "salaries.csv", dtype=str)
rev   = pd.read_csv(RAW / "performance_reviews.csv", dtype=str)
goals = pd.read_csv(RAW / "goals.csv", dtype=str)
```

Same `pd.read_csv(..., dtype=str)` as the script. `dtype=str` (optional arg)
forces every column to load as text so we can see the raw mess before converting
types. `RAW / "employees.csv"` uses `pathlib`'s `/` operator to join the folder
and filename.

```python
print("Raw shapes:")
for name, df in [("employees", emp), ("departments", dept),
                 ("salaries", sal), ("performance_reviews", rev), ("goals", goals)]:
    print(f"  {name:22s} {df.shape}")
```

- `[("employees", emp), ...]` — a **list of tuples**. Each tuple pairs a label
  with its DataFrame so we can loop over both at once.
- `for name, df in [...]:` — **tuple unpacking** in a loop: each pass pulls the
  name and the df out of one tuple.
- `df.shape` — DataFrame property returning `(rows, columns)`.
- `f"  {name:22s} {df.shape}"` — f-string; `:22s` left-pads the name to 22
  chars so the output aligns.

---

## The "look first" cells — unique to the notebook

These cells don't change data; they **reveal** it. This is the most important
habit the notebook teaches that the script can't.

```python
emp.head(12)
```

- `.head(n)` — DataFrame method showing the first `n` rows. `n` is **optional**
  (default 5). In a notebook, putting a DataFrame as the **last line of a cell**
  auto-displays it as a formatted table — no `print()` needed. This is a
  notebook-only convenience (the "rich display").

```python
print("Duplicate rows BEFORE:")
print("  employees          :", emp.duplicated().sum())
print("  performance_reviews:", rev.duplicated().sum())
```

- `.duplicated()` — pandas method returning a Boolean Series: `True` for each
  row that is an exact copy of an earlier row. Optional args: `subset=` (only
  check some columns), `keep=` (`"first"` default / `"last"` / `False`).
- `.sum()` — on a Boolean Series, `True` counts as 1, so `.sum()` **counts** the
  duplicates. (A handy idiom: `boolean_series.sum()` = "how many are True".)

We print this **before** and **after** the fix so the effect is visible — a
verification habit worth keeping.

```python
print("Distinct gender values :", sorted(emp["gender"].dropna().unique()))
print("Distinct status values :", sorted(emp["status"].dropna().unique()))
```

- `.unique()` — returns the distinct values in the column (as an array).
- `.dropna()` — drops missing values first, so `NaN` doesn't clutter the list.
- `sorted(...)` — built-in Python function that returns a **sorted list**.
  Required arg: something iterable. Optional: `key=`, `reverse=`. We sort just so
  the printout is tidy and easy to scan.

**Why this matters:** you cannot write a correct `gender_map` until you've *seen*
every messy variant. This cell is how you discover that `L` and `P` exist before
deciding how to map them.

---

## Fix cells — same logic as the script, shown step by step

### Duplicates
```python
emp = emp.drop_duplicates().reset_index(drop=True)
rev = rev.drop_duplicates().reset_index(drop=True)
```
Identical to the script. `.drop_duplicates()` removes copies; `.reset_index(
drop=True)` renumbers rows and discards the gappy old index.

### Whitespace & casing
```python
def clean_text(series):
    return (series.astype(str)
                  .str.strip()
                  .str.replace(r"\s+", " ", regex=True))

emp["full_name"] = clean_text(emp["full_name"]).str.title()
dept["dept_name"] = clean_text(dept["dept_name"])
```
Same `clean_text` helper as the script. Note it's **defined inside the
notebook** (notebooks often define helpers in-line as you go), whereas the
script groups all helpers at the top. `.str.title()` Title-Cases names.

### Categories
```python
gender_map = {
    "male": "Male", "m": "Male", "l": "Male",
    "female": "Female", "f": "Female", "p": "Female",
}
def map_gender(v):
    if pd.isna(v):
        return np.nan
    return gender_map.get(str(v).strip().lower(), np.nan)

emp["gender"] = emp["gender"].apply(map_gender)
emp["status"] = emp["status"].str.strip().str.title()
```
Same as the script: `.get(key, default)` returns `np.nan` for any unexpected
value instead of crashing. `.apply(map_gender)` runs it on every cell.

```python
print("  gender:", emp["gender"].value_counts(dropna=False).to_dict())
```
- `.value_counts()` — pandas method that **counts how many of each value**. Key
  optional arg: `dropna=False` to *include* missing values in the count (default
  `True` hides them). Great for sanity-checking a categorical column after a fix.
- `.to_dict()` — converts the result to a plain dict for compact printing.

### Dates
```python
from datetime import datetime
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]

def parse_date(value):
    if pd.isna(value) or str(value).strip() == "":
        return pd.NaT
    s = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return pd.NaT

for col in ["hire_date", "termination_date"]:
    emp[col] = emp[col].apply(parse_date)
sal["effective_date"] = sal["effective_date"].apply(parse_date)

print("Unparsed hire_date     :", emp["hire_date"].isna().sum())
```
Identical parser to the script (`datetime.strptime`, try/except over formats,
`pd.NaT` on failure). The extra `print(... .isna().sum())` is a **verification
step**: it counts how many dates failed to parse. Seeing `0` confirms every
format was handled — exactly the kind of check the script assumes but doesn't
display.

### Numbers as text
```python
def clean_salary(v):
    if pd.isna(v):
        return np.nan
    s = str(v).strip().replace("Rp", "").replace(".", "").replace(",", "").replace(" ", "")
    return pd.to_numeric(s, errors="coerce")

emp["monthly_salary_idr"] = emp["monthly_salary_idr"].apply(clean_salary).astype("Int64")

goals["achievement_pct"] = (goals["achievement_pct"].astype(str)
                            .str.replace("%", "", regex=False).str.strip())
goals["achievement_pct"] = pd.to_numeric(goals["achievement_pct"], errors="coerce")
```
Same as the script. Note `.str.replace("%", "", regex=False)` — here
`regex=False` (optional) says "treat `%` as a literal character, not a pattern".
Then `pd.to_numeric(..., errors="coerce")` turns cleaned text into numbers,
making any leftover bad value `NaN`.

### Missing values
```python
for col in ["gender", "city", "employment_type"]:
    emp[col] = emp[col].fillna("Unknown")
sal["change_reason"] = sal["change_reason"].fillna("Unknown")
```
Same deliberate choice as the script: fill only the columns where "Unknown" is a
valid category. `satisfaction_score` and `weight_pct` are **left as NaN** on
purpose — inventing a measured value would bias the analysis. The notebook spells
this reasoning out in its markdown; the script just does it.

### Types & validation
```python
emp["employee_id"] = pd.to_numeric(emp["employee_id"], errors="coerce").astype("Int64")
...
assert emp["employee_id"].is_unique, "employee_id should be unique!"
orphans = set(emp["dept_id"].dropna()) - set(dept["dept_id"].dropna())
assert not orphans, f"employees reference missing departments: {orphans}"
```
The same casts (`"Int64"` nullable integers for IDs, floats for scores) and the
same `assert` integrity checks as the script's `validate()` function — just
written inline in a cell instead of wrapped in a function. See
`CLEANING_EXPLAINED.md` §7 for a full breakdown of the set math and `assert`.

### Save
```python
emp.to_csv(OUT / "employees.csv", index=False)
...
for f in sorted(OUT.glob("*.csv")):
    print("  ", f.name)
```
- `.to_csv(path, index=False)` — write the table out; `index=False` skips the
  row-number column.
- `OUT.glob("*.csv")` — `Path` method: finds files matching a pattern. `*` means
  "anything", so `*.csv` lists every CSV in the folder. Returns a generator,
  which `sorted(...)` turns into an ordered list.
- `f.name` — `Path` property: just the filename (no folder path).

---

## Why keep both versions in the repo?

Recruiters like seeing this pairing, because it shows two real skills:

1. **The notebook** proves you can *explore* — inspect data, reason about each
   problem, and verify your fix. That's analytical thinking.
2. **The script** proves you can *productionise* — take what you learned and
   turn it into clean, reusable, importable code with validation.

Together they tell the story: "I investigated the data here, then turned my
findings into a reliable pipeline there." That's exactly the arc of real work.

---

## Notebook-specific things worth remembering

- **Cells share state.** A variable made in cell 3 is available in cell 8. Great
  for building up step by step — but if you run cells out of order you can
  confuse yourself. Rule of thumb: when in doubt, *Restart & Run All* to confirm
  the notebook works top-to-bottom (which is exactly how we tested it).
- **Last line auto-displays.** `emp.head()` on its own line shows a table; you
  rarely need `print()` for DataFrames in a notebook.
- **Markdown cells carry the reasoning.** In a portfolio notebook the prose is
  half the value — it shows you understand *why*, not just *how*.
