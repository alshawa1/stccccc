import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'c:\Users\dell\Downloads\فايلات مهاره\STC_System')

import polars as pl
from core.data_loader import DataLoader

portfolio_path = r"c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx"
dl = DataLoader("main_portfolio")
portfolio, result = dl.load(portfolio_path)

print(f"Portfolio loaded: {len(portfolio):,} rows")

# عمود المحافظ
prt_col = None
for c in ["المحافظ", "المحفظة", "اسم المحفظة"]:
    if c in portfolio.columns:
        prt_col = c
        break

print(f"Portfolio column: '{prt_col}'")

if prt_col:
    portfolios = portfolio[prt_col].cast(pl.String).str.strip_chars().unique().drop_nulls().sort().to_list()
    print(f"Unique portfolios ({len(portfolios)}):")
    for p in portfolios:
        cnt = len(portfolio.filter(pl.col(prt_col) == p))
        print(f"  '{p}' → {cnt:,} صف")

# اختبار module8
from modules.module8_balancing import PortfolioBalancingModule, is_human_collector

# المحصلون
all_collectors = portfolio["المحصل"].cast(pl.String).unique().drop_nulls().to_list()
human = [c for c in all_collectors if is_human_collector(c)]
system = [c for c in all_collectors if not is_human_collector(c)]
print(f"\nTotal collectors: {len(all_collectors)}")
print(f"Human: {len(human)} | System: {len(system)}")
print(f"System: {system}")

# اختبر بمحفظة مصدر حقيقية
if prt_col and portfolios:
    source = [portfolios[0]]
    print(f"\n=== Running balancing: source={source} ===")
    try:
        r = PortfolioBalancingModule().run(portfolio, source_portfolios=source)
        print("SUCCESS!")
        print(f"data rows: {len(r['data']):,}")
        print(f"summary_pivot:\n{r['summary_pivot']}")
        if r.get('planning_sheet') is not None:
            ps = r['planning_sheet']
            print(f"\nplanning_sheet ({len(ps)} rows, cols: {ps.columns}):")
            print(ps.head(5))
        print(f"stats: {r['stats']}")
    except Exception as e:
        import traceback
        print("ERROR:")
        traceback.print_exc()
