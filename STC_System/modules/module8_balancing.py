"""
modules/module8_balancing.py
─────────────────────────────
Module 8 — التوازن الشامل للمحافظ (Full Portfolio Balancing System) using Polars.

الخوارزمية (Giver/Receiver Snake-Draft):
  1. تجمع كل العملاء الفريدين برقم الهوية — العميل لا يتفرق بين محصلين.
  2. تحدد المانحين (Givers) وهم من عندهم عملاء زيادة عن المتوسط، والمستقبلين (Receivers).
  3. تسحب من المانحين فقط من المحفظة المصدر المحددة.
  4. توزع المسحوبين على المستقبلين بخوارزمية Snake-Draft لتوازن العدد والرصيد.
  5. المانح لا يظهر أبداً في عمود "المحصل الجديد".
  6. تُبقي رقم اليوزر الأصلي للمحصل القديم في عمود اليوزر دون تعديل.
"""
from __future__ import annotations

import math
import logging
import re
from collections import Counter
from typing import Dict, List, Optional

import polars as pl

_log = logging.getLogger("Module8_Balancing")

# ── Smart Column Detection ────────────────────────────────────────────────────
_ID_COLS         = ["رقم الهوية", "الهوية", "هويا", "رقم هوية"]
_NAME_COLS       = ["اسم العميل", "العميل", "الاسم"]
_BALANCE_COLS    = ["متبقي سداد موثق", "متبقي السداد الموثق", "متبقي سداد", "الرصيد المتبقي", "المتبقي", "الرصيد"]
_PORTFOLIO_COLS  = ["المحافظ", "المحفظة", "اسم المحفظة", "Portfolio", "محفظة", "محافظ"]
_SUPERVISOR_COLS = ["المشرف", "اسم المشرف"]
_COLLECTOR_COLS  = ["المحصل", "اسم المحصل", "الموظف", "محصل"]
_USER_COLS       = ["اسم المستخدم", "اليوزر", "User", "user", "المستخدم"]


