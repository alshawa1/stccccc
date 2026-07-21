import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'c:\Users\dell\Downloads\فايلات مهاره\STC_System')

import polars as pl
from core.data_loader import DataLoader

portfolio_path = r"c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx"
dl = DataLoader("main_portfolio")
portfolio, result = dl.load(portfolio_path)

print(f"Portfolio loaded: {len(portfolio):,} rows")

from modules.module8_balancing import PortfolioBalancingModule

source = ["المحفظه الاولي 2025"]
print(f"Source: {source}")

try:
    r = PortfolioBalancingModule().run(portfolio, source_portfolios=source)
    print("\n✅ SUCCESS!")
    print(f"data rows: {len(r['data']):,}")
    print(f"summary_pivot rows: {len(r['summary_pivot'])}")
    
    # planning_sheet
    ps = r.get('planning_sheet')
    if ps is not None:
        print(f"planning_sheet: {len(ps)} rows, {len(ps.columns)} columns")
    else:
        print("planning_sheet: None")
    
    # stats
    for k, v in r['stats'].items():
        print(f"  {k}: {v}")
    
    # Show summary pivot
    print("\n=== ملخص التوزيع ===")
    print(r['summary_pivot'].head(10))
    
except Exception as e:
    import traceback
    print("ERROR:")
    traceback.print_exc()
