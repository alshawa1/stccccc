"""
Speed benchmark: openpyxl vs xlsxwriter vs polars write_excel
for large datasets (54k rows × 43 cols)
"""
import sys, time, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'c:\Users\dell\Downloads\فايلات مهاره\STC_System')

import polars as pl
import xlsxwriter

# Simulate real data
n = 54023
import random, string

cols = {
    'رقم الهوية':    ['1234567890'] * n,
    'الاسم':         ['محمد أحمد علي'] * n,
    'المبلغ':        [random.uniform(100, 50000) for _ in range(n)],
    'عدد العملاء':   [round(1/random.randint(1,5), 4) for _ in range(n)],
    'الحالة':        [random.choice(['مهمل', 'غير مهمل', 'واعد']) for _ in range(n)],
    'عدد أيام الإهمال': [random.randint(0, 200) for _ in range(n)],
    'المشرف':        ['أحمد محمد'] * n,
    'المحصل':        ['خالد سالم'] * n,
}
# Add dummy columns up to 43
for i in range(len(cols), 43):
    cols[f'عمود_{i}'] = [f'قيمة_{i}'] * n
df = pl.DataFrame(cols)

print(f"DataFrame: {df.shape}")
out_dir = r'c:\Users\dell\Downloads\فايلات مهاره'

# ── Test 1: xlsxwriter constant_memory ──────────────────────────────────────
out1 = os.path.join(out_dir, 'bench_xlsxwriter.xlsx')
t0 = time.time()
wb = xlsxwriter.Workbook(out1, {'constant_memory': True})
ws = wb.add_worksheet('Sheet1')
ws.right_to_left()
ws.freeze_panes(1, 0)
ws.autofilter(0, 0, n, len(df.columns) - 1)

navy = '#1f2d5a'
hdr_fmt = wb.add_format({
    'bold': True, 'bg_color': navy, 'font_color': '#FFFFFF',
    'border': 1, 'align': 'right', 'valign': 'vcenter', 'font_name': 'Tahoma', 'font_size': 11,
})
num_fmt = wb.add_format({'num_format': '#,##0.000', 'align': 'right'})
data_fmt = wb.add_format({'align': 'right', 'font_name': 'Tahoma', 'font_size': 10})

for col_idx, header in enumerate(df.columns):
    ws.write(0, col_idx, header, hdr_fmt)

# write rows
float_cols = {i for i, dt in enumerate(df.dtypes) if dt in (pl.Float32, pl.Float64)}
for row_idx, row_tuple in enumerate(df.iter_rows(), start=1):
    for col_idx, val in enumerate(row_tuple):
        fmt = num_fmt if col_idx in float_cols else data_fmt
        ws.write(row_idx, col_idx, '' if val is None else val, fmt)

wb.close()
t1 = time.time()
print(f"xlsxwriter (constant_memory + per-cell write): {t1-t0:.2f}s → {os.path.getsize(out1)//1024}KB")

# ── Test 2: xlsxwriter with write_row (no per-cell format) ──────────────────
out2 = os.path.join(out_dir, 'bench_xlsxwriter_row.xlsx')
t0 = time.time()
wb2 = xlsxwriter.Workbook(out2, {'constant_memory': True})
ws2 = wb2.add_worksheet('Sheet1')
ws2.right_to_left()
ws2.freeze_panes(1, 0)
ws2.autofilter(0, 0, n, len(df.columns) - 1)

hdr_fmt2 = wb2.add_format({'bold': True, 'bg_color': navy, 'font_color': '#FFFFFF',
    'border': 1, 'align': 'right', 'valign': 'vcenter'})
for col_idx, header in enumerate(df.columns):
    ws2.write(0, col_idx, header, hdr_fmt2)

for row_idx, row_tuple in enumerate(df.iter_rows(), start=1):
    ws2.write_row(row_idx, 0, ['' if v is None else v for v in row_tuple])

wb2.close()
t1 = time.time()
print(f"xlsxwriter (write_row, no per-cell fmt): {t1-t0:.2f}s → {os.path.getsize(out2)//1024}KB")

# ── Test 3: polars write_excel ───────────────────────────────────────────────
out3 = os.path.join(out_dir, 'bench_polars.xlsx')
t0 = time.time()
df.write_excel(
    workbook=out3,
    worksheet='Sheet1',
    table_style='TableStyleMedium9',
    autofilter=True,
    freeze_rows=1,
    autofit=False,
    header_format={'bold': True, 'bg_color': navy, 'font_color': '#FFFFFF'},
    column_formats={'عدد العملاء': '#,##0.000', 'المبلغ': '#,##0.000'},
)
t1 = time.time()
print(f"polars write_excel (xlsxwriter backend): {t1-t0:.2f}s → {os.path.getsize(out3)//1024}KB")

print("\nDone! Files written to:", out_dir)
