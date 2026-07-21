import sys
sys.stdout.reconfigure(encoding='utf-8')

import polars as pl
from python_calamine import CalamineWorkbook

def is_human_collector(name: str) -> bool:
    name_clean = str(name).strip()
    if not name_clean:
        return False
    system_keywords = ["الكتروني", "سحب", "تدوير", "استبعاد", "عناية", "عنايه", "نظام", "system", "auto", "توزيع", "خارج التغطية", "خارج التغطيه"]
    for kw in system_keywords:
        if kw in name_clean:
            return False
    return True

file_path = r"c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx"
wb = CalamineWorkbook.from_path(file_path)
sheet = wb.get_sheet_by_name(wb.sheet_names[0])
data = sheet.to_python()
headers = [str(h).strip() for h in data[0]]
records = data[1:]
df = pl.DataFrame(records, schema=headers, orient="row")

col_col = "المحصل"
unique_cols = df[col_col].unique().to_list()

print("--- CLASSIFICATION ---")
for c in sorted(unique_cols):
    c_str = str(c).strip()
    is_human = is_human_collector(c_str)
    status = "HUMAN" if is_human else "SYSTEM/NON-HUMAN"
    print(f"{c_str}: {status}")
