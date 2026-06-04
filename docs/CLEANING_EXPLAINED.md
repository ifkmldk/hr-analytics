# Cleaning Script — Line-by-Line Learning Guide

A walkthrough of `scripts/clean_hr_data.py` that explains **every** piece of
syntax: what each function does, which library it comes from, and which
arguments are required vs optional. Written so you can learn the *why* behind
each line, even without typing it yourself.

> Read this next to the actual script. Section numbers follow the code's
> top-to-bottom order.

---

## 0. The imports — where everything comes from

```python
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
```

| Line | What it does |
|------|--------------|
| `from __future__ import annotations` | A forward-compatibility switch. It makes Python treat type hints (like `-> pd.Series`) as plain text instead of evaluating them. Harmless, lets us annotate freely. Must be the **first** import. |
| `from datetime import datetime` | Pulls the `datetime` **class** out of Python's built-in `datetime` module. We use it to parse date strings. |
| `from pathlib import Path` | Pulls the `Path` class from the built-in `pathlib` module — the modern way to handle file paths (instead of gluing strings with `/`). |
| `import numpy as np` | NumPy: numerical library. We mainly use `np.nan` (the "missing number" marker). `as np` is just a nickname so we type `np.` instead of `numpy.`. |
| `import pandas as pd` | Pandas: the core data-analysis library. Gives us the `DataFrame` (a table) and `Series` (a single column). `as pd` is the universal convention. |

**`import X` vs `from X import Y`:** `import pandas as pd` brings in the whole
library (you call `pd.read_csv`). `from datetime import datetime` brings in just
one piece (you call `datetime` directly, no prefix).

---

## 1. Module-level constants

```python
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT = Path(__file__).resolve().parent.parent / "data" / "clean_rebuilt"
```

- `__file__` — a built-in variable holding the path of *this script file*.
- `.resolve()` — a `Path` **method** that turns it into a full absolute path.
  No required args.
- `.parent` — a `Path` **property** giving the containing folder. Chaining
  `.parent.parent` walks up two levels (from `scripts/` up to the project root).
- `/ "data" / "raw"` — `pathlib` cleverly **overloads the `/` operator** so you
  build paths by "dividing". This produces `.../data/raw` and works on Windows
  and Mac/Linux alike. This is why `Path` is better than string concatenation.

```python
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]
```

A plain Python **list** of format strings. The `%` codes are
`strptime` directives: `%Y`=4-digit year, `%m`=month, `%d`=day. Order matters —
we try them top to bottom.

```python
GENDER_MAP = {
    "male": "Male", "m": "Male", "l": "Male",
    "female": "Female", "f": "Female", "p": "Female",
}
```

A **dictionary** (`{key: value}`). Maps every messy variant (left) to one clean
value (right). Dictionaries give instant lookups — the backbone of standardising
categories.

---

## 2. `clean_text()` — strip and collapse whitespace

```python
def clean_text(series: pd.Series) -> pd.Series:
    """Strip ends and collapse internal whitespace to single spaces."""
    return (series.astype(str)
                  .str.strip()
                  .str.replace(r"\s+", " ", regex=True))
```

- `def clean_text(series):` — defines a function named `clean_text` taking one
  argument, `series`.
- `series: pd.Series` and `-> pd.Series` — **type hints**. They say "expects a
  pandas Series, returns a Series". Optional and not enforced, but they document
  intent and help editors autocomplete.
- `"""..."""` — a **docstring**: documentation shown when someone runs
  `help(clean_text)`.

The transformation chain (read top to bottom, each step feeds the next):

| Call | Library / source | Required args | Optional args | What it does |
|------|------------------|---------------|---------------|--------------|
| `.astype(str)` | pandas Series method | the target type (`str`) | — | Forces every value to text, so string ops won't crash on numbers/NaN. |
| `.str.strip()` | pandas `.str` accessor | none | `to_strip` (chars to remove; default = whitespace) | Removes leading/trailing spaces. The `.str` accessor lets you run Python string methods on a whole column at once. |
| `.str.replace(r"\s+", " ", regex=True)` | pandas `.str` accessor | `pat` (pattern), `repl` (replacement) | `regex=` (default depends on version — set explicitly), `n=`, `case=`, `flags=` | Replaces any run of whitespace (`\s+`) with a single space. `r"..."` is a **raw string** so backslashes are literal. `regex=True` says "treat `pat` as a regular expression". |

The parentheses around the whole chain let us put each `.method()` on its own
line for readability — a common pandas style.

---

## 3. `parse_date()` — handle mixed date formats

```python
def parse_date(value) -> pd.Timestamp:
    if pd.isna(value) or str(value).strip() == "":
        return pd.NaT
    s = str(value).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return pd.NaT
```

- `pd.isna(value)` — pandas **function** (not a method): returns `True` if the
  value is missing (`NaN`, `None`, `NaT`). One required arg.
