"""
modules/module6b_rotation.py
─────────────────────────────
Module 6B — السحب والتدوير الفعلي (Portfolio Rotation Execution) using Polars.

يقوم بـ:
1. استخراج عملاء المحصل المسحوب
2. توزيعهم على باقي محصلي نفس المشرف (Round Robin by رقم الهوية)
3. إنتاج 3 تقارير: ملخص التوزيع، ملف التنفيذ، ملخص السحب
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Dict, List, Optional

import polars as pl

from core.utils import get_today

_log = logging.getLogger("Module6B_Rotation")

# أعمدة المحفظة المعتمدة (Smart Detection)
_ID_COLS         = ["رقم الهوية", "الهوية"]
_BALANCE_COLS    = ["متبقي سداد موثق", "متبقي السداد الموثق", "متبقي سداد", "الرصيد المتبقي"]
_YEAR_COLS       = ["سنة التعثر", "سنة_التعثر"]
_SUPERVISOR_COLS = ["المشرف", "اسم المشرف"]
_COLLECTOR_COLS  = ["المحصل", "اسم المحصل", "الموظف"]
_USER_COLS       = ["اسم المستخدم", "اليوزر", "User", "user", "المستخدم"]
_MAIN_STATUS     = ["الحالة الرئيسية"]
_SUB_STATUS      = ["الحالة الفرعية"]


def _detect(df: pl.DataFrame, candidates: List[str]) -> Optional[str]:
    """إيجاد أول عمود مطابق من قائمة المرشحين."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


