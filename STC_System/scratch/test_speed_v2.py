import time, sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
sys.path.insert(0, r'c:\Users\dell\Downloads\فايلات مهاره\STC_System')
import polars as pl
from core.data_loader import load_files
from core.utils import MAIN_PORTFOLIO

portfolio_path = r'c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx'
if not os.path.exists(portfolio_path):
    print('Portfolio file not found')
    sys.exit(1)

t0 = time.time()
dfs, results = load_files({MAIN_PORTFOLIO: portfolio_path})
t1 = time.time()
portfolio = dfs[MAIN_PORTFOLIO]
print(f'Load: {t1-t0:.2f}s, shape={portfolio.shape}')

from modules.module3_neglect import NeglectModule
t2 = time.time()
r = NeglectModule().run(portfolio)
t3 = time.time()
print(f'Module3 run: {t3-t2:.2f}s, neglected={len(r["data"])}, full={len(r["full_analysis"])}')
print(f'عدد العملاء exists: {"عدد العملاء" in r["full_analysis"].columns}')

from export.excel_writer import ExcelReportWriter
out = r'c:\Users\dell\Downloads\فايلات مهاره\test_neglect_speed.xlsx'
t4 = time.time()
writer = ExcelReportWriter(out)
writer.write_neglect(
    r['data'], r['full_analysis'],
    r['pivot_summary'], r['pivot_supervisor'], r['pivot_collector'],
    r['pivot_status'], r['pivot_branch'], r['pivot_portfolio'], r['pivot_days']
)
writer.write_dashboard(r['stats'], 3)
writer.write_summary(r['stats'])
writer.save()
t5 = time.time()
print(f'Excel write+save: {t5-t4:.2f}s')
print(f'TOTAL: {t5-t0:.2f}s')
print(f'Output: {os.path.basename(out)}')
