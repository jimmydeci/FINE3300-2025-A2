# Part_B_CPI/CPI.py
# Logic utilities for Part B (CPI). No plotting; just read/transform/analyze.

from __future__ import annotations
import os
import re
import pandas as pd

# Accept both "Jan-24" and "24-Jan" styles; we will normalize to "Jan-24"
MONTHS_12 = ["Jan-24", "Feb-24", "Mar-24", "Apr-24", "May-24", "Jun-24",
             "Jul-24", "Aug-24", "Sep-24", "Oct-24", "Nov-24", "Dec-24"]

PROV_MAP = {
    "AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba", "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador", "NS": "Nova Scotia", "ON": "Ontario",
    "PEI": "Prince Edward Island", "QC": "Quebec", "SK": "Saskatchewan", "Canada": "Canada"
}

# Capture month columns whether "Jan-24" or "24-Jan"
MONTH_COL_RE = re.compile(
    r"^(?:"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-\d{2}"      # Jan-24
    r"|"
    r"\d{2}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"      # 24-Jan
    r")$"
)


def _normalize_month(col: str) -> str:
    """Return 'Mon-YY' (e.g., 'Jan-24') regardless of 'Jan-24' or '24-Jan' input."""
    if "-" not in col:
        return col
    a, b = col.split("-", 1)
    # If already Mon-YY
    if a in {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"}:
        return f"{a}-{b}"
    # If YY-Mon
    return f"{b}-{a}"


def _month_order_series(df: pd.DataFrame, month_col: str) -> pd.Series:
    order = {m: i for i, m in enumerate(MONTHS_12)}
    return df[month_col].map(order)


def _jurisdiction_from_filename(filename: str) -> str:
    # e.g., "AB.CPI.1810000401.csv" -> "AB"
    code = filename.split(".", 1)[0]
    return PROV_MAP.get(code, code)


def read_one_cpi_csv(path: str, jurisdiction: str) -> pd.DataFrame:
    """Read one CPI CSV and return long-form: Item, Month, Jurisdiction, CPI."""
    df = pd.read_csv(path)
    # find month columns that match either pattern
    month_cols = [c for c in df.columns if MONTH_COL_RE.match(c)]
    if not month_cols:
        raise ValueError(
            f"No month columns recognized in {os.path.basename(path)}")

    # Normalize month names to 'Mon-YY'
    norm_map = {c: _normalize_month(c) for c in month_cols}
    df = df.rename(columns=norm_map)
    month_cols = [norm_map[c] for c in month_cols]

    # melt to long
    long = df.melt(id_vars=["Item"], value_vars=month_cols,
                   var_name="Month", value_name="CPI")
    long["Jurisdiction"] = jurisdiction

    # force month order
    long["MonthOrder"] = _month_order_series(long, "Month")
    long = long.sort_values(["Jurisdiction", "Item", "MonthOrder"]).drop(
        columns=["MonthOrder"])
    return long[["Item", "Month", "Jurisdiction", "CPI"]]


def load_all_cpi(data_dir: str) -> pd.DataFrame:
    """Read all CPI CSVs (excluding MinimumWages.csv) and combine."""
    frames = []
    for fn in os.listdir(data_dir):
        if not fn.lower().endswith(".csv"):
            continue
        if "MinimumWages" in fn:
            continue
        juris = _jurisdiction_from_filename(fn)
        frames.append(read_one_cpi_csv(os.path.join(data_dir, fn), juris))
    if not frames:
        raise FileNotFoundError(f"No CPI CSVs found in {data_dir}")
    return pd.concat(frames, ignore_index=True)


def preview_first_n(df: pd.DataFrame, n: int = 12) -> pd.DataFrame:
    return df.head(n).copy()


def avg_mom(series: pd.Series) -> float:
    """Average month-over-month % change, 1 decimal, ignoring the first NaN."""
    pct = series.pct_change()*100
    return round(pct.iloc[1:].mean(), 1)


def avg_mom_table(cpi: pd.DataFrame) -> pd.DataFrame:
    """For Canada and each province: average MoM for Food, Shelter, All-items excluding food and energy."""
    targets = ["Food", "Shelter", "All-items excluding food and energy"]
    rows = []
    for juris in sorted(cpi["Jurisdiction"].unique()):
        for it in targets:
            sub = cpi[(cpi["Jurisdiction"] == juris) & (cpi["Item"] == it)]
            if sub.empty:
                continue
            # order months properly
            pivot = sub.set_index("Month").reindex(MONTHS_12)
            rows.append({"Jurisdiction": juris, "Item": it,
                        "Avg MoM Change (%)": avg_mom(pivot["CPI"])})
    return pd.DataFrame(rows)


def highest_avg_mom_province(mtm_table: pd.DataFrame) -> dict:
    """Province (exclude Canada) with highest overall avg across the three categories."""
    overall = (mtm_table.groupby("Jurisdiction")["Avg MoM Change (%)"]
               .mean().reset_index(name="Overall Avg MoM (%)"))
    prov_only = overall[overall["Jurisdiction"] != "Canada"]
    if prov_only.empty:
        return {}
    return prov_only.loc[prov_only["Overall Avg MoM (%)"].idxmax()].to_dict()


def equivalent_salary_table(cpi: pd.DataFrame, base_juris: str = "Ontario", base_salary: float = 100_000) -> pd.DataFrame:
    """Using All-items Dec-24 CPI, compute salary equivalents to base_salary in base_juris."""
    all_items = cpi[cpi["Item"] == "All-items"]
    dec_vals = all_items[all_items["Month"] ==
                         "Dec-24"].set_index("Jurisdiction")["CPI"]
    # if files used "24-Dec" naming, try that too
    if dec_vals.empty:
        dec_vals = all_items[all_items["Month"] ==
                             "24-Dec"].set_index("Jurisdiction")["CPI"]
    base = float(dec_vals.loc[base_juris])
    eq = (dec_vals / base) * base_salary
    return eq.round(2).rename(f"Equivalent to ${int(base_salary):,} in {base_juris} (Dec-24)").reset_index()


def load_min_wages(data_dir: str) -> pd.DataFrame:
    mw_path = os.path.join(data_dir, "MinimumWages.csv")
    if not os.path.exists(mw_path):
        raise FileNotFoundError(f"MinimumWages.csv not found in {data_dir}")
    mw = pd.read_csv(mw_path)
    # Expect columns: Province (AB, BC, ...), Minimum Wage
    code_to_name = {k: v for k, v in PROV_MAP.items() if k != "Canada"}
    mw["Jurisdiction"] = mw["Province"].map(code_to_name)
    mw = mw.drop(columns=["Province"]).rename(columns={"Minimum Wage": "Wage"})
    return mw


def nominal_min_wage_hi_lo(mw: pd.DataFrame) -> tuple[dict, dict]:
    hi = mw.loc[mw["Wage"].idxmax()].to_dict()
    lo = mw.loc[mw["Wage"].idxmin()].to_dict()
    return hi, lo


def real_min_wage_rank(mw: pd.DataFrame, cpi: pd.DataFrame) -> pd.DataFrame:
    """Real min wage proxy = nominal wage / All-items CPI (Dec-24)."""
    all_items = cpi[cpi["Item"] == "All-items"]
    dec_vals = all_items[all_items["Month"] ==
                         "Dec-24"].set_index("Jurisdiction")["CPI"]
    if dec_vals.empty:
        dec_vals = all_items[all_items["Month"] ==
                             "24-Dec"].set_index("Jurisdiction")["CPI"]
    tbl = mw.set_index("Jurisdiction").join(
        dec_vals.rename("Dec_AllItems_CPI"))
    tbl["RealWage_IndexAdj"] = (
        tbl["Wage"] / tbl["Dec_AllItems_CPI"]).astype(float)
    return tbl.sort_values("RealWage_IndexAdj", ascending=False).reset_index()


def services_annual_change(cpi: pd.DataFrame) -> pd.DataFrame:
    """(Dec-24 - Jan-24)/Jan-24 for 'Services' item, % to 1 decimal."""
    svc = cpi[cpi["Item"] == "Services"]
    jan = svc[svc["Month"].isin(["Jan-24", "24-Jan"])
              ].set_index("Jurisdiction")["CPI"]
    dec = svc[svc["Month"].isin(["Dec-24", "24-Dec"])
              ].set_index("Jurisdiction")["CPI"]
    out = (((dec - jan) / jan) *
           100.0).round(1).rename("Annual Change in Services CPI (%)").reset_index()
    return out


def highest_services_inflation(services_tbl: pd.DataFrame) -> dict:
    if services_tbl.empty:
        return {}
    return services_tbl.loc[services_tbl["Annual Change in Services CPI (%)"].idxmax()].to_dict()
