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

print("All unique supervisors and counts in original Excel:")
print(
    df.group_by("المشرف")
    .agg(pl.col("رقم الهوية").count().alias("count"))
    .sort("count", descending=True)
)
