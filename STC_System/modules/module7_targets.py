"""
modules/module7_targets.py
──────────────────────────
Module 7 — العملاء المستهدفة (Target Customers) using Polars.
Works on the main portfolio file (المحفظة الموزعة).

Rules:
1. FULLY PAID ("تم السداد", "كامل المديونية", "كامل المبلغ") -> NOT TARGETED (غير مستهدف - تم سداد كامل المديونية).
2. REGULAR PAYERS ("منتظم", "منتظم بالسداد") -> TARGETED (مستهدف).
3. NON-CONTACT / DISQUALIFIED -> NOT TARGETED (غير مستهدف).
4. POSITIVE INTENTS -> TARGETED (مستهدف) categorized into 6 functional groups.
"""
from __future__ import annotations

import logging
from typing import Dict

import polars as pl

_log = logging.getLogger("Module7_Targets")

POSITIVE = "مستهدف"
NEGATIVE = "غير مستهدف"

# ── 1. Full Payment Disqualification (تم السداد بالكامل) ────────────────────────
FULLY_PAID_KEYWORDS = [
    "تم السداد", "سدد كامل", "كامل المديونية", "كامل المديونيه", "كامل المبلغ",
    "سداد كامل", "مسدد بالكامل", "سدد المديونية كامله", "سدد المديونية كاملة",
    "تم سداد كامل", "خلاص سدد", "تم سداد المبلغ كاملا", "مسدد كامل"
]

# ── 2. Dictionaries of Positive Keywords by Category ──────────────────────────
TARGET_CATEGORIES = {
    "💰 مرتبطة بالراتب": [
        "أول الشهر", "اول الشهر", "على الراتب", "ع الراتب", "علي الراتب",
        "بعد نزول الراتب", "بعد تحويل الراتب", "نهاية الشهر", "بانتظار الراتب",
        "مع راتب", "الراتب", "راتب", "معاش", "بينزل", "ينزل الراتب"
    ],
    "🏛️ مرتبطة بالدعم الحكومي": [
        "حساب المواطن", "حساب مواطن", "الضمان", "ضمان", "مواطن", "دعم حكومي", "دعم"
    ],
    "🤝 وعود بالسداد ومنتظمين": [
        "منتظم", "منتظم بالسداد", "منتظمة", "منتظمه", "منتظم شهريا", "منتظم بالسداد شهريا",
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
        "بعد التحويل", "بعد الإيداع", "بعد الايداع", "سدد دفعه", "سدد دفعة",
        "على دفعات", "علي دفعات", "تحويل", "إيداع", "ايداع", "دفعة", "دفعه",
        "دفعات", "بسدد", "بيسدد", "يسدد", "سيسدد", "سدد 200", "تسدد", "سدد"
    ]
}

# ── 3. Disqualifying Negative / Non-Contact Keywords ──────────────────────────
DISQUALIFY_KEYWORDS = [
    # لا يرد / عدم تواصل
    "لايرد", "لا يرد", "مايرد", "مايردش", "ما يرد", "لم يرد", "لا ترد", "لا رد",
    "لم يتم الرد", "لم يتم رد", "م بيشبك", "م يشبك", "م ىيشبك", "ما يشبك", "مبيشبك", "لا يجيب",
    "بريد", "بريد صوتي", "بيزي", "مشغول",
    # إغلاق / إلغاء / أعذار مؤقتة
    "مغلق", "قفل", "قفل الخط", "قفلت", "ردت وقفلت", "يكنسل", "كنسل", "خارج التغطية",
    "يصلي", "صلي", "في العمل", "في الشغل", "لايمكن", "لا يمكن", "بيراجع الفرع",
    "اجتماع", "في اجتماع", "الوقت غير مناسب", "غير مناسب", "يفصل", "فصل", "بيفصل", "عدم تجاوب", "لعدم التجاوب",
    # صمت / عدم اهتمام
    "رد وساكت", "رد و ساكت", "يرد وما يتكلم", "يرد وساكته", "ردت وساكته", "رد وبعد", "رد وقفل",
    "ساكت", "ساكته", "يرد يسكت", "يتكلم",
    # رفض صريح
    "ماني مسدد", "ما عندي وماني مسدد", "ما عندي وماني", "ما عندي", "ما يبي", "ما يبي ازعاج",
    "رافض", "رفض", "رفض السداد", "رافض السداد", "انكر", "تنكر", "ما يقدر", "مقدر اسدد", "ما تقدر", "ما يقدر",
    # أرقام خاطئة / مستبعدين
    "غير صحيح", "لا يخص", "لايخص", "رقم خطأ", "رقم غلط", "خروج نهائي", "سجن", "مسجون"
]


