import polars as pl
import os
import sys

# Add path
sys.path.insert(0, ".")
from core.data_loader import load_files
from core.utils import MAIN_PORTFOLIO

portfolio_path = r"c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx"
output_file = r"c:\Users\dell\Downloads\فايلات مهاره\STC_System\scratch\promises_report.txt"

with open(output_file, "w", encoding="utf-8") as f:
    if os.path.exists(portfolio_path):
        dfs, _ = load_files({MAIN_PORTFOLIO: portfolio_path})
        df = dfs[MAIN_PORTFOLIO]
        
        f.write("Columns:\n" + ", ".join(df.columns) + "\n\n")
        
        main_col = next((c for c in ["الحالة الرئيسية"] if c in df.columns), None)
        sub_col = next((c for c in ["الحالة الفرعية"] if c in df.columns), None)
        followup_col = next((c for c in ["تاريخ المتابعة", "آخر متابعة على العميل", "أخر متابعة للعميل"] if c in df.columns), None)
        
        if main_col and sub_col:
            f.write("Unique Main Statuses:\n" + ", ".join(map(str, df[main_col].unique().to_list())) + "\n\n")
            
            promise_rows = df.filter(
                pl.col(main_col).cast(pl.String).str.contains("وعد") |
                pl.col(main_col).cast(pl.String).str.contains("واعد")
            )
            f.write(f"Total promise rows: {len(promise_rows)}\n\n")
            if len(promise_rows) > 0:
                f.write("Unique sub-statuses under promise:\n" + ", ".join(map(str, promise_rows[sub_col].unique().to_list())) + "\n\n")
                
                # Check for "طلب مهلة" or similar
                mohl_rows = promise_rows.filter(
                    pl.col(sub_col).cast(pl.String).str.contains("مهلة") |
                    pl.col(sub_col).cast(pl.String).str.contains("مهله")
                )
                f.write(f"Total promise + request delay (طلب مهلة) rows: {len(mohl_rows)}\n\n")
                
                # Show sample
                f.write("Sample promise + request delay (first 20 rows):\n")
                f.write(str(mohl_rows.select([main_col, sub_col, followup_col]).head(20)) + "\n")
    else:
        f.write("Portfolio path not found: " + portfolio_path + "\n")

print("Report written successfully to scratch/promises_report.txt")
