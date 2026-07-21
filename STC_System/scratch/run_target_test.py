import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'c:\Users\dell\Downloads\فايلات مهاره\STC_System')

import polars as pl

# Replicate make_portfolio, make_promise, make_maharah exactly as in the test file
def make_portfolio():
    return pl.DataFrame({
        "رقم الحساب":     ["ACC001","ACC002","ACC003","ACC004","ACC005","ACC006","ACC007","ACC008","ACC009","ACC010"],
        "رقم الهوية":     ["ID001","ID002","ID003","ID004","ID005","ID006","ID007","ID008","ID009","ID010"],
        "اسم العميل":     ["أحمد","فاطمة","محمد","نورة","خالد","ريم","عمر","هند","سعد","مها"],
        "المحصل":         ["محصل1","محصل1","محصل2","محصل2","محصل3","محصل3","محصل4","محصل4","محصل5","محصل5"],
        "المشرف":         ["مشرف1","مشرف1","مشرف2","مشرف2","مشرف1","مشرف1","مشرف2","مشرف2","مشرف1","مشرف2"],
        "المحفظة":        ["محفظة1","محفظة1","محفظة1","محفظة1","محفظة2","محفظة2","محفظة2","محفظة2","محفظة1","محفظة2"],
        "الفرع":          ["فرع1","فرع1","فرع2","فرع2","فرع1","فرع2","فرع1","فرع2","فرع1","فرع2"],
        "متبقي سداد موثق": ["1000","2000","3000","4000","5000","6000","7000","8000","9000","10000"],
        "الحالة الرئيسية": ["متأخر","متأخر","متأخر","متأخر","متأخر","متأخر","متأخر","متأخر","متأخر","متأخر"],
        "الحالة الفرعية":  ["لم يتم التواصل"]*10,
        "سنة التعثر":     ["2023"]*10,
        "اليوزر":         ["user1","user1","user2","user2","user3","user3","user4","user4","user5","user5"],
    })

def make_promise():
    return pl.DataFrame({
        "رقم الحساب": ["ACC001","ACC002","ACC003","ACC004","ACC005"],
        "تاريخ الوعد": ["2024-01-01","2024-01-02","2024-01-03","2024-01-04","2024-01-05"],
        "مبلغ الوعد": ["500","1000","1500","2000","2500"],
        "حالة الوعد": ["معلق","منجز","معلق","ملغي","منجز"],
    })

def make_maharah():
    return pl.DataFrame({
        "رقم الحساب": ["ACC001","ACC002","ACC003","ACC004","ACC005","ACC006","ACC007","ACC008","ACC009","ACC010"],
        "تاريخ آخر نشاط": ["2024-01-01"]*10,
        "نوع النشاط": ["مكالمة"]*10,
        "ملاحظة": ["ملاحظة"]*10,
    })

try:
    from modules.module7_targets import TargetCustomersModule
    r = TargetCustomersModule().run(make_portfolio(), make_promise(), make_maharah())
    
    print("Keys:", list(r.keys()))
    print("Columns:", r["data"].columns)
    print("Has تصنيف العميل:", "تصنيف العميل" in r["data"].columns)
    print("stats keys:", list(r["stats"].keys()))
    print("إجمالي العملاء:", r["stats"].get("إجمالي العملاء"))
    print("PASS!")
    
except Exception as e:
    import traceback
    print("FAIL:")
    traceback.print_exc()