class TargetCustomersModule:
    CLASS_COL    = "العملاء المستهدفة"
    CATEGORY_COL = "تصنيف الاستهداف"
    PRIORITY_COL = "أولوية التحصيل"
    REASON_COL   = "سبب التصنيف"

    def run(
        self,
        portfolio: pl.DataFrame,
        promise: pl.DataFrame = None,
        maharah: pl.DataFrame = None,
    ) -> Dict:
        _log.info("▶ بدء تحديد العملاء المستهدفة (معالجة كامل السداد والمنتظمين)")

        id_col = next((c for c in ["رقم الهوية", "الهوية"] if c in portfolio.columns), None)
        if id_col:
            portfolio = portfolio.with_columns(
                (pl.lit(1.0) / pl.col(id_col).count().over(id_col).cast(pl.Float64)).alias("عدد العملاء")
            )
        else:
            portfolio = portfolio.with_columns(pl.lit(1.0).alias("عدد العملاء"))

        df = portfolio.clone()
        df = self._classify(df)

        positive_df = df.filter(pl.col(self.CLASS_COL) == POSITIVE)

        piv_sup = self._build_pivot(df, "المشرف")
        collector = next((c for c in ["المحصل", "الموظف"] if c in df.columns), "")
        piv_col   = self._build_pivot(df, collector) if collector else pl.DataFrame()

        total = len(df)
        pos_count = df.filter(pl.col(self.CLASS_COL) == POSITIVE).height
        neg_count = df.filter(pl.col(self.CLASS_COL) == NEGATIVE).height

        category_counts = {}
        if pos_count > 0:
            cat_df = positive_df.group_by(self.CATEGORY_COL).len()
            for r in cat_df.iter_rows(named=True):
                category_counts[r[self.CATEGORY_COL]] = int(r["len"])

        stats = {
            "إجمالي العملاء":    total,
            "مستهدف":            pos_count,
            "غير مستهدف":        neg_count,
            "نسبة المستهدفين %": round(pos_count / total * 100, 1) if total else 0.0,
        }
        stats.update(category_counts)

        return {
            "data":             df,
            "positive_data":    positive_df,
            "pivot_supervisor": piv_sup,
            "pivot_collector":  piv_col,
            "stats":            stats,
        }

    def _normalize_text(self, text_col: str) -> pl.Expr:
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

    def _classify(self, df: pl.DataFrame) -> pl.DataFrame:
        note_col = next((c for c in ["المتابعة", "الملاحظة", "الملاحظات", "ملاحظة"] if c in df.columns), None)
        main_col = next((c for c in ["الحالة الرئيسية", "الحالة"] if c in df.columns), None)
        sub_col  = next((c for c in ["الحالة الفرعية"] if c in df.columns), None)

        if not note_col:
            _log.warning("لم يتم العثور على عمود المتابعة!")
            return df.with_columns([
                pl.lit(NEGATIVE).alias(self.CLASS_COL),
                pl.lit("❌ غير مستهدف").alias(self.CATEGORY_COL),
                pl.lit("لا يوجد عمود متابعة").alias(self.REASON_COL),
                pl.lit(2).cast(pl.Int32).alias(self.PRIORITY_COL),
            ])

        note_expr = self._normalize_text(note_col)
        main_expr = self._normalize_text(main_col) if main_col else pl.lit("")
        sub_expr  = self._normalize_text(sub_col) if sub_col else pl.lit("")

        # ── 1. فحص كولوم كامل السداد (مستبعد فوراً لأنه سدد وخلاص) ──────────────
        has_fully_paid = pl.lit(False)
        for kw in FULLY_PAID_KEYWORDS:
            kw_norm = kw.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
            has_fully_paid = has_fully_paid | note_expr.str.contains(kw_norm, literal=True) | main_expr.str.contains(kw_norm, literal=True) | sub_expr.str.contains(kw_norm, literal=True)

        # ── 2. فحص الكلمات السلبية والمستبعدة ────────────────────────────────
        has_disqualify = pl.lit(False)
        disqualify_reasons = []
        for kw in DISQUALIFY_KEYWORDS:
            kw_norm = kw.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
            match_cond = note_expr.str.contains(kw_norm, literal=True)
            has_disqualify = has_disqualify | match_cond
            disqualify_reasons.append(pl.when(match_cond).then(pl.lit(f"مستبعد: {kw}")).otherwise(pl.lit(None)))

        disqualify_reason_expr = pl.coalesce(disqualify_reasons).fill_null("عدم تواصل / استبعاد")

        # ── 3. فحص الفئات الإيجابية الست (شاملة المنتظمين) ────────────────────
        category_expr_list = []
        has_any_positive = pl.lit(False)

        for cat_name, kw_list in TARGET_CATEGORIES.items():
            cat_match = pl.lit(False)
            for kw in kw_list:
                kw_norm = kw.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
                # فحص الكلمة في المتابعة والحالة الفرعية والحالة الرئيسية
                cat_match = cat_match | note_expr.str.contains(kw_norm, literal=True) | sub_expr.str.contains(kw_norm, literal=True)
            
            has_any_positive = has_any_positive | cat_match
            category_expr_list.append(
                pl.when(cat_match).then(pl.lit(cat_name)).otherwise(pl.lit(None))
            )

        pos_category_expr = pl.coalesce(category_expr_list).fill_null("🤝 وعود بالسداد ومنتظمين")

        # ── 4. فحص الحالات الرئيسية المؤكدة للاستهداف ─────────────────────────
        pos_main_statuses = ["سداد جزئي", "واعد بالسداد", "وعد السداد", "تسوية", "جدولة"]
        has_pos_main = pl.lit(False)
        for st in pos_main_statuses:
            st_norm = st.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه").replace("ى", "ي")
            has_pos_main = has_pos_main | main_expr.str.contains(st_norm, literal=True)

        # ── 5. قاعدة الاستهداف النهائية ───────────────────────────────────────
        note_has_text = (note_expr != "") & (note_expr != "-") & (note_expr != "---")
        
        # الشرط الحازم:
        # إذا تم السداد بالكامل (has_fully_paid) -> غير مستهدف إطلاقاً (خلاص سدد).
        # وإلا لو لم تكن هناك كلمة سلبية وبشرط وجود مؤشر إيجابي (منتظم أو وعد أو فئة إيجابية) -> مستهدف.
        is_targeted = (~has_fully_paid) & (~has_disqualify) & (has_any_positive | (has_pos_main & note_has_text & ~note_expr.str.contains("رد و ساكت|لايرد|قفل|بريد|يكنسل")))

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
                .then(pl.lit("مؤشر إيجابي صريح بالسداد / منتظم"))
                .otherwise(
                    pl.when(has_disqualify)
                    .then(disqualify_reason_expr)
                    .otherwise(pl.lit("لا تتوفر عبارات سداد إيجابية"))
                )
            )
        )

        df = df.with_columns([
            class_expr.alias(self.CLASS_COL),
            category_result_expr.alias(self.CATEGORY_COL),
            reason_result_expr.alias(self.REASON_COL),
            pl.when(is_targeted).then(pl.lit(1)).otherwise(pl.lit(2)).cast(pl.Int32).alias(self.PRIORITY_COL)
        ])

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
            _log.warning("فشل إنشاء جدول المحور لـ %s: %s", group_col, e)
            return pl.DataFrame()
