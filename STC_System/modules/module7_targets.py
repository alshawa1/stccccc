"""
modules/module7_targets.py
──────────────────────────
Module 7 — العملاء المستهدفة (Target Customers) using Polars.
Works only on the main portfolio file (المحفظة الموزعة).
Classifies customers into "مستهدف" or "غير مستهدف" based on positive and negative keywords in the follow-up column (المتابعة).
"""
from __future__ import annotations

import logging
from typing import Dict

import polars as pl

_log = logging.getLogger("Module7_Targets")

POSITIVE = "مستهدف"
NEGATIVE = "غير مستهدف"


class TargetCustomersModule:
    CLASS_COL    = "العملاء المستهدفة"
    PRIORITY_COL = "أولوية التحصيل"
    REASON_COL   = "سبب التصنيف"

    def run(
        self,
        portfolio: pl.DataFrame,
        promise: pl.DataFrame = None,
        maharah: pl.DataFrame = None,
    ) -> Dict:
        _log.info("▶ بدء تحديد العملاء المستهدفة (Polars)")

        # 1. إضافة كولوم عدد العملاء = 1 / countif(رقم الهوية)
        id_col = next((c for c in ["رقم الهوية", "الهوية"] if c in portfolio.columns), None)
        if id_col:
            portfolio = portfolio.with_columns(
                (pl.lit(1.0) / pl.col(id_col).count().over(id_col).cast(pl.Float64)).alias("عدد العملاء")
            )
        else:
            portfolio = portfolio.with_columns(pl.lit(1.0).alias("عدد العملاء"))

        df = portfolio.clone()

        # 2. تصنيف العملاء بناءً على كولوم المتابعة
        df = self._classify(df)

        # 3. إعداد الجداول المحورية والإحصائيات
        positive_df = df.filter(pl.col(self.CLASS_COL) == POSITIVE)

        piv_sup = self._build_pivot(df, "المشرف")
        collector = next((c for c in ["المحصل", "الموظف"] if c in df.columns), "")
        piv_col   = self._build_pivot(df, collector) if collector else pl.DataFrame()

        total = len(df)
        pos_count = df.filter(pl.col(self.CLASS_COL) == POSITIVE).height
        neg_count = df.filter(pl.col(self.CLASS_COL) == NEGATIVE).height

        stats = {
            "إجمالي العملاء":    total,
            "مستهدف":            pos_count,
            "غير مستهدف":        neg_count,
            "نسبة المستهدفين %": round(pos_count / total * 100, 1) if total else 0.0,
        }

        return {
            "data":             df,
            "positive_data":    positive_df,
            "pivot_supervisor": piv_sup,
            "pivot_collector":  piv_col,
            "stats":            stats,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _normalize_column(self, df: pl.DataFrame, col_name: str) -> pl.Expr:
        """
        توحيد الحروف والنصوص لتسهيل البحث بالكلمات المفتاحية
        """
        return (
            pl.col(col_name)
            .fill_null("")
            .cast(pl.String)
            .str.strip_chars()
            .str.to_lowercase()
            .str.replace_all("أ", "ا")
            .str.replace_all("إ", "ا")
            .str.replace_all("آ", "ا")
            .str.replace_all("ة", "ه")
            .str.replace_all("ى", "ي")
        )

    def _classify(self, df: pl.DataFrame) -> pl.DataFrame:
        note_col = next((c for c in ["المتابعة", "الملاحظة", "الملاحظات", "ملاحظة"] if c in df.columns), None)
        main_col = next((c for c in ["الحالة الرئيسية", "الحالة"] if c in df.columns), None)

        if not note_col:
            _log.warning("لم يتم العثور على عمود المتابعة في ملف المحفظة!")
            return df.with_columns([
                pl.lit(NEGATIVE).alias(self.CLASS_COL),
                pl.lit("لا يوجد عمود متابعة").alias(self.REASON_COL),
                pl.lit(2).cast(pl.Int32).alias(self.PRIORITY_COL),
            ])

        # ── الكلمات الإيجابية (تدل على عميل مستهدف) ――――――――――――――――――――――――――――
        POS_KEYWORDS = [
            # كلمات الراتب / حساب مواطن / أول الشهر — مجدي بلغ المستخدم
            "ع الراتب", "علي الراتب", "على الراتب", "الراتب", "راتب",
            "يوم 1", "يوم الاول", "يوم الأول", "اول الشهر", "أول الشهر",
            "حساب مواطن", "يوم مواطن", "مواطن",
            "اخر الشهر", "آخر الشهر", "نهاية الشهر",
            "بسدد", "بيسدد", "بسددها", "يسدد", "سيسدد",
            "منتظم", "منتظم السداد", "منتظمه",
            # كلمات وعد / سداد عامة
            "وعد", "واعد", "سداد", "اتفاق", "قسط", "اقساط", "تسوية", "جدولة",
            "هيدفع", "سيدفع", "دفعة", "دفعه",
            "معاش", "بينزل", "ينزل", "بكره", "بكرة",
            "ابشر", "نفسه", "متعاون",
        ]

        # الحالات الرئيسية الإيجابية — شرط إضافي للتصنيف كمستهدف
        POSITIVE_MAIN_STATUSES = [
            "سداد جزئي", "سداد جزئيي",
            "واعد بالسداد", "وعد السداد", "وعد سداد",
            "مسدد جزئي", "تسوية", "جدولة",
            "متوفي والورثة", "ورثة", "والورثة واعدين",
        ]

        # كلمات سلبية — تلغي التصنيف كمستهدف نهائياً مهما وجدت كلمة إيجابية
        NEG_KEYWORDS = [
            "لايرد", "لا يرد", "مايرد", "مايردش", "ما يرد", "لم يرد",
            "مغلق", "خارج التغطية",
            "خروج نهائي", "بالسجن", "سجن", "مسجون",
            "غير صحيح", "لا يخص", "لايخص", "رقم خطأ", "رقم غلط",
            "الارقام لا تخص", "بريد صوتي", "بيزي",
            "مرفوض", "رفض", "رافض", "رافض السداد", "رفض السداد",
            "ما يقدر", "مقدر اسدد", "ما عندي قدره",
            "انكر", "تنكر", "مستحيل", "اشتكي",
            "يرد وما يتكلم", "يرد وساكته", "ردت وساكته",
        ]

        # تنظيف عمود المتابعة والحالة الرئيسية
        note_expr = self._normalize_column(df, note_col)
        main_expr = self._normalize_column(df, main_col) if main_col else pl.lit("")

        # فحص الكلمات الإيجابية في عمود المتابعة
        has_pos = pl.lit(False)
        pos_reasons = []
        for kw in POS_KEYWORDS:
            kw_norm = kw.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
            match_cond = note_expr.str.contains(kw_norm, literal=True)
            has_pos = has_pos | match_cond
            pos_reasons.append(pl.when(match_cond).then(pl.lit(f"كلمة إيجابية: {kw}")).otherwise(pl.lit(None)))

        # فحص الحالة الرئيسية الإيجابية (سداد جزئي / واعد / ورثة)
        has_positive_main = pl.lit(False)
        for status in POSITIVE_MAIN_STATUSES:
            st_norm = status.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
            has_positive_main = has_positive_main | main_expr.str.contains(st_norm, literal=True)

        has_neg = pl.lit(False)
        neg_reasons = []
        for kw in NEG_KEYWORDS:
            kw_norm = kw.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
            match_cond = note_expr.str.contains(kw_norm, literal=True)
            has_neg = has_neg | match_cond
            neg_reasons.append(pl.when(match_cond).then(pl.lit(f"كلمة سلبية: {kw}")).otherwise(pl.lit(None)))

        pos_reason_expr = pl.coalesce(pos_reasons).fill_null("إيجابي")
        neg_reason_expr = pl.coalesce(neg_reasons).fill_null("سلبي")

        # قاعدة التصنيف:
        # 1. لو فيه كلمة سلبية (لا يرد / مغلق / رفض) → غير مستهدف فوراً
        # 2. لو فيه كلمة إيجابية بدون كلمة سلبية → مستهدف
        # 3. لو فيه حالة رئيسية إيجابية بدون كلمة سلبية → مستهدف
        # 4. لو ما فيهش حاجة → غير مستهدف
        is_targeted = (~has_neg) & (has_pos | has_positive_main)

        class_expr = pl.when(is_targeted).then(pl.lit(POSITIVE)).otherwise(pl.lit(NEGATIVE))
        reason_expr = pl.when(is_targeted).then(
            pl.when(has_positive_main & ~has_pos)
            .then(pl.lit("حالة رئيسية إيجابية"))
            .otherwise(pos_reason_expr)
        ).otherwise(
            pl.when(has_neg).then(neg_reason_expr).otherwise(pl.lit("لا توجد مؤشرات إيجابية"))
        )

        df = df.with_columns([
            class_expr.alias(self.CLASS_COL),
            reason_expr.alias(self.REASON_COL),
        ])

        df = df.with_columns(
            pl.when(pl.col(self.CLASS_COL) == POSITIVE).then(pl.lit(1))
            .otherwise(pl.lit(2))
            .cast(pl.Int32)
            .alias(self.PRIORITY_COL)
        )

        return df

    def _build_pivot(self, df: pl.DataFrame, group_col: str) -> pl.DataFrame:
        if not group_col or group_col not in df.columns:
            return pl.DataFrame()

        try:
            pivot = (
                df.group_by([group_col, self.CLASS_COL])
                .len()
                .pivot(on=self.CLASS_COL, index=group_col, values="len")
                .fill_null(0)
            )
            for col in [POSITIVE, NEGATIVE]:
                if col not in pivot.columns:
                    pivot = pivot.with_columns(pl.lit(0).alias(col))
            pivot = pivot.with_columns(
                (pl.col(POSITIVE) + pl.col(NEGATIVE)).alias("الإجمالي")
            )
            return pivot
        except Exception as e:
            _log.warning("فشل إنشاء محور العملاء المستهدفين لـ %s: %s", group_col, e)
            return pl.DataFrame()
