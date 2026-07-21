import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'c:\Users\dell\Downloads\فايلات مهاره\STC_System')

import polars as pl
from core.data_loader import DataLoader
from modules.module8_balancing import PortfolioBalancingModule

portfolio_path = r"c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx"
dl = DataLoader("main_portfolio")
portfolio, result = dl.load(portfolio_path)

source = ["المحفظه الاولي 2025"]
r = PortfolioBalancingModule().run(portfolio, source_portfolios=source)
df_out = r["data"]

# Let's inspect the columns
print("df_out columns:", df_out.columns)

# Check if there are any rows where المحصل الجديد does not match اسم المستخدم (the updated column)
check = df_out.select(["المحصل", "اسم المستخدم", "المحصل الجديد", "اليوزر الجديد", "حالة السحب"]).unique()
print("\nUnique mapping in output:")
print(check.filter(pl.col("حالة السحب") == "سحب").head(30))

# Let's check if there are any mismatches where المحصل is X but اسم المستخدم is Y, which doesn't match the original portfolio mapping
print("\nChecking for mismatches:")
# Original mapping:
orig_map = portfolio.select(["المحصل", "اسم المستخدم"]).drop_nulls().with_columns([
    pl.col("المحصل").cast(pl.String).str.strip_chars(),
    pl.col("اسم المستخدم").cast(pl.String).str.strip_chars()
]).unique()

# Output mapping:
out_map = df_out.select(["المحصل", "اسم المستخدم"]).drop_nulls().with_columns([
    pl.col("المحصل").cast(pl.String).str.strip_chars(),
    pl.col("اسم المستخدم").cast(pl.String).str.strip_chars()
]).unique()

# Find any output mappings that DO NOT exist in original mappings
mismatches = out_map.join(orig_map, on=["المحصل", "اسم المستخدم"], how="anti")
print("Mismatches found (should be 0):")
print(mismatches)
