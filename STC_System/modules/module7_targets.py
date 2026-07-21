"""
modules/module7_targets.py
──────────────────────────
Module 7 — العملاء المستهدفة (Target Customers) using Polars.

STRICT TWO-STEP PROCESS:
STEP 1: Strictly filter rows by "الحالة الرئيسية" and "الحالة الفرعية" FIRST.
        Rows that do not match are completely ignored and dropped before reading "المتابعة".
STEP 2: For the matching rows only, scan "المتابعة" for positive keywords 
        while prioritizing negative exclusions (like "ما بسدد", "سحب", etc.).
"""
from __future__ import annotations

import logging
from typing import Dict, Any

import polars as pl

_log = logging.getLogger("Module7_Targets")

POSITIVE = "مستهدف"
NEGATIVE = "غير مستهدف"

# ── 1. Full Payment Disqualification ───────────────────────────────────────────
FULLY_PAID_KEYWORDS = [
    "تم السداد", "سدد كامل", "كامل المديونية", "كامل المديونيه", "كامل المبلغ",
    "سداد كامل", "مسدد بالكامل", "سدد المديونية كامله", "سدد المديونية كاملة",
    "تم سداد كامل", "خلاص سدد", "تم سداد المبلغ كاملا", "مسدد كامل"
]

# ── 2. Strict Positive Keyword Dictionaries by Category ────────────────────────
TARGET_CATEGORIES = {
    "💰 مرتبطة بالراتب": [
        "أول الشهر", "اول الشهر", "على الراتب", "ع الراتب", "علي الراتب",
        "بعد نزول الراتب", "بعد تحويل الراتب", "نهاية الشهر", "بانتظار الراتب",
        "مع راتب", "الراتب", "راتب", "معاش", "تقاعد", "التقاعد", "بينزل", "ينزل الراتب"
    ],
    "🏛️ مرتبطة بالدعم الحكومي": [
        "حساب المواطن", "حساب مواطن", "الضمان", "ضمان", "مواطن", "دعم حكومي", "دعم"
    ],
    "🤝 وعود بالسداد ومنتظمين": [
        "منتظم", "منتظمة", "منتظمه", "منتظمين", "انتظام", "منتظم بالسداد", "منتظم شهريا", "منتظم بالسداد شهريا",
        "تم الاتفاق على السداد", "وعد بالسداد", "سداد قريب", "سيتم السداد",
        "وعد", "واعد", "تسوية", "جدولة", "ابشر", "أبشر", "متعاون", "اتفقنا",
        "اتفقت", "سدد منها", "قريب", "وضحت له"
    ],
    "📅 مرتبطة بتاريخ أو وقت محدد": [
        "يوم الخميس", "يوم الاحد", "يوم الأحد", "يوم الاثنين", "يوم الإثنين",
        "يوم الثلاثاء", "يوم الاربعاء", "يوم الأربعاء", "يوم الجمعة", "يوم السبت",
        "يوم 1", "يوم الاول", "شهر 7", "شهر 8", "شهر 9", "شهر 10", "شهر 11", "شهر 12",
        "شهر 1", "شهر 2", "شهر 3", "شهر 4", "شهر 5", "شهر 6", "بكره", "بكرة", "اليوم"
    ],
    "💼 مرتبطة بدخل أو بيع أو مستحقات": [
        "بانتظار المستحقات", "المستحقات", "مستحقات", "بعد البيع", "دخل", "بيع"
    ],
    "💳 مرتبطة بتحويل أو إيداع أو دفعات": [
        "بعد التحويل", "بعد الإيداع", "بعد الايداع", "سدد دفعه", "سدد دفعة", "سدد دفعه الشهر", "سدد دفعة الشهر",
        "على دفعات", "علي دفعات", "تحويل", "إيداع", "ايداع", "دفعة", "دفعه",
        "دفعات", "بسدد", "بيسدد", "يسدد", "سيسدد", "سدد 200", "تسدد", "سدد"
    ]
}

