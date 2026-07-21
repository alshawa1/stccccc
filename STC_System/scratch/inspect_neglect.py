import polars as pl
import os
import sys

sys.path.insert(0, ".")
from core.data_loader import load_files
from core.utils import MAIN_PORTFOLIO
from modules.module3_neglect import NeglectModule

portfolio_path = r"c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx"
output_file = r"c:\Users\dell\Downloads\فايلات مهاره\STC_System\scratch\neglect_check_report.txt"

with open(output_file, "w", encoding="utf-8") as f:
    if os.path.exists(portfolio_path):
        dfs, _ = load_files({MAIN_PORTFOLIO: portfolio_path})
        df = dfs[MAIN_PORTFOLIO]
        
        # Run Neglect Module
        module = NeglectModule()
        result = module.run(df)
        full_analysis = result["full_analysis"]
        
        f.write(f"Total rows analyzed: {len(full_analysis)}\n")
        f.write(f"Total neglected: {result['stats']['مهمل']}\n")
        f.write(f"Total not neglected: {result['stats']['غير مهمل']}\n\n")
        
        # Group by main status, sub status, and neglect status
        grouped = (
            full_analysis.group_by(["الحالة الرئيسية", "الحالة الفرعية", "حالة الإهمال"])
            .agg([
                pl.len().alias("Count"),
                pl.col("عدد أيام الإهمال").min().alias("MinDays"),
                pl.col("عدد أيام الإهمال").max().alias("MaxDays"),
                pl.col("عدد أيام الإهمال").mean().round(1).alias("AvgDays")
            ])
            .sort(["الحالة الرئيسية", "الحالة الفرعية", "حالة الإهمال"])
        )
        
        f.write("Neglect classification by Main/Sub Status:\n")
        f.write(str(grouped) + "\n")
    else:
        f.write("Portfolio path not found\n")

print("Report written successfully to scratch/neglect_check_report.txt")
