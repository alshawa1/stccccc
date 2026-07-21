import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'c:\Users\dell\Downloads\فايلات مهاره\STC_System')

import time
import polars as pl
from core.data_loader import load_files
from core.utils import MAIN_PORTFOLIO
from modules.module8_balancing import PortfolioBalancingModule

portfolio_path = r'c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx'
dfs, _ = load_files({MAIN_PORTFOLIO: portfolio_path})
portfolio = dfs[MAIN_PORTFOLIO]

# Print unique collectors and their portfolios
print("\nCollectors with their portfolios:")
print(
    portfolio.group_by(["المحصل", "المحافظ"])
    .agg(pl.col("رقم الهوية").count().alias("count"))
    .sort(["المحافظ", "count"], descending=[False, True])
)

source_p = ["المحفظه الاولي 2025"]
target_p = ["المحفظه الثانية 2025", "المحفظة الاولي 2026", "المحفظة الثانية 2026"]

bm = PortfolioBalancingModule()
res = bm.run(portfolio, source_portfolios=source_p, target_portfolios=target_p)

# Let's inspect target_collectors from the run
print("\nSummary Pivot Collectors:")
print(res["summary_pivot"]["المحصل"].to_list())