# ── 3. Disqualifying Negative Keywords inside Follow-ups (المتابعة) ─────────────
DISQUALIFY_KEYWORDS = [
    # نفي ومماطلة صريحة
    "ما بسدد", "افاد انو ما بسدد", "افاد انه ما بسدد", "ما يسدد", "افاد انو ما يسدد",
    "ما عندي وماني مسدد", "ما عندي وماني", "ماني مسدد", "ومصر يسدد", "ومصر ما يسدد",
    "مماطل", "ماطل", "رافض", "رفض", "رفض السداد", "رافض السداد", "انكر", "أنكر", "ينكر",
    "تنازل", "سحب", "مريض", "مسافر", "مسافر بمصر", "لا تتم",
    
    # عدم الرد والإغلاق
    "لايرد", "لا يرد", "لا يررد", "لابرد", "مايرد", "مايردش", "ما يرد", "لم يرد", "لا ترد", "لا رد",
    "لم يتم الرد", "لمم يتم الرد", "لم يتم رد", "ولا ترد", "م بيشبك", "م يشبك", "م ىيشبك", "ما يشبك", "مبيشبك", "لا يجيب",
    "بريد", "بريد صوتي", "بيزي", "مشغول", "ما يمسك", "مغلق", "قفل", "قفل الخط", "يسكر الخط", "سكر الخط", "قفلت",
    "ردت وقفلت", "يكنسل", "كنسل", "خارج التغطية", "تحديث متابعه", "تحديث متابعة", "اخوه مو موجود",
    "اجتماع", "في اجتماع", "الوقت غير مناسب", "غير مناسب", "يفصل", "فصل", "بيفصل", "عدم تجاوب", "لعدم التجاوب",
    "رد وساكت", "رد و ساكت", "رد ويسكت", "رد بدون تجاوب", "يرد وما يتكلم", "يرد وساكته", "ساكت", "ساكته"
]


