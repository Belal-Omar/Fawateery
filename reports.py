# -*- coding: utf-8 -*-
"""
وحدة التقارير والإحصائيات المتقدمة - نظام فواتيري
تتضمن:
1. عرض تحليلي تفاعلي مع بطاقات مؤشرات (KPIs) ورسوم بيانية وجداول تفصيلية.
2. طباعة وتصدير تقارير PDF احترافية تنفيذية فائقة الجودة مع رسوم بيانية وتواقيع.
3. تصدير جداول بيانات Excel منسقة.
"""

import os
import sys
import tempfile
import webbrowser
from datetime import datetime, timedelta
import calendar

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import warnings
warnings.filterwarnings('ignore', message='.*Tight layout not applied.*')
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

# ضبط خطوط الرسوم البيانية لتدعم اللغة العربية بشكل قياسي وصحيح
plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Arial', 'Tahoma'] + [f for f in plt.rcParams.get('font.sans-serif', []) if f not in ['Segoe UI', 'Arial', 'Tahoma']]
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['axes.unicode_minus'] = False

import pandas as pd
from fpdf import FPDF

from database import Database
from company_settings import get_company_settings
import arabic_reshaper
from bidi.algorithm import get_display

try:
    from tkcalendar import DateEntry
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False

from icon_manager import ICONS


def format_chart_arabic(text):
    """تهيئة النص العربي للرسوم البيانية Matplotlib بدون عكس أو قلب الحروف"""
    if not text:
        return ""
    return str(text)


def format_arabic(text):
    """تهيئة النص العربي لمستندات PDF باستخدام FPDF وخط Amiri"""
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)
    reshaped_text = arabic_reshaper.reshape(text)
    return get_display(reshaped_text)


def get_font_path(font_name):
    """البحث المرن عن مسار الخط العربي"""
    search_dirs = []
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            search_dirs.append(sys._MEIPASS)
            search_dirs.append(os.path.join(sys._MEIPASS, 'Amiri'))
            search_dirs.append(os.path.join(sys._MEIPASS, 'Fonts'))
        exe_dir = os.path.dirname(sys.executable)
        search_dirs.append(exe_dir)
        search_dirs.append(os.path.join(exe_dir, 'Amiri'))
        search_dirs.append(os.path.join(exe_dir, 'Fonts'))

    current_dir = os.path.dirname(os.path.abspath(__file__))
    search_dirs.append(os.path.join(current_dir, 'Amiri'))
    search_dirs.append(os.path.join(current_dir, 'Fonts'))
    search_dirs.append(current_dir)

    for d in search_dirs:
        candidate = os.path.join(d, font_name)
        if os.path.exists(candidate):
            return candidate
    return font_name


