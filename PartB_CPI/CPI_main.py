# Part_B_CPI/CPI_main.py
# Runner for Part B. Prints answers and writes one Excel with multiple sheets.

import os
import argparse
import pandas as pd
from CPI import (
    load_all_cpi, preview_first_n, avg_mom_table, highest_avg_mom_province,
    equivalent_salary_table, load_min_wages, nominal_min_wage_hi_lo,
    real_min_wage_rank, services_annual_change, highest_services_inflation
)


def main():
    from pathlib import Path
    # --- fix default path so it always points to src/ ---
    here = Path(__file__).resolve().parent
    default_data_dir = (here.parent / "src").as_posix()

    p = argparse.ArgumentParser(description="FINE3300 A2 - Part B (CPI)")
    p.add_argument("--data_dir", type=str, default=default_data_dir,
                   help="Folder containing the 11 CPI CSVs + MinimumWages.csv")
    p.add_argument("--out_xlsx", type=str,
                   default="CPI_Analysis.xlsx", help="Output Excel workbook")
    args = p.parse_args()

    cpi = load_all_cpi(args.data_dir)

    # 1) Combine the 11 data frames into one long-form df
    # Sort by month, then region, then item
    cpi = cpi.sort_values(
        by=["Month", "Jurisdiction", "Item"]).reset_index(drop=True)

    # 2) Print the first 12 lines
    preview = preview_first_n(cpi, 12)
    print("\nQ2) First 12 rows of combined CPI data:")
    print(preview.to_string(index=False))

    # 3) Avg MoM change for Food, Shelter, All-items excl. food & energy
    mtm = avg_mom_table(cpi)
    mtm_wide = (mtm.pivot(index="Jurisdiction", columns="Item", values="Avg MoM Change (%)")
                .reindex(columns=["Food", "Shelter", "All-items excluding food and energy"]))
    mtm_wide = mtm_wide.round(1).reset_index()
    print("\nQ3) Average month-to-month change (%), 1 dp:")
    print(mtm_wide.to_string(index=False))

    # 4) Province with highest overall avg change (exclude Canada)
    highest_mtm = highest_avg_mom_province(mtm)
    print("\nQ4) Province with highest overall average MoM (Food/Shelter/All-items excl. food & energy):")
    print(highest_mtm)

    # 5) Equivalent salary to $100,000 in Ontario (Dec-24 All-items)
    eq_salary = equivalent_salary_table(
        cpi, base_juris="Ontario", base_salary=100_000)
    print("\nQ5) Equivalent salary to $100,000 in Ontario (Dec-24 All-items CPI):")
    print(eq_salary.to_string(index=False))

    # 6) Minimum wages — nominal highest/lowest and real ranking
    min_wages = load_min_wages(args.data_dir)
    nominal_hi, nominal_lo = nominal_min_wage_hi_lo(min_wages)
    real_rank = real_min_wage_rank(min_wages, cpi)

    print("\nQ6) Minimum wage analysis (nominal & real):")
    print(
        f"  Nominal minimum wage (highest): {nominal_hi['Jurisdiction']} - ${nominal_hi['Wage']:.2f}")
    print(
        f"  Nominal minimum wage (lowest): {nominal_lo['Jurisdiction']} - ${nominal_lo['Wage']:.2f}")

    # Print top 5 REAL (CPI-adjusted) for context
    print("\n  Top 5 by REAL minimum wage (nominal/CPI-adjusted):")
    print(real_rank.head(5).to_string(index=False))

    # Explicit single answer the question asks for: highest REAL
    highest_real = real_rank.iloc[0]  # real_rank is sorted desc by real index
    print("\n  Province with highest REAL minimum wage (Dec-24 CPI adjusted):")
    print({
        "Jurisdiction": highest_real["Jurisdiction"],
        "Nominal Wage": highest_real["Wage"],
        "Dec_AllItems_CPI": highest_real["Dec_AllItems_CPI"],
        "Real Index": round(highest_real["RealWage_IndexAdj"], 4)
    })

    # 7) Annual change in Services CPI (Jan→Dec)
    svc_tbl = services_annual_change(cpi)
    print("\nQ7) Annual change in Services CPI (Jan→Dec %):")
    print(svc_tbl.to_string(index=False))

    # 8) Region with highest Services inflation
    top_services = highest_services_inflation(svc_tbl)
    print("\nQ8) Region with highest Services inflation (Jan→Dec %):")
    print(top_services)

    # 9) Save all outputs to one Excel workbook (multiple sheets)
    with pd.ExcelWriter(args.out_xlsx, engine="xlsxwriter") as w:
        cpi.to_excel(w, sheet_name="Combined", index=False)
        preview.to_excel(w, sheet_name="Preview_12_Rows", index=False)
        mtm.to_excel(w, sheet_name="Avg_MoM_Target", index=False)
        # Also save overall averages for convenience
        overall = (mtm.groupby("Jurisdiction")["Avg MoM Change (%)"]
                   .mean().reset_index(name="Overall Avg MoM (%)"))
        overall.to_excel(w, sheet_name="Overall_Avg_MoM", index=False)
        eq_salary.to_excel(w, sheet_name="Equivalent_Salary", index=False)
        real_rank.to_excel(w, sheet_name="MinWage_Real_Nominal", index=False)
        svc_tbl.to_excel(w, sheet_name="Services_Annual_Change", index=False)

    print(f"\n✅ Wrote Excel: {os.path.abspath(args.out_xlsx)}")


if __name__ == "__main__":
    main()
