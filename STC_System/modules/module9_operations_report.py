import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import polars as pl

_log = logging.getLogger("STC_OPS")

_ID_COLS           = ["رقم الهوية", "الهوية", "الرقم الرئيسي", "رقم العميل", "رقم الحساب", "ID"]
_BALANCE_COLS      = ["متبقي سداد موثق", "متبقي السداد الموثق", "متبقي سداد العقد", "مبلغ المديونية", "المديونية", "Balance"]
_PAID_COLS         = ["السدادات الموثقة", "سدادات العقود", "مبلغ السداد", "Paid"]
_PORTFOLIO_COLS     = ["المحافظ", "المحفظة", "اسم المحفظة", "Portfolio"]
_SUPERVISOR_COLS    = ["المشرف", "اسم المشرف", "Supervisor"]
_COLLECTOR_COLS     = ["المحصل", "اسم المحصل", "الموظف", "محصل", "Collector"]
_USER_COLS          = ["اسم المستخدم", "اليوزر", "User", "user", "المستخدم"]
_FOLLOWUP_DATE_COLS = ["تاريخ المتابعة", "تاريخ اخر متابعة", "آخر متابعة للعميل", "المتابعة", "Followup Date"]
_MAIN_STATUS_COLS   = ["الحالة الرئيسية", "الحالة", "Main Status"]
_SUB_STATUS_COLS    = ["الحالة الفرعية", "Sub Status"]


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