class PortfolioRotationModule:
    """تنفيذ عملية السحب والتدوير الفعلي."""

    def run(
        self,
        portfolio: pl.DataFrame,
        withdrawn_collector: str,
        supervisor_name: str,
    ) -> Dict:
        """
        تنفيذ السحب والتدوير.

        Parameters
        ----------
        portfolio           : DataFrame كامل ملف المحفظة الموزعة
        withdrawn_collector : اسم المحصل المراد سحب محفظته
        supervisor_name     : اسم المشرف (لاستخراج المحصلين التابعين له)

        Returns
        -------
        dict يحتوي على:
          data               : DataFrame كامل مع الأعمدة المحسوبة
          execution_report   : ملف التنفيذ (هوية + محصل جديد + يوزر جديد)
          distribution_summary: ملخص التوزيع بالمحصل
          withdrawal_summary  : ملخص عملية السحب
          stats              : إحصائيات سريعة
          collectors_pool    : قائمة المحصلين الذين وُزِّع عليهم
        """
        _log.info("▶ بدء السحب والتدوير — المحصل: %s — المشرف: %s",
                  withdrawn_collector, supervisor_name)

        # ── الكشف التلقائي عن الأعمدة ────────────────────────────────────────
        id_col   = _detect(portfolio, _ID_COLS)
        bal_col  = _detect(portfolio, _BALANCE_COLS)
        yr_col   = _detect(portfolio, _YEAR_COLS)
        sup_col  = _detect(portfolio, _SUPERVISOR_COLS)
        col_col  = _detect(portfolio, _COLLECTOR_COLS)
        usr_col  = _detect(portfolio, _USER_COLS)
        main_col = _detect(portfolio, _MAIN_STATUS)
        sub_col  = _detect(portfolio, _SUB_STATUS)

        if not col_col:
            raise ValueError("لم يتم العثور على عمود المحصل في المحفظة")
        if not id_col:
            raise ValueError("لم يتم العثور على عمود رقم الهوية في المحفظة")

        df = portfolio.clone()

        # ── استخراج عملاء المحصل المسحوب ─────────────────────────────────────
        withdrawn_df = df.filter(
            pl.col(col_col).cast(pl.String).str.strip_chars() == withdrawn_collector.strip()
        )
        _log.info("  📋 عدد سجلات المحصل المسحوب: %d", len(withdrawn_df))

        if len(withdrawn_df) == 0:
            raise ValueError(f"لا توجد سجلات للمحصل: {withdrawn_collector}")

        # ── إضافة عمود "إجمالي العميل" (SUMIF by رقم الهوية) ─────────────────
        if bal_col:
            # تنظيف عمود الرصيد (قد يحتوي فواصل)
            bal_expr = (
                pl.col(bal_col)
                .cast(pl.String, strict=False)
                .str.replace_all(",", "")
                .str.strip_chars()
                .cast(pl.Float64, strict=False)
                .fill_null(0.0)
            )
            withdrawn_df = withdrawn_df.with_columns(bal_expr.alias("_bal_clean"))
            withdrawn_df = withdrawn_df.with_columns(
                pl.col("_bal_clean").sum().over(id_col).alias("إجمالي العميل")
            )
        else:
            withdrawn_df = withdrawn_df.with_columns(pl.lit(0.0).alias("إجمالي العميل"))
            _log.warning("  ⚠️ لم يتم العثور على عمود الرصيد — إجمالي العميل = 0")

        # ── عمود "سنة التعثر" ─────────────────────────────────────────────────
        if yr_col:
            # موجود مباشرة — نحوّله لـ Int
            withdrawn_df = withdrawn_df.with_columns(
                pl.col(yr_col)
                .cast(pl.String, strict=False)
                .str.strip_chars()
                .cast(pl.Int32, strict=False)
                .fill_null(9999)
                .alias("سنة التعثر")
            )
        else:
            withdrawn_df = withdrawn_df.with_columns(pl.lit(9999).cast(pl.Int32).alias("سنة التعثر"))

        # ── قائمة المحصلين المتاحين (نفس المشرف - المسحوب) ─────────────────
        if sup_col:
            sup_mask = pl.col(sup_col).cast(pl.String).str.strip_chars() == supervisor_name.strip()
            collectors_pool: List[str] = (
                df.filter(sup_mask)
                .select(col_col)
                .unique()
                .to_series()
                .cast(pl.String)
                .str.strip_chars()
                .to_list()
            )
        else:
            collectors_pool = []

        # استبعاد المحصل المسحوب
        collectors_pool = [
            c for c in collectors_pool
            if c.strip() != withdrawn_collector.strip()
        ]
        collectors_pool = sorted(collectors_pool)  # ترتيب أبجدي ثابت
        _log.info("  👥 المحصلون المتاحون (%d): %s", len(collectors_pool), collectors_pool)

        if not collectors_pool:
            raise ValueError(
                f"لا يوجد محصلون آخرون تحت المشرف '{supervisor_name}' "
                f"لتوزيع المحفظة عليهم"
            )

        # ── توزيع Round Robin by رقم الهوية ──────────────────────────────────
        # 1. الحصول على قائمة هويات فريدة مرتبة
        unique_ids = (
            withdrawn_df
            .select([id_col, "إجمالي العميل", "سنة التعثر"])
            .unique(subset=[id_col])
            .sort(["سنة التعثر", "إجمالي العميل"], descending=[False, True])
        )

        n_collectors = len(collectors_pool)
        n_customers  = len(unique_ids)

        # Round Robin assignment
        assignments = {
            row[0]: collectors_pool[i % n_collectors]
            for i, row in enumerate(unique_ids.iter_rows())
        }

        # عمود التوزيع
        id_series    = unique_ids.get_column(id_col).cast(pl.String)
        col_assigned = pl.Series(
            "التوزيع",
            [assignments[str(i)] for i in unique_ids.get_column(id_col).to_list()]
        )
        assign_df = pl.DataFrame({
            id_col: id_series,
            "التوزيع": col_assigned,
        })

        # ── join التوزيع على كامل سجلات المحصل (XLOOKUP by هوية) ────────────
        withdrawn_df = withdrawn_df.with_columns(
            pl.col(id_col).cast(pl.String).alias(id_col)
        )
        assign_df = assign_df.with_columns(
            pl.col(id_col).cast(pl.String)
        )
        withdrawn_df = withdrawn_df.join(assign_df.select([id_col, "التوزيع"]),
                                         on=id_col, how="left")
        withdrawn_df = withdrawn_df.rename({"التوزيع": "المحصل الجديد"})

        # ── عمود اليوزر الجديد (XLOOKUP: اسم المحصل → اسم المستخدم) ─────────
        if usr_col:
            # جدول ربط: اسم المحصل → اليوزر من المحفظة الأصلية
            user_map = (
                df.select([col_col, usr_col])
                .unique(subset=[col_col])
                .with_columns([
                    pl.col(col_col).cast(pl.String).str.strip_chars(),
                    pl.col(usr_col).cast(pl.String).str.strip_chars(),
                ])
            )
            withdrawn_df = withdrawn_df.join(
                user_map.rename({col_col: "المحصل الجديد", usr_col: "اليوزر الجديد"}),
                on="المحصل الجديد",
                how="left",
            )
        else:
            withdrawn_df = withdrawn_df.with_columns(pl.lit("").alias("اليوزر الجديد"))

        # ── الفرز النهائي ─────────────────────────────────────────────────────
        sort_cols   = []
        sort_descs  = []
        if main_col and main_col in withdrawn_df.columns:
            sort_cols.append(main_col);  sort_descs.append(False)
        if sub_col  and sub_col  in withdrawn_df.columns:
            sort_cols.append(sub_col);   sort_descs.append(False)
        sort_cols.append("سنة التعثر");  sort_descs.append(False)   # ASC قديمها أول
        sort_cols.append("إجمالي العميل"); sort_descs.append(True)  # DESC أكبر أول

        withdrawn_df = withdrawn_df.sort(sort_cols, descending=sort_descs)

        # ── تنظيف العمود المؤقت ───────────────────────────────────────────────
        if "_bal_clean" in withdrawn_df.columns:
            withdrawn_df = withdrawn_df.drop("_bal_clean")

        # ── ملف التنفيذ ───────────────────────────────────────────────────────
        exec_cols = [id_col, "اسم العميل", "المحصل الجديد", "اليوزر الجديد"] \
            if "اسم العميل" in withdrawn_df.columns \
            else [id_col, "المحصل الجديد", "اليوزر الجديد"]
        execution_report = (
            withdrawn_df
            .select([c for c in exec_cols if c in withdrawn_df.columns])
            .unique(subset=[id_col])
            .sort(id_col)
        )

        # ── ملخص التوزيع ─────────────────────────────────────────────────────
        dist_agg = (
            withdrawn_df
            .unique(subset=[id_col])
            .group_by("المحصل الجديد")
            .agg([
                pl.col(id_col).count().alias("عدد العملاء"),
                pl.col("إجمالي العميل").sum().alias("إجمالي متبقي السداد"),
            ])
            .with_columns(
                (pl.col("إجمالي متبقي السداد") / pl.col("عدد العملاء"))
                .round(2)
                .alias("متوسط قيمة العميل")
            )
            .sort("عدد العملاء", descending=True)
        )

        # ── ملخص عملية السحب ─────────────────────────────────────────────────
        total_customers = n_customers
        total_balance   = withdrawn_df.unique(subset=[id_col]) \
                          .get_column("إجمالي العميل").sum() if bal_col else 0.0
        withdrawal_summary = pl.DataFrame({
            "البند":  [
                "المحصل المسحوب",
                "المشرف",
                "عدد العملاء المسحوبين",
                "عدد المديونيات",
                "عدد المحصلين الذين وُزِّع عليهم",
                "إجمالي متبقي السداد الموثق",
                "تاريخ التنفيذ",
            ],
            "القيمة": [
                withdrawn_collector,
                supervisor_name,
                str(total_customers),
                str(len(withdrawn_df)),
                str(n_collectors),
                f"{total_balance:,.2f}",
                str(get_today()),
            ],
        })

        stats = {
            "المحصل المسحوب":              withdrawn_collector,
            "المشرف":                      supervisor_name,
            "عدد العملاء المسحوبين":      total_customers,
            "عدد المديونيات":             len(withdrawn_df),
            "عدد المحصلين المستقبِلين":   n_collectors,
            "إجمالي متبقي السداد":        round(total_balance, 2),
        }

        _log.info("  ✅ اكتملت عملية السحب والتدوير: %d عميل → %d محصل",
                  total_customers, n_collectors)

        return {
            "data":                 withdrawn_df,
            "execution_report":     execution_report,
            "distribution_summary": dist_agg,
            "withdrawal_summary":   withdrawal_summary,
            "stats":                stats,
            "collectors_pool":      collectors_pool,
        }

    @staticmethod
    def get_supervisors(portfolio: pl.DataFrame) -> List[str]:
        """إرجاع قائمة المشرفين الفريدين من المحفظة."""
        col = _detect(portfolio, _SUPERVISOR_COLS)
        if not col:
            return []
        return (
            portfolio.select(col)
            .unique()
            .to_series()
            .cast(pl.String)
            .str.strip_chars()
            .drop_nulls()
            .sort()
            .to_list()
        )

    @staticmethod
    def get_collectors_for_supervisor(
        portfolio: pl.DataFrame, supervisor_name: str
    ) -> List[str]:
        """إرجاع قائمة المحصلين التابعين لمشرف معين."""
        sup_col = _detect(portfolio, _SUPERVISOR_COLS)
        col_col = _detect(portfolio, _COLLECTOR_COLS)
        if not sup_col or not col_col:
            return []
        return (
            portfolio
            .filter(
                pl.col(sup_col).cast(pl.String).str.strip_chars() == supervisor_name.strip()
            )
            .select(col_col)
            .unique()
            .to_series()
            .cast(pl.String)
            .str.strip_chars()
            .drop_nulls()
            .sort()
            .to_list()
        )