- `or str(value).strip() == ""` — also treat empty strings as missing. `or`
  means "if either condition is true".
- `return pd.NaT` — `NaT` = "Not a Time", pandas' missing-value marker *for
  dates* (the datetime equivalent of `NaN`).
- `for fmt in DATE_FORMATS:` — loops over each format string we defined.
- `try: ... except ValueError: continue` — **error handling**. We *attempt* to
  parse; if `strptime` raises `ValueError` (wrong format), we `continue` to the
  next format instead of crashing.
- `datetime.strptime(s, fmt)` — from the `datetime` class. "**str p**arse
  **time**": turns a string into a real datetime. Two **required** args:
  the string `s` and the format `fmt`. Returns the first format that succeeds.
- Final `return pd.NaT` — if *no* format matched, mark it missing so we can
  inspect it later (better than guessing).

---

## 4. `map_gender()` — canonicalise categories

```python
def map_gender(value):
    if pd.isna(value):
        return np.nan
    return GENDER_MAP.get(str(value).strip().lower(), np.nan)
```

- `.lower()` — built-in string method; lowercases so `"M"`, `"m"`, `"Male"` all
  become comparable to our lowercase dictionary keys.
- `GENDER_MAP.get(key, default)` — dictionary **method** `.get()`. Required arg:
  the `key` to look up. Optional second arg: the **default** returned if the key
  is missing. Here the default is `np.nan` — so any unexpected value safely
  becomes "missing" rather than raising a `KeyError` (which `GENDER_MAP[key]`
  would do). This is why `.get()` is safer than `[]` for lookups that might miss.

---

## 5. `clean_salary()` — text to number

```python
def clean_salary(value):
    if pd.isna(value):
        return np.nan
    s = (str(value).strip()
         .replace("Rp", "").replace(".", "").replace(",", "").replace(" ", ""))
    return pd.to_numeric(s, errors="coerce")
```

- Chained `.replace(old, new)` — built-in **string** method (not the pandas
  one). Two required args: the substring to find and what to replace it with.
  We strip out `Rp`, thousands dots, commas, and spaces, leaving only digits.
- `pd.to_numeric(s, errors="coerce")` — pandas **function** that converts to a
  number. Required arg: the value/series. Key optional arg: `errors=`:
  - `"raise"` (default) — crash on bad input,
  - `"coerce"` — turn bad input into `NaN` (what we want — robust),
  - `"ignore"` — leave bad input unchanged.

---

## 6. Per-table cleaner: `clean_employees()` (the big one)

```python
def clean_employees(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates().reset_index(drop=True)
```

- `.drop_duplicates()` — pandas DataFrame method. No required args. Useful
  optionals: `subset=` (check only certain columns), `keep=` (`"first"` default,
  `"last"`, or `False` to drop all copies). Removes identical rows.
- `.reset_index(drop=True)` — after dropping rows the index has gaps (0,1,4,5…).
  This renumbers it 0,1,2,3… `drop=True` (optional, default `False`) throws away
  the old index instead of keeping it as a new column.

```python
    df["full_name"] = clean_text(df["full_name"]).str.title()
```

- `df["full_name"]` — selects one column (a Series). Assigning back to it
  overwrites that column.
- `.str.title()` — `.str` accessor + `title()`: Title-Cases Each Word.

```python
    df["gender"] = df["gender"].apply(map_gender)
```

- `.apply(func)` — pandas method that runs a function on **every value** in the
  Series. Required arg: the function (note: `map_gender`, no parentheses — we
  pass the function itself, not its result). Optional: `args=` for extra
  positional args. This is how we apply our custom cleaners element-by-element.

```python
    for col in ["hire_date", "termination_date"]:
        df[col] = df[col].apply(parse_date)
```

A loop so we don't repeat the same line for two columns. `df[col]` uses the loop
variable to select each column in turn.

```python
    df["monthly_salary_idr"] = df["monthly_salary_idr"].apply(clean_salary).astype("Int64")
```

- `.astype("Int64")` — note the **capital `I`**. `"Int64"` (nullable integer)
  can hold whole numbers **and** missing values. Lowercase `"int64"` cannot hold
  `NaN`, so we use the capitalised nullable type here.

```python
    for col in ["gender", "city", "employment_type"]:
        df[col] = df[col].fillna("Unknown")
```

- `.fillna(value)` — pandas method that replaces missing values. Required arg:
  what to fill with. Optional: `method=` (e.g. forward-fill), `limit=`. We fill
  these *categorical* columns with `"Unknown"` — a legitimate category. We
  deliberately do **not** fill `satisfaction_score` (a measured value).

```python
    for col in ["employee_id", "dept_id", "manager_id"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in ["satisfaction_score", "last_performance_score"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df
```

IDs become nullable integers; scores stay floats (they have decimals). `return
df` hands back the cleaned table.

