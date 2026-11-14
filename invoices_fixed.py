import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import datetime
import json
from fpdf import FPDF
from arabic_reshaper import reshape
from bidi.algorithm import get_display
import os
import sys
import pandas as pd
from database import Database

def get_font_path(font_name):
    """الحصول على مسار الخط - يعمل في التطوير وفي EXE"""
    if getattr(sys, 'frozen', False):
        # نحن في EXE - الملفات في نفس المجلد
        base_path = sys._MEIPASS
        return os.path.join(base_path, font_name)
    else:
        # نحن في development - الملفات في مجلد Amiri
        current_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(current_dir, 'Amiri', font_name)

# دالة معالجة النصوص العربية محسنة
def ar(text):
    if not text:
        return ""
    try:
        # إعادة تشكيل النص العربي
        reshaped_text = reshape(text)
        # تطبيق الخوارزمية ثنائية الاتجاه
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception as e:
        print(f"Error reshaping Arabic text: {e}")
        return text

# كلاس PDF مخصص للفواتير مطابق للتصميم في PDF مع دعم عربي كامل
class CustomInvoicePDF(FPDF):
    def __init__(self, company_settings=None):
        super().__init__()
        self.company_settings = company_settings or {}
        self.set_auto_page_break(auto=True, margin=15)
        self.font_name = 'Amiri'
        try:
            amiri_regular = get_font_path('Amiri-Regular.ttf')
            amiri_bold = get_font_path('Amiri-Bold.ttf')
            
            if os.path.exists(amiri_regular):
                self.add_font('Amiri', '', amiri_regular, uni=True)
            if os.path.exists(amiri_bold):
                self.add_font('Amiri', 'B', amiri_bold, uni=True)
        except Exception as e:
            print(f"Warning: Amiri font not found, using default fonts: {e}")
            self.font_name = 'Arial'

        self.set_right_margin(10)
        self.set_left_margin(10)
    
    def header(self):
        # بيانات البائع في الأعلى بمحاذاة لليمين
        self.set_font('Amiri', 'B', 14)
        
        # اسم الشركة بالعربية والإنجليزية
        company_name_ar = self.company_settings.get('company_name_ar', 'محمد بن منير بن محمد سعيد دغستاني')
        company_name_en = self.company_settings.get('company_name_en', 'Mohammed bin Munir bin Mohammed Saeed Daghestani')
        
        self.cell(0, 8, ar(company_name_ar), 0, 1, 'R')
        self.set_font('Amiri', 'B', 12)
        self.cell(0, 6, company_name_en, 0, 1, 'R')
        
        # السجل التجاري والرقم الضريبي
        commercial_register = self.company_settings.get('commercial_register', '4030330926')
        tax_number = self.company_settings.get('tax_number', '300262161400003')
        
        self.cell(0, 6, ar(f"س.ت.: {commercial_register}"), 0, 1, 'R')
        self.cell(0, 6, ar(f"الرقم الضريبي: {tax_number}"), 0, 1, 'R')
        
        # خط فاصل
        self.line(10, 42, 200, 42)
        self.ln(12)
        
        # العنوان الرئيسي
        self.set_font('Amiri', 'B', 18)
        self.cell(0, 10, ar("فاتورة ضريبية") + " / Tax Invoice", 0, 1, 'C')
        self.ln(5)
    
    def add_invoice_data(self, invoice, customer_data):
        # معلومات الفاتورة
        self.set_font('Amiri', 'B', 12)
        
        # استخراج التاريخ - التأكد من أنه نص بالتنسيق الصحيح
        invoice_date = str(invoice[3]) if invoice[3] else datetime.now().strftime('%Y-%m-%d')
        
        # التاريخ ورقم الفاتورة بمحاذاة صحيحة
        self.cell(100)
        self.cell(40, 8, "Date : " + invoice_date, 0, 0, 'L')
        self.cell(0, 8, ar("التاريخ :"), 0, 1, 'R')
        self.ln(4)
        
        # جدول معلومات الفاتورة
        self.set_fill_color(240, 240, 240)
        
        # الصف الأول - محاذاة لليمين للنصوص العربية
        self.set_line_width(0.5)
        self.cell(30, 10, ar("الموافق"), 1, 0, 'C', 1)
        self.cell(30, 10, ar("رقم الفاتورة"), 1, 0, 'C', 1)
        self.cell(25, 10, str(invoice[1]), 1, 0, 'C')
        self.cell(30, 10, "Inv No.", 1, 0, 'C', 1)
        self.cell(35, 10, ar("رقم العميل"), 1, 0, 'C', 1)
        self.cell(30, 10, "Cust No", 1, 1, 'C', 1)
        
        # اسم العميل والرقم الضريبي - محاذاة لليمين
        self.cell(0, 10, ar("اسم العميل: ") + ar(customer_data[1]), 1, 1, 'R')
        self.cell(0, 10, "VAT No# " + (customer_data[2] if customer_data[2] else "310431653500003"), 1, 1, 'R')
        
        # عنوان العميل - محاذاة لليمين
        if customer_data[3]:
            self.cell(0, 10, ar("موقع العميل: ") + ar(customer_data[3]), 1, 1, 'R')
        
        self.ln(10)
        
        # جدول العناصر
        self.create_items_table(invoice)
        
        # المجاميع
        self.create_totals_section(invoice)
        
        # التوقيع والمعلومات الإضافية
        self.create_footer()
    
    def create_items_table(self, invoice):
        items = json.loads(invoice[4])
        
        # رأس الجدول - نصوص عربية بمحاذاة صحيحة
        self.set_font('Amiri', 'B', 13)
        self.set_fill_color(220, 220, 220)
        
        # العناوين العربية بمحاذاة لليمين
        headers_arabic = [
            ar("القيمة الإجمالية"),
            ar("سعر الوحدة"), 
            ar("الكمية"),
            ar("الوحدة"),
            ar("البنود"),
            ar("رقم الصنف")
        ]
        widths = [35, 30, 25, 25, 80, 25]
        
        self.set_line_width(0.5)
        for i, header in enumerate(headers_arabic):
            self.cell(widths[i], 10, header, 1, 0, 'C', 1)
        self.ln()
        
        # بيانات العناصر - محاذاة صحيحة للنصوص العربية
        self.set_font('Amiri', 'B', 11)
        self.set_fill_color(255, 255, 255)
        
        for i, item in enumerate(items, 1):
            # كتابة البيانات من اليمين لليسار
            self.cell(35, 10, f"{item['total']:.2f}", 1, 0, 'C')
            self.cell(30, 10, f"{item['price']:.2f}", 1, 0, 'C')
            self.cell(25, 10, str(item['quantity']), 1, 0, 'C')
            self.cell(25, 10, ar(item.get('unit', '')), 1, 0, 'C')
            self.cell(80, 10, ar(item['description']), 1, 0, 'R')  # محاذاة لليمين للوصف
            self.cell(25, 10, str(i), 1, 1, 'C')
        
        self.ln(10)
    
    def create_totals_section(self, invoice):
        subtotal = invoice[5]
        tax_amount = invoice[6]
        discount = invoice[7]
        grand_total = invoice[8]
        
        # العناوين الإنجليزية
        self.set_font('Amiri', 'B', 13)
        self.set_fill_color(220, 220, 220)
        
        self.set_line_width(0.5)
        headers_english = ["Net Amount", "15% VAT", "Discount", "Total Amount"]
        for header in headers_english:
            self.cell(47.5, 10, header, 1, 0, 'C', 1)
        self.ln()
        
        # العناوين العربية - مكتوبة بشكل صحيح
        headers_arabic = [
            ar("صافي المبلغ"),
            ar("الضريبة 15%"), 
            ar("الخصم"),
            ar("إجمالي المبلغ")
        ]
        for header in headers_arabic:
            self.cell(47.5, 10, header, 1, 0, 'C', 1)
        self.ln()
        
        # القيم
        self.set_font('Amiri', 'B', 14)
        self.set_fill_color(255, 255, 255)
        
        values = [f"{grand_total:.2f}", f"{tax_amount:.2f}", f"{discount:.2f}", f"{subtotal:.2f}"]
        for value in values:
            self.cell(47.5, 12, value, 1, 0, 'C')
        self.ln(15)
    
    def create_footer(self):
        self.set_font('Amiri', 'B', 11)
        
        # معلومات الاتصال - نصوص عربية صحيحة
        address = self.company_settings.get('address', 'جدة - أبحر الشمالية - شارع أبي محمد العطار')
        phone1 = self.company_settings.get('phone1', '0582224122')
        phone2 = self.company_settings.get('phone2', '0538833640')
        po_box = self.company_settings.get('po_box', '117332')
        postal_code = self.company_settings.get('postal_code', '21391')
        email = self.company_settings.get('email', 'seapearl.est@gmail.com')
        
        contact_info = ar(f"المقر الرئيسي: {address} - جوال: {phone1} / {phone2} - ص.ب: {po_box} {postal_code}")
        self.multi_cell(0, 5, contact_info, 0, 'C')
        
        self.cell(0, 5, f"E-mail: {email}", 0, 1, 'C')
        
        # مساحة التوقيع - نصوص عربية صحيحة
        self.ln(10)
        signature_text = ar("أقر أنا الموقع أدناه بصحة صافي المبلغ بهذه الفاتورة والالتزام بالدفع خلال المدة المتفق عليها")
        self.multi_cell(0, 5, signature_text, 0, 'C')
        self.ln(15)
        
        # توقيع البائع والعميل - نصوص عربية صحيحة
        owner_name = self.company_settings.get('owner_name', 'محمد بن منير دغستاني')
        self.cell(90, 5, ar(f"توقيع البائع: {owner_name}"), 0, 0, 'C')
        self.cell(90, 5, ar("توقيع العميل: _________________________"), 0, 1, 'C')

