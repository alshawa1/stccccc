import polars as pl
import os
import sys

sys.path.insert(0, ".")
from core.data_loader import load_files
from core.utils import MAIN_PORTFOLIO, get_today
from modules.module3_neglect import NeglectModule

portfolio_path = r"c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx"
output_file = r"c:\Users\dell\Downloads\فايلات مهاره\STC_System\scratch\check_raw_dates.txt"

with open(output_file, "w", encoding="utf-8") as f:
    if os.path.exists(portfolio_path):
        dfs, _ = load_files({MAIN_PORTFOLIO: portfolio_path})
        df = dfs[MAIN_PORTFOLIO]
        
        module = NeglectModule()
        result = module.run(df)
        full = result["full_analysis"]
        
        # Filter rows with "طلب مهلة"
        mohl = full.filter(
            pl.col("الحالة الفرعية").cast(pl.String).str.contains("مهلة") |
            pl.col("الحالة الفرعية").cast(pl.String).str.contains("مهله")
        )
        
        f.write("Sample request delay rows with original and parsed dates:\n")
        cols_to_select = ["الحالة الرئيسية", "الحالة الفرعية", "تاريخ المتابعة", "تاريخ المتابعة (Date)", "تاريخ اليوم", "عدد أيام الإهمال"]
        available_cols = [c for c in cols_to_select if c in mohl.columns]
        
        f.write(str(mohl.select(available_cols).head(30)) + "\n")
        
        # Also print date formats distributions or samples
        f.write("\nRaw date sample values:\n")
        f.write(str(df["تاريخ المتابعة"].head(30)) + "\n")
    else:
        f.write("Portfolio path not found\n")

print("Report written successfully to scratch/check_raw_dates.txt")
