import sys
sys.stdout.reconfigure(encoding='utf-8')
import polars as pl
from python_calamine import CalamineWorkbook

file_path = r"c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx"
wb = CalamineWorkbook.from_path(file_path)
sheet = wb.get_sheet_by_name(wb.sheet_names[0])
data = sheet.to_python()
headers = [str(h).strip() for h in data[0]]
records = data[1:]
df = pl.DataFrame(records, schema=headers, orient="row")

# Load supervisors filtering to mimic DataLoader
allowed_sups = ["لمياء كمال", "منيرة علي", "تركي ياسين", "محمد أيمن"]
df_filtered = df.filter(pl.col("المشرف").str.strip_chars().is_in(allowed_sups))

print(f"Total rows after supervisor filter: {df_filtered.height}")

portfolios = df_filtered["المحافظ"].unique().to_list()
for p in sorted(portfolios):
    print(f"\nPortfolio: {p}")
    p_df = df_filtered.filter(pl.col("المحافظ") == p)
    col_counts = p_df.group_by("المحصل").agg(pl.col("رقم الهوية").count().alias("cnt")).sort("cnt", descending=True)
    for row in col_counts.iter_rows(named=True):
        print(f"  - {row['المحصل']}: {row['cnt']} rows")
