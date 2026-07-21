import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'c:\Users\dell\Downloads\فايلات مهاره\STC_System')

import polars as pl
from core.data_loader import DataLoader

portfolio_path = r"c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx"
dl = DataLoader("main_portfolio")
portfolio, result = dl.load(portfolio_path)

print("Check mapping between المحصل and اسم المستخدم:")
# Clean columns
df = portfolio.select(["المحصل", "اسم المستخدم"]).drop_nulls()
df = df.with_columns([
    pl.col("المحصل").cast(pl.String).str.strip_chars(),
    pl.col("اسم المستخدم").cast(pl.String).str.strip_chars(),
])

# Group by المحصل and list unique users
collector_users = df.group_by("المحصل").agg(pl.col("اسم المستخدم").unique())
print(collector_users.head(30))

# Let's count how many collectors have multiple users
mult = collector_users.filter(pl.col("اسم المستخدم").list.len() > 1)
print(f"\nCollectors with multiple users ({len(mult)}):")
print(mult)

# Let's count how many users have multiple collectors
user_collectors = df.group_by("اسم المستخدم").agg(pl.col("المحصل").unique())
mult_users = user_collectors.filter(pl.col("المحصل").list.len() > 1)
print(f"\nUsers with multiple collectors ({len(mult_users)}):")
print(mult_users.head(20))