class CustomStatementPDF(FPDF):
    """PDF class مخصص لكشف الحساب بدون header تلقائي"""
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.font_name = 'Amiri'
        try:
            amiri_regular = get_font_path('Amiri-Regular.ttf')
            amiri_bold = get_font_path('Amiri-Bold.ttf')
            
            if os.path.exists(amiri_regular):
                self.add_font('Amiri', '', amiri_regular, uni=True)
            if os.path.exists(amiri_bold):
                self.add_font('Amiri', 'B', amiri_bold, uni=True)
        except Exception as e:
            print(f"Warning: Amiri font not found, using default fonts: {e}")
            self.font_name = 'Arial'
        self.set_right_margin(10)
        self.set_left_margin(10)
    
    def header(self):
        # header فارغ - لا شيء يكتب تلقائياً
        pass

# دالة الطباعة المحدثة
def print_invoice_with_settings(db, invoice_id):
    invoice = db.execute_query("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    if not invoice:
        messagebox.showerror("خطأ", "❌ الفاتورة غير موجودة.")
        return None
    
    invoice = invoice[0]
    customer = db.execute_query("SELECT * FROM customers WHERE id = ?", (invoice[2],))
    customer_data = customer[0] if customer else ("", "غير معروف", "", "", "")

    try:
        # استيراد إعدادات الشركة
        from company_settings import get_company_settings
        company_settings = get_company_settings(db)
        
        pdf = CustomInvoicePDF(company_settings)
        pdf.add_page()
        pdf.add_invoice_data(invoice, customer_data)
        
        filename = f"فاتورة_{invoice[1]}.pdf"
        pdf.output(filename)
        
        try:
            if os.name == 'nt':
                os.startfile(filename)
            elif os.name == 'posix':
                os.system(f'xdg-open {filename}')
        except Exception as e:
            messagebox.showwarning("تنبيه", f"⚠️ تعذر فتح ملف PDF: {e}")
            
        return filename
        
    except Exception as e:
        messagebox.showerror("خطأ", f"❌ فشل في الطباعة:\n{str(e)}")
        return None
