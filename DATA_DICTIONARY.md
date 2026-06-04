# Data Dictionary — Nusantara Tech HR Dataset

A synthetic but realistic HR dataset for a fictional Indonesian tech company,
**Nusantara Tech** (~4,500 employees, snapshot as of 2025-01-01).

The data is provided in two forms:
- **`data/raw/`** — data as it arrives from source systems: inconsistent date
  formats, mixed categorical labels, missing values, duplicates, salary stored
  as text, stray whitespace. This is the *input* to the cleaning project.
- **`data/clean/`** — the internally consistent "source of truth" after cleaning.

> All names, salaries, and records are fabricated. Any resemblance to real
> people or companies is coincidental.

---

## Schema overview

```
departments (1) ──< employees (many)
employees   (1) ──< salaries (many, history)
employees   (1) ──< performance_reviews (many, per period)
employees   (1) ──< goals (many, per year)
employees   (1) ──< employees (self-join via manager_id)
```

---

## `departments.csv`
Master list of departments.

| Column            | Type    | Description                                  |
|-------------------|---------|----------------------------------------------|
| dept_id           | int     | Primary key.                                 |
| dept_name         | text    | Department name (e.g. "Engineering").        |
| division          | text    | Parent division (Technology/Commercial/Ops). |
| salary_band_mid   | int     | Reference midpoint monthly salary (IDR mn).  |

## `employees.csv`
One row per employee. **Primary key: `employee_id`.**

| Column                 | Type   | Description                                       |
|------------------------|--------|---------------------------------------------------|
| employee_id            | int    | Primary key (1001+).                              |
| full_name              | text   | Employee full name.                               |
| gender                 | text   | Male / Female. *(raw: M, F, L, P, mixed case)*    |
| dept_id                | int    | FK → departments.dept_id.                         |
| job_level              | text   | Intern→Junior→Mid→Senior→Lead→Manager→Head.       |
| city                   | text   | Work city, or "Remote".                           |
| employment_type        | text   | Permanent / Contract / Probation.                 |
| hire_date              | date   | Join date. *(raw: mixed formats)*                 |
| termination_date       | date   | Resignation date; blank if still active.          |
| status                 | text   | Active / Resigned. *(raw: mixed case)*            |
| monthly_salary_idr     | int    | Current monthly salary, IDR. *(raw: some "Rp..")* |
| satisfaction_score     | float  | 1.0–5.0 engagement/satisfaction.                  |
| last_performance_score | float  | 1.0–5.0 most recent review score.                 |
| manager_id             | int    | FK → employees.employee_id (self-join). Nullable. |

## `salaries.csv`
Salary history — multiple rows per employee over time.

| Column             | Type | Description                                          |
|--------------------|------|------------------------------------------------------|
| salary_id          | int  | Primary key.                                         |
| employee_id        | int  | FK → employees.employee_id.                          |
| effective_date     | date | When this salary took effect. *(raw: mixed formats)* |
| monthly_salary_idr | int  | Monthly salary at that point, IDR.                   |
| change_reason      | text | Initial / Annual Raise / Promotion / Adjustment / …  |

## `performance_reviews.csv`
Semi-annual review scores. Periods: 2023-H1 … 2024-H2.

| Column        | Type  | Description                              |
|---------------|-------|------------------------------------------|
| review_id     | int   | Primary key.                             |
| employee_id   | int   | FK → employees.employee_id.              |
| review_period | text  | e.g. "2024-H2".                          |
| review_score  | float | 1.0–5.0 score for that period.           |
| reviewer_id   | int   | FK → employees (the manager). Nullable.  |

## `goals.csv`
Annual goals/KPIs (2024). Multiple rows per employee.

| Column          | Type  | Description                                      |
|-----------------|-------|--------------------------------------------------|
| goal_id         | int   | Primary key.                                     |
| employee_id     | int   | FK → employees.employee_id.                      |
| goal_title      | text  | Goal description (department-specific).          |
| weight_pct      | int   | Weight of this goal (sums ~100% per employee).   |
| achievement_pct | float | Achievement 0–130%. *(raw: some "85%" strings)*  |
| period          | text  | "2024".                                          |

---

## Known data quality issues in `raw/` (what to fix)

1. **Date formats** — `hire_date` / `effective_date` mix ISO, `DD/MM/YYYY`,
   `MM/DD/YYYY`, `DD-MM-YYYY`.
2. **Categorical inconsistency** — `gender` appears as M/F/L/P/Male/Female in
   mixed case; `status` in mixed case; `dept_name` with trailing spaces.
3. **Numeric-as-text** — some `monthly_salary_idr` like `Rp30.100.000`;
   some `achievement_pct` like `"85%"`.
4. **Whitespace / casing** — names with leading/trailing/double spaces and
   inconsistent capitalisation.
5. **Missing values** — `gender`, `city`, `satisfaction_score`,
   `employment_type`, `change_reason`, `reviewer_id`.
6. **Duplicates** — full duplicate rows in `employees` and
   `performance_reviews`.
