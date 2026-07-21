import polars as pl
import os
import sys

sys.path.insert(0, ".")
from core.data_loader import load_files
from core.utils import MAIN_PORTFOLIO

portfolio_path = r"c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx"
output_file = r"c:\Users\dell\Downloads\فايلات مهاره\STC_System\scratch\check_date_diffs.txt"

with open(output_file, "w", encoding="utf-8") as f:
    if os.path.exists(portfolio_path):
        dfs, _ = load_files({MAIN_PORTFOLIO: portfolio_path})
        df = dfs[MAIN_PORTFOLIO]
        
        f.write("Samples where followup columns might differ:\n")
        cols = ["الحالة الرئيسية", "الحالة الفرعية", "تاريخ المتابعة", "أخر متابعة للعميل", "تاريخ الاسناد"]
        available = [c for c in cols if c in df.columns]
        
        # Filter for rows where they differ
        diff_df = df.filter(
            pl.col("تاريخ المتابعة").cast(pl.String) != pl.col("أخر متابعة للعميل").cast(pl.String)
        )
        f.write(f"Total rows where they differ: {len(diff_df)}\n\n")
        f.write("Sample rows where they differ:\n")
        f.write(str(diff_df.select(available).head(30)) + "\n")
        
        # Filter for rows where تاريخ المتابعة is null or empty
        null_df = df.filter(
            pl.col("تاريخ المتابعة").is_null() | 
            (pl.col("تاريخ المتابعة").cast(pl.String).str.strip_chars() == "") |
            (pl.col("تاريخ المتابعة").cast(pl.String).str.strip_chars() == "---")
        )
        f.write(f"\nTotal rows where تاريخ المتابعة is null/empty: {len(null_df)}\n\n")
        f.write("Sample rows where تاريخ المتابعة is null/empty:\n")
        f.write(str(null_df.select(available).head(30)) + "\n")
        
    else:
        f.write("Portfolio path not found\n")

print("Report written successfully to scratch/check_date_diffs.txt")
