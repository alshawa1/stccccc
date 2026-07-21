import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'c:\Users\dell\Downloads\فايلات مهاره\STC_System')

import polars as pl
from python_calamine import CalamineWorkbook
import copy
import math

# 1. Load the original excel file
file_path = r"c:\Users\dell\Downloads\فايلات مهاره\المحفظه الموزعه.xlsx"
wb = CalamineWorkbook.from_path(file_path)
sheet = wb.get_sheet_by_name(wb.sheet_names[0])
data = sheet.to_python()
headers = [str(h).strip() for h in data[0]]
records = data[1:]
df = pl.DataFrame(records, schema=headers, orient="row")

# Clean float column for balance
bal_col = "متبقي سداد موثق"
id_col = "رقم الهوية"
prt_col = "المحافظ"
col_col = "المحصل"
usr_col = "اسم المستخدم"

def _clean_float(series: pl.Series) -> pl.Series:
    return (
        series
        .cast(pl.String, strict=False)
        .str.replace_all(",", "")
        .str.strip_chars()
        .cast(pl.Float64, strict=False)
        .fill_null(0.0)
    )

df = df.with_columns([
    pl.col(prt_col).cast(pl.String).str.strip_chars().alias(prt_col),
    pl.col(col_col).cast(pl.String).str.strip_chars().alias(col_col),
])
df = df.with_columns(_clean_float(df[bal_col]).alias(bal_col))

SUM_COL = "إجمالي مديونيات العميل"
df = df.with_columns(pl.col(bal_col).sum().over(id_col).alias(SUM_COL))

df_active = df.filter(pl.col(bal_col) >= 50.0)

source_clean = ["المحفظه الاولي 2025"]
target_clean = ["المحفظه الثانية 2025", "المحفظة الاولي 2026", "المحفظة الثانية 2026"]

def is_human_collector(name: str) -> bool:
    name_clean = str(name).strip()
    if not name_clean:
        return False
    system_keywords = ["الكتروني", "سحب", "تدوير", "استبعاد", "عناية", "عنايه", "نظام", "system", "auto", "توزيع", "خارج التغطية", "خارج التغطيه"]
    for kw in system_keywords:
        if kw in name_clean:
            return False
    return True

# Classify human collectors
all_active_collectors = df_active.select(col_col).unique().to_series().drop_nulls().to_list()
human_collectors = [c for c in all_active_collectors if is_human_collector(c)]

# Active human data
df_active_human = df_active.filter(pl.col(col_col).is_in(human_collectors))

# ── Phase 1: Source Analysis
source_df_human = df_active_human.filter(pl.col(prt_col).is_in(source_clean))
source_collector_stats = (
    source_df_human.unique(subset=[id_col])
    .group_by(col_col)
    .agg([
        pl.col(id_col).count().alias("cnt"),
        pl.col(SUM_COL).sum().alias("bal"),
    ])
    .sort(col_col)
)

all_scope_human = df_active_human.filter(pl.col(prt_col).is_in(source_clean + target_clean))
global_collector_stats = (
    all_scope_human.unique(subset=[id_col, col_col])
    .group_by(col_col)
    .agg([
        pl.col(id_col).count().alias("g_cnt"),
        pl.col(SUM_COL).sum().alias("g_bal"),
    ])
)

n_global_collectors = global_collector_stats.height
total_global_cnt = int(global_collector_stats["g_cnt"].sum())
total_global_bal = float(global_collector_stats["g_bal"].sum())

ideal_cnt = total_global_cnt / n_global_collectors if n_global_collectors else 0
ideal_bal = total_global_bal / n_global_collectors if n_global_collectors else 0

global_lookup = {
    str(r[col_col]): {"g_cnt": int(r["g_cnt"]), "g_bal": float(r["g_bal"])}
    for r in global_collector_stats.iter_rows(named=True)
}

withdrawal_plan = []
for row in source_collector_stats.iter_rows(named=True):
    c = str(row[col_col])
    cnt = int(row["cnt"])
    bal = float(row["bal"])
    g = global_lookup.get(c, {"g_cnt": cnt, "g_bal": bal})
    g_cnt = g["g_cnt"]
    excess_cnt = g_cnt - int(ideal_cnt)
    excess_cnt = min(excess_cnt, cnt)
    if excess_cnt > 0:
        withdrawal_plan.append({
            "collector":      c,
            "current_cnt":    cnt,
            "current_bal":    bal,
            "global_cnt":     g_cnt,
            "ideal_cnt":      int(ideal_cnt),
            "excess_cnt":     excess_cnt,
        })