def _detect(df: pl.DataFrame, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    for c in df.columns:
        for cand in candidates:
            if cand in c or c in cand:
                return c
    return None


def _clean_float(series: pl.Series) -> pl.Series:
    return (
        series
        .cast(pl.String, strict=False)
        .str.replace_all(",", "")
        .str.strip_chars()
        .cast(pl.Float64, strict=False)
        .fill_null(0.0)
    )


def normalize_name(name: str) -> str:
    if not name:
        return ""
    s = str(name).strip()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه")
    return s


def is_human_collector(name: str) -> bool:
    name_clean = str(name).strip()
    if not name_clean:
        return False
    system_keywords = [
        "الكتروني", "سحب", "تدوير", "استبعاد", "عناية", "عنايه",
        "نظام", "system", "auto", "توزيع", "خارج التغطية", "خارج التغطيه",
    ]
    for kw in system_keywords:
        if kw in name_clean:
            return False
    return True


def _std(values: list) -> float:
    if not values or len(values) < 2:
        return 0.0
    n = len(values)
    mean = sum(values) / n
    return math.sqrt(sum((x - mean) ** 2 for x in values) / n)


class PortfolioBalancingModule:
    """
    التوازن الشامل للمحافظ — خوارزمية Giver/Receiver Snake-Draft.

    تضمن توازناً رياضياً في عدد العملاء والرصيد معاً،
    مع ضمان أن المحصل المسحوب منه لا يظهر في "المحصل الجديد".
    """

    @staticmethod
    def get_portfolios(portfolio: pl.DataFrame) -> List[str]:
        """دالة داخل الكلاس لجلب أسماء المحافظ المتاحة"""
        prt_col = _detect(portfolio, _PORTFOLIO_COLS)
        if not prt_col:
            return []
        return (
            portfolio.select(prt_col)
            .unique()
            .to_series()
            .cast(pl.String)
            .str.strip_chars()
            .drop_nulls()
            .sort()
            .to_list()
        )

    @staticmethod
    def get_collectors_per_portfolio(portfolio: pl.DataFrame) -> Dict[str, List[str]]:
        """إرجاع dict: {اسم المحفظة: [قائمة المحصلين البشريين]}"""
        prt_col = _detect(portfolio, _PORTFOLIO_COLS)
        col_col = _detect(portfolio, _COLLECTOR_COLS)
        if not prt_col or not col_col:
            return {}

        result = {}
        portfolios = (
            portfolio.select(prt_col)
            .unique().to_series()
            .cast(pl.String).str.strip_chars()
            .drop_nulls().sort().to_list()
        )
        for prt in portfolios:
            collectors = (
                portfolio.filter(pl.col(prt_col).cast(pl.String).str.strip_chars() == prt)
                .select(col_col).unique().to_series()
                .cast(pl.String).str.strip_chars().drop_nulls().sort().to_list()
            )
            result[prt] = [c for c in collectors if is_human_collector(c)]
        return result

    # ─────────────────────────────────────────────────────────────────────────
    def run(
        self,
        portfolio: pl.DataFrame,
        source_portfolios: List[str],
        target_portfolios: Optional[List[str]] = None,
        alpha: float = 0.5,
        beta: float = 0.5,
        min_receiver_chunk: Optional[int] = None,
    ) -> Dict:
        """
        خوارزمية Giver/Receiver Snake-Draft للتوازن الشامل.

        المعاملات
        ----------
        portfolio         : إطار البيانات الكامل للمحفظة
        source_portfolios : المحافظ المصدر (نسحب منها فقط عند التوزيع)
        target_portfolios : المحافظ المستهدفة — فارغ = الكل
        """

        # ── 1. كشف الأعمدة ────────────────────────────────────────────────
        id_col  = _detect(portfolio, _ID_COLS)
        bal_col = _detect(portfolio, _BALANCE_COLS)
        prt_col = _detect(portfolio, _PORTFOLIO_COLS)
        col_col = _detect(portfolio, _COLLECTOR_COLS)
        usr_col = _detect(portfolio, _USER_COLS)

        if not id_col or not col_col or not prt_col:
            raise ValueError("لم يتم العثور على الأعمدة الأساسية (الهوية، المحصل، أو المحافظ)")

        # ── 2. تنظيف وتوحيد البيانات ───────────────────────────────────────
        df = portfolio.clone()
        df = df.with_columns([
            pl.col(id_col)
            .cast(pl.String)
            .str.replace(r"\.0$", "", literal=False)
            .str.strip_chars()
            .alias(id_col),
            pl.col(prt_col).cast(pl.String).str.strip_chars().alias(prt_col),
            pl.col(col_col).cast(pl.String).str.strip_chars().alias(col_col),
        ])
        if bal_col:
            df = df.with_columns(_clean_float(df[bal_col]).alias(bal_col))
        if usr_col and usr_col in df.columns:
            df = df.with_columns(pl.col(usr_col).cast(pl.String).str.strip_chars().alias(usr_col))

        # ── 3. فلتر المبالغ >= 50 ─────────────────────────────────────────
        df_active = df.clone()
        if bal_col:
            df_active = df_active.filter(pl.col(bal_col) >= 50.0)

        # ── 4. تحديد المحافظ المصدر ───────────────────────────────────────
        source_clean = [s.strip() for s in source_portfolios]

        # ── 5. بناء قاموس توحيد الأسماء والتشكيل (norm_to_orig) ───────────
        raw_names = df_active.select(col_col).to_series().drop_nulls().to_list()
        counts = Counter(raw_names)
        grouped_spellings: Dict[str, List[str]] = {}
        for raw in raw_names:
            norm = normalize_name(raw)
            if norm not in grouped_spellings:
                grouped_spellings[norm] = []
            grouped_spellings[norm].append(raw)

        norm_to_orig = {}
        for norm, raws in grouped_spellings.items():
            best_raw = max(raws, key=lambda r: counts[r])
            norm_to_orig[norm] = best_raw.strip()

        # ── 6. تحديد المحصلين البشريين ────────────────────────────────────
        all_active_collectors = (
            df_active.select(col_col).unique().to_series().drop_nulls().to_list()
        )
        human_collectors_normalized = sorted(list({
            normalize_name(c) for c in all_active_collectors if is_human_collector(c)
        }))

        df_human = df_active.filter(
            pl.col(col_col).map_elements(is_human_collector, return_dtype=pl.Boolean)
        ).with_columns(
            pl.col(col_col).map_elements(normalize_name, return_dtype=pl.String).alias("norm_col")
        )

        if len(df_human) == 0:
            raise ValueError("لا توجد سجلات للمحصلين البشر في المحافظ المختارة")

        # ── 6.5. توحيد المحصل لكل عميل (Unification) ─────────────────────
        id_col_balances_early = (
            df_human
            .group_by([id_col, "norm_col"])
            .agg(pl.col(bal_col).sum().alias("sum_bal"))
        )
        primary_collectors_early = (
            id_col_balances_early
            .sort("sum_bal", descending=True)
            .group_by(id_col)
            .first()
        )
        df_human = (
            df_human
            .drop("norm_col")
            .join(
                primary_collectors_early.select([id_col, "norm_col"]),
                on=id_col,
                how="left"
            )
        )

        # ── 7. lookup اليوزر الأصلي ────────────────────────────────────────
        user_lookup = self._build_user_lookup(df_active, col_col, usr_col)
        user_dict = (
            {str(r[col_col]).strip(): str(r[usr_col]).strip()
             for r in user_lookup.iter_rows(named=True)}
        if user_lookup is not None else {}
        )

        # ── 8. تجميع وحيد لكل عميل بالهوية ──────────────────────────────
        # نحدد إذا كنا نعمل في وضع الحد الأدنى للمستقبل (min_receiver_chunk)
        # إذا كان كذلك، سنقوم ببناء التجميع والموازنة بالكامل للمحفظة المصدر بشكل مستقل
        
        is_chunk_mode = min_receiver_chunk is not None and min_receiver_chunk > 0
        
        # 8.1. التجميع العام (لعرض الإحصاءات الكلية قبل وبعد)
        id_col_balances_all = (
            df_human
            .group_by([id_col, "norm_col"])
            .agg(pl.col(bal_col).sum().alias("sum_bal"))
        )
        primary_collectors_all = id_col_balances_all.sort("sum_bal", descending=True).group_by(id_col).first()
        client_level_all = (
            df_human
            .group_by(id_col)
            .agg([
                pl.col(bal_col).sum().alias("client_bal"),
                pl.len().alias("rows_count")
            ])
            .join(primary_collectors_all.select([id_col, "norm_col"]), on=id_col, how="left")
        )
        portfolio_primary_all = (
            df_human
            .group_by([id_col, prt_col])
            .agg(pl.col(bal_col).sum().alias("sum_bal"))
            .sort("sum_bal", descending=True)
            .group_by(id_col)
            .first()
        )
        client_level_all = client_level_all.join(
            portfolio_primary_all.select([id_col, prt_col]), on=id_col, how="left"
        )
        
        collector_stats_all = (
            df_human
            .group_by("norm_col")
            .agg([
                pl.len().alias("cnt"),
                pl.col(bal_col).sum().alias("bal"),
            ])
            .sort("norm_col")
        )
        collector_lookup_before: Dict[str, Dict] = {
            c: {"cnt": 0, "bal": 0.0} for c in human_collectors_normalized
        }
        for r in collector_stats_all.iter_rows(named=True):
            collector_lookup_before[str(r["norm_col"])] = {
                "cnt": int(r["cnt"]),
                "bal": float(r["bal"]),
            }

        # 8.2. التجميع الفعلي لعملية الموازنة
        if is_chunk_mode:
            # نفلتر البيانات للمحفظة المصدر فقط
            df_human_active = df_human.filter(pl.col(prt_col).is_in(source_clean))
        else:
            df_human_active = df_human

        id_col_balances = (
            df_human_active
            .group_by([id_col, "norm_col"])
            .agg(pl.col(bal_col).sum().alias("sum_bal"))
        )

        primary_collectors = (
            id_col_balances
            .sort("sum_bal", descending=True)
            .group_by(id_col)
            .first()
        )

        client_level = (
            df_human_active
            .group_by(id_col)
            .agg([
                pl.col(bal_col).sum().alias("client_bal"),
                pl.len().alias("rows_count")
            ])
            .join(primary_collectors.select([id_col, "norm_col"]), on=id_col, how="left")
        )

        portfolio_primary = (
            df_human_active
            .group_by([id_col, prt_col])
            .agg(pl.col(bal_col).sum().alias("sum_bal"))
            .sort("sum_bal", descending=True)
            .group_by(id_col)
            .first()
        )
        client_level = client_level.join(
            portfolio_primary.select([id_col, prt_col]), on=id_col, how="left"
        )

        # ── 9. إحصاءات الحالة الحالية (للموازنة الفعلية) ────────────────────
        collector_stats = (
            df_human_active
            .group_by("norm_col")
            .agg([
                pl.len().alias("cnt"),
                pl.col(bal_col).sum().alias("bal"),
            ])
            .sort("norm_col")
        )

        n_collectors = len(human_collectors_normalized)
        if n_collectors == 0:
            raise ValueError("لا يوجد محصلون بشريون")

        collector_lookup: Dict[str, Dict] = {
            c: {"cnt": 0, "bal": 0.0} for c in human_collectors_normalized
        }
        for r in collector_stats.iter_rows(named=True):
            collector_lookup[str(r["norm_col"])] = {
                "cnt": int(r["cnt"]),
                "bal": float(r["bal"]),
            }

        # ── 10. حساب الهدف المثالي والمانحين والمستقبلين ─────────────────
        total_cnt = sum(c["cnt"] for c in collector_lookup.values())
        total_bal = sum(c["bal"] for c in collector_lookup.values())
        
        if is_chunk_mode:
            final_col_map = {}
            withdrawn_clients = []
            givers = []
            receivers = []
            giver_withdrawn = {}
            giver_withdrawn_bal = {}
            target_cnt = {c: 0 for c in human_collectors_normalized}

            for sp in source_clean:
                df_human_sp = df_human.filter(pl.col(prt_col) == sp)
                if len(df_human_sp) == 0:
                    continue

                id_col_balances_sp = (
                    df_human_sp
                    .group_by([id_col, "norm_col"])
                    .agg(pl.col(bal_col).sum().alias("sum_bal"))
                )
                primary_collectors_sp = (
                    id_col_balances_sp
                    .sort("sum_bal", descending=True)
                    .group_by(id_col)
                    .first()
                )
                client_level_sp = (
                    df_human_sp
                    .group_by(id_col)
                    .agg([
                        pl.col(bal_col).sum().alias("client_bal"),
                        pl.len().alias("rows_count")
                    ])
                    .join(primary_collectors_sp.select([id_col, "norm_col"]), on=id_col, how="left")
                )

                collector_stats_sp = (
                    df_human_sp
                    .group_by("norm_col")
                    .agg([
                        pl.len().alias("cnt"),
                        pl.col(bal_col).sum().alias("bal"),
                    ])
                )
                collector_lookup_sp = {c: {"cnt": 0, "bal": 0.0} for c in human_collectors_normalized}
                for r in collector_stats_sp.iter_rows(named=True):
                    collector_lookup_sp[str(r["norm_col"])] = {"cnt": int(r["cnt"]), "bal": float(r["bal"])}

                source_counts = {c: collector_lookup_sp[c]["cnt"] for c in human_collectors_normalized}
                source_balances = {c: collector_lookup_sp[c]["bal"] for c in human_collectors_normalized}
                total_source_clients = sum(source_counts.values())

                if total_source_clients == 0:
                    continue

                max_active = total_source_clients // min_receiver_chunk
                if max_active == 0:
                    max_active = 1
                if max_active > n_collectors:
                    max_active = n_collectors

                sorted_by_source_cnt = sorted(
                    human_collectors_normalized,
                    key=lambda c: (-source_counts[c], -source_balances[c], c)
                )
                selected_active = sorted_by_source_cnt[:max_active]
                selected_active_set = set(selected_active)

                floor_source = total_source_clients // max_active
                rem_source = total_source_clients % max_active
                ceil_active_set = set(selected_active[:rem_source])

                target_cnt_source = {}
                for c in human_collectors_normalized:
                    if c in selected_active_set:
                        target_cnt_source[c] = floor_source + (1 if c in ceil_active_set else 0)
                    else:
                        target_cnt_source[c] = 0
                    target_cnt[c] += target_cnt_source[c]

                sp_givers = []
                sp_receivers = []
                for c in human_collectors_normalized:
                    diff = target_cnt_source[c] - source_counts[c]
                    if diff < 0:
                        sp_givers.append((c, -diff))
                    elif diff > 0:
                        sp_receivers.append((c, diff))

                givers.extend(sp_givers)
                receivers.extend(sp_receivers)

                sp_withdrawn_clients = []
                for g_col, n_withdraw in sp_givers:
                    g_clients = (
                        client_level_sp
                        .filter(pl.col("norm_col") == g_col)
                        .sort("client_bal", descending=True)
                        .to_dicts()
                    )
                    withdrawn = []
                    pulled_rows = 0
                    for client in g_clients:
                        if pulled_rows >= n_withdraw:
                            break
                        withdrawn.append(client)
                        pulled_rows += client["rows_count"]
                    sp_withdrawn_clients.extend(withdrawn)

                    actual_withdrawn = pulled_rows
                    withdrawn_bal = sum(c["client_bal"] for c in withdrawn)
                    giver_withdrawn[g_col] = giver_withdrawn.get(g_col, 0) + actual_withdrawn
                    giver_withdrawn_bal[g_col] = giver_withdrawn_bal.get(g_col, 0.0) + withdrawn_bal
                    collector_lookup_sp[g_col]["cnt"] -= actual_withdrawn
                    collector_lookup_sp[g_col]["bal"] -= withdrawn_bal

                withdrawn_clients.extend(sp_withdrawn_clients)
                n_with = len(sp_withdrawn_clients)
                if n_with > 0:
                    eligible_receivers = [r[0] for r in sp_receivers]
                    receiver_target_cnt = {r[0]: r[1] for r in sp_receivers}
                    n_recv = len(eligible_receivers)
                    recv_sorted_by_bal = sorted(eligible_receivers, key=lambda c: (collector_lookup_sp[c]["bal"], c))

                    receiver_assigned_cnt = {c: 0 for c in eligible_receivers}
                    sp_withdrawn_clients.sort(key=lambda x: -x["client_bal"])

                    going_fwd = True
                    idx_src = 0
                    while idx_src < len(sp_withdrawn_clients):
                        available = [c for c in eligible_receivers if receiver_assigned_cnt.get(c, 0) < receiver_target_cnt.get(c, 0)]
                        if not available:
                            remaining = sp_withdrawn_clients[idx_src:]
                            for i, client in enumerate(remaining):
                                c = recv_sorted_by_bal[i % n_recv]
                                final_col_map[client[id_col]] = c
                                collector_lookup_sp[c]["cnt"] += client["rows_count"]
                                collector_lookup_sp[c]["bal"] += client["client_bal"]
                            break

                        if going_fwd:
                            order = sorted(available, key=lambda c: collector_lookup_sp[c]["bal"])
                        else:
                            order = sorted(available, key=lambda c: -collector_lookup_sp[c]["bal"])

                        for c in order:
                            if idx_src >= len(sp_withdrawn_clients):
                                break
                            if receiver_assigned_cnt.get(c, 0) >= receiver_target_cnt.get(c, 0):
                                continue
                            client = sp_withdrawn_clients[idx_src]
                            final_col_map[client[id_col]] = c
                            collector_lookup_sp[c]["cnt"] += client["rows_count"]
                            collector_lookup_sp[c]["bal"] += client["client_bal"]
                            receiver_assigned_cnt[c] += client["rows_count"]
                            idx_src += 1
                        going_fwd = not going_fwd

            ideal_cnt = total_cnt / n_collectors
            ideal_bal = total_bal / n_collectors
        else:
            n_collectors_active = n_collectors  # كل المحصلين هم هدف التوازن
            ideal_cnt = total_cnt / n_collectors_active
            ideal_bal = total_bal / n_collectors_active

            # نوزع الكوتة: floor لكلهم، والباقي يأخذ +1 بالترتيب تنازلياً
            floor_cnt = total_cnt // n_collectors_active
            remainder = total_cnt % n_collectors_active
            sorted_by_cnt_desc = sorted(
                human_collectors_normalized,
                key=lambda c: (-collector_lookup[c]["cnt"], c)
            )
            ceil_set = set(sorted_by_cnt_desc[:remainder])
            target_cnt = {
                c: (floor_cnt + 1 if c in ceil_set else floor_cnt)
                for c in human_collectors_normalized
            }

            givers = []
            receivers = []
            for c in human_collectors_normalized:
                diff = target_cnt[c] - collector_lookup[c]["cnt"]
                if diff < 0:
                    givers.append((c, -diff))   # عدد الزيادة التي يجب سحبها
                elif diff > 0:
                    receivers.append((c, diff)) # عدد الناقص الذي يجب إضافته

        # ── 11. سحب العملاء من المانحين (فقط من المحفظة المصدر) ────────────
        withdrawn_clients: List[Dict] = []
        final_col_map: Dict[str, str] = {}

        # خرائط مساعدة
        orig_collector_map = {
            r[id_col]: r["norm_col"] for r in client_level.iter_rows(named=True)
        }
        all_client_bals = {
            r[id_col]: r["client_bal"] for r in client_level.iter_rows(named=True)
        }

        # تتبع كم سحبنا فعلاً من كل مانح
        giver_withdrawn: Dict[str, int] = {}
        giver_withdrawn_bal: Dict[str, float] = {}

        for g_col, n_withdraw in givers:
            # عملاء هذا المانح الموجودون في المحفظة المصدر فقط
            g_clients = (
                client_level
                .filter(
                    (pl.col("norm_col") == g_col)
                    & (pl.col(prt_col).is_in(source_clean))
                )
                .sort("client_bal", descending=True)  # الأعلى رصيداً أولاً
                .to_dicts()
            )
            withdrawn = []
            pulled_rows = 0
            for client in g_clients:
                if pulled_rows >= n_withdraw:
                    break
                withdrawn.append(client)
                pulled_rows += client["rows_count"]
                
            withdrawn_clients.extend(withdrawn)

            actual_withdrawn = pulled_rows
            withdrawn_bal = sum(c["client_bal"] for c in withdrawn)

            giver_withdrawn[g_col] = actual_withdrawn
            giver_withdrawn_bal[g_col] = withdrawn_bal

            # تحديث collector_lookup بعد السحب
            collector_lookup[g_col]["cnt"] -= actual_withdrawn
            collector_lookup[g_col]["bal"] -= withdrawn_bal



        # ── 12. توزيع المسحوبين على المستقبلين النشطين ─────────────────────────
        n_with = len(withdrawn_clients)
        
        if min_receiver_chunk is not None and min_receiver_chunk > 0:
            # في وضع الحد الأدنى، نوزع فقط على المستقبلين المختارين الذين لديهم عجز فعلي
            eligible_receivers = [r[0] for r in receivers]
            receiver_target_cnt = {r[0]: r[1] for r in receivers}
            n_recv = len(eligible_receivers)
            recv_sorted_by_bal = sorted(
                eligible_receivers,
                key=lambda c: (collector_lookup[c]["bal"], c)
            )
        else:
            # الوضع التقليدي: التوزيع بالتساوي على الجميع
            givers_set = {g[0] for g in givers}
            eligible_receivers = [
                c for c in human_collectors_normalized
                if c not in givers_set or giver_withdrawn.get(c, 0) == 0
            ]
            n_recv = len(eligible_receivers)
            if n_recv > 0 and n_with > 0:
                base_share = n_with // n_recv
                extra      = n_with % n_recv
                recv_sorted_by_bal = sorted(
                    eligible_receivers,
                    key=lambda c: (collector_lookup[c]["bal"], c)
                )
                receiver_target_cnt = {}
                for i, c in enumerate(recv_sorted_by_bal):
                    receiver_target_cnt[c] = base_share + (1 if i < extra else 0)
            else:
                recv_sorted_by_bal = []
                receiver_target_cnt = {r[0]: r[1] for r in receivers}

        receiver_assigned_cnt = {c: 0 for c in eligible_receivers}

        # فرز المسحوبين تنازلياً بالرصيد لتحقيق أفضل توازن للرصيد
        withdrawn_clients.sort(key=lambda x: -x["client_bal"])

        going_fwd = True
        idx_src = 0
        while idx_src < len(withdrawn_clients):
            available = [
                c for c in eligible_receivers
                if receiver_assigned_cnt.get(c, 0) < receiver_target_cnt.get(c, 0)
            ]
            if not available:
                # إذا امتلأت كل الكوتات، وزع الباقي بالـ Round-Robin البسيط
                remaining = withdrawn_clients[idx_src:]
                for i, client in enumerate(remaining):
                    c = recv_sorted_by_bal[i % n_recv] if (n_recv > 0 and recv_sorted_by_bal) else eligible_receivers[i % len(eligible_receivers)]
                    cid_s = client[id_col]
                    c_rows = client["rows_count"]
                    final_col_map[cid_s] = c
                    collector_lookup[c]["cnt"] += c_rows
                    collector_lookup[c]["bal"] += client["client_bal"]
                break

            # Snake: تصاعدي ثم تنازلي بالرصيد الحالي
            if going_fwd:
                order = sorted(available, key=lambda c: collector_lookup[c]["bal"])
            else:
                order = sorted(available, key=lambda c: -collector_lookup[c]["bal"])

            for c in order:
                if idx_src >= len(withdrawn_clients):
                    break
                if receiver_assigned_cnt.get(c, 0) >= receiver_target_cnt.get(c, 0):
                    continue

                client = withdrawn_clients[idx_src]
                cid_s = client[id_col]
                c_rows = client["rows_count"]

                final_col_map[cid_s] = c
                collector_lookup[c]["cnt"] += c_rows
                collector_lookup[c]["bal"] += client["client_bal"]
                receiver_assigned_cnt[c] = receiver_assigned_cnt.get(c, 0) + c_rows
                idx_src += 1

            going_fwd = not going_fwd

        # للحفاظ على التوافق مع الكود التالي
        receivers_list = eligible_receivers



        # receiver_state = الحالة النهائية بعد كل التعديلات
        receiver_state = collector_lookup

        # ── 13. assignments: الخريطة النهائية للعملاء المنقولين ─────────────
        # فقط العملاء الذين انتقلوا لمحصل مختلف عن الأصلي
        assignments: Dict[str, str] = {
            cid_s: norm_to_orig.get(final_c, final_c)
            for cid_s, final_c in final_col_map.items()
            if final_c != orig_collector_map.get(cid_s, "")
        }

        total_withdrawn_bal = sum(all_client_bals[cid_s] for cid_s in assignments)

        # ── 14. بناء شيت المخرجات الكامل ──────────────────────────────────
        if assignments:
            assign_df = pl.DataFrame({
                id_col:          list(assignments.keys()),
                "المحصل الجديد": [str(v).strip() for v in assignments.values()],
                "حالة السحب":    ["تم السحب"] * len(assignments),
            }).with_columns(
                pl.col(id_col)
                .cast(pl.String)
                .str.replace(r"\.0$", "", literal=False)
                .str.strip_chars()
            )
        else:
            assign_df = pl.DataFrame({
                id_col:          pl.Series([], dtype=pl.String),
                "المحصل الجديد": pl.Series([], dtype=pl.String),
                "حالة السحب":    pl.Series([], dtype=pl.String),
            })

        df_out = portfolio.clone().with_columns([
            pl.col(id_col)
            .cast(pl.String)
            .str.replace(r"\.0$", "", literal=False)
            .str.strip_chars()
            .alias(id_col),
            pl.col(col_col).cast(pl.String).str.strip_chars().alias(col_col),
        ])

        # الاحتفاظ برقم اليوزر الأصلي للمحصل القديم دون تعديل
        if usr_col and usr_col in df_out.columns:
            df_out = df_out.with_columns(pl.col(usr_col).alias("اليوزر"))
        else:
            df_out = df_out.with_columns(pl.lit("").alias("اليوزر"))

        df_out = df_out.join(assign_df, on=id_col, how="left")
        df_out = df_out.with_columns([
            pl.col("حالة السحب").fill_null(""),
            pl.col("المحصل الجديد").fill_null(""),
        ])

        # عمود النهائي: المحصل الجديد إن وُجد، وإلا المحصل الأصلي
        df_out = df_out.with_columns(
            pl.when(pl.col("حالة السحب") == "تم السحب")
            .then(pl.col("المحصل الجديد"))
            .otherwise(pl.col(col_col))
            .alias("النهائي")
        )
        # ترتيب الأعمدة
        new_cols  = ["حالة السحب", "المحصل الجديد", "النهائي", "اليوزر"]
        base_cols = [c for c in df_out.columns if c not in new_cols]
        df_out = df_out.select(base_cols + [c for c in new_cols if c in df_out.columns])


        # ── 15. ملخص التوزيع العام (كل المحصلين بعد التوازن) ──────────────
        sorted_collectors_raw = sorted(list({
            c for c in norm_to_orig.values() if is_human_collector(c)
        }))

        # ✅ استخدام collector_lookup_before للحالة "قبل"
        cnts_before = [collector_lookup_before[normalize_name(c)]["cnt"] for c in sorted_collectors_raw]
        bals_before = [collector_lookup_before[normalize_name(c)]["bal"] for c in sorted_collectors_raw]
        cnts_after  = [receiver_state[normalize_name(c)]["cnt"]          for c in sorted_collectors_raw]
        bals_after  = [receiver_state[normalize_name(c)]["bal"]          for c in sorted_collectors_raw]

        summary_rows = []
        for c in sorted_collectors_raw:
            norm = normalize_name(c)
            after  = receiver_state[norm]
            before = collector_lookup_before[norm]
            summary_rows.append({
                "المحصل":              c,
                "اليوزر":             user_dict.get(c, ""),
                "عدد العملاء قبل":    before["cnt"],
                "متبقي سداد قبل":     round(before["bal"], 2),
                "عدد العملاء بعد":    after["cnt"],
                "إجمالي متبقي السداد": round(after["bal"], 2),
            })

        summary_rows.append({
            "المحصل":              "📊 الإجمالي",
            "اليوزر":             f"{n_collectors} محصل",
            "عدد العملاء قبل":    sum(cnts_before),
            "متبقي سداد قبل":     round(sum(bals_before), 2),
            "عدد العملاء بعد":    sum(cnts_after),
            "إجمالي متبقي السداد": round(sum(bals_after), 2),
        })
        summary_rows.append({
            "المحصل":              "📈 الانحراف المعياري",
            "اليوزر":             None,
            "عدد العملاء قبل":    round(_std(cnts_before), 2),
            "متبقي سداد قبل":     round(_std(bals_before), 2),
            "عدد العملاء بعد":    round(_std(cnts_after), 2),
            "إجمالي متبقي السداد": round(_std(bals_after), 2),
        })
        summary_rows.append({
            "المحصل":              "✅ أقصى فرق",
            "اليوزر":             None,
            "عدد العملاء قبل":    max(cnts_before) - min(cnts_before),
            "متبقي سداد قبل":     round(max(bals_before) - min(bals_before), 2),
            "عدد العملاء بعد":    max(cnts_after) - min(cnts_after),
            "إجمالي متبقي السداد": round(max(bals_after) - min(bals_after), 2),
        })

        summary_pivot = pl.DataFrame(summary_rows, infer_schema_length=None)

        # ── 16. شيت ملخص المحفظة المصدر (جديد) ────────────────────────────
        source_summary = self._build_source_summary(
            source_portfolios=source_clean,
            source_portfolio_name=", ".join(source_clean),
            givers=givers,
            giver_withdrawn=giver_withdrawn,
            giver_withdrawn_bal=giver_withdrawn_bal,
            collector_lookup_before=collector_lookup_before,
            receiver_state=receiver_state,
            receiver_target_cnt=receiver_target_cnt,
            receivers=receivers,
            norm_to_orig=norm_to_orig,
            user_dict=user_dict,
            total_cnt=total_cnt,
            ideal_cnt=ideal_cnt,
            ideal_bal=ideal_bal,
        )

        # ── 17. تقرير التوازن التفصيلي ─────────────────────────────────────
        withdrawn_list = [
            {
                "from_collector": norm_to_orig.get(orig_collector_map[cid_s], orig_collector_map[cid_s]),
                "balance": all_client_bals[cid_s],
            }
            for cid_s in assignments
        ]
        planning_df = self._build_planning_sheet(
            collector_lookup_before, receiver_state, target_cnt,
            user_dict, ideal_cnt, ideal_bal, withdrawn_list, norm_to_orig
        )

        # ── 18. إحصاءات مُعادة للواجهة ─────────────────────────────────────
        bal_range_after = max(bals_after) - min(bals_after) if bals_after else 0

        # ── 19. شيت نتيجة التوزيع النهائية ─────────────────────────────────
        final_result_rows = []
        if "النهائي" in df_out.columns and bal_col in df_out.columns:
            df_src_f = df_out.filter(pl.col(prt_col).is_in(source_clean))
            df_src_f = df_src_f.filter(
                pl.col("النهائي").map_elements(is_human_collector, return_dtype=pl.Boolean)
            )
            if len(df_src_f) > 0:
                grp = (
                    df_src_f
                    .group_by([prt_col, "النهائي"])
                    .agg([
                        pl.len().alias("عدد العملاء النهائي"),
                        pl.col(bal_col).cast(pl.Float64, strict=False).sum().alias("إجمالي متبقي سداد موثق"),
                    ])
                    .sort([prt_col, "عدد العملاء النهائي"], descending=[False, True])
                    .rename({"النهائي": "المحصل"})
                )
                grp = grp.with_columns(
                    pl.Series("اليوزر", [user_dict.get(str(r["المحصل"]).strip(), "") for r in grp.iter_rows(named=True)])
                )
                grp = grp.select([prt_col, "المحصل", "اليوزر", "عدد العملاء النهائي", "إجمالي متبقي سداد موثق"])
                for prt in source_clean:
                    df_prt = grp.filter(pl.col(prt_col) == prt)
                    if len(df_prt) == 0:
                        continue
                    final_result_rows.extend(df_prt.to_dicts())
                    final_result_rows.append({
                        prt_col: prt,
                        "المحصل": "📊 إجمالي المحفظة",
                        "اليوزر": f"{len(df_prt)} محصل نشط",
                        "عدد العملاء النهائي": int(df_prt["عدد العملاء النهائي"].sum()),
                        "إجمالي متبقي سداد موثق": round(float(df_prt["إجمالي متبقي سداد موثق"].sum()), 2),
                    })
        final_result_sheet = (
            pl.DataFrame(final_result_rows, infer_schema_length=None)
            if final_result_rows else pl.DataFrame()
        )

        return {
            "data":               df_out,
            "summary_pivot":      summary_pivot,
            "source_summary":     source_summary,
            "planning_sheet":     planning_df,
            "final_result_sheet": final_result_sheet,
            "stats": {
                "عدد العملاء المنقولين":         len(assignments),
                "عدد المحصلين البشريين":          n_collectors,
                "إجمالي متبقي السداد المنقول":   round(total_withdrawn_bal, 2),
                "المتوسط المثالي (عدد)":          f"{ideal_cnt:.1f} عميل",
                "المتوسط المثالي (سداد)":         f"{ideal_bal:,.0f} ريال",
                "الانحراف قبل":                   f"{_std(cnts_before):.1f}",
                "الانحراف بعد":                   f"{_std(cnts_after):.1f}",
                "أقصى فرق عدد قبل التوازن":       f"{max(cnts_before) - min(cnts_before)} صف",
                "أقصى فرق عدد بعد التوازن":       f"{max(cnts_after) - min(cnts_after)} صف",
                "أقصى فرق رصيد قبل التوازن":      f"{max(bals_before) - min(bals_before):,.0f} ريال",
                "أقصى فرق رصيد بعد التوازن":      f"{bal_range_after:,.0f} ريال",
                "انحراف الرصيد قبل":              f"{_std(bals_before):,.0f}",
                "انحراف الرصيد بعد":              f"{_std(bals_after):,.0f}",
            },
        }

    # ─────────────────────────────────────────────────────────────────────────
    def _build_source_summary(
        self,
        source_portfolios: List[str],
        source_portfolio_name: str,
        givers: List,
        giver_withdrawn: Dict[str, int],
        giver_withdrawn_bal: Dict[str, float],
        collector_lookup_before: Dict[str, Dict],
        receiver_state: Dict[str, Dict],
        receiver_target_cnt: Dict[str, int],
        receivers: List,
        norm_to_orig: Dict,
        user_dict: Dict,
        total_cnt: int,
        ideal_cnt: float,
        ideal_bal: float,
    ) -> pl.DataFrame:
        """
        شيت ملخص المحفظة المصدر:
        يوضح المحصلين الذين سُحب منهم عملاء، وأعدادهم وأرصادهم قبل وبعد السحب.
        """
        cols = [
            "المحصل", "اليوزر",
            "عدد العملاء قبل السحب", "متبقي سداد قبل السحب",
            "عدد المسحوبين", "متبقي سداد المسحوبين",
            "عدد العملاء بعد السحب", "متبقي سداد بعد السحب",
            "الهدف المثالي", "الحالة",
        ]

        rows = []

        # عنوان
        header = {k: "" for k in cols}
        header["المحصل"] = f"═══ ملخص المحفظة المصدر: {source_portfolio_name} ═══"
        rows.append(header)

        # المانحون (المسحوب منهم)
        giver_set = {g[0] for g in givers}
        total_withdrawn_cnt = 0
        total_withdrawn_bal_sum = 0.0

        for g_col, n_needed in givers:
            orig_name = norm_to_orig.get(g_col, g_col)
            before = collector_lookup_before.get(g_col, {"cnt": 0, "bal": 0.0})
            actual_pulled = giver_withdrawn.get(g_col, 0)
            actual_pulled_bal = giver_withdrawn_bal.get(g_col, 0.0)
            after_cnt = before["cnt"] - actual_pulled
            after_bal = before["bal"] - actual_pulled_bal

            total_withdrawn_cnt += actual_pulled
            total_withdrawn_bal_sum += actual_pulled_bal

            tgt = receiver_state.get(g_col, {}).get("cnt", int(ideal_cnt))

            if actual_pulled == 0:
                status = "⚠️ لا يوجد عملاء في المحفظة المصدر"
            elif actual_pulled < n_needed:
                status = f"⚠️ سُحب {actual_pulled} من {n_needed} مطلوب (عجز {n_needed - actual_pulled})"
            else:
                status = "✅ تم السحب الكامل"

            rows.append({
                "المحصل":                   orig_name,
                "اليوزر":                  user_dict.get(orig_name, ""),
                "عدد العملاء قبل السحب":   f"{before['cnt']:,}",
                "متبقي سداد قبل السحب":    f"{before['bal']:,.2f}",
                "عدد المسحوبين":            f"{actual_pulled:,}",
                "متبقي سداد المسحوبين":    f"{actual_pulled_bal:,.2f}",
                "عدد العملاء بعد السحب":   f"{after_cnt:,}",
                "متبقي سداد بعد السحب":    f"{after_bal:,.2f}",
                "الهدف المثالي":            f"{int(ideal_cnt):,}",
                "الحالة":                   status,
            })

        # فاصل
        sep = {k: "─" * 8 for k in cols}
        rows.append(sep)

        # المستقبلون (من أُضيف لهم عملاء)
        recv_header = {k: "" for k in cols}
        recv_header["المحصل"] = "══ المحصلون المستقبِلون (المضاف إليهم) ══"
        rows.append(recv_header)

        total_received_cnt = 0
        for r_col, n_needed in receivers:
            orig_name = norm_to_orig.get(r_col, r_col)
            before = collector_lookup_before.get(r_col, {"cnt": 0, "bal": 0.0})
            after  = receiver_state.get(r_col, {"cnt": 0, "bal": 0.0})
            added  = after["cnt"] - before["cnt"]
            total_received_cnt += max(added, 0)

            rows.append({
                "المحصل":                   orig_name,
                "اليوزر":                  user_dict.get(orig_name, ""),
                "عدد العملاء قبل السحب":   f"{before['cnt']:,}",
                "متبقي سداد قبل السحب":    f"{before['bal']:,.2f}",
                "عدد المسحوبين":            f"+{max(added,0):,}",
                "متبقي سداد المسحوبين":    f"+{round(after['bal']-before['bal'],2):,.2f}",
                "عدد العملاء بعد السحب":   f"{after['cnt']:,}",
                "متبقي سداد بعد السحب":    f"{after['bal']:,.2f}",
                "الهدف المثالي":            f"{int(ideal_cnt):,}",
                "الحالة":                   "✅ استقبل" if added > 0 else "─",
            })

        # فاصل
        rows.append({k: "═" * 8 for k in cols})

        # ملخص إجمالي
        rows.append({
            "المحصل":                   "📊 إجمالي المسحوب",
            "اليوزر":                  "",
            "عدد العملاء قبل السحب":   "",
            "متبقي سداد قبل السحب":    "",
            "عدد المسحوبين":            f"{total_withdrawn_cnt:,}",
            "متبقي سداد المسحوبين":    f"{total_withdrawn_bal_sum:,.2f}",
            "عدد العملاء بعد السحب":   "",
            "متبقي سداد بعد السحب":    "",
            "الهدف المثالي":            f"{int(ideal_cnt):,}",
            "الحالة":                   f"وزّع على {len(receivers)} محصل",
        })

        return pl.DataFrame(rows, schema={k: pl.String for k in cols})

    # ─────────────────────────────────────────────────────────────────────────
    def _build_user_lookup(
        self, df: pl.DataFrame, col_col: str, usr_col: Optional[str]
    ) -> Optional[pl.DataFrame]:
        if not usr_col:
            return None
        return (
            df.select([col_col, usr_col])
            .unique(subset=[col_col])
            .with_columns([
                pl.col(col_col).cast(pl.String).str.strip_chars(),
                pl.col(usr_col).cast(pl.String).str.strip_chars(),
            ])
        )

    # ─────────────────────────────────────────────────────────────────────────
    def _build_planning_sheet(
        self,
        collector_lookup_before: Dict,
        state_after: Dict,
        target_cnt: Dict,
        user_dict: Dict,
        ideal_cnt: float,
        ideal_bal: float,
        withdrawn_list: List,
        norm_to_orig: Dict,
    ) -> pl.DataFrame:
        """
        تقرير تفصيلي شامل يوضح حالة التوازن قبل وبعد لكل محصل.
        """
        cols_keys = [
            "المحصل", "اليوزر",
            "عدد العملاء قبل", "متبقي سداد قبل",
            "الهدف المثالي",
            "عدد العملاء بعد", "متبقي سداد بعد",
            "مسحوب", "مضاف", "الحالة",
        ]

        pulled_from: Dict[str, int] = {}
        assigned_to: Dict[str, int] = {}
        for w in withdrawn_list:
            norm_from = normalize_name(w["from_collector"])
            pulled_from[norm_from] = pulled_from.get(norm_from, 0) + 1

        for c in state_after:
            before_cnt = collector_lookup_before.get(c, {"cnt": 0})["cnt"]
            after_cnt  = state_after[c]["cnt"]
            pulled = pulled_from.get(c, 0)
            added = after_cnt - (before_cnt - pulled)
            assigned_to[c] = max(added, 0)

        rows = []
        rows.append({k: "" for k in cols_keys})
        rows[0]["المحصل"] = "═══ تقرير التوازن الشامل (Giver/Receiver Snake-Draft) ═══"

        sorted_collectors_raw = sorted(list({
            c for c in norm_to_orig.values() if is_human_collector(c)
        }))
        cnts_before = [collector_lookup_before[normalize_name(c)]["cnt"] for c in sorted_collectors_raw]
        cnts_after  = [state_after[normalize_name(c)]["cnt"]             for c in sorted_collectors_raw]
        bals_before = [collector_lookup_before[normalize_name(c)]["bal"]  for c in sorted_collectors_raw]
        bals_after  = [state_after[normalize_name(c)]["bal"]              for c in sorted_collectors_raw]

        for c in sorted_collectors_raw:
            norm   = normalize_name(c)
            before = collector_lookup_before[norm]
            after  = state_after.get(norm, {"cnt": 0, "bal": 0.0})
            pulled = pulled_from.get(norm, 0)
            added  = assigned_to.get(norm, 0)
            tgt    = target_cnt.get(norm, int(ideal_cnt))

            if pulled > 0 and added == 0:
                status = f"↑ سُحب منه {pulled:,}"
            elif added > 0 and pulled == 0:
                status = f"↓ أُضيف إليه {added:,}"
            elif pulled > 0 and added > 0:
                status = f"↕ سُحب {pulled:,} وأُضيف {added:,}"
            elif after["cnt"] == tgt:
                status = "✓ متوازن"
            else:
                d = after["cnt"] - tgt
                status = f"{'↑' if d > 0 else '↓'} يختلف بـ {abs(d):,}"

            rows.append({
                "المحصل":           c,
                "اليوزر":          user_dict.get(c, ""),
                "عدد العملاء قبل": f"{before['cnt']:,}",
                "متبقي سداد قبل":  f"{before['bal']:,.2f}",
                "الهدف المثالي":    f"{tgt:,}",
                "عدد العملاء بعد": f"{after['cnt']:,}",
                "متبقي سداد بعد":  f"{after['bal']:,.2f}",
                "مسحوب":           f"{pulled:,}" if pulled else "-",
                "مضاف":            f"{added:,}"  if added  else "-",
                "الحالة":          status,
            })

        sep = {k: "─" * 10 for k in cols_keys}
        rows.append(sep)

        rows.append({
            "المحصل":           "📊 الإجمالي",
            "اليوزر":          f"{len(collector_lookup_before)} محصل",
            "عدد العملاء قبل": f"{sum(cnts_before):,}",
            "متبقي سداد قبل":  f"{sum(bals_before):,.2f}",
            "الهدف المثالي":   f"{int(ideal_cnt):,}",
            "عدد العملاء بعد": f"{sum(cnts_after):,}",
            "متبقي سداد بعد":  f"{sum(bals_after):,.2f}",
            "مسحوب":           f"{sum(pulled_from.values()):,}",
            "مضاف":            f"{sum(assigned_to.values()):,}",
            "الحالة":          "─",
        })

        rows.append({
            "المحصل":           "📈 انحراف معياري قبل",
            "اليوزر":          "",
            "عدد العملاء قبل": f"{_std(cnts_before):.2f}",
            "متبقي سداد قبل":  f"{_std(bals_before):,.2f}",
            "الهدف المثالي":   "",
            "عدد العملاء بعد": "",
            "متبقي سداد بعد":  "",
            "مسحوب": "", "مضاف": "", "الحالة": "",
        })

        rows.append({
            "المحصل":           "📉 انحراف معياري بعد",
            "اليوزر":          "",
            "عدد العملاء قبل": "",
            "متبقي سداد قبل":  "",
            "الهدف المثالي":   "",
            "عدد العملاء بعد": f"{_std(cnts_after):.2f}",
            "متبقي سداد بعد":  f"{_std(bals_after):,.2f}",
            "مسحوب": "", "مضاف": "", "الحالة": "",
        })

        rows.append({
            "المحصل":           "✅ أقصى فرق بين محصلَين",
            "اليوزر":          "",
            "عدد العملاء قبل": f"{max(cnts_before) - min(cnts_before):,}",
            "متبقي سداد قبل":  f"{max(bals_before) - min(bals_before):,.2f}",
            "الهدف المثالي":   "",
            "عدد العملاء بعد": f"{max(cnts_after) - min(cnts_after):,}",
            "متبقي سداد بعد":  f"{max(bals_after) - min(bals_after):,.2f}",
            "مسحوب": "", "مضاف": "",
            "الحالة": "← يجب أن يكون قريب من 1",
        })

        return pl.DataFrame(rows, schema={k: pl.String for k in cols_keys})


# ── دالة مستقلة خارج الكلاس (تغطية الواجهة) ─────────────────────────────────
def get_portfolios(portfolio: pl.DataFrame) -> List[str]:
    """دالة مستقلة لتغطية أي نداء مباشر من الواجهة برة الكلاس"""
    return PortfolioBalancingModule.get_portfolios(portfolio)