> The other per-table cleaners (`clean_departments`, `clean_salaries`,
> `clean_reviews`, `clean_goals`) use the **same building blocks** — `.copy()`,
> `pd.to_numeric`, `.fillna`, `.apply`, `.str` ops — so once you understand this
> one, you understand them all. One new call: `.copy()` makes an independent copy
> so edits don't accidentally change the original DataFrame (avoids pandas'
> "SettingWithCopyWarning").

---

## 7. `validate()` — guard rails with `assert`

```python
def validate(emp, dept):
    assert emp["employee_id"].is_unique, "employee_id not unique"
    orphans = set(emp["dept_id"].dropna()) - set(dept["dept_id"].dropna())
    assert not orphans, f"employees reference missing departments: {orphans}"
    mgr = set(emp["manager_id"].dropna())
    ids = set(emp["employee_id"].dropna())
    assert mgr.issubset(ids), "manager_id values that aren't employees"
    assert set(emp["gender"].unique()).issubset({"Male", "Female", "Unknown"})
    assert (emp["monthly_salary_idr"].dropna() > 0).all(), "non-positive salary"
```

- `assert condition, "message"` — a Python **statement**, not a function. If
  `condition` is `False`, it raises `AssertionError` with your message and stops
  the program. The message is optional but recommended. Asserts are cheap
  insurance: they catch data problems *before* they reach the analysis.
- `.is_unique` — pandas Series **property** (no parentheses): `True` if no
  duplicates.
- `.dropna()` — removes missing values before comparing.
- `set(...)` — built-in: makes a **set** (unordered, unique items). Sets support
  math: `A - B` = items in A not in B (here, dept IDs used by employees that
  don't exist in the departments table = "orphans").
- `.issubset(other)` — set method: `True` if every item is also in `other`.
  We use it to confirm every `manager_id` is a real `employee_id`.
- `.unique()` — pandas method returning the distinct values in a column.
- `(series > 0).all()` — `series > 0` makes a Series of True/False; `.all()`
  returns `True` only if *every* value is True. Confirms all salaries are
  positive.
- `f"...{orphans}"` — an **f-string**: text with `{variable}` slots filled in at
  runtime. Handy for readable error messages.

---

## 8. `main()` — wiring it together

```python
def main():
    OUT.mkdir(parents=True, exist_ok=True)

    dept  = clean_departments(pd.read_csv(RAW / "departments.csv", dtype=str))
    emp   = clean_employees(pd.read_csv(RAW / "employees.csv", dtype=str))
    ...
    validate(emp, dept)

    tables = {"departments": dept, "employees": emp, ...}
    for name, df in tables.items():
        df.to_csv(OUT / f"{name}.csv", index=False)
        print(f"  wrote {name:22s} {df.shape}")

    print("Cleaning complete. Validation passed.")
```

- `OUT.mkdir(parents=True, exist_ok=True)` — `Path` method to create the output
  folder. Optional args: `parents=True` creates intermediate folders too;
  `exist_ok=True` means "don't error if it already exists".
- `pd.read_csv(path, dtype=str)` — pandas function to load a CSV. Required arg:
  the file path. Key optional arg here: `dtype=str` forces **everything** to be
  read as text, so we see the raw mess before converting types ourselves.
  (Other common optionals: `sep=`, `header=`, `na_values=`, `usecols=`.)
- We call each cleaner on each freshly-loaded table, then `validate()`.
- `tables = {...}` — a dict pairing each output name with its DataFrame.
- `for name, df in tables.items():` — `.items()` yields `(key, value)` pairs so
  we can loop over name **and** DataFrame together.
- `.to_csv(path, index=False)` — writes a DataFrame to CSV. Required: the path.
  `index=False` (optional) stops pandas writing the row-number index as an extra
  column — almost always what you want for clean output.
- `.shape` — DataFrame property: a `(rows, columns)` tuple.
- `f"{name:22s}"` — f-string **formatting**: `:22s` pads the string to 22
  characters so the printout lines up in neat columns.

```python
if __name__ == "__main__":
    main()
```

A Python idiom. `__name__` equals `"__main__"` only when the file is **run
directly** (`python clean_hr_data.py`). If the file is *imported* by another
script, this block is skipped — so importing the functions won't accidentally
trigger the whole pipeline. Standard way to make a file both a runnable program
and an importable module.

---

## The mental model to take away

Almost all pandas cleaning is the same four moves:

1. **Select** a column: `df["col"]`
2. **Transform** it: `.str.something()`, `.apply(func)`, `pd.to_numeric(...)`
3. **Assign** it back: `df["col"] = ...`
4. **Verify**: `.value_counts()`, `assert`, `.isna().sum()`

Master those, and the rest is vocabulary — knowing *which* method exists for the
job. When you meet a new one, the question is always the same: *what does it
return, what are its required args, and what do the optional ones change?*
""")
