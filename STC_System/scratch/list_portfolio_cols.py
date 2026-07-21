import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'c:\Users\dell\Downloads\فايلات مهاره\STC_System')

from core.data_loader import DataLoader

portfolio_path = r"c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx"
dl = DataLoader("main_portfolio")
portfolio, result = dl.load(portfolio_path)

print(f"Portfolio loaded: {len(portfolio):,} rows")
print("\nAll columns:")
for c in portfolio.columns:
    print(f"  '{c}'")