class ExecutiveReportPDF(FPDF):
    """كلاس PDF متقدم لتوليد تقارير إدارية وتنفيذية فاخرة مع رسوم بيانية"""
    def __init__(self, company_settings=None):
        super().__init__()
        self.company_settings = company_settings or {}
        
        try:
            amiri_reg = get_font_path('Amiri-Regular.ttf')
            amiri_bld = get_font_path('Amiri-Bold.ttf')
            if os.path.exists(amiri_reg):
                self.add_font('Amiri', '', amiri_reg, uni=True)
            if os.path.exists(amiri_bld):
                self.add_font('Amiri', 'B', amiri_bld, uni=True)
            try:
                self.add_font('Arial', '', 'arial.ttf', uni=True)
                self.add_font('Arial', 'B', 'arialbd.ttf', uni=True)
            except Exception:
                pass
        except Exception as e:
            print(f"Font loading error in report PDF: {e}")

        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=True, margin=15)

    def draw_report_header(self, title_text, from_date, to_date):
        """رأس التقرير الرسمي"""
        # إطار خارجي
        self.set_draw_color(27, 54, 93)
        self.set_line_width(0.6)
        self.rect(8, 8, 194, 281)

        co_ar = self.company_settings.get('company_name_ar', 'مؤسسة فواتيري للمقاولات والتجارة')
        co_en = self.company_settings.get('company_name_en', 'FAWATEERY ESTABLISHMENT')
        cr = self.company_settings.get('commercial_register', '4030330926')
        vat = self.company_settings.get('tax_number', '300262161400003')

        # شريط الرأس
        self.set_fill_color(27, 54, 93)
        self.rect(10, 10, 190, 26, 'F')
        self.set_fill_color(201, 151, 0)
        self.rect(10, 36, 190, 1.5, 'F')

        self.set_text_color(255, 255, 255)
        self.set_font('Amiri', 'B', 16)
        self.set_xy(10, 13)
        self.cell(190, 7, format_arabic(title_text), 0, 1, 'C')

        self.set_font('Amiri', '', 10)
        self.cell(190, 6, format_arabic(f"{co_ar}  |  س.ت: {cr}  |  الرقم الضريبي: {vat}"), 0, 1, 'C')

        # شريط النطاق الزمني
        self.set_fill_color(248, 250, 252)
        self.set_draw_color(203, 213, 225)
        self.rect(10, 41, 190, 9, 'DF')
        self.set_xy(10, 42)
        self.set_text_color(27, 54, 93)
        self.set_font('Amiri', 'B', 10)
        period_text = f"الفترة الزمنية للتقرير: من {from_date} إلى {to_date}   |   تاريخ الإصدار: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        self.cell(190, 7, format_arabic(period_text), 0, 1, 'C')

        self.set_y(54)

    def draw_kpi_cards(self, kpis):
        """رسم بطاقات المؤشرات الرئيسية الأربعة"""
        y = self.get_y()
        box_w = 46.5
        box_h = 20

        for i, (title, val_str, color_rgb) in enumerate(kpis):
            bx = 10 + (i * 47.8)
            self.set_fill_color(248, 250, 252)
            self.set_draw_color(226, 232, 240)
            self.rect(bx, y, box_w, box_h, 'DF')
            self.set_fill_color(*color_rgb)
            self.rect(bx, y, box_w, 2.5, 'F')

            self.set_xy(bx, y + 4)
            self.set_font('Amiri', 'B', 9)
            self.set_text_color(71, 85, 105)
            self.cell(box_w, 4.5, format_arabic(title), 0, 1, 'C')

            self.set_xy(bx, y + 9.5)
            self.set_font('Amiri', 'B', 11)
            self.set_text_color(*color_rgb)
            self.cell(box_w, 7, format_arabic(val_str), 0, 1, 'C')

        self.set_y(y + 24)

    def draw_chart_image(self, chart_path):
        """إدراج الرسم البياني في التقرير"""
        if chart_path and os.path.exists(chart_path):
            y = self.get_y()
            # خلفية الرسم
            self.set_fill_color(255, 255, 255)
            self.set_draw_color(226, 232, 240)
            self.rect(10, y, 190, 84, 'DF')
            try:
                self.image(chart_path, x=12, y=y + 2, w=186, h=80)
            except Exception as e:
                print(f"Error embedding chart in PDF: {e}")
            self.set_y(y + 88)

    def draw_table_section(self, headers, rows, col_widths, total_row=None):
        """رسم جدول البيانات التفصيلي"""
        self.set_fill_color(27, 54, 93)
        self.set_text_color(255, 255, 255)
        self.set_font('Amiri', 'B', 9.5)

        y = self.get_y()
        self.set_xy(10, y)

        for w, h in zip(col_widths, headers):
            self.cell(w, 8, format_arabic(h), 1, 0, 'C', True)
        self.ln()

        self.set_font('Amiri', '', 9)
        self.set_draw_color(226, 232, 240)

        for idx, row in enumerate(rows):
            # التأكد من عدم تجاوز الصفحة
            if self.get_y() > 240:
                self.add_page()
                self.set_fill_color(27, 54, 93)
                self.set_text_color(255, 255, 255)
                self.set_font('Amiri', 'B', 9.5)
                for w, h in zip(col_widths, headers):
                    self.cell(w, 8, format_arabic(h), 1, 0, 'C', True)
                self.ln()
                self.set_font('Amiri', '', 9)

            if idx % 2 == 0:
                self.set_fill_color(248, 250, 252)
            else:
                self.set_fill_color(255, 255, 255)

            self.set_text_color(15, 23, 42)
            for c_idx, (w, val) in enumerate(zip(col_widths, row)):
                align = 'R' if c_idx == len(row) - 1 or 'ريال' in str(val) or str(val).replace(',', '').replace('.', '').isdigit() else 'C'
                self.cell(w, 7.5, format_arabic(str(val)), 1, 0, align, True)
            self.ln()

        if total_row:
            self.set_fill_color(241, 245, 249)
            self.set_text_color(27, 54, 93)
            self.set_font('Amiri', 'B', 10)
            first_w = sum(col_widths[:-1])
            self.cell(first_w, 8.5, format_arabic(total_row[0]), 1, 0, 'C', True)
            self.set_text_color(185, 28, 28)
            self.cell(col_widths[-1], 8.5, format_arabic(str(total_row[1])), 1, 1, 'R', True)

    def draw_report_footer(self):
        """تذييل التقرير والتواقيع الرسمية"""
        y = max(self.get_y() + 6, 238)
        if y > 245:
            self.add_page()
            y = 238

        sig_boxes = [("المسؤول المالي / المحاسب", "التوقيع: ....................."),
                     ("المراجعة والتدقيق الداخلي", "التوقيع: ....................."),
                     ("المدير العام / الاعتماد", "الختم والاعتماد: ................")]
        
        for i, (title, note) in enumerate(sig_boxes):
            bx = 12 + (i * 63)
            self.set_draw_color(203, 213, 225)
            self.set_fill_color(248, 250, 252)
            self.rect(bx, y, 58, 20, 'DF')
            self.set_fill_color(27, 54, 93)
            self.rect(bx, y, 58, 2, 'F')

            self.set_xy(bx, y + 3)
            self.set_font('Amiri', 'B', 9)
            self.set_text_color(27, 54, 93)
            self.cell(58, 4.5, format_arabic(title), 0, 1, 'C')

            self.set_xy(bx, y + 9.5)
            self.set_font('Amiri', '', 8)
            self.set_text_color(100, 116, 139)
            self.cell(58, 5, format_arabic(note), 0, 1, 'C')

        self.set_xy(10, 268)
        self.set_font('Amiri', '', 8.5)
        self.set_text_color(100, 116, 139)
        self.cell(190, 5, format_arabic("وثيقة إدارية صادرة إلكترونياً من نظام فواتيري لإدارة الحسابات والمشاريع"), 0, 1, 'C')


