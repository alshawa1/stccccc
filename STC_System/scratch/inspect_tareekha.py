import polars as pl
import os
import sys

sys.path.insert(0, ".")
from core.data_loader import load_files
from core.utils import MAIN_PORTFOLIO

portfolio_path = r"c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx"
output_file = r"c:\Users\dell\Downloads\فايلات مهاره\STC_System\scratch\check_tareekha.txt"

with open(output_file, "w", encoding="utf-8") as f:
    if os.path.exists(portfolio_path):
        dfs, _ = load_files({MAIN_PORTFOLIO: portfolio_path})
        df = dfs[MAIN_PORTFOLIO]
        
        f.write("Raw samples of تاريخها and followup dates:\n")
        cols = ["الحالة الرئيسية", "الحالة الفرعية", "تاريخ المتابعة", "تاريخها", "أخر متابعة للعميل"]
        available = [c for c in cols if c in df.columns]
        
        f.write(str(df.select(available).head(40)) + "\n")
    else:
        f.write("Portfolio path not found\n")

print("Report written to scratch/check_tareekha.txt")
