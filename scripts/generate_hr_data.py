"""
generate_hr_data.py
--------------------
Generates a realistic, relational synthetic HR dataset for a fictional company,
"Nusantara Tech". Produces 5 linked tables and writes two versions of each:

  data/clean/   -> internally consistent "source of truth"
  data/raw/     -> the SAME data with realistic, intentional "dirtiness"
                   injected (typos, mixed date formats, duplicates, missing
                   values, inconsistent casing/whitespace, etc.)

The raw/ files are what a candidate would receive in the real world and must
clean. The clean/ files are the target after cleaning.

Design goals (so the data does NOT look random):
  - Salary scales with job level + tenure, with department-based bands.
  - Attrition probability is a function of satisfaction, salary-vs-band,
    tenure, and last performance score (i.e. it tells a real story).
  - Performance review scores correlate (loosely) with goal achievement.
  - A real manager hierarchy via manager_id (enables self-joins).

Run:  python generate_hr_data.py
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import date, timedelta
from faker import Faker

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
SEED = 42
N_EMPLOYEES = 4500
COMPANY_START = date(2015, 1, 1)
SNAPSHOT_DATE = date(2025, 1, 1)   # "today" for the dataset

random.seed(SEED)
np.random.seed(SEED)
fake = Faker("id_ID")              # Indonesian names/locale
Faker.seed(SEED)

OUT_CLEAN = "data/clean"
OUT_RAW = "data/raw"
os.makedirs(OUT_CLEAN, exist_ok=True)
os.makedirs(OUT_RAW, exist_ok=True)

# ----------------------------------------------------------------------------
# 1. Departments  (master table)
# ----------------------------------------------------------------------------
DEPARTMENTS = [
    # dept_id, dept_name, division, salary_band_mid (monthly IDR, millions)
    (1,  "Engineering",        "Technology",      28),
    (2,  "Data & Analytics",   "Technology",      26),
    (3,  "Product",            "Technology",      27),
    (4,  "Design",             "Technology",      22),
    (5,  "Sales",              "Commercial",      20),
    (6,  "Marketing",          "Commercial",      19),
    (7,  "Customer Success",   "Commercial",      15),
    (8,  "Finance",            "Operations",      21),
    (9,  "People & Culture",   "Operations",      18),
    (10, "Operations",         "Operations",      16),
]
departments = pd.DataFrame(
    DEPARTMENTS, columns=["dept_id", "dept_name", "division", "salary_band_mid"]
)

# Job levels and their multipliers on the department band midpoint
LEVELS = [
    # level_name, salary_multiplier, weight (how common)
    ("Intern",          0.35, 0.04),
    ("Junior",          0.70, 0.26),
    ("Mid",             1.00, 0.34),
    ("Senior",          1.45, 0.22),
    ("Lead",            1.90, 0.09),
    ("Manager",         2.40, 0.04),
    ("Head",            3.20, 0.01),
]
level_names = [l[0] for l in LEVELS]
level_mult = {l[0]: l[1] for l in LEVELS}
level_weights = np.array([l[2] for l in LEVELS])
level_weights = level_weights / level_weights.sum()

CITIES = ["Jakarta", "Bandung", "Surabaya", "Yogyakarta", "Medan", "Remote"]
EMP_TYPE = ["Permanent", "Contract", "Probation"]
GENDERS = ["Male", "Female"]

# ----------------------------------------------------------------------------
# 2. Employees
# ----------------------------------------------------------------------------
def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 1)))

rows = []
for i in range(1, N_EMPLOYEES + 1):
    emp_id = 1000 + i
    gender = random.choice(GENDERS)
    if gender == "Male":
        name = fake.name_male()
    else:
        name = fake.name_female()

    dept = departments.sample(1).iloc[0]
    level = np.random.choice(level_names, p=level_weights)

    hire_date = random_date(COMPANY_START, SNAPSHOT_DATE - timedelta(days=30))
    tenure_years = (SNAPSHOT_DATE - hire_date).days / 365.25

    # Salary: department band * level multiplier * tenure bump * noise
    band_mid = dept["salary_band_mid"]
    base = band_mid * level_mult[level]
    tenure_bump = 1 + min(tenure_years, 10) * 0.018       # up to ~+18%
    noise = np.random.normal(1.0, 0.08)
    monthly_salary_m = max(4.5, base * tenure_bump * noise)   # floor 4.5jt
    monthly_salary = int(round(monthly_salary_m * 1_000_000, -4))  # round to 10k

    # Satisfaction 1-5 (slightly lower for very long tenure & low salary)
    sat = np.random.normal(3.6, 0.8)
    if monthly_salary_m < base * 0.95:
        sat -= 0.4
    satisfaction = float(np.clip(round(sat, 1), 1.0, 5.0))

    # Last performance score 1-5 (will also drive goal achievement)
    perf = float(np.clip(round(np.random.normal(3.5, 0.7), 1), 1.0, 5.0))

    # --- Attrition model: did this person leave? -----------------------------
    # Higher risk when: low satisfaction, underpaid, very low or churny tenure,
    # low performance. Produces a realistic ~16-18% attrition rate.
    risk = 0.16
    risk += (3.5 - satisfaction) * 0.08
    risk += (base - monthly_salary_m) / base * 0.30
    if tenure_years < 1.5:
        risk += 0.08
    if perf < 2.8:
        risk += 0.10
    if level in ("Intern", "Contract"):
        risk += 0.06
    risk = float(np.clip(risk, 0.03, 0.80))
    left = random.random() < risk

    termination_date = ""
    status = "Active"
    if left:
        # left somewhere between hire+6mo and snapshot
        earliest = hire_date + timedelta(days=180)
        if earliest < SNAPSHOT_DATE:
            term = random_date(earliest, SNAPSHOT_DATE)
            termination_date = term.isoformat()
            status = "Resigned"
        else:
            left = False  # not enough tenure to have left yet

    rows.append({
        "employee_id": emp_id,
        "full_name": name,
        "gender": gender,
        "dept_id": int(dept["dept_id"]),
        "job_level": level,
        "city": random.choice(CITIES),
        "employment_type": random.choices(EMP_TYPE, weights=[0.78, 0.14, 0.08])[0],
        "hire_date": hire_date.isoformat(),
        "termination_date": termination_date,
        "status": status,
        "monthly_salary_idr": monthly_salary,
        "satisfaction_score": satisfaction,
        "last_performance_score": perf,
        "manager_id": None,   # filled below
    })

employees = pd.DataFrame(rows)

# --- Assign a realistic manager hierarchy -----------------------------------
# Within each department, higher-level employees manage lower-level ones.
level_rank = {n: r for r, n in enumerate(level_names)}
employees["level_rank"] = employees["job_level"].map(level_rank)

for dept_id, grp in employees.groupby("dept_id"):
    grp_sorted = grp.sort_values("level_rank", ascending=False)
    managers_pool = grp_sorted[grp_sorted["level_rank"] >= level_rank["Senior"]]
    for idx, row in grp.iterrows():
        # candidates = same dept, strictly higher rank
        higher = grp[grp["level_rank"] > row["level_rank"]]
        if len(higher) > 0:
            employees.at[idx, "manager_id"] = int(higher.sample(1)["employee_id"].iloc[0])
        else:
            employees.at[idx, "manager_id"] = None  # top of the tree (Head)

employees = employees.drop(columns=["level_rank"])

# ----------------------------------------------------------------------------
# 3. Salaries (history)  - a few raises over tenure
# ----------------------------------------------------------------------------
sal_rows = []
sal_id = 1
for _, e in employees.iterrows():
    hire = date.fromisoformat(e["hire_date"])
    end = (date.fromisoformat(e["termination_date"])
           if e["termination_date"] else SNAPSHOT_DATE)
    current = e["monthly_salary_idr"]
    # work backwards: current salary is the latest; earlier ones are lower
    n_changes = max(1, int((end - hire).days / 365.25 / 1.5))  # raise ~every 1.5y
    n_changes = min(n_changes, 6)
    salary_points = []
    sal = current
    for k in range(n_changes):
        salary_points.append(sal)
        sal = int(round(sal / np.random.uniform(1.04, 1.12), -4))  # earlier = lower
    salary_points = list(reversed(salary_points))  # chronological
    span = (end - hire).days
    for k, amount in enumerate(salary_points):
        eff = hire + timedelta(days=int(span * k / max(len(salary_points), 1)))
        sal_rows.append({
            "salary_id": sal_id,
            "employee_id": e["employee_id"],
            "effective_date": eff.isoformat(),
            "monthly_salary_idr": amount,
            "change_reason": ("Initial" if k == 0
                              else random.choice(["Annual Raise", "Promotion",
                                                  "Adjustment", "Market Correction"])),
        })
        sal_id += 1
salaries = pd.DataFrame(sal_rows)

# ----------------------------------------------------------------------------
# 4. Performance reviews (semi-annual)
# ----------------------------------------------------------------------------
rev_rows = []
rev_id = 1
PERIODS = ["2023-H1", "2023-H2", "2024-H1", "2024-H2"]
period_end = {
    "2023-H1": date(2023, 6, 30), "2023-H2": date(2023, 12, 31),
    "2024-H1": date(2024, 6, 30), "2024-H2": date(2024, 12, 31),
}
for _, e in employees.iterrows():
    hire = date.fromisoformat(e["hire_date"])
    end = (date.fromisoformat(e["termination_date"])
           if e["termination_date"] else SNAPSHOT_DATE)
    base_perf = e["last_performance_score"]
    for p in PERIODS:
        pe = period_end[p]
        if hire <= pe <= end:
            score = float(np.clip(round(np.random.normal(base_perf, 0.4), 1), 1.0, 5.0))
            rev_rows.append({
                "review_id": rev_id,
                "employee_id": e["employee_id"],
                "review_period": p,
                "review_score": score,
                "reviewer_id": e["manager_id"] if pd.notna(e["manager_id"]) else None,
            })
            rev_id += 1
performance_reviews = pd.DataFrame(rev_rows)

# ----------------------------------------------------------------------------
# 5. Goals (KPIs) - tied loosely to performance
# ----------------------------------------------------------------------------
GOAL_CATALOG = {
    "Engineering": ["Reduce production incidents", "Ship roadmap features",
                    "Improve test coverage", "Cut API latency"],
    "Data & Analytics": ["Automate reporting pipeline", "Improve data quality",
                          "Deliver self-serve dashboards", "Reduce query cost"],
    "Product": ["Increase activation rate", "Launch new module",
                "Improve retention", "Run discovery interviews"],
    "Design": ["Redesign onboarding", "Build design system",
               "Improve usability score"],
    "Sales": ["Hit quarterly quota", "Grow pipeline", "Improve win rate",
              "Expand key accounts"],
    "Marketing": ["Grow qualified leads", "Improve CAC", "Launch campaign",
                  "Grow organic traffic"],
    "Customer Success": ["Reduce churn", "Improve NPS", "Increase upsell",
                         "Cut response time"],
    "Finance": ["Close books faster", "Improve forecast accuracy",
                "Reduce overdue invoices"],
    "People & Culture": ["Reduce time-to-hire", "Improve eNPS",
                         "Cut regretted attrition"],
    "Operations": ["Improve SLA compliance", "Reduce process cost",
                   "Automate manual workflow"],
}
dept_name_by_id = dict(zip(departments["dept_id"], departments["dept_name"]))

goal_rows = []
goal_id = 1
for _, e in employees.iterrows():
    dname = dept_name_by_id[e["dept_id"]]
    catalog = GOAL_CATALOG.get(dname, ["Achieve team objectives"])
    n_goals = random.randint(2, 4)
    perf = e["last_performance_score"]
    for _ in range(n_goals):
        # achievement % correlates with performance score (perf 1-5 -> ~40-110%)
        ach = np.random.normal(40 + perf * 14, 12)
        ach = float(np.clip(round(ach, 0), 0, 130))
        goal_rows.append({
            "goal_id": goal_id,
            "employee_id": e["employee_id"],
            "goal_title": random.choice(catalog),
            "weight_pct": random.choice([20, 25, 30, 40, 50]),
            "achievement_pct": ach,
            "period": "2024",
        })
        goal_id += 1
goals = pd.DataFrame(goal_rows)

# ----------------------------------------------------------------------------
# Write CLEAN versions
# ----------------------------------------------------------------------------
departments.to_csv(f"{OUT_CLEAN}/departments.csv", index=False)
employees.to_csv(f"{OUT_CLEAN}/employees.csv", index=False)
salaries.to_csv(f"{OUT_CLEAN}/salaries.csv", index=False)
performance_reviews.to_csv(f"{OUT_CLEAN}/performance_reviews.csv", index=False)
goals.to_csv(f"{OUT_CLEAN}/goals.csv", index=False)

print("CLEAN written:")
for f in os.listdir(OUT_CLEAN):
    df = pd.read_csv(f"{OUT_CLEAN}/{f}")
    print(f"  {f:28s} {len(df):>6} rows  {len(df.columns)} cols")

# ----------------------------------------------------------------------------
# Inject realistic DIRTINESS into a copy -> raw/
# ----------------------------------------------------------------------------
def dirty_employees(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d = d.astype(object)

    # 1. Inconsistent date formats in hire_date
    def mess_date(s):
        if not isinstance(s, str) or not s:
            return s
        y, m, dd = s.split("-")
        fmt = random.random()
        if fmt < 0.4:   return s                       # keep ISO
        elif fmt < 0.7: return f"{dd}/{m}/{y}"         # 31/12/2020
        elif fmt < 0.85:return f"{m}/{dd}/{y}"         # US-ish
        else:           return f"{dd}-{m}-{y}"         # 31-12-2020
    d["hire_date"] = d["hire_date"].apply(mess_date)

    # 2. Inconsistent casing + whitespace in names
    def mess_name(n):
        r = random.random()
        if r < 0.10: return n.upper()
        if r < 0.20: return n.lower()
        if r < 0.30: return f"  {n} "        # stray whitespace
        if r < 0.34: return n.replace(" ", "  ")  # double space
        return n
    d["full_name"] = d["full_name"].apply(mess_name)

    # 3. Missing values scattered in non-key columns
    for col, frac in [("gender", 0.04), ("city", 0.06),
                      ("satisfaction_score", 0.08), ("employment_type", 0.03)]:
        idx = d.sample(frac=frac).index
        d.loc[idx, col] = np.nan

    # 4. Inconsistent categorical labels
    gmap = {"Male": ["Male", "M", "male", "L"], "Female": ["Female", "F", "female", "P"]}
    def mess_gender(g):
        if pd.isna(g): return g
        return random.choice(gmap.get(g, [g]))
    d["gender"] = d["gender"].apply(mess_gender)

    d["status"] = d["status"].apply(
        lambda s: random.choice([s, s.upper(), s.lower()]) if isinstance(s, str) else s)

    # 5. Salary occasionally stored as string with separators / 'Rp'
    def mess_salary(v):
        if pd.isna(v): return v
        r = random.random()
        if r < 0.08: return f"Rp{int(v):,}".replace(",", ".")  # Rp28.000.000
        if r < 0.12: return f"{int(v)} "                        # trailing space
        return int(v)
    d["monthly_salary_idr"] = d["monthly_salary_idr"].apply(mess_salary)

    # 6. Duplicate rows (full duplicates)
    dups = d.sample(frac=0.015)
    d = pd.concat([d, dups], ignore_index=True)

    # 7. A few employee_id typos turned into floats / strings already handled by object
    return d

emp_raw = dirty_employees(employees)
emp_raw.to_csv(f"{OUT_RAW}/employees.csv", index=False)

# departments: small dirtiness (trailing spaces, casing)
dept_raw = departments.copy().astype(object)
dept_raw["dept_name"] = dept_raw["dept_name"].apply(
    lambda s: random.choice([s, s + " ", s.upper()]))
dept_raw.to_csv(f"{OUT_RAW}/departments.csv", index=False)

# salaries: mixed date formats + some missing change_reason
sal_raw = salaries.copy().astype(object)
def mess_date2(s):
    if not isinstance(s, str): return s
    y, m, dd = s.split("-")
    return random.choice([s, f"{dd}/{m}/{y}", f"{dd}-{m}-{y}"])
sal_raw["effective_date"] = sal_raw["effective_date"].apply(mess_date2)
miss_idx = sal_raw.sample(frac=0.05).index
sal_raw.loc[miss_idx, "change_reason"] = np.nan
sal_raw.to_csv(f"{OUT_RAW}/salaries.csv", index=False)

# performance_reviews: a few missing reviewer_id + duplicate reviews
rev_raw = performance_reviews.copy().astype(object)
miss_idx = rev_raw.sample(frac=0.04).index
rev_raw.loc[miss_idx, "reviewer_id"] = np.nan
rev_dups = rev_raw.sample(frac=0.01)
rev_raw = pd.concat([rev_raw, rev_dups], ignore_index=True)
rev_raw.to_csv(f"{OUT_RAW}/performance_reviews.csv", index=False)

# goals: achievement sometimes as "85%" string, some missing weights
goal_raw = goals.copy().astype(object)
def mess_ach(v):
    if pd.isna(v): return v
    return random.choice([v, f"{int(v)}%", v])
goal_raw["achievement_pct"] = goal_raw["achievement_pct"].apply(mess_ach)
miss_idx = goal_raw.sample(frac=0.03).index
goal_raw.loc[miss_idx, "weight_pct"] = np.nan
goal_raw.to_csv(f"{OUT_RAW}/goals.csv", index=False)

print("\nRAW (dirty) written:")
for f in os.listdir(OUT_RAW):
    df = pd.read_csv(f"{OUT_RAW}/{f}")
    print(f"  {f:28s} {len(df):>6} rows  {len(df.columns)} cols")

# ----------------------------------------------------------------------------
# Quick sanity stats (so we know the data tells a story)
# ----------------------------------------------------------------------------
attr = (employees["status"] != "Active").mean()
print(f"\nSanity check:")
print(f"  Attrition rate         : {attr:.1%}")
print(f"  Avg monthly salary (jt): {employees['monthly_salary_idr'].mean()/1e6:.1f}")
print(f"  Avg satisfaction       : {employees['satisfaction_score'].mean():.2f}")
print(f"  Employees w/ manager   : {employees['manager_id'].notna().mean():.1%}")