class OperationsReportModule:
    """
    نظام تقارير العمليات الاحترافي (Operations Reporting System - Reports Center)
    يدعم إنشاء تقارير مستقلة بالكامل:
    - 📅 Daily Report (تقرير يومي)
    - 🗓 Weekly Report (تقرير أسبوعي)
    - 📆 Monthly Report (تقرير شهري)
    مع فلترة مخصصة وحساب دقيق للمؤشرات حسب نوع التقرير والفترة الزمنية المختارة دون تعديل البيانات الأصلية.
    """

    @staticmethod
    def get_filter_options(portfolio: pl.DataFrame) -> Dict[str, List[str]]:
        """يستخرج خيارات الفلاتر المتاحة من الملف لتغذية واجهة المستخدم"""
        if portfolio is None or len(portfolio) == 0:
            return {}

        def _get_unique(col_name: Optional[str]) -> List[str]:
            if not col_name or col_name not in portfolio.columns:
                return []
            s = (
                portfolio[col_name]
                .cast(pl.String, strict=False)
                .str.strip_chars()
                .drop_nulls()
                .unique()
                .sort()
            )
            result = [v for v in s.to_list() if v and str(v).strip() != ""]
            return result

        return {
            "supervisors": _get_unique(_detect(portfolio, _SUPERVISOR_COLS)),
            "collectors": _get_unique(_detect(portfolio, _COLLECTOR_COLS)),
            "portfolios": _get_unique(_detect(portfolio, _PORTFOLIO_COLS)),
            "main_statuses": _get_unique(_detect(portfolio, _MAIN_STATUS_COLS)),
            "sub_statuses": _get_unique(_detect(portfolio, _SUB_STATUS_COLS)),
        }

    def run(
        self,
        portfolio: pl.DataFrame,
        payments: Optional[pl.DataFrame] = None,
        report_mode: str = "daily",  # "daily", "weekly", "monthly"
        target_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        supervisors: Optional[List[str]] = None,
        collectors: Optional[List[str]] = None,
        portfolios: Optional[List[str]] = None,
        main_statuses: Optional[List[str]] = None,
        sub_statuses: Optional[List[str]] = None,
    ) -> Dict[str, Any]:

        if portfolio is None or len(portfolio) == 0:
            raise ValueError("ملف المحفظة فارغ أو غير ممرر")

        # 1. كشف الأعمدة الأساسية
        id_col        = _detect(portfolio, _ID_COLS)
        bal_col       = _detect(portfolio, _BALANCE_COLS)
        paid_col      = _detect(portfolio, _PAID_COLS)
        prt_col       = _detect(portfolio, _PORTFOLIO_COLS)
        sup_col       = _detect(portfolio, _SUPERVISOR_COLS)
        col_col       = _detect(portfolio, _COLLECTOR_COLS)
        usr_col       = _detect(portfolio, _USER_COLS)
        followup_col  = _detect(portfolio, _FOLLOWUP_DATE_COLS)
        main_stat_col = _detect(portfolio, _MAIN_STATUS_COLS)
        sub_stat_col  = _detect(portfolio, _SUB_STATUS_COLS)

        if not id_col or not prt_col or not col_col:
            raise ValueError("لم يتم العثور على الأعمدة الأساسية للمحفظة (الهوية، المحفظة، المحصل)")

        df_work = portfolio.clone()

        # 2. تطبيق الفلاتر المخصصة من المستخدم (إن وجدت)
        if supervisors and sup_col and sup_col in df_work.columns:
            df_work = df_work.filter(pl.col(sup_col).cast(pl.String).str.strip_chars().is_in(supervisors))
        if collectors and col_col and col_col in df_work.columns:
            df_work = df_work.filter(pl.col(col_col).cast(pl.String).str.strip_chars().is_in(collectors))
        if portfolios and prt_col and prt_col in df_work.columns:
            df_work = df_work.filter(pl.col(prt_col).cast(pl.String).str.strip_chars().is_in(portfolios))
        if main_statuses and main_stat_col and main_stat_col in df_work.columns:
            df_work = df_work.filter(pl.col(main_stat_col).cast(pl.String).str.strip_chars().is_in(main_statuses))
        if sub_statuses and sub_stat_col and sub_stat_col in df_work.columns:
            df_work = df_work.filter(pl.col(sub_stat_col).cast(pl.String).str.strip_chars().is_in(sub_statuses))

        if len(df_work) == 0:
            raise ValueError("لا توجد بيانات مطابقة للفلاتر المحددة!")

        # 3. تحديد نوع التقرير والفترة الزمنية والتغطية
        today_obj = date.today()
        report_mode = report_mode.lower().strip()
        
        report_title = ""
        report_period_str = ""

        # تحويل تاريخ المتابعة لـ String YYYY-MM-DD
        if followup_col and followup_col in df_work.columns:
            followup_series_str = (
                df_work[followup_col]
                .cast(pl.String, strict=False)
                .str.strip_chars()
                .str.slice(0, 10)
            )
        else:
            followup_series_str = pl.Series([today_obj.strftime("%Y-%m-%d")] * len(df_work))

        # حساب التغطية بناءً على نوع التقرير
        if report_mode == "daily":
            if not target_date:
                non_null_dates = followup_series_str.filter(followup_series_str.str.contains(r"^\d{4}-\d{2}-\d{2}$")).to_list()
                target_date_str = max(non_null_dates) if non_null_dates else today_obj.strftime("%Y-%m-%d")
            else:
                target_date_str = str(target_date).strip()

            report_title = "📅 التقرير اليومي (Daily Report)"
            report_period_str = f"تاريخ التقرير: {target_date_str}"
            is_covered_expr = (followup_series_str == target_date_str) | (followup_series_str.str.contains(target_date_str))

        elif report_mode == "weekly":
            if not start_date or not end_date:
                e_dt = today_obj
                s_dt = today_obj - timedelta(days=6)
                start_date_str = s_dt.strftime("%Y-%m-%d")
                end_date_str = e_dt.strftime("%Y-%m-%d")
            else:
                start_date_str = str(start_date).strip()
                end_date_str = str(end_date).strip()

            report_title = "🗓 التقرير الأسبوعي (Weekly Report)"
            report_period_str = f"الفترة الأسبوعية: من {start_date_str} إلى {end_date_str}"
            is_covered_expr = (followup_series_str >= start_date_str) & (followup_series_str <= end_date_str)

        elif report_mode == "monthly":
            m_val = month if month else today_obj.month
            y_val = year if year else today_obj.year
            month_prefix = f"{y_val:04d}-{m_val:02d}"

            report_title = "📆 التقرير الشهري (Monthly Report)"
            report_period_str = f"فترة الشهر: {month_prefix} ({m_val}/{y_val})"
            is_covered_expr = followup_series_str.str.starts_with(month_prefix)
        else:
            report_title = "📊 تقرير العمليات"
            report_period_str = f"تاريخ التقرير: {today_obj.strftime('%Y-%m-%d')}"
            is_covered_expr = pl.Series([True] * len(df_work))

        # 4. مبالغ المديونية والسداد
        bal_series = _clean_float(df_work[bal_col]) if bal_col and bal_col in df_work.columns else pl.Series([0.0] * len(df_work))
        paid_series = _clean_float(df_work[paid_col]) if paid_col and paid_col in df_work.columns else pl.Series([0.0] * len(df_work))

        # معالجة ملف السدادات الإضافية إن وجد
        payments_sum_map = {}
        payments_cnt_map = {}
        if payments is not None and len(payments) > 0:
            pmt_id_col = _detect(payments, _ID_COLS)
            pmt_amt_col = _detect(payments, _PAID_COLS) or _detect(payments, ["مبلغ السداد", "المبلغ", "Amount"])
            if pmt_id_col and pmt_amt_col:
                pmt_clean = payments.with_columns([
                    pl.col(pmt_id_col).cast(pl.String).str.replace(r"\.0$", "", literal=False).str.strip_chars(),
                    _clean_float(payments[pmt_amt_col]).alias("clean_pmt_amt")
                ])
                grp_pmt = pmt_clean.group_by(pmt_id_col).agg([
                    pl.col("clean_pmt_amt").sum().alias("total_pmt"),
                    pl.len().alias("count_pmt")
                ])
                for r in grp_pmt.iter_rows(named=True):
                    payments_sum_map[str(r[pmt_id_col])] = float(r["total_pmt"])
                    payments_cnt_map[str(r[pmt_id_col])] = int(r["count_pmt"])

        if payments_sum_map:
            ids_str = df_work[id_col].cast(pl.String).str.replace(r"\.0$", "", literal=False).str.strip_chars().to_list()
            added_pmts = [payments_sum_map.get(i, 0.0) for i in ids_str]
            added_cnts = [payments_cnt_map.get(i, 0) for i in ids_str]
            total_paid_expr = paid_series + pl.Series(added_pmts)
            has_paid_flag = (paid_series > 0).cast(pl.Int64)
            count_paid_expr = pl.Series(added_cnts) + has_paid_flag
        else:
            total_paid_expr = paid_series
            count_paid_expr = (paid_series > 0).cast(pl.Int64)

        # إضافة الأعمدة التحليلية الجديدة على النسخة المفردة
        df_out = df_work.with_columns([
            pl.when(is_covered_expr).then(pl.lit("Covered")).otherwise(pl.lit("Not Covered")).alias("Coverage Status"),
            pl.when(is_covered_expr).then(pl.lit(1)).otherwise(pl.lit(0)).alias("Coverage Value"),
            pl.when(is_covered_expr).then(pl.lit("تمت التغطية")).otherwise(pl.lit("لم تتم التغطية")).alias("حالة التغطية"),
            total_paid_expr.alias("إجمالي السداد التحليلي"),
            count_paid_expr.alias("عدد عمليات السداد"),
            (
                pl.when(total_paid_expr + bal_series > 0)
                .then((total_paid_expr / (total_paid_expr + bal_series)) * 100.0)
                .otherwise(0.0)
            ).alias("نسبة التحصيل %")
        ])

        # 5. حساب الـ Pivot Tables حصرياً للبيانات المفلترة والمحسوبة
        pivot_supervisor  = self._build_group_summary(df_out, sup_col or col_col, "المشرف", bal_col)
        pivot_collector   = self._build_group_summary(df_out, col_col, "المحصل", bal_col, usr_col=usr_col, sup_col=sup_col)
        pivot_portfolio   = self._build_group_summary(df_out, prt_col, "المحافظ", bal_col)
        pivot_main_status = self._build_group_summary(df_out, main_stat_col, "الحالة الرئيسية", bal_col) if main_stat_col else pl.DataFrame()
        pivot_sub_status  = self._build_group_summary(df_out, sub_stat_col, "الحالة الفرعية", bal_col) if sub_stat_col else pl.DataFrame()

        # 6. الترتيب Top 10
        top10_supervisors = pivot_supervisor.filter(~pl.col("المشرف").str.contains("📊")).sort("نسبة التغطية %", descending=True).head(10) if not pivot_supervisor.is_empty() else pl.DataFrame()
        top10_collectors  = pivot_collector.filter(~pl.col("المحصل").str.contains("📊")).sort("نسبة التغطية %", descending=True).head(10) if not pivot_collector.is_empty() else pl.DataFrame()
        top10_portfolios  = pivot_portfolio.filter(~pl.col("المحافظ").str.contains("📊")).sort("متبقي سداد موثق", descending=True).head(10) if not pivot_portfolio.is_empty() else pl.DataFrame()

        # 7. حساب الـ KPIs حصرياً للتخصيص الحالي
        total_cust     = len(df_out)
        covered_cust   = int(df_out["Coverage Value"].sum())
        uncovered_cust = total_cust - covered_cust
        cov_rate       = round((covered_cust / total_cust * 100), 2) if total_cust > 0 else 0.0

        total_paid_val = round(float(df_out["إجمالي السداد التحليلي"].sum()), 2)
        total_bal_val  = round(float(bal_series.sum()), 2)
        paid_cnt_val   = int(df_out["عدد عمليات السداد"].sum())
        avg_paid_val   = round(total_paid_val / paid_cnt_val, 2) if paid_cnt_val > 0 else 0.0
        coll_rate      = round((total_paid_val / (total_paid_val + total_bal_val) * 100), 2) if (total_paid_val + total_bal_val) > 0 else 0.0

        stats = {
            "نوع التقرير": report_title,
            "الفترة الزمنية": report_period_str,
            "إجمالي العملاء": total_cust,
            "عدد العملاء المغطين": covered_cust,
            "عدد العملاء غير المغطين": uncovered_cust,
            "نسبة التغطية": f"{cov_rate}%",
            "إجمالي السداد": f"{total_paid_val:,.2f} ريال",
            "عدد عمليات السداد": paid_cnt_val,
            "إجمالي متبقي السداد الموثق": f"{total_bal_val:,.2f} ريال",
            "متوسط السداد": f"{avg_paid_val:,.2f} ريال",
            "نسبة التحصيل": f"{coll_rate}%",
        }

        return {
            "report_mode": report_mode,
            "report_title": report_title,
            "report_period": report_period_str,
            "data": df_out,
            "stats": stats,
            "pivot_supervisor": pivot_supervisor,
            "pivot_collector": pivot_collector,
            "pivot_portfolio": pivot_portfolio,
            "pivot_main_status": pivot_main_status,
            "pivot_sub_status": pivot_sub_status,
            "top10_supervisors": top10_supervisors,
            "top10_collectors": top10_collectors,
            "top10_portfolios": top10_portfolios,
        }

    def _build_group_summary(
        self,
        df: pl.DataFrame,
        group_col: Optional[str],
        label: str,
        bal_col: Optional[str],
        usr_col: Optional[str] = None,
        sup_col: Optional[str] = None,
    ) -> pl.DataFrame:

        if not group_col or group_col not in df.columns:
            return pl.DataFrame()

        grp_cols = [group_col]
        if usr_col and usr_col in df.columns and group_col != usr_col:
            grp_cols.append(usr_col)
        if sup_col and sup_col in df.columns and group_col != sup_col:
            grp_cols.append(sup_col)

        bal_exp = _clean_float(df[bal_col]) if bal_col and bal_col in df.columns else pl.lit(0.0)

        df_work = df.with_columns([
            bal_exp.alias("_clean_bal")
        ])

        agg_df = (
            df_work
            .group_by(grp_cols)
            .agg([
                pl.len().alias("عدد العملاء"),
                pl.col("Coverage Value").sum().alias("تمت التغطية"),
                (pl.len() - pl.col("Coverage Value").sum()).alias("لم تتم التغطية"),
                (pl.col("Coverage Value").sum() / pl.len() * 100.0).round(2).alias("نسبة التغطية %"),
                pl.col("إجمالي السداد التحليلي").sum().round(2).alias("إجمالي السداد"),
                pl.col("_clean_bal").sum().round(2).alias("متبقي سداد موثق"),
            ])
            .sort("عدد العملاء", descending=True)
        )

        agg_df = agg_df.rename({group_col: label})

        total_row = {
            label: f"📊 إجمالي {label}",
            "عدد العملاء": int(agg_df["عدد العملاء"].sum()),
            "تمت التغطية": int(agg_df["تمت التغطية"].sum()),
            "لم تتم التغطية": int(agg_df["لم تتم التغطية"].sum()),
            "نسبة التغطية %": round((float(agg_df["تمت التغطية"].sum()) / float(agg_df["عدد العملاء"].sum()) * 100.0), 2) if agg_df["عدد العملاء"].sum() > 0 else 0.0,
            "إجمالي السداد": round(float(agg_df["إجمالي السداد"].sum()), 2),
            "متبقي سداد موثق": round(float(agg_df["متبقي سداد موثق"].sum()), 2),
        }
        if usr_col and usr_col in grp_cols:
            total_row[usr_col] = "-"
        if sup_col and sup_col in grp_cols:
            total_row[sup_col] = "-"

        rows = agg_df.to_dicts()
        rows.append(total_row)
        return pl.DataFrame(rows, infer_schema_length=None)