class TargetCustomersModule:
    CLASS_COL    = "العملاء المستهدفة"
    CATEGORY_COL = "تصنيف الاستهداف"
    PRIORITY_COL = "أولوية التحصيل"
    REASON_COL   = "سبب التصنيف"

    def run(
        self,
        portfolio: pl.DataFrame,
        promise: pl.DataFrame | None = None,
        maharah: pl.DataFrame | None = None,
    ) -> Dict[str, Any]:
        _log.info("▶ بدء تحديد العملاء المستهدفة")

        # ── الخطوة الأولى: الفلترة الصارمة بحسب الحالة الرئيسية والفرعية ────────
        filtered_portfolio = self._step1_filter_by_status(portfolio)

        if filtered_portfolio.is_empty():
            _log.warning("لا توجد سجلات تطابق شروط الحالة الرئيسية والفرعية!")
            empty_df = portfolio.head(0).with_columns([
                pl.lit(NEGATIVE).alias(self.CLASS_COL),
                pl.lit("❌ غير مستهدف").alias(self.CATEGORY_COL),
                pl.lit("غير مطابق لشروط الحالة الرئيسية/الفرعية").alias(self.REASON_COL),
                pl.lit(2).cast(pl.Int32).alias(self.PRIORITY_COL),
                pl.lit(1.0).alias("عدد العملاء")
            ])
            return {
                "data": empty_df,
                "positive_data": empty_df.head(0),
                "pivot_supervisor": pl.DataFrame(),
                "pivot_collector": pl.DataFrame(),
                "stats": {"إجمالي العملاء بعد الفلترة": 0, "مستهدف": 0, "غير مستهدف": 0, "نسبة المستهدفين %": 0.0}
            }

        id_col = next((c for c in ["رقم الهوية", "الهوية"] if c in filtered_portfolio.columns), None)
        if id_col:
            filtered_portfolio = filtered_portfolio.with_columns(
                (pl.lit(1.0) / pl.col(id_col).count().over(id_col).cast(pl.Float64)).alias("عدد العملاء")
            )
        else:
            filtered_portfolio = filtered_portfolio.with_columns(pl.lit(1.0).alias("عدد العملاء"))

        # ── الخطوة الثانية: فحص عمود المتابعة للسجلات المقبولة فقط ─────────────
        df = self._step2_classify_notes(filtered_portfolio.clone())

        positive_df = df.filter(pl.col(self.CLASS_COL) == POSITIVE)

        piv_sup = self._build_pivot(df, "المشرف")
        collector = next((c for c in ["المحصل", "الموظف"] if c in df.columns), "")
        piv_col   = self._build_pivot(df, collector) if collector else pl.DataFrame()

        total = len(df)
        pos_count = positive_df.height
        neg_count = total - pos_count

        category_counts: Dict[str, int] = {}
        if pos_count > 0:
            cat_df = positive_df.group_by(self.CATEGORY_COL).len()
            for r in cat_df.iter_rows(named=True):
                category_counts[str(r[self.CATEGORY_COL])] = int(r["len"])

        stats: Dict[str, Any] = {
            "إجمالي العملاء بعد الفلترة": total,
            "مستهدف":                    pos_count,
            "غير مستهدف":                neg_count,
            "نسبة المستهدفين %":        round(pos_count / total * 100, 1) if total else 0.0,
        }
        stats.update(category_counts)

        return {
            "data":             df,
            "positive_data":    positive_df,
            "pivot_supervisor": piv_sup,
            "pivot_collector":  piv_col,
            "stats":            stats,
        }

    @staticmethod
    def _normalize_text_str(s: str) -> str:
        """توحيد الأحرف للنصوص الثابتة والقواميس."""
        return (
            s.replace("أ", "ا")
            .replace("إ", "ا")
            .replace("آ", "ا")
            .replace("ة", "ه")
            .replace("ى", "ي")
            .strip()
            .lower()
        )

    def _normalize_text(self, text_col: str) -> pl.Expr:
        """توحيد الأحرف لعمود النص داخل Polars."""
        return (
            pl.col(text_col)
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

    def _step1_filter_by_status(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        [المرحلة الأولى]: الفلترة المبدئية قبل النظر في المتابعة إطلاقاً.
        تُبقي فقط الصفوف التي تحقق:
        1. الحالة الرئيسية = (سداد جزئي OR واعد بالسداد OR متابعة)
        2. OR (الحالة الرئيسية = متوفي AND الحالة الفرعية تحتوي على 'واعد')
        """
        main_col = next((c for c in ["الحالة الرئيسية", "الحالة"] if c in df.columns), None)
        sub_col  = next((c for c in ["الحالة الفرعية"] if c in df.columns), None)

        if not main_col:
            _log.warning("لم يتم العثور على عمود الحالة الرئيسية!")
            return df

        main_expr = self._normalize_text(main_col)
        sub_expr  = self._normalize_text(sub_col) if sub_col else pl.lit("")

        # 1. الحالات الرئيسية المسموح بها فقط
        allowed_main = main_expr.str.contains("سداد جزئي|واعد بالسداد|متابعه|متابعة")

        # 2. استثناء المتوفي: يجب أن تكون الحالة الفرعية واعدين
        is_deceased_promised = (main_expr.str.contains("متوفي")) & (sub_expr.str.contains("واعد"))

        filtered_df = df.filter(allowed_main | is_deceased_promised)
        _log.info(f"إجمالي الملف: {len(df)} | المقبول بعد فلترة الحالة (قبل المتابعة): {len(filtered_df)}")
        return filtered_df

    def _step2_classify_notes(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        [المرحلة الثانية]: فحص عمود 'المتابعة' فقط للصفوف التي اجتازت المرحلة الأولى.
        """
        note_col = next((c for c in ["المتابعة", "الملاحظة", "الملاحظات", "ملاحظة"] if c in df.columns), None)

        if not note_col:
            _log.warning("لم يتم العثور على عمود المتابعة!")
            return df.with_columns([
                pl.lit(NEGATIVE).alias(self.CLASS_COL),
                pl.lit("❌ غير مستهدف").alias(self.CATEGORY_COL),
                pl.lit("لا يوجد عمود متابعة").alias(self.REASON_COL),
                pl.lit(2).cast(pl.Int32).alias(self.PRIORITY_COL),
            ])

        note_expr = self._normalize_text(note_col)

        # 1. فحص سداد كامل المديونية في المتابعة
        has_fully_paid = pl.lit(False)
        for kw in FULLY_PAID_KEYWORDS:
            kw_norm = self._normalize_text_str(kw)
            has_fully_paid = has_fully_paid | note_expr.str.contains(kw_norm, literal=True)

        # 2. فحص العبارات السلبية / المماطلة / النفي في المتابعة (تُستبعد فوراً)
        has_disqualify = pl.lit(False)
        disqualify_reasons = []
        for kw in DISQUALIFY_KEYWORDS:
            kw_norm = self._normalize_text_str(kw)
            match_cond = note_expr.str.contains(kw_norm, literal=True)
            has_disqualify = has_disqualify | match_cond
            disqualify_reasons.append(
                pl.when(match_cond).then(pl.lit(f"مستبعد: {kw}")).otherwise(pl.lit(None))
            )

        disqualify_reason_expr = pl.coalesce(disqualify_reasons).fill_null("عدم تواصل / استبعاد")

        # 3. فحص الكلمات الإيجابية في المتابعة
        category_expr_list = []
        has_any_positive = pl.lit(False)

        for cat_name, kw_list in TARGET_CATEGORIES.items():
            cat_match = pl.lit(False)
            for kw in kw_list:
                kw_norm = self._normalize_text_str(kw)
                cat_match = cat_match | note_expr.str.contains(kw_norm, literal=True)
            
            has_any_positive = has_any_positive | cat_match
            category_expr_list.append(
                pl.when(cat_match).then(pl.lit(cat_name)).otherwise(pl.lit(None))
            )

        pos_category_expr = pl.coalesce(category_expr_list)

        # 4. القرار النهائي للاستهداف
        is_targeted = (~has_fully_paid) & (~has_disqualify) & has_any_positive

        class_expr = pl.when(is_targeted).then(pl.lit(POSITIVE)).otherwise(pl.lit(NEGATIVE))
        
        category_result_expr = (
            pl.when(is_targeted)
            .then(pos_category_expr)
            .otherwise(pl.lit("❌ غير مستهدف"))
        )

        reason_result_expr = (
            pl.when(has_fully_paid)
            .then(pl.lit("✅ تم سداد كامل المديونية"))
            .otherwise(
                pl.when(is_targeted)
                .then(pl.lit("كلمة إيجابية صريحة بالسداد / منتظم"))
                .otherwise(
                    pl.when(has_disqualify)
                    .then(disqualify_reason_expr)
                    .otherwise(pl.lit("لا تتوفر عبارات سداد إيجابية"))
                )
            )
        )

        return df.with_columns([
            class_expr.alias(self.CLASS_COL),
            category_result_expr.alias(self.CATEGORY_COL),
            reason_result_expr.alias(self.REASON_COL),
            pl.when(is_targeted).then(pl.lit(1)).otherwise(pl.lit(2)).cast(pl.Int32).alias(self.PRIORITY_COL)
        ])

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
            
            return pivot.with_columns(
                (pl.col(POSITIVE) + pl.col(NEGATIVE)).alias("الإجمالي")
            )
        except Exception as e:
            _log.warning("فشل إنشاء جدول المحور لـ %s: %s", group_col, e)
            return pl.DataFrame()
