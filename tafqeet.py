# -*- coding: utf-8 -*-
"""
Tafqeet Helper - تحويل الأرقام إلى كلمات باللغة العربية
يدعم الريال السعودي والهللات
"""

ONES = ["", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة"]
TENS = ["", "عشرة", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"]
HUNDREDS = ["", "مائة", "مئتان", "ثلاثمائة", "أربعمائة", "خمسمائة", "ستمائة", "سبعمائة", "ثمانمائة", "تسعمائة"]
SPECIAL_TEENS = {
    10: "عشرة",
    11: "أحد عشر",
    12: "اثنا عشر",
    13: "ثلاثة عشر",
    14: "أربعة عشر",
    15: "خمسة عشر",
    16: "ستة عشر",
    17: "سبعة عشر",
    18: "ثمانية عشر",
    19: "تسعة عشر",
}

def _convert_hundreds(n):
    if n == 0:
        return ""
    parts = []
    c = n // 100
    r = n % 100
    if c > 0:
        parts.append(HUNDREDS[c])
    
    if r > 0:
        if 10 <= r <= 19:
            parts.append(SPECIAL_TEENS[r])
        else:
            unit = r % 10
            ten = r // 10
            unit_str = ONES[unit]
            ten_str = TENS[ten]
            if unit_str and ten_str:
                parts.append(f"{unit_str} و{ten_str}")
            elif unit_str:
                parts.append(unit_str)
            elif ten_str:
                parts.append(ten_str)
                
    return " و".join(parts)

def number_to_arabic_words(number):
    """تحويل عدد صحيح إلى كلمات عربية"""
    if number == 0:
        return "صفر"
    
    parts = []
    
    # مليارات
    billions = number // 1000000000
    number %= 1000000000
    if billions == 1:
        parts.append("مليار")
    elif billions == 2:
        parts.append("ملياران")
    elif 3 <= billions <= 10:
        parts.append(f"{_convert_hundreds(billions)} مليارات")
    elif billions > 10:
        parts.append(f"{_convert_hundreds(billions)} مليار")
        
    # ملايين
    millions = number // 1000000
    number %= 1000000
    if millions == 1:
        parts.append("مليون")
    elif millions == 2:
        parts.append("مليونان")
    elif 3 <= millions <= 10:
        parts.append(f"{_convert_hundreds(millions)} ملايين")
    elif millions > 10:
        parts.append(f"{_convert_hundreds(millions)} مليون")

    # آلاف
    thousands = number // 1000
    number %= 1000
    if thousands == 1:
        parts.append("ألف")
    elif thousands == 2:
        parts.append("ألفان")
    elif 3 <= thousands <= 10:
        parts.append(f"{_convert_hundreds(thousands)} آلاف")
    elif thousands > 10:
        parts.append(f"{_convert_hundreds(thousands)} ألف")

    # مئات وعشرات وآحاد
    if number > 0:
        rem = _convert_hundreds(number)
        if rem:
            parts.append(rem)

    return " و".join(parts)

def tafqeet_currency(amount, currency="ريال سعودي", fraction_name="هللة"):
    """
    تحويل المبلغ إلى صيغة تفقيط مالية كاملة:
    فقط ... ريال سعودي و ... هللة لا غير
    """
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return ""
    
    if amount == 0:
        return f"فقط صفر {currency} لا غير"
    
    integer_part = int(abs(amount))
    fraction_part = int(round((abs(amount) - integer_part) * 100))
    
    words_int = number_to_arabic_words(integer_part)
    res = f"فقط {words_int} {currency}"
    
    if fraction_part > 0:
        words_frac = number_to_arabic_words(fraction_part)
        res += f" و{words_frac} {fraction_name}"
        
    res += " لا غير"
    return res

if __name__ == "__main__":
    test_cases = [1500, 250.75, 1250000, 3500.50, 10, 12, 105]
    for tc in test_cases:
        print(f"{tc} -> {tafqeet_currency(tc)}")