# ── Phase 2: Pulling Clients
withdrawn_ids = []
for wp in withdrawal_plan:
    collector = wp["collector"]
    excess = wp["excess_cnt"]
    collector_clients = (
        source_df_human
        .filter(pl.col(col_col) == collector)
        .unique(subset=[id_col])
        .sort(SUM_COL, descending=False)
    )
    to_withdraw = collector_clients.head(excess)
    for row in to_withdraw.iter_rows(named=True):
        withdrawn_ids.append({
            "id": str(row[id_col]),
            "from_collector": collector,
            "balance": float(row.get(SUM_COL, 0)),
        })

# ── Phase 3: Greedy Allocation to target collectors
target_collectors = (
    df_active_human.filter(pl.col(prt_col).is_in(target_clean))
    .select(col_col).unique().to_series()
    .cast(pl.String).str.strip_chars().drop_nulls().sort().to_list()
)

def _init_collector_state(df, id_col, sum_col, target_clean, target_collectors, prt_col, col_col):
    target_df = df.filter(pl.col(prt_col).is_in(target_clean))
    pairs = target_df.select([col_col, prt_col]).unique().drop_nulls()
    state = {}
    for row in pairs.iter_rows(named=True):
        c = str(row[col_col]).strip()
        p = str(row[prt_col]).strip()
        state[f"{c} | {p}"] = {"cnt": 0, "bal": 0.0}
    agg = (
        target_df.unique(subset=[id_col])
        .group_by([col_col, prt_col])
        .agg([
            pl.col(id_col).count().alias("cnt"),
            pl.col(sum_col).sum().alias("bal")
        ])
    )
    for row in agg.iter_rows(named=True):
        c = str(row[col_col]).strip()
        p = str(row[prt_col]).strip()
        key = f"{c} | {p}"
        if key in state:
            state[key]["cnt"] = int(row["cnt"])
            state[key]["bal"] = float(row["bal"])
    return state

state_before = _init_collector_state(df_active_human, id_col, SUM_COL, target_clean, target_collectors, prt_col, col_col)
state_after = copy.deepcopy(state_before)

client_units = pl.DataFrame({
    id_col: [w["id"] for w in withdrawn_ids],
    SUM_COL: [w["balance"] for w in withdrawn_ids],
}).unique(subset=[id_col]).sort(SUM_COL, descending=True)

def _assign_greedy(client_units, collector_state, alpha, beta):
    collectors = list(collector_state.keys())
    assignments = {}
    for row in client_units.iter_rows(named=True):
        cid  = str(row[id_col])
        cbal = float(row.get(SUM_COL, 0) or 0)
        max_cnt = max((collector_state[c]["cnt"] for c in collectors), default=1) or 1
        max_bal = max((collector_state[c]["bal"] for c in collectors), default=1) or 1
        best_col, best_score = None, float("inf")
        for c in collectors:
            score = (
                alpha * (collector_state[c]["cnt"] / max_cnt) +
                beta  * (collector_state[c]["bal"] / max_bal)
            )
            if score < best_score:
                best_score = score
                best_col   = c
        assignments[cid] = best_col
        collector_state[best_col]["cnt"] += 1
        collector_state[best_col]["bal"] += cbal
    return assignments

assignments = _assign_greedy(client_units, state_after, 0.5, 0.5)

# Import Balancing module to call _build_planning_sheet
from modules.module8_balancing import PortfolioBalancingModule
bm = PortfolioBalancingModule()

print("Building planning sheet...")
planning_df = bm._build_planning_sheet(
    df, source_df_human, id_col, SUM_COL, col_col, prt_col,
    source_clean, target_clean,
    source_collector_stats, ideal_cnt, ideal_bal,
    withdrawal_plan, state_before, state_after, withdrawn_ids
)

print("\nPlanning sheet head 20:")
print(planning_df.head(20))
