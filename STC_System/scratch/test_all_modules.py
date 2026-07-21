"""Full end-to-end test for all 4 modules using the new xlsxwriter-based ExcelReportWriter."""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'c:\Users\dell\Downloads\فايلات مهاره\STC_System')

from core.data_loader import load_files
from core.utils import MAIN_PORTFOLIO
import polars as pl

portfolio_path = r'c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx'
OUT = r'c:\Users\dell\Downloads\فايلات مهاره'

# Load once
print("Loading portfolio...")
t0 = time.time()
dfs, _ = load_files({MAIN_PORTFOLIO: portfolio_path})
portfolio = dfs[MAIN_PORTFOLIO]
print(f"  → {portfolio.shape}  ({time.time()-t0:.2f}s)")

from export.excel_writer_xl import ExcelReportWriter

results = {}

# ── Module 3: الإهمال ────────────────────────────────────────────────────────
print("\n[Module 3] الإهمال...")
from modules.module3_neglect import NeglectModule
t = time.time()
r3 = NeglectModule().run(portfolio)
out3 = os.path.join(OUT, 'test_m3_neglect.xlsx')
w3 = ExcelReportWriter(out3)
w3.write_neglect(r3['data'], r3['full_analysis'], r3['pivot_summary'],
    r3['pivot_supervisor'], r3['pivot_collector'], r3['pivot_status'],
    r3['pivot_branch'], r3['pivot_portfolio'], r3['pivot_days'])
w3.write_dashboard(r3['stats'], 3)
w3.write_summary(r3['stats'])
w3.save()
results['الإهمال'] = time.time()-t
print(f"  ✅ {results['الإهمال']:.1f}s  →  {os.path.basename(out3)} ({os.path.getsize(out3)//1024} KB)")

# ── Module 1: أخطاء النظام ───────────────────────────────────────────────────
print("\n[Module 1] أخطاء النظام...")
from modules.module1_errors import SystemErrorsModule
t = time.time()
r1 = SystemErrorsModule().run(portfolio, pl.DataFrame())
out1 = os.path.join(OUT, 'test_m1_errors.xlsx')
w1 = ExcelReportWriter(out1)
w1.write_errors(r1['data'])
w1.write_dashboard(r1['stats'], 1)
w1.write_summary(r1['stats'])
w1.save()
results['أخطاء النظام'] = time.time()-t
print(f"  ✅ {results['أخطاء النظام']:.1f}s  →  {os.path.basename(out1)} ({os.path.getsize(out1)//1024} KB)")

# ── Module 2: التوصل ────────────────────────────────────────────────────────
print("\n[Module 2] التوصل وعدم التوصل...")
from modules.module2_contact import ContactStatusModule
t = time.time()
r2 = ContactStatusModule().run(portfolio)
out2 = os.path.join(OUT, 'test_m2_contact.xlsx')
w2 = ExcelReportWriter(out2)
w2.write_contact(r2['data'], r2['pivot_supervisor'], r2['pivot_collector'], r2['pivot_status'])
w2.write_dashboard(r2['stats'], 2)
w2.write_summary(r2['stats'])
w2.save()
results['التوصل'] = time.time()-t
print(f"  ✅ {results['التوصل']:.1f}s  →  {os.path.basename(out2)} ({os.path.getsize(out2)//1024} KB)")

# ── Module 7: العملاء المستهدفة ─────────────────────────────────────────────
print("\n[Module 7] العملاء المستهدفة...")
from modules.module7_targets import TargetCustomersModule
t = time.time()
r7 = TargetCustomersModule().run(portfolio, pl.DataFrame(), pl.DataFrame())
out7 = os.path.join(OUT, 'test_m7_targets.xlsx')
w7 = ExcelReportWriter(out7)
w7.write_targets(r7['data'], r7['pivot_supervisor'])
w7.write_dashboard(r7['stats'], 7)
w7.write_summary(r7['stats'])
w7.save()
results['العملاء المستهدفة'] = time.time()-t
print(f"  ✅ {results['العملاء المستهدفة']:.1f}s  →  {os.path.basename(out7)} ({os.path.getsize(out7)//1024} KB)")

print("\n" + "="*60)
print("SUMMARY:")
for mod, elapsed in results.items():
    print(f"  {mod}: {elapsed:.1f}s")
print(f"  TOTAL (4 modules): {sum(results.values()):.1f}s")
print("="*60)
