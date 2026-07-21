import sys
sys.stdout.reconfigure(encoding='utf-8')

import polars as pl
from python_calamine import CalamineWorkbook
import os

file_path = r"c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx"
wb = CalamineWorkbook.from_path(file_path)
sheet = wb.get_sheet_by_name(wb.sheet_names[0])
data = sheet.to_python()
headers = [str(h).strip() for h in data[0]]
records = data[1:]
df = pl.DataFrame(records, schema=headers, orient="row")

print("Columns:", df.columns)

# Detect collector, portfolio, and balance columns
col_col = None
for c in ["المحصل", "اسم المحصل", "الموظف"]:
    if c in df.columns:
        col_col = c
        break

prt_col = None
for p in ["المحافظ", "المحفظة", "اسم المحفظة", "Portfolio"]:
    if p in df.columns:
        prt_col = p
        break

bal_col = None
for b in ["متبقي سداد موثق", "متبقي السداد الموثق", "متبقي سداد", "الرصيد المتبقي"]:
    if b in df.columns:
        bal_col = b
        break

print(f"Detected: Collector={col_col}, Portfolio={prt_col}, Balance={bal_col}")

if col_col and prt_col:
    # Print portfolios
    ports = df[prt_col].unique().to_list()
    print("\nUnique Portfolios:")
    for p in ports:
        print(" -", p)
        
    # Print unique collectors and their counts/balances
    print("\nUnique Collectors:")
    stats = df.group_by(col_col).agg([
        pl.col(col_col).count().alias("count"),
    ]).sort("count", descending=True)
    for row in stats.iter_rows(named=True):
        print(f" - {row[col_col]}: {row['count']} rows")
