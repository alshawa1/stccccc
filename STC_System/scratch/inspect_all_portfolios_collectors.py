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

print("All unique portfolios in original Excel:")
for p in df["المحافظ"].unique().to_list():
    p_df = df.filter(pl.col("المحافظ") == p)
    print(f"\nPortfolio: {p} (Total rows: {p_df.height})")
    print(
        p_df.group_by("المحصل")
        .agg(pl.col("رقم الهوية").count().alias("count"))
        .sort("count", descending=True)
        .head(10)
    )
