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

# Group by supervisor for 'تحصيل الكتروني' and 'سحب وتدوير'
print("Supervisors for 'تحصيل الكتروني':")
print(
    df.filter(pl.col("المحصل").str.strip_chars() == "تحصيل الكتروني")
    .group_by("المشرف")
    .agg(pl.col("رقم الهوية").count().alias("count"))
)

print("\nSupervisors for 'سحب وتدوير':")
print(
    df.filter(pl.col("المحصل").str.strip_chars() == "سحب وتدوير")
    .group_by("المشرف")
    .agg(pl.col("رقم الهوية").count().alias("count"))
)