class ReportsModule:
    """وحدة التقارير والإحصائيات الحديثة"""
    def __init__(self, notebook, status_callback, invoice_module, employees_module, transactions_module, projects_module):
        self.db = Database()
        self.status_callback = status_callback
        self.invoice_module = invoice_module
        self.employees_module = employees_module
        self.transactions_module = transactions_module
        self.projects_module = projects_module
        
        self.current_report_data = {}
        self.current_chart_fig = None
        
        self.frame = ttk.Frame(notebook)
        self.create_widgets()
        self.update_date_ranges()
        
        # إنشاء التقرير المالي الافتراضي بعد إعداد الواجهة
        self.frame.after(100, self.generate_report)

    def create_widgets(self):
        """بناء واجهة التقارير الحديثة"""
        main_container = ttk.Frame(self.frame, padding=15)
        main_container.pack(fill='both', expand=True)

        # 1. شريط التحكم والبحث بالأعلى
        control_card = ttk.LabelFrame(main_container, text="📊 إعدادات واستخراج التقرير", padding=12)
        control_card.pack(fill='x', pady=(0, 10))

        # نوع التقرير
        ttk.Label(control_card, text="نوع التقرير:", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=(10, 5))
        report_types = [
            "التقرير المالي الشامل",
            "تحليل الإيرادات والمصروفات",
            "ملخص أداء المشاريع",
            "تقرير الموظفين والرواتب",
            "تقرير العملاء والمبيعات",
            "تقرير يومي",
            "تقرير أسبوعي",
            "تقرير شهري",
            "تقرير سنوي",
            "تقرير مخصص"
        ]
        self.report_type = ttk.Combobox(control_card, values=report_types, state='readonly', font=('Segoe UI', 10), width=24)
        self.report_type.current(0)
        self.report_type.pack(side='right', padx=5)
        self.report_type.bind('<<ComboboxSelected>>', self.update_date_ranges)

        # التواريخ
        ttk.Label(control_card, text="من:", font=('Segoe UI', 10)).pack(side='right', padx=(15, 3))
        if HAS_TKCALENDAR:
            self.from_date = DateEntry(control_card, width=11, font=('Segoe UI', 10), date_pattern='yyyy-mm-dd')
        else:
            self.from_date = ttk.Entry(control_card, width=12, font=('Segoe UI', 10))
        self.from_date.pack(side='right', padx=4)

        ttk.Label(control_card, text="إلى:", font=('Segoe UI', 10)).pack(side='right', padx=(10, 3))
        if HAS_TKCALENDAR:
            self.to_date = DateEntry(control_card, width=11, font=('Segoe UI', 10), date_pattern='yyyy-mm-dd')
        else:
            self.to_date = ttk.Entry(control_card, width=12, font=('Segoe UI', 10))
        self.to_date.pack(side='right', padx=4)

        # أزرار الإجراءات
        btn_box = ttk.Frame(control_card)
        btn_box.pack(side='left', padx=5)

        ttk.Button(btn_box, text="⚡ عرض التقرير", command=self.generate_report, width=14).pack(side='left', padx=4)
        ttk.Button(btn_box, text="🖨️ طباعة PDF احترافي", command=self.print_report, width=18).pack(side='left', padx=4)
        ttk.Button(btn_box, text="📥 تصدير Excel", command=self.export_report, width=14).pack(side='left', padx=4)

        # 2. شريط بطاقات المؤشرات الرئيسية (KPIs)
        self.kpi_frame = ttk.Frame(main_container)
        self.kpi_frame.pack(fill='x', pady=(0, 10))
        self.kpi_labels = {}
        self.build_kpi_cards()

        # 3. تبويبات النتائج (لوحة المؤشرات والرسوم البيانية / التقرير التفصيلي)
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill='both', expand=True)

        # تبويب لوحة الرسوم البيانية والجداول
        self.dashboard_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_tab, text="📊 لوحة المؤشرات والرسوم البيانية")

        # تقسيم التبويب إلى نصفين (رسم بياني بالأعلى وجدول بالأسفل)
        self.chart_container = ttk.Frame(self.dashboard_tab)
        self.chart_container.pack(fill='both', expand=True, padx=5, pady=5)

        self.table_container = ttk.LabelFrame(self.dashboard_tab, text="📋 جدول البيانات التحليلي", padding=8)
        self.table_container.pack(fill='both', expand=True, padx=5, pady=(0, 5))

        self.tree = ttk.Treeview(self.table_container, show='headings', height=7)
        self.tree_scroll = ttk.Scrollbar(self.table_container, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scroll.set)
        self.tree.pack(side='left', fill='both', expand=True)
        self.tree_scroll.pack(side='right', fill='y')

        # تبويب التقرير النصي المفصل
        self.text_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.text_tab, text="📄 التقرير المفصل والملخص التنفيذي")

        text_scroll = ttk.Scrollbar(self.text_tab)
        text_scroll.pack(side='right', fill='y')
        self.result_text = tk.Text(self.text_tab, wrap='word', font=('Segoe UI', 11), yscrollcommand=text_scroll.set, padx=15, pady=15)
        self.result_text.pack(fill='both', expand=True)
        text_scroll.config(command=self.result_text.yview)

        # تكوين تنسيقات النصوص بمحاذاة لليمين لمنع تشقلب الكلمات والنقاط
        self.result_text.tag_configure('right', justify='right')
        self.result_text.tag_configure('h1', font=('Segoe UI', 15, 'bold'), foreground='#1B365D', spacing3=8, justify='right')
        self.result_text.tag_configure('h2', font=('Segoe UI', 12, 'bold'), foreground='#2E5B88', spacing1=10, spacing3=5, justify='right')
        self.result_text.tag_configure('metric_green', font=('Segoe UI', 11, 'bold'), foreground='#10B981', justify='right')
        self.result_text.tag_configure('metric_red', font=('Segoe UI', 11, 'bold'), foreground='#EF4444', justify='right')
        self.result_text.tag_configure('bold', font=('Segoe UI', 11, 'bold'), foreground='#1E293B', justify='right')
        self.result_text.tag_configure('normal', font=('Segoe UI', 11), foreground='#334155', spacing1=3, justify='right')

    def build_kpi_cards(self):
        """إنشاء بطاقات المؤشرات الأنيقة"""
        for w in self.kpi_frame.winfo_children():
            w.destroy()

        cards_spec = [
            ('income', '💵 إجمالي الإيرادات', '#10B981', '0.00 ر.س'),
            ('expense', '💸 إجمالي المصروفات', '#EF4444', '0.00 ر.س'),
            ('profit', '📈 صافي الأرباح', '#6366F1', '0.00 ر.س'),
            ('margin', '🎯 نسبة الربحية', '#F59E0B', '0.0%'),
            ('count', '🧾 العمليات / الفواتير', '#0284C7', '0 عملية')
        ]

        for key, title, color, default_val in cards_spec:
            card = tk.Frame(self.kpi_frame, bg='white', highlightbackground='#E2E8F0', highlightthickness=1)
            card.pack(side='right', fill='both', expand=True, padx=4)

            top_bar = tk.Frame(card, bg=color, height=3)
            top_bar.pack(fill='x')

            tk.Label(card, text=title, font=('Segoe UI', 9, 'bold'), fg='#64748B', bg='white').pack(pady=(6, 2))
            val_lbl = tk.Label(card, text=default_val, font=('Segoe UI', 13, 'bold'), fg=color, bg='white')
            val_lbl.pack(pady=(0, 8))
            self.kpi_labels[key] = val_lbl

    def update_date_ranges(self, event=None):
        """تحديث النطاق الزمني حسب نوع التقرير المختار"""
        today = datetime.now().date()
        rtype = self.report_type.get()

        if rtype == "تقرير يومي":
            self.set_dates(today, today)
        elif rtype == "تقرير أسبوعي":
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            self.set_dates(start, end)
        elif rtype == "تقرير شهري":
            first_day = today.replace(day=1)
            last_day_num = calendar.monthrange(today.year, today.month)[1]
            last_day = today.replace(day=last_day_num)
            self.set_dates(first_day, last_day)
        elif rtype == "تقرير سنوي":
            self.set_dates(today.replace(month=1, day=1), today.replace(month=12, day=31))
        elif rtype in ["التقرير المالي الشامل", "تحليل الإيرادات والمصروفات", "ملخص أداء المشاريع", "تقرير الموظفين والرواتب", "تقرير العملاء والمبيعات"]:
            # افتراضياً بداية الشهر الحالي إلى اليوم
            first_day = today.replace(day=1)
            self.set_dates(first_day, today)

    def set_dates(self, start, end):
        try:
            self.from_date.delete(0, tk.END)
            self.from_date.insert(0, start.strftime('%Y-%m-%d'))
            self.to_date.delete(0, tk.END)
            self.to_date.insert(0, end.strftime('%Y-%m-%d'))
        except Exception:
            pass

    def load_reports(self):
        """تحديث بيانات التقارير تلقائياً عند طلب التحديث المركزي أو تعديل البيانات"""
        try:
            self.generate_report()
        except Exception as e:
            print(f"Error in load_reports: {e}")

    def generate_report(self):
        """توليد التقرير المختار وتحديث كافة الرسوم والجداول والملخصات"""
        rtype = self.report_type.get()
        f_date = self.from_date.get().strip()
        t_date = self.to_date.get().strip()

        if not f_date or not t_date:
            messagebox.showwarning("تنبيه", "⚠️ يرجى تحديد تاريخ البداية والنهاية")
            return

        try:
            self.current_report_data = {
                'title': rtype,
                'from_date': f_date,
                'to_date': t_date,
                'kpis': [],
                'headers': [],
                'rows': [],
                'col_widths': [],
                'total_row': None,
                'chart_fig': None
            }

            if rtype in ["التقرير المالي الشامل", "تقرير يومي", "تقرير أسبوعي", "تقرير شهري", "تقرير سنوي", "تقرير مخصص"]:
                self._load_financial_report_data(f_date, t_date, rtype)
            elif rtype == "تحليل الإيرادات والمصروفات":
                self._load_income_expense_analysis_data(f_date, t_date)
            elif rtype == "ملخص أداء المشاريع":
                self._load_projects_report_data(f_date, t_date)
            elif rtype == "تقرير الموظفين والرواتب":
                self._load_employees_report_data(f_date, t_date)
            elif rtype == "تقرير العملاء والمبيعات":
                self._load_customers_report_data(f_date, t_date)

            self.render_report_view()
            self.status_callback(f"✅ تم استخراج التقرير: {rtype}")
        except Exception as e:
            messagebox.showerror("خطأ في التقرير", f"❌ فشل في إعداد التقرير: {str(e)}")

    def _load_financial_report_data(self, f_date, t_date, title):
        """تحميل بيانات التقرير المالي الشامل"""
        # الإيرادات من المعاملات والصندوق
        income_res = self.db.execute_query(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'income' AND date BETWEEN ? AND ?",
            (f_date, t_date)
        )
        income = float(income_res[0][0]) if income_res and income_res[0] else 0.0

        # المصروفات
        expense_res = self.db.execute_query(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'expense' AND date BETWEEN ? AND ?",
            (f_date, t_date)
        )
        expense = float(expense_res[0][0]) if expense_res and expense_res[0] else 0.0

        # الفواتير
        inv_count_res = self.db.execute_query("SELECT COUNT(*), COALESCE(SUM(grand_total), 0) FROM invoices WHERE date BETWEEN ? AND ?", (f_date, t_date))
        inv_count = inv_count_res[0][0] if inv_count_res and inv_count_res[0] else 0
        inv_total = float(inv_count_res[0][1]) if inv_count_res and inv_count_res[0] else 0.0

        profit = income - expense
        margin = (profit / income * 100) if income > 0 else 0.0

        # تحديث بيانات المؤشرات
        self.current_report_data['kpis'] = [
            ("إجمالي الإيرادات", f"{income:,.2f} ر.س", (16, 185, 129)),
            ("إجمالي المصروفات", f"{expense:,.2f} ر.س", (239, 68, 68)),
            ("صافي الأرباح", f"{profit:,.2f} ر.س", (99, 102, 241) if profit >= 0 else (225, 29, 72)),
            ("نسبة الربحية", f"{margin:.1f}%", (245, 158, 11)),
        ]

        self.kpi_labels['income'].config(text=f"{income:,.2f} ر.س")
        self.kpi_labels['expense'].config(text=f"{expense:,.2f} ر.س")
        self.kpi_labels['profit'].config(text=f"{profit:,.2f} ر.س", fg='#10B981' if profit >= 0 else '#EF4444')
        self.kpi_labels['margin'].config(text=f"{margin:.1f}%")
        self.kpi_labels['count'].config(text=f"{inv_count} فواتير ({inv_total:,.0f} ر.س)")

        # استخراج توزيع المصروفات حسب الفئات
        categories_data = self.db.execute_query('''
            SELECT COALESCE(category, 'عام'), SUM(amount) as total
            FROM transactions
            WHERE date BETWEEN ? AND ? AND type = 'expense'
            GROUP BY category
            ORDER BY total DESC
        ''', (f_date, t_date))

        headers = ['الفئة / البند', 'عدد العمليات', 'المبلغ الإجمالي (ر.س)', 'النسبة المئوية']
        col_widths = [60, 35, 55, 40]
        rows = []
        for cat, amt in categories_data:
            pct = (amt / expense * 100) if expense > 0 else 0
            cnt_res = self.db.execute_query("SELECT COUNT(*) FROM transactions WHERE date BETWEEN ? AND ? AND type='expense' AND category=?", (f_date, t_date, cat))
            cnt = cnt_res[0][0] if cnt_res else 1
            rows.append([cat, f"{cnt} عملية", f"{amt:,.2f}", f"{pct:.1f}%"])

        self.current_report_data['headers'] = headers
        self.current_report_data['rows'] = rows
        self.current_report_data['col_widths'] = col_widths
        self.current_report_data['total_row'] = ('الإجمالي الكلي للمصروفات', f"{expense:,.2f} ر.س")

        # إنشاء الرسم البياني المزدوج (بار شهري + دونات فئات)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.8), dpi=100)
        fig.patch.set_facecolor('#FFFFFF')

        # 1. رسم مقارنة الإيرادات والمصروفات
        cats = [format_chart_arabic('الإيرادات'), format_chart_arabic('المصروفات'), format_chart_arabic('صافي الربح')]
        vals = [income, expense, profit]
        colors = ['#10B981', '#EF4444', '#6366F1' if profit >= 0 else '#DC2626']
        bars = ax1.bar(cats, vals, color=colors, width=0.55, edgecolor='#CBD5E1', linewidth=0.8)
        ax1.set_title(format_chart_arabic('الأداء المالي الإجمالي (ر.س)'), fontsize=11, fontweight='bold', color='#1E293B', pad=10)
        ax1.grid(axis='y', linestyle='--', alpha=0.3)
        for b, v in zip(bars, vals):
            y_pos = b.get_height()
            ax1.text(b.get_x() + b.get_width()/2., y_pos + (max(vals)*0.02 if max(vals)>0 else 10),
                     f"{v:,.0f}", ha='center', va='bottom', fontsize=9, fontweight='bold', color='#334155')

        # 2. رسم دائري لفئات المصروفات
        if categories_data:
            cat_labels = [format_chart_arabic(c[0]) for c in categories_data[:5]]
            cat_amts = [c[1] for c in categories_data[:5]]
            pie_colors = ['#6366F1', '#EC4899', '#F59E0B', '#10B981', '#06B6D4']
            ax2.pie(cat_amts, labels=cat_labels, autopct='%1.1f%%', colors=pie_colors[:len(cat_amts)],
                    startangle=140, textprops={'fontsize': 8.5, 'color': '#1E293B'},
                    wedgeprops={'edgecolor': 'white', 'linewidth': 1.5, 'width': 0.6})
            ax2.set_title(format_chart_arabic('أعلى بنود المصروفات'), fontsize=11, fontweight='bold', color='#1E293B', pad=10)
        else:
            ax2.text(0.5, 0.5, format_chart_arabic('لا توجد مصروفات مسجلة'), ha='center', va='center', color='#94A3B8')
            ax2.axis('off')

        plt.tight_layout()
        self.current_report_data['chart_fig'] = fig

        # إعداد النص المفصل
        text_content = [
            ('h1', f"📑 التقرير المالي التنفيذي الشامل\n"),
            ('normal', f"الفترة من {f_date} إلى {t_date}\n"),
            ('normal', "─" * 60 + "\n\n"),
            ('h2', "1. ملخص المؤشرات المالية الرئيسية:\n"),
            ('bold', f"• إجمالي الإيرادات المحققة: "), ('metric_green', f"{income:,.2f} ريال سعودي\n"),
            ('bold', f"• إجمالي المصروفات التشغيلية: "), ('metric_red', f"{expense:,.2f} ريال سعودي\n"),
            ('bold', f"• صافي الربح المحقق: "), ('metric_green' if profit >= 0 else 'metric_red', f"{profit:,.2f} ريال سعودي\n"),
            ('bold', f"• هامش الربحية العام: "), ('normal', f"{margin:.2f}%\n\n"),
            ('h2', "2. حركة الفواتير والمبيعات:\n"),
            ('normal', f"• عدد الفواتير الصادرة خلال الفترة: {inv_count} فاتورة\n"),
            ('normal', f"• إجمالي قيمة الفواتير: {inv_total:,.2f} ريال سعودي\n"),
            ('normal', f"• متوسط قيمة الفاتورة: {(inv_total/inv_count) if inv_count>0 else 0:,.2f} ريال سعودي\n\n"),
            ('h2', "3. تفاصيل بنود المصروفات:\n")
        ]
        for c, a in categories_data:
            pct = (a/expense*100) if expense>0 else 0
            text_content.append(('normal', f"  - {c}: {a:,.2f} ر.س ({pct:.1f}%)\n"))

        self.current_report_data['text_tokens'] = text_content

    def _load_income_expense_analysis_data(self, f_date, t_date):
        """تحليل متعمق للإيرادات والمصروفات حسب الشهور"""
        monthly_data = self.db.execute_query('''
            SELECT strftime('%Y-%m', date) as month, 
                   SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as inc,
                   SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as exp
            FROM transactions
            WHERE date BETWEEN ? AND ?
            GROUP BY strftime('%Y-%m', date)
            ORDER BY month
        ''', (f_date, t_date))

        total_inc = sum(row[1] for row in monthly_data) if monthly_data else 0.0
        total_exp = sum(row[2] for row in monthly_data) if monthly_data else 0.0
        net = total_inc - total_exp

        self.kpi_labels['income'].config(text=f"{total_inc:,.2f} ر.س")
        self.kpi_labels['expense'].config(text=f"{total_exp:,.2f} ر.س")
        self.kpi_labels['profit'].config(text=f"{net:,.2f} ر.س", fg='#10B981' if net>=0 else '#EF4444')
        self.kpi_labels['margin'].config(text=f"{(net/total_inc*100) if total_inc>0 else 0:.1f}%")
        self.kpi_labels['count'].config(text=f"{len(monthly_data)} شهور")

        headers = ['الشهر', 'الإيرادات (ر.س)', 'المصروفات (ر.س)', 'صافي الشهر (ر.س)', 'نسبة الإنجاز']
        col_widths = [40, 45, 45, 45, 25]
        rows = []
        for m, i, e in monthly_data:
            diff = i - e
            pct = f"{(diff/i*100):.1f}%" if i>0 else "0%"
            rows.append([m, f"{i:,.2f}", f"{e:,.2f}", f"{diff:,.2f}", pct])

        self.current_report_data['kpis'] = [
            ("إجمالي الإيرادات", f"{total_inc:,.2f} ر.س", (16, 185, 129)),
            ("إجمالي المصروفات", f"{total_exp:,.2f} ر.س", (239, 68, 68)),
            ("صافي الفترة", f"{net:,.2f} ر.س", (99, 102, 241)),
            ("عدد الأشهر", str(len(monthly_data)), (245, 158, 11)),
        ]
        self.current_report_data['headers'] = headers
        self.current_report_data['rows'] = rows
        self.current_report_data['col_widths'] = col_widths
        self.current_report_data['total_row'] = ('المجموع العام', f"{net:,.2f} ر.س")

        # الرسم البياني
        fig, ax = plt.subplots(figsize=(10, 3.8), dpi=100)
        fig.patch.set_facecolor('#FFFFFF')
        if monthly_data:
            import numpy as np
            months = [r[0] for r in monthly_data]
            incs = [r[1] for r in monthly_data]
            exps = [r[2] for r in monthly_data]
            x = np.arange(len(months))
            width = 0.35
            ax.bar(x - width/2, incs, width, label=format_chart_arabic('الإيرادات'), color='#10B981')
            ax.bar(x + width/2, exps, width, label=format_chart_arabic('المصروفات'), color='#EF4444')
            ax.set_xticks(x)
            ax.set_xticklabels([format_chart_arabic(m) for m in months], rotation=25)
            ax.legend(prop={'size': 9})
            ax.grid(axis='y', linestyle='--', alpha=0.3)
            ax.set_title(format_chart_arabic('المقارنة الشهرية للإيرادات والمصروفات'), fontsize=12, fontweight='bold', color='#1E293B')
        else:
            ax.text(0.5, 0.5, format_chart_arabic('لا توجد بيانات متاحة في هذه الفترة'), ha='center', va='center')
        plt.tight_layout()
        self.current_report_data['chart_fig'] = fig

        text_content = [
            ('h1', "📊 تحليل ومقارنة الإيرادات والمصروفات الدورية\n"),
            ('normal', f"الفترة من {f_date} إلى {t_date}\n\n"),
            ('bold', f"• إجمالي إيرادات الفترة: {total_inc:,.2f} ر.س\n"),
            ('bold', f"• إجمالي مصروفات الفترة: {total_exp:,.2f} ر.س\n"),
            ('bold', f"• الصافي العام المحقق: {net:,.2f} ر.س\n\n"),
            ('h2', "البيان الشهري التفصيلي:\n")
        ]
        for r in rows:
            text_content.append(('normal', f"• شهر {r[0]}: إيرادات {r[1]} ر.س | مصروفات {r[2]} ر.س | صافي {r[3]} ر.س\n"))
        self.current_report_data['text_tokens'] = text_content

    def _load_projects_report_data(self, f_date, t_date):
        """تحميل ملخص أداء المشاريع"""
        projects = self.db.execute_query(
            "SELECT id, name, start_date, end_date, budget, status FROM projects WHERE start_date <= ? AND (end_date IS NULL OR end_date >= ?)",
            (t_date, f_date)
        )
        headers = ['المشروع', 'الحالة', 'الميزانية (ر.س)', 'الإيرادات (ر.س)', 'المصروفات (ر.س)', 'صافي الربح']
        col_widths = [45, 25, 35, 35, 35, 35]
        rows = []
        tot_b = 0.0
        tot_i = 0.0
        tot_e = 0.0

        for p in projects:
            pid, name, sdate, edate, budget, status = p
            budget = budget or 0.0
            inc = float(self.db.execute_query("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='income' AND project_id=? AND date BETWEEN ? AND ?", (pid, f_date, t_date))[0][0])
            exp = float(self.db.execute_query("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='expense' AND project_id=? AND date BETWEEN ? AND ?", (pid, f_date, t_date))[0][0])
            profit = inc - exp
            tot_b += budget
            tot_i += inc
            tot_e += exp
            rows.append([name, status or 'ساري', f"{budget:,.2f}", f"{inc:,.2f}", f"{exp:,.2f}", f"{profit:,.2f}"])

        tot_profit = tot_i - tot_e
        self.kpi_labels['income'].config(text=f"{tot_i:,.2f} ر.س")
        self.kpi_labels['expense'].config(text=f"{tot_e:,.2f} ر.س")
        self.kpi_labels['profit'].config(text=f"{tot_profit:,.2f} ر.س", fg='#10B981' if tot_profit>=0 else '#EF4444')
        self.kpi_labels['margin'].config(text=f"{len(projects)} مشاريع")
        self.kpi_labels['count'].config(text=f"ميزانيات: {tot_b:,.0f} ر.س")

        self.current_report_data['kpis'] = [
            ("إجمالي إيرادات المشاريع", f"{tot_i:,.2f} ر.س", (16, 185, 129)),
            ("إجمالي مصروفات المشاريع", f"{tot_e:,.2f} ر.س", (239, 68, 68)),
            ("أرباح المشاريع", f"{tot_profit:,.2f} ر.س", (99, 102, 241)),
            ("عدد المشاريع النشطة", str(len(projects)), (245, 158, 11)),
        ]
        self.current_report_data['headers'] = headers
        self.current_report_data['rows'] = rows
        self.current_report_data['col_widths'] = col_widths
        self.current_report_data['total_row'] = ('إجمالي أرباح المشاريع', f"{tot_profit:,.2f} ر.س")

        # الرسم البياني
        fig, ax = plt.subplots(figsize=(10, 3.8), dpi=100)
        fig.patch.set_facecolor('#FFFFFF')
        if projects:
            pnames = [format_chart_arabic(p[1][:15]) for p in projects[:6]]
            p_profits = [float(r[5].replace(',', '')) for r in rows[:6]]
            p_colors = ['#10B981' if x>=0 else '#EF4444' for x in p_profits]
            ax.barh(pnames, p_profits, color=p_colors, height=0.55)
            ax.set_title(format_chart_arabic('صافي أرباح أعلى المشاريع (ر.س)'), fontsize=12, fontweight='bold', color='#1E293B')
            ax.grid(axis='x', linestyle='--', alpha=0.3)
        else:
            ax.text(0.5, 0.5, format_chart_arabic('لا توجد مشاريع مسجلة في هذا النطاق'), ha='center', va='center')
        plt.tight_layout()
        self.current_report_data['chart_fig'] = fig

        text_content = [
            ('h1', "🏗️ تقرير تقييم وأداء المشاريع\n"),
            ('normal', f"الفترة من {f_date} إلى {t_date}\n\n"),
            ('bold', f"• عدد المشاريع قيد التنفيذ والمكتملة: {len(projects)}\n"),
            ('bold', f"• إجمالي ميزانيات المشاريع: {tot_b:,.2f} ر.س\n"),
            ('bold', f"• إجمالي الإيرادات المحصلة: {tot_i:,.2f} ر.س\n"),
            ('bold', f"• إجمالي المصروفات على المشاريع: {tot_e:,.2f} ر.س\n"),
            ('metric_green' if tot_profit>=0 else 'metric_red', f"• صافي أرباح المشاريع: {tot_profit:,.2f} ر.س\n\n"),
            ('h2', "بيان المشاريع التفصيلي:\n")
        ]
        for r in rows:
            text_content.append(('normal', f"• {r[0]} ({r[1]}): إيراد {r[3]} ر.س | صرف {r[4]} ر.س | ربح {r[5]} ر.س\n"))
        self.current_report_data['text_tokens'] = text_content

    def _load_employees_report_data(self, f_date, t_date):
        """تحميل تقرير الموظفين والرواتب"""
        employees = self.db.execute_query('''
            SELECT e.name, e.position, e.salary, COUNT(s.id) as cnt,
                   COALESCE(SUM(s.net_salary), 0) as paid
            FROM employees e
            LEFT JOIN salaries s ON e.id = s.employee_id AND s.month_year BETWEEN ? AND ?
            GROUP BY e.id, e.name, e.position, e.salary
            ORDER BY e.name
        ''', (f_date, t_date))

        headers = ['اسم الموظف', 'المسمى الوظيفي', 'الراتب الأساسي', 'رواتب مسددة', 'المجموع المدفوع']
        col_widths = [50, 45, 35, 30, 40]
        rows = []
        tot_sal = 0.0
        tot_paid = 0.0
        for emp in employees:
            name, pos, sal, cnt, paid = emp
            sal = sal or 0.0
            paid = paid or 0.0
            tot_sal += sal
            tot_paid += paid
            rows.append([name, pos or 'موظف', f"{sal:,.2f}", f"{cnt} أشهر", f"{paid:,.2f}"])

        self.kpi_labels['income'].config(text=f"{len(employees)} موظف")
        self.kpi_labels['expense'].config(text=f"{tot_sal:,.2f} ر.س")
        self.kpi_labels['profit'].config(text=f"{tot_paid:,.2f} ر.س", fg='#6366F1')
        self.kpi_labels['margin'].config(text=f"{(tot_paid/tot_sal*100) if tot_sal>0 else 0:.1f}% مسدد")
        self.kpi_labels['count'].config(text=f"رواتب: {tot_paid:,.0f} ر.س")

        self.current_report_data['kpis'] = [
            ("عدد الموظفين", str(len(employees)), (2, 132, 199)),
            ("إجمالي الرواتب الأساسية", f"{tot_sal:,.2f} ر.س", (245, 158, 11)),
            ("إجمالي المسدد فعلياً", f"{tot_paid:,.2f} ر.س", (16, 185, 129)),
            ("متوسط الراتب", f"{(tot_sal/len(employees)) if employees else 0:,.2f} ر.س", (99, 102, 241)),
        ]
        self.current_report_data['headers'] = headers
        self.current_report_data['rows'] = rows
        self.current_report_data['col_widths'] = col_widths
        self.current_report_data['total_row'] = ('إجمالي الرواتب والمسدد', f"{tot_paid:,.2f} ر.س")

        # رسم بياني
        fig, ax = plt.subplots(figsize=(10, 3.8), dpi=100)
        fig.patch.set_facecolor('#FFFFFF')
        if employees:
            enames = [format_chart_arabic(e[0][:12]) for e in employees[:7]]
            esals = [e[2] or 0.0 for e in employees[:7]]
            ax.bar(enames, esals, color='#0284C7', width=0.55)
            ax.set_title(format_chart_arabic('هيكل الرواتب الأساسية للموظفين (ر.س)'), fontsize=12, fontweight='bold', color='#1E293B')
            ax.grid(axis='y', linestyle='--', alpha=0.3)
        plt.tight_layout()
        self.current_report_data['chart_fig'] = fig

        text_content = [
            ('h1', "👥 تقرير شؤون الموظفين والرواتب والأجور\n"),
            ('normal', f"الفترة من {f_date} إلى {t_date}\n\n"),
            ('bold', f"• إجمالي عدد الكادر الوظيفي: {len(employees)} موظف\n"),
            ('bold', f"• إجمالي سلم الرواتب الشهري: {tot_sal:,.2f} ر.س\n"),
            ('bold', f"• إجمالي المبالغ المنصرفة فعلياً: {tot_paid:,.2f} ر.س\n\n"),
            ('h2', "كشف رواتب الموظفين:\n")
        ]
        for r in rows:
            text_content.append(('normal', f"• {r[0]} ({r[1]}): الراتب {r[2]} ر.س | المسدد {r[4]} ر.س\n"))
        self.current_report_data['text_tokens'] = text_content

    def _load_customers_report_data(self, f_date, t_date):
        """تحميل تقرير العملاء والمبيعات"""
        customers = self.db.execute_query('''
            SELECT c.name, c.tax_number, COUNT(i.id) as cnt,
                   COALESCE(SUM(i.grand_total), 0) as tot
            FROM customers c
            LEFT JOIN invoices i ON c.id = i.customer_id AND i.date BETWEEN ? AND ?
            GROUP BY c.id, c.name, c.tax_number
            ORDER BY tot DESC
        ''', (f_date, t_date))

        headers = ['اسم العميل', 'الرقم الضريبي', 'عدد الفواتير', 'إجمالي المشتريات (ر.س)']
        col_widths = [65, 45, 35, 55]
        rows = []
        tot_inv = 0
        tot_sales = 0.0
        for cust in customers:
            name, tax_no, cnt, tot = cust
            tot = tot or 0.0
            tot_inv += cnt
            tot_sales += tot
            rows.append([name, tax_no or '-', str(cnt), f"{tot:,.2f}"])

        self.kpi_labels['income'].config(text=f"{tot_sales:,.2f} ر.س")
        self.kpi_labels['expense'].config(text=f"{len(customers)} عميل")
        self.kpi_labels['profit'].config(text=f"{tot_inv} فاتورة", fg='#10B981')
        self.kpi_labels['margin'].config(text=f"{(tot_sales/len(customers)) if customers else 0:,.0f} ر.س/عميل")
        self.kpi_labels['count'].config(text=f"إجمالي: {tot_sales:,.0f} ر.س")

        self.current_report_data['kpis'] = [
            ("إجمالي المبيعات للعملاء", f"{tot_sales:,.2f} ر.س", (16, 185, 129)),
            ("عدد العملاء المتعاملين", str(len(customers)), (2, 132, 199)),
            ("إجمالي عدد الفواتير", str(tot_inv), (99, 102, 241)),
            ("متوسط قيمة العميل", f"{(tot_sales/len(customers)) if customers else 0:,.2f} ر.س", (245, 158, 11)),
        ]
        self.current_report_data['headers'] = headers
        self.current_report_data['rows'] = rows
        self.current_report_data['col_widths'] = col_widths
        self.current_report_data['total_row'] = ('إجمالي مبيعات العملاء', f"{tot_sales:,.2f} ر.س")

        # الرسم البياني
        fig, ax = plt.subplots(figsize=(10, 3.8), dpi=100)
        fig.patch.set_facecolor('#FFFFFF')
        top_custs = [c for c in customers if c[3] > 0][:5]
        if top_custs:
            cnames = [format_chart_arabic(c[0][:14]) for c in top_custs]
            camts = [c[3] for c in top_custs]
            ax.bar(cnames, camts, color='#6366F1', width=0.55)
            ax.set_title(format_chart_arabic('أعلى العملاء من حيث حجم المشتريات (ر.س)'), fontsize=12, fontweight='bold', color='#1E293B')
            ax.grid(axis='y', linestyle='--', alpha=0.3)
        else:
            ax.text(0.5, 0.5, format_chart_arabic('لا توجد مشتريات مسجلة للعملاء في هذه الفترة'), ha='center', va='center')
        plt.tight_layout()
        self.current_report_data['chart_fig'] = fig

        text_content = [
            ('h1', "🤝 تقرير العملاء والمبيعات الشامل\n"),
            ('normal', f"الفترة من {f_date} إلى {t_date}\n\n"),
            ('bold', f"• إجمالي عدد العملاء: {len(customers)}\n"),
            ('bold', f"• إجمالي الفواتير الصادرة: {tot_inv} فاتورة\n"),
            ('metric_green', f"• إجمالي المبيعات المحققة: {tot_sales:,.2f} ريال سعودي\n\n"),
            ('h2', "كشف تفاصيل العملاء:\n")
        ]
        for r in rows:
            text_content.append(('normal', f"• {r[0]}: {r[2]} فواتير | مشتريات {r[3]} ر.س\n"))
        self.current_report_data['text_tokens'] = text_content

    def render_report_view(self):
        """تحديث الواجهة بالرسم البياني والجدول والنص المفصل"""
        # 1. تحديث الرسم البياني
        for w in self.chart_container.winfo_children():
            w.destroy()

        fig = self.current_report_data.get('chart_fig')
        if fig:
            self.current_chart_fig = fig
            canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
            canvas.draw()
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill='both', expand=True)
            # منع التمرير اللانهائي على الرسوم البيانية لتثبيتها وحمايتها من الانجراف
            canvas_widget._no_scroll = True
            canvas_widget._is_matplotlib = True
            canvas_widget.bind('<MouseWheel>', lambda e: "break")

        # 2. تحديث جدول البيانات
        self.tree.delete(*self.tree.get_children())
        headers = self.current_report_data.get('headers', [])
        rows = self.current_report_data.get('rows', [])

        self.tree['columns'] = headers
        for h in headers:
            self.tree.heading(h, text=h, anchor='center')
            self.tree.column(h, width=150, anchor='center')

        for r in rows:
            self.tree.insert('', 'end', values=r)

        # 3. تحديث النص المفصل بمحاذاة لليمين لمنع قلب النص
        self.result_text.config(state='normal')
        self.result_text.delete(1.0, tk.END)
        tokens = self.current_report_data.get('text_tokens', [])
        for tag, txt in tokens:
            self.result_text.insert(tk.END, txt, (tag, 'right'))
        self.result_text.tag_add('right', '1.0', tk.END)
        self.result_text.config(state='disabled')

    def print_report(self):
        """توليد ملف PDF احترافي فائق الدقة وفتحه مباشرة للطباعة"""
        try:
            if not self.current_report_data:
                self.generate_report()

            rtype = self.current_report_data.get('title', 'تقرير مالي')
            f_date = self.current_report_data.get('from_date', '')
            t_date = self.current_report_data.get('to_date', '')

            # حفظ الرسم البياني لصورة مؤقتة لتضمينه في الـ PDF
            temp_chart_path = None
            if self.current_chart_fig:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                self.current_chart_fig.savefig(tmp.name, dpi=200, bbox_inches='tight', facecolor='white')
                tmp.close()
                temp_chart_path = tmp.name

            # إعداد مجلد الحفظ
            out_dir = 'Invoices' if os.path.exists('Invoices') else '.'
            safe_name = rtype.replace(' ', '_').replace('/', '_')
            filename = os.path.join(out_dir, f"report_{safe_name}_{f_date}_{t_date}.pdf")

            # استرجاع إعدادات الشركة
            co_settings = get_company_settings(self.db)

            # إنشاء كائن PDF
            pdf = ExecutiveReportPDF(co_settings)
            pdf.add_page()
            pdf.draw_report_header(rtype, f_date, t_date)

            # رسم بطاقات المؤشرات
            kpis = self.current_report_data.get('kpis', [])
            if kpis:
                pdf.draw_kpi_cards(kpis)

            # رسم المخطط البياني
            if temp_chart_path and os.path.exists(temp_chart_path):
                pdf.draw_chart_image(temp_chart_path)
                try:
                    os.unlink(temp_chart_path)
                except Exception:
                    pass

            # رسم جدول البيانات
            headers = self.current_report_data.get('headers', [])
            rows = self.current_report_data.get('rows', [])
            col_widths = self.current_report_data.get('col_widths', [])
            tot_row = self.current_report_data.get('total_row')

            if headers and rows:
                pdf.draw_table_section(headers, rows, col_widths, tot_row)

            # رسم التذييل والتواقيع
            pdf.draw_report_footer()

            # حفظ الملف
            pdf.output(filename)

            if os.path.exists(filename):
                try:
                    webbrowser.open(f"file://{os.path.abspath(filename)}")
                except Exception:
                    os.startfile(os.path.abspath(filename))
                messagebox.showinfo("نجاح الطباعة", f"✅ تم تجهيز التقرير التنفيذي بصيغة PDF بنجاح!\nالمسار: {filename}")
            else:
                messagebox.showerror("خطأ", "❌ تعذر حفظ ملف PDF")

        except Exception as e:
            messagebox.showerror("خطأ في الطباعة", f"❌ فشل في إنشاء ملف PDF للتقرير: {str(e)}")

    def export_report(self):
        """تصدير التقرير كملف Excel منسق"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="حفظ التقرير كملف Excel"
            )
            if not filename:
                return

            headers = self.current_report_data.get('headers', [])
            rows = self.current_report_data.get('rows', [])

            if not headers or not rows:
                messagebox.showwarning("تنبيه", "⚠️ لا توجد بيانات لتصديرها")
                return

            df = pd.DataFrame(rows, columns=headers)
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='بيانات التقرير', index=False)

            messagebox.showinfo("نجاح التصدير", f"✅ تم تصدير التقرير بنجاح إلى:\n{filename}")

        except Exception as e:
            messagebox.showerror("خطأ في التصدير", f"❌ فشل في تصدير التقرير: {str(e)}")