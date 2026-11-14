import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import simpledialog, filedialog
from datetime import datetime, timedelta
from database import Database
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
import os
import sys
from calendar import monthcalendar
import calendar
from central_refresh import emit_account_items_change

def get_font_path(font_name):
    """الحصول على مسار الخط - يعمل في التطوير وفي EXE بمرونة كاملة"""
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
            
    # Fallback to font_name
    return font_name

# استيراد مكتبات العربية
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    def ar(text):
        """تحويل النص العربي للعرض الصحيح"""
        if not text:
            return text
        reshaped_text = arabic_reshaper.reshape(text)
        return get_display(reshaped_text)
except ImportError:
    print("⚠️ يرجى تثبيت مكتبات العربية: pip install arabic-reshaper python-bidi")
    def ar(text):
        """دالة بديلة إذا لم تكن المكتبات مثبتة"""
        return text

class CalendarDialog:
    """نافذة تقويم مخصصة"""
    def __init__(self, parent, date_str=None):
        self.parent = parent
        self.result = None
        
        # تحليل التاريخ الحالي
        if date_str:
            try:
                self.date = datetime.strptime(date_str, '%Y-%m-%d')
            except:
                self.date = datetime.now()
        else:
            self.date = datetime.now()
        
        self.year = self.date.year
        self.month = self.date.month
        
        self.create_dialog()
    
    def create_scrollable_content(self):
        """إنشاء محتوى قابل للتمرير"""
        # إنشاء إطار رئيسي للتمرير
        self.scroll_frame = ttk.Frame(self.dialog)
        self.scroll_frame.pack(fill='both', expand=True)
        
        # إنشاء Canvas للتمرير
        self.canvas = tk.Canvas(self.scroll_frame)
        self.canvas.pack(side='left', fill='both', expand=True)
        
        # إنشاء شريط تمرير عمودي
        scrollbar = ttk.Scrollbar(self.scroll_frame, orient='vertical', command=self.canvas.yview)
        scrollbar.pack(side='right', fill='y')
        
        # ربط Canvas مع شريط التمرير
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # إنشاء إطار المحتوى الفعلي
        self.content_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor='nw')
        
        # تحديث حجم التمرير عند تغيير المحتوى
        self.content_frame.bind('<Configure>', self.on_frame_configure)
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        # تفعيل التمرير بالعجلة من أي مكان في النافذة
        self.dialog.bind('<MouseWheel>', self.on_mousewheel)
        self.canvas.bind('<MouseWheel>', self.on_mousewheel)
        self.content_frame.bind('<MouseWheel>', self.on_mousewheel)
        
        # تفعيل التمرير لجميع العناصر الفرعية
        self.bind_mousewheel_recursively(self.content_frame)
    
    def bind_mousewheel_recursively(self, widget):
        """ربط تمرير العجلة بشكل متكرر لجميع العناصر الفرعية"""
        widget.bind('<MouseWheel>', self.on_mousewheel)
        for child in widget.winfo_children():
            self.bind_mousewheel_recursively(child)
    
    def on_frame_configure(self, event):
        """تحديث منطقة التمرير عند تغيير حجم الإطار"""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def on_canvas_configure(self, event):
        """تحديث عرض الإطار عند تغيير حجم Canvas"""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def on_mousewheel(self, event):
        """معالجة تمرير العجلة من أي مكان في النافذة"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
    
    def create_dialog(self):
        """إنشاء نافذة التقويم"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("اختر التاريخ")
        self.dialog.geometry("400x400")  # تكبير النافذة أكثر جداً
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # إنشاء ScrollArea للنافذة
        self.create_scrollable_content()
        
        # إطار التاريخ
        date_frame = ttk.Frame(self.dialog)
        date_frame.pack(fill='x', padx=12, pady=10)
        
        # أزرار التنقل في الشهور
        ttk.Button(date_frame, text="◀", command=self.prev_month, width=3).pack(side='right', padx=2)
        ttk.Button(date_frame, text="▶", command=self.next_month, width=3).pack(side='right', padx=2)
        
        # اسم الشهر والسنة
        self.month_label = ttk.Label(date_frame, text="", font=('Segoe UI', 11, 'bold'))
        self.month_label.pack(side='right', padx=10)
        
        self.update_month_label()
        
        # إطار التقويم
        cal_frame = ttk.Frame(self.dialog)
        cal_frame.pack(fill='both', expand=True, padx=12, pady=8)
        
        # أيام الأسبوع - ترتيب صحيح يتطابق مع monthcalendar (الأحد أول يوم)
        days = ['ح', 'ن', 'ث', 'أ', 'خ', 'ج', 'س']  # أيام الأسبوع بالعربية (الأحد أول يوم)
        for i, day in enumerate(days):
            ttk.Label(cal_frame, text=day, font=('Segoe UI', 9, 'bold')).grid(row=0, column=i, padx=2, pady=2)
        
        # أيام الشهر
        self.cal_buttons = {}
        cal_data = monthcalendar(self.year, self.month)
        
        # الحصول على أول يوم في الشهر والأسبوع الذي يبدأ فيه
        first_day = datetime(self.year, self.month, 1)
        # تحديد يوم الأسبوع (0=الأحد، 1=الاثنين، ...)
        first_weekday = first_day.weekday()
        # تحويل لترتيب عربي (الأحد=0، الاثنين=1، ...)
        arabic_first_weekday = (first_weekday + 1) % 7
        
        # عدد أيام الشهر
        import calendar
        days_in_month = calendar.monthrange(self.year, self.month)[1]
        
        # عرض الأيام في الشبكة المرتبة
        day_counter = 1
        for week_num in range(6):
            for day_num in range(7):
                if week_num == 0 and day_num < arabic_first_weekday:
                    # أيام فارغة قبل بداية الشهر
                    ttk.Label(cal_frame, text="").grid(row=week_num + 1, column=day_num, padx=2, pady=2)
                elif day_counter <= days_in_month:
                    # أيام الشهر المرتبة
                    btn = ttk.Button(cal_frame, text=str(day_counter), width=3)
                    btn.grid(row=week_num + 1, column=day_num, padx=2, pady=2)
                    
                    # تمييز اليوم الحالي
                    if (day_counter == self.date.day and 
                        self.month == datetime.now().month and 
                        self.year == datetime.now().year):
                        btn.configure(style='Accent.TButton')
                    
                    # ربط الحدث
                    btn.bind('<Button-1>', lambda e, d=day_counter: self.select_date(d))
                    self.cal_buttons[day_counter] = btn
                    day_counter += 1
                else:
                    # أيام فارغة بعد نهاية الشهر
                    ttk.Label(cal_frame, text="").grid(row=week_num + 1, column=day_num, padx=2, pady=2)
        
        # التركيز على النافذة
        self.dialog.focus_set()
        
        # توسيط النافذة
        self.center_window()
        
        # التأكد من ظهور جميع العناصر
        self.dialog.update_idletasks()
    
    def center_window(self):
        """توسيط النافذة"""
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def update_month_label(self):
        """تحديث اسم الشهر والسنة"""
        month_names = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                      'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
        month_name = month_names[self.month - 1]
        self.month_label.config(text=f"{month_name} {self.year}")
    
    def prev_month(self):
        """الشهر السابق"""
        self.month -= 1
        if self.month == 0:
            self.month = 12
            self.year -= 1
        self.refresh_calendar()
    
    def next_month(self):
        """الشهر التالي"""
        self.month += 1
        if self.month == 13:
            self.month = 1
            self.year += 1
        self.refresh_calendar()
    
    def go_today(self):
        """الذهاب ليوم اليوم"""
        today = datetime.now()
        self.year = today.year
        self.month = today.month
        self.select_date(today.day)
    
    def refresh_calendar(self):
        """تحديث التقويم"""
        self.update_month_label()
        
        # البحث عن إطار التقويم فقط
        cal_frame = None
        
        for widget in self.dialog.winfo_children():
            if isinstance(widget, ttk.Frame):
                children = widget.winfo_children()
                
                # التحقق إذا كان هذا إطار التقويم (يحتوي على أيام الأسبوع)
                if len(children) >= 7:
                    has_day_buttons = False
                    for child in children:
                        if isinstance(child, ttk.Button) and child.cget('text').isdigit():
                            has_day_buttons = True
                            break
                    if has_day_buttons:
                        cal_frame = widget
                        break
        
        # تحديث إطار التقويم فقط
        if cal_frame:
            # مسح أزرار الأيام القديمة فقط
            children_to_destroy = []
            for child in cal_frame.winfo_children():
                if isinstance(child, ttk.Button) and child.cget('text').isdigit():
                    children_to_destroy.append(child)
            
            for child in children_to_destroy:
                child.destroy()
            
            # إعادة بناء أيام الشهر
            cal_data = monthcalendar(self.year, self.month)
            
            # الحصول على أول يوم في الشهر والأسبوع الذي يبدأ فيه
            first_day = datetime(self.year, self.month, 1)
            # تحديد يوم الأسبوع (0=الأحد، 1=الاثنين، ...)
            first_weekday = first_day.weekday()
            # تحويل لترتيب عربي (الأحد=0، الاثنين=1، ...)
            arabic_first_weekday = (first_weekday + 1) % 7
            
            # عدد أيام الشهر
            import calendar
            days_in_month = calendar.monthrange(self.year, self.month)[1]
            
            # عرض الأيام في الشبكة المرتبة
            day_counter = 1
            for week_num in range(6):
                for day_num in range(7):
                    if week_num == 0 and day_num < arabic_first_weekday:
                        # أيام فارغة قبل بداية الشهر
                        ttk.Label(cal_frame, text="").grid(row=week_num + 1, column=day_num, padx=1, pady=1)
                    elif day_counter <= days_in_month:
                        # أيام الشهر المرتبة
                        btn = ttk.Button(cal_frame, text=str(day_counter), width=3)
                        btn.grid(row=week_num + 1, column=day_num, padx=1, pady=1)
                        
                        # تمييز اليوم الحالي
                        if (day_counter == self.date.day and 
                            self.month == datetime.now().month and 
                            self.year == datetime.now().year):
                            btn.configure(style='Accent.TButton')
                        
                        btn.bind('<Button-1>', lambda e, d=day_counter: self.select_date(d))
                        day_counter += 1
                    else:
                        # أيام فارغة بعد نهاية الشهر
                        ttk.Label(cal_frame, text="").grid(row=week_num + 1, column=day_num, padx=1, pady=1)
    
    def select_date(self, day):
        """اختيار تاريخ"""
        self.result = datetime(self.year, self.month, day).strftime('%Y-%m-%d')
        self.dialog.destroy()
    
    def cancel(self):
        """إلغاء الاختيار"""
        self.dialog.destroy()
    
    def show(self):
        """عرض النافذة والانتظار للنتيجة"""
        self.dialog.wait_window()
        return self.result

class CustomVoucherPDF(FPDF):
    """كلاس PDF احترافي فائق الدقة للسندات المالية والمحاسبية"""
    def __init__(self, company_settings=None):
        super().__init__()
        self.company_settings = company_settings or {}
        
        # تحميل الخطوط
        try:
            amiri_regular = get_font_path('Amiri-Regular.ttf')
            amiri_bold = get_font_path('Amiri-Bold.ttf')
            
            if os.path.exists(amiri_regular):
                self.add_font('Amiri', '', amiri_regular, uni=True)
            if os.path.exists(amiri_bold):
                self.add_font('Amiri', 'B', amiri_bold, uni=True)
            
            try:
                self.add_font('Arial', '', 'arial.ttf', uni=True)
                self.add_font('Arial', 'B', 'arialbd.ttf', uni=True)
            except:
                pass
        except Exception as e:
            print(f"⚠️ خطأ في تحميل خطوط: {e}")

        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=True, margin=10)

    def _get_logo_path(self):
        """الحصول على مسار الشعار المتاح"""
        for candidate in ['fawateery_icon_256.png', 'fawateery_icon.ico', 'أيقونة إف للحسابات والنمو.png', 'images/fawateery_icon_256.png']:
            p = get_font_path(candidate) if os.path.exists(get_font_path(candidate)) else candidate
            if os.path.exists(p) and not p.endswith('.ico'):
                return p
        return None

    def _generate_qr_temp_file(self, data):
        """إنشاء صورة QR مؤقتة"""
        try:
            import qrcode
            import tempfile
            qr = qrcode.QRCode(version=1, box_size=3, border=1)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#1B365D", back_color="white")
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            img.save(tmp.name)
            tmp.close()
            return tmp.name
        except Exception as e:
            return None

    def draw_corporate_header(self, title_text, voucher_number, voucher_date, project_name=""):
        """رأس سند فاخر مع شعار الشركة وتفاصيل التسجيل والترخيص"""
        # الإطار الخارجي والداخلي للصفحة
        self.set_draw_color(27, 54, 93)   # كحلي ملكي
        self.set_line_width(0.7)
        self.rect(8, 8, 194, 281)
        self.set_draw_color(201, 151, 0)  # خط ذهبي
        self.set_line_width(0.3)
        self.rect(9.5, 9.5, 191, 278)

        # بيانات الشركة
        co_ar = self.company_settings.get('company_name_ar', 'مؤسسة فواتيري للمقاولات والتجارة')
        co_en = self.company_settings.get('company_name_en', 'FAWATEERY ESTABLISHMENT')
        cr = self.company_settings.get('commercial_register', '4030330926')
        vat = self.company_settings.get('tax_number', '300262161400003')
        phone = self.company_settings.get('phone1', '')
        address = self.company_settings.get('address', '')

        # شريط خلفية الرأس
        self.set_fill_color(248, 250, 252)
        self.rect(10, 10, 190, 36, 'F')
        self.set_fill_color(27, 54, 93)
        self.rect(10, 10, 190, 3.5, 'F')
        self.set_fill_color(201, 151, 0)
        self.rect(10, 13.5, 190, 1, 'F')

        # الشعار
        logo_path = self._get_logo_path()
        if logo_path:
            try:
                self.image(logo_path, x=95, y=16, w=20, h=20)
            except Exception:
                pass

        # الجانب الأيمن (عربي)
        self.set_xy(118, 16)
        self.set_text_color(27, 54, 93)
        self.set_font('Amiri', 'B', 13)
        self.cell(80, 6, ar(co_ar[:38]), 0, 1, 'R')
        self.set_font('Amiri', '', 9)
        self.set_text_color(71, 85, 105)
        self.set_x(118)
        self.cell(80, 5, ar(f"س.ت: {cr}   |   الرقم الضريبي: {vat}"), 0, 1, 'R')
        if phone or address:
            self.set_x(118)
            self.cell(80, 5, ar(f"{address[:35]} - هاتف: {phone}"), 0, 1, 'R')

        # الجانب الأيسر (إنجليزي)
        self.set_xy(12, 16)
        self.set_text_color(27, 54, 93)
        self.set_font('Arial', 'B', 10)
        self.cell(80, 6, co_en[:35], 0, 1, 'L')
        self.set_font('Arial', '', 8)
        self.set_text_color(71, 85, 105)
        self.set_x(12)
        self.cell(80, 5, f"C.R: {cr}  |  VAT: {vat}", 0, 1, 'L')
        if phone:
            self.set_x(12)
            self.cell(80, 5, f"Phone: {phone}", 0, 1, 'L')

        # شريط عنوان السند ورقم السند
        y_banner = 49
        self.set_fill_color(27, 54, 93)
        self.rect(10, y_banner, 190, 16, 'F')
        self.set_fill_color(201, 151, 0)
        self.rect(10, y_banner + 15, 190, 1, 'F')

        # عنوان السند في المنتصف
        self.set_xy(10, y_banner + 3)
        self.set_text_color(255, 255, 255)
        self.set_font('Amiri', 'B', 16)
        self.cell(190, 7, ar(title_text), 0, 1, 'C')

        # بطاقة بيانات السند السريعة
        y_info = 67
        self.set_fill_color(248, 250, 252)
        self.set_draw_color(226, 232, 240)
        self.rect(10, y_info, 190, 14, 'DF')
        self.set_fill_color(27, 54, 93)
        self.rect(10, y_info, 3, 14, 'F')

        self.set_font('Amiri', 'B', 10)
        self.set_text_color(27, 54, 93)
        self.set_xy(15, y_info + 4)
        self.cell(50, 6, ar(f"رقم السند: #{voucher_number}"), 0, 0, 'R')
        self.cell(60, 6, ar(f"تاريخ الإصدار: {voucher_date}"), 0, 0, 'C')
        proj_str = f"المشروع: {project_name}" if project_name and project_name != 'غير محدد' else "المشروع: عام"
        self.cell(70, 6, ar(proj_str), 0, 1, 'L')

        self.set_y(y_info + 18)

    def draw_beneficiary_and_tafqeet_box(self, beneficiary, total_amount, description):
        """صندوق المستفيد والمبلغ رقماً وكتابة (تفقيط)"""
        try:
            from tafqeet import tafqeet_currency
            tafqeet_text = tafqeet_currency(total_amount)
        except Exception:
            tafqeet_text = f"فقط {total_amount:,.2f} ريال لا غير"

        y = self.get_y()
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(203, 213, 225)
        self.rect(10, y, 190, 36, 'DF')
        self.set_fill_color(201, 151, 0)
        self.rect(197, y, 3, 36, 'F')

        # سطر المستفيد
        self.set_xy(14, y + 3)
        self.set_font('Amiri', 'B', 10)
        self.set_text_color(71, 85, 105)
        self.cell(32, 6, ar("يصرف إلى المكرم:"), 0, 0, 'R')
        self.set_font('Amiri', 'B', 11)
        self.set_text_color(15, 23, 42)
        self.cell(140, 6, ar(beneficiary if beneficiary else "السادة / المحترمين"), 0, 1, 'R')

        # سطر المبلغ رقماً وكتابة
        self.set_xy(14, y + 11)
        self.set_font('Amiri', 'B', 10)
        self.set_text_color(71, 85, 105)
        self.cell(32, 6, ar("مبلغ وقدره:"), 0, 0, 'R')
        self.set_font('Amiri', 'B', 12)
        self.set_text_color(185, 28, 28)  # أحمر مالي فخم
        self.cell(50, 6, ar(f"{total_amount:,.2f} ريال سعودي"), 0, 0, 'R')

        self.set_font('Amiri', 'B', 10)
        self.set_text_color(27, 54, 93)
        self.cell(90, 6, ar(f"({tafqeet_text})"), 0, 1, 'R')

        # سطر البيان
        self.set_xy(14, y + 20)
        self.set_font('Amiri', 'B', 10)
        self.set_text_color(71, 85, 105)
        self.cell(32, 6, ar("وذلك لقاء:"), 0, 0, 'R')
        self.set_font('Amiri', '', 10)
        self.set_text_color(15, 23, 42)
        clean_desc = description.replace('\n', ' ')[:90] if description else "حسب تفاصيل البنود أدناه"
        self.cell(140, 6, ar(clean_desc), 0, 1, 'R')

        self.set_y(y + 39)

    def draw_items_table(self, items, total_amount):
        """جدول تفاصيل بنود السند الاحترافي"""
        y = self.get_y()
        self.set_xy(10, y)

        # ترويسة الجدول
        self.set_fill_color(27, 54, 93)
        self.set_text_color(255, 255, 255)
        self.set_draw_color(27, 54, 93)
        self.set_font('Amiri', 'B', 10)

        self.cell(12, 9, ar('م'), 1, 0, 'C', True)
        self.cell(48, 9, ar('كود / اسم الحساب'), 1, 0, 'C', True)
        self.cell(68, 9, ar('البيان والتفاصيل'), 1, 0, 'C', True)
        self.cell(34, 9, ar('المشروع'), 1, 0, 'C', True)
        self.cell(28, 9, ar('المبلغ (ر.س)'), 1, 1, 'C', True)

        self.set_draw_color(226, 232, 240)
        self.set_font('Amiri', '', 10)

        for idx, itm in enumerate(items, 1):
            acc = itm.get('account', 'عام')
            desc = itm.get('description', '-')
            amt = float(itm.get('amount', 0.0))
            proj = itm.get('project_name', '') or ''
            if proj == 'غير محدد':
                proj = ''

            # تنظيف الوصف
            if 'سند صرف #' in desc and '-' in desc:
                desc = desc.split('-', 1)[1].strip()
            if '(مشروع:' in desc:
                desc = desc.split('(مشروع:')[0].strip()

            # تلوين الصفوف
            if idx % 2 == 0:
                self.set_fill_color(248, 250, 252)
            else:
                self.set_fill_color(255, 255, 255)

            self.set_text_color(15, 23, 42)
            self.cell(12, 8.5, str(idx), 1, 0, 'C', True)
            self.cell(48, 8.5, ar(acc[:24]), 1, 0, 'C', True)
            self.cell(68, 8.5, ar(desc[:36]), 1, 0, 'R', True)
            self.cell(34, 8.5, ar(proj[:18]), 1, 0, 'C', True)
            
            self.set_font('Amiri', 'B', 10)
            self.set_text_color(185, 28, 28)
            self.cell(28, 8.5, f"{amt:,.2f}", 1, 1, 'C', True)
            self.set_font('Amiri', '', 10)

        # صف الإجمالي
        self.set_fill_color(241, 245, 249)
        self.set_text_color(27, 54, 93)
        self.set_font('Amiri', 'B', 11)
        self.cell(162, 9, ar(f"المجموع الكلي ({len(items)} بند)"), 1, 0, 'C', True)
        self.set_text_color(185, 28, 28)
        self.cell(28, 9, f"{total_amount:,.2f}", 1, 1, 'C', True)

    def draw_signatures_and_footer(self, qr_text=""):
        """مربعات التواقيع الرسمية الأربعة وختم التحقق"""
        y_sig = 224
        self.set_xy(10, y_sig)

        sig_boxes = [
            ("المستلم", "الاسم: ...................\nالتوقيع: ................."),
            ("أمين الصندوق / المحاسب", "الاسم: ...................\nالتوقيع: ................."),
            ("المراجعة والتدقيق", "الاسم: ...................\nالتوقيع: ................."),
            ("الاعتماد / المدير العام", "الاسم: ...................\nالاعتماد: ................")
        ]

        box_w = 46.5
        box_h = 24

        for i, (title, note) in enumerate(sig_boxes):
            bx = 10 + (i * 47.8)
            self.set_fill_color(248, 250, 252)
            self.set_draw_color(203, 213, 225)
            self.rect(bx, y_sig, box_w, box_h, 'DF')
            self.set_fill_color(27, 54, 93)
            self.rect(bx, y_sig, box_w, 2, 'F')

            self.set_xy(bx, y_sig + 3)
            self.set_font('Amiri', 'B', 9)
            self.set_text_color(27, 54, 93)
            self.cell(box_w, 5, ar(title), 0, 1, 'C')

            self.set_xy(bx, y_sig + 9)
            self.set_font('Amiri', '', 8)
            self.set_text_color(100, 116, 139)
            lines = note.split('\n')
            for line in lines:
                self.cell(box_w, 5, ar(line), 0, 1, 'C')
                self.set_x(bx)

        # تذييل التحقق ورمز QR
        y_foot = 252
        if qr_text:
            qr_file = self._generate_qr_temp_file(qr_text)
            if qr_file and os.path.exists(qr_file):
                try:
                    self.image(qr_file, x=10, y=y_foot, w=22, h=22)
                    os.unlink(qr_file)
                except Exception:
                    pass

        self.set_xy(34, y_foot + 4)
        self.set_font('Amiri', 'B', 9)
        self.set_text_color(27, 54, 93)
        self.cell(160, 5, ar("تم إصدار هذا السند رسمياً عبر نظام فواتيري لإدارة الحسابات والمشاريع"), 0, 1, 'R')
        
        self.set_xy(34, y_foot + 10)
        self.set_font('Amiri', '', 8)
        self.set_text_color(100, 116, 139)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cell(160, 5, ar(f"تاريخ الطباعة: {now_str}   |   وثيقة محاسبية معتمدة"), 0, 1, 'R')

    def add_voucher_data(self, voucher_data):
        """إضافة سند صرف بتصميم احترافي متكامل"""
        if isinstance(voucher_data, dict):
            vnum = voucher_data.get('number', '1')
            vdate = voucher_data.get('date', datetime.now().strftime('%Y-%m-%d'))
            proj = voucher_data.get('project_name', 'عام')
            items = voucher_data.get('items', [])
            total = float(voucher_data.get('total', 0.0))
            beneficiary = voucher_data.get('beneficiary', '')
            desc = voucher_data.get('description', '')
        else:
            vdate = voucher_data[0] if len(voucher_data) > 0 else datetime.now().strftime('%Y-%m-%d')
            vnum = voucher_data[1] if len(voucher_data) > 1 else '1'
            acc = voucher_data[2] if len(voucher_data) > 2 else 'عام'
            desc = voucher_data[3] if len(voucher_data) > 3 else ''
            amt = float(voucher_data[4]) if len(voucher_data) > 4 else 0.0
            proj = voucher_data[5] if len(voucher_data) > 5 else ''
            items = [{'account': acc, 'description': desc, 'amount': amt, 'project_name': proj}]
            total = amt
            beneficiary = acc

        if not beneficiary and items:
            beneficiary = items[0].get('account', 'المكرم / الجهة المعنية')

        self.draw_corporate_header("ســنـد صـــرف نـقـديـة", vnum, vdate, proj)
        self.draw_beneficiary_and_tafqeet_box(beneficiary, total, desc)
        self.draw_items_table(items, total)

        co_name = self.company_settings.get('company_name_ar', 'Fawateery')
        qr_payload = f"سند صرف #{vnum}\nالمؤسسة: {co_name}\nالتاريخ: {vdate}\nالمبلغ: {total:.2f} ريال"
        self.draw_signatures_and_footer(qr_payload)

    def add_journal_voucher_data(self, voucher_data):
        """إضافة سند قيد يومية بتصميم احترافي"""
        if isinstance(voucher_data, dict):
            vnum = voucher_data.get('number', '1')
            vdate = voucher_data.get('date', datetime.now().strftime('%Y-%m-%d'))
            proj = voucher_data.get('project', 'عام')
            debit_acc = voucher_data.get('debit_account', '')
            credit_acc = voucher_data.get('credit_account', '')
            debit_val = float(voucher_data.get('debit', 0.0))
            credit_val = float(voucher_data.get('credit', 0.0))
            desc = voucher_data.get('description', '')
        else:
            vdate = voucher_data[0] if len(voucher_data) > 0 else datetime.now().strftime('%Y-%m-%d')
            vnum = voucher_data[1] if len(voucher_data) > 1 else '1'
            debit_acc = voucher_data[2] if len(voucher_data) > 2 else ''
            desc = voucher_data[3] if len(voucher_data) > 3 else ''
            debit_val = float(voucher_data[4]) if len(voucher_data) > 4 and str(voucher_data[4]).replace('.', '').isdigit() else 0.0
            credit_val = float(voucher_data[5]) if len(voucher_data) > 5 and str(voucher_data[5]).replace('.', '').isdigit() else 0.0
            credit_acc = voucher_data[2] if len(voucher_data) > 2 else ''
            proj = voucher_data[6] if len(voucher_data) > 6 else 'عام'

        total_amount = max(debit_val, credit_val)

        self.draw_corporate_header("ســنـد قـيـد يـومـيـة", vnum, vdate, proj)
        self.draw_beneficiary_and_tafqeet_box(debit_acc, total_amount, desc)

        # جدول اليومية (مدين ودائن)
        y = self.get_y()
        self.set_xy(10, y)
        self.set_fill_color(27, 54, 93)
        self.set_text_color(255, 255, 255)
        self.set_font('Amiri', 'B', 10)

        self.cell(15, 9, ar('م'), 1, 0, 'C', True)
        self.cell(55, 9, ar('اسم الحساب'), 1, 0, 'C', True)
        self.cell(64, 9, ar('البيان / الشرح'), 1, 0, 'C', True)
        self.cell(28, 9, ar('مدين (ر.س)'), 1, 0, 'C', True)
        self.cell(28, 9, ar('دائن (ر.س)'), 1, 1, 'C', True)

        self.set_font('Amiri', '', 10)
        self.set_text_color(15, 23, 42)

        # صف المدين
        self.set_fill_color(255, 255, 255)
        self.cell(15, 8.5, '1', 1, 0, 'C', True)
        self.cell(55, 8.5, ar(str(debit_acc)[:28]), 1, 0, 'C', True)
        self.cell(64, 8.5, ar(str(desc)[:32]), 1, 0, 'R', True)
        self.cell(28, 8.5, f"{debit_val:,.2f}" if debit_val > 0 else "-", 1, 0, 'C', True)
        self.cell(28, 8.5, "-", 1, 1, 'C', True)

        # صف الدائن
        self.set_fill_color(248, 250, 252)
        self.cell(15, 8.5, '2', 1, 0, 'C', True)
        self.cell(55, 8.5, ar(str(credit_acc)[:28]), 1, 0, 'C', True)
        self.cell(64, 8.5, ar(str(desc)[:32]), 1, 0, 'R', True)
        self.cell(28, 8.5, "-", 1, 0, 'C', True)
        self.cell(28, 8.5, f"{credit_val:,.2f}" if credit_val > 0 else "-", 1, 1, 'C', True)

        # صف الإجمالي
        self.set_fill_color(241, 245, 249)
        self.set_text_color(27, 54, 93)
        self.set_font('Amiri', 'B', 10)
        self.cell(134, 9, ar("المجموع المتوازن"), 1, 0, 'C', True)
        self.cell(28, 9, f"{total_amount:,.2f}", 1, 0, 'C', True)
        self.cell(28, 9, f"{total_amount:,.2f}", 1, 1, 'C', True)

        co_name = self.company_settings.get('company_name_ar', 'Fawateery')
        qr_payload = f"سند قيد #{vnum}\nالمؤسسة: {co_name}\nالتاريخ: {vdate}\nالمبلغ: {total_amount:.2f} ريال"
        self.draw_signatures_and_footer(qr_payload)


class CustomDailyVouchersPDF(FPDF):
    """كلاس PDF احترافي لسجل سندات الصرف واليومية اليومي المجمع"""
    def __init__(self, company_settings=None):
        super().__init__()
        self.company_settings = company_settings or {}
        
        try:
            amiri_regular = get_font_path('Amiri-Regular.ttf')
            amiri_bold = get_font_path('Amiri-Bold.ttf')
            
            if os.path.exists(amiri_regular):
                self.add_font('Amiri', '', amiri_regular, uni=True)
            if os.path.exists(amiri_bold):
                self.add_font('Amiri', 'B', amiri_bold, uni=True)
            try:
                self.add_font('Arial', '', 'arial.ttf', uni=True)
                self.add_font('Arial', 'B', 'arialbd.ttf', uni=True)
            except:
                pass
        except Exception as e:
            print(f"⚠️ خطأ في تحميل خطوط: {e}")

        self.set_margins(10, 10, 10)
        self.set_auto_page_break(auto=True, margin=10)

    def draw_daily_header(self, date):
        """ترويسة كشف السندات اليومي الاحترافي"""
        # الإطار
        self.set_draw_color(27, 54, 93)
        self.set_line_width(0.6)
        self.rect(8, 8, 194, 281)

        co_ar = self.company_settings.get('company_name_ar', 'FAWATEERY')
        cr = self.company_settings.get('commercial_register', '---')
        vat = self.company_settings.get('tax_number', '---')

        self.set_fill_color(27, 54, 93)
        self.rect(10, 10, 190, 24, 'F')
        self.set_fill_color(201, 151, 0)
        self.rect(10, 34, 190, 1.5, 'F')

        self.set_text_color(255, 255, 255)
        self.set_font('Amiri', 'B', 16)
        self.set_xy(10, 13)
        self.cell(190, 7, ar("كـشـف ســنـدات الـصـرف الـيـومـيـة"), 0, 1, 'C')

        self.set_font('Amiri', '', 10)
        self.cell(190, 6, ar(f"{co_ar}   |   س.ت: {cr}   |   الرقم الضريبي: {vat}"), 0, 1, 'C')

        # بطاقة التاريخ
        self.set_fill_color(248, 250, 252)
        self.set_draw_color(203, 213, 225)
        self.rect(10, 39, 190, 10, 'DF')
        self.set_xy(10, 41)
        self.set_text_color(27, 54, 93)
        self.set_font('Amiri', 'B', 11)
        self.cell(190, 6, ar(f"تاريخ التقرير: {date}   |   كافة السندات المسجلة بالخزينة لليوم المحدد"), 0, 1, 'C')

        self.set_y(54)

    def draw_daily_table(self, vouchers):
        """جدول السندات اليومية بتنسيق محاسبي راقٍ"""
        self.set_fill_color(27, 54, 93)
        self.set_text_color(255, 255, 255)
        self.set_font('Amiri', 'B', 10)

        self.cell(12, 8.5, ar('م'), 1, 0, 'C', True)
        self.cell(24, 8.5, ar('رقم السند'), 1, 0, 'C', True)
        self.cell(46, 8.5, ar('الحساب / المستفيد'), 1, 0, 'C', True)
        self.cell(56, 8.5, ar('البيان والوصف'), 1, 0, 'C', True)
        self.cell(26, 8.5, ar('المشروع'), 1, 0, 'C', True)
        self.cell(26, 8.5, ar('المبلغ (ر.س)'), 1, 1, 'C', True)

        self.set_font('Amiri', '', 9.5)
        self.set_draw_color(226, 232, 240)

        total_amount = 0.0
        for idx, v in enumerate(vouchers, 1):
            desc = v[0]
            amt = float(v[1]) if str(v[1]).replace('.', '').isdigit() else 0.0
            acc = v[2]
            proj = v[3] or "عام"

            num = "N/A"
            actual_desc = desc
            if 'سند صرف #' in desc:
                parts = desc.split('#')[1].split()
                if parts:
                    num = parts[0]
                actual_desc = desc.split('-', 1)[1].strip() if '-' in desc else desc
                if '(مشروع:' in actual_desc:
                    actual_desc = actual_desc.split('(مشروع:')[0].strip()

            if idx % 2 == 0:
                self.set_fill_color(248, 250, 252)
            else:
                self.set_fill_color(255, 255, 255)

            self.set_text_color(15, 23, 42)
            self.cell(12, 8, str(idx), 1, 0, 'C', True)
            self.cell(24, 8, f"#{num}", 1, 0, 'C', True)
            self.cell(46, 8, ar(str(acc)[:22]), 1, 0, 'C', True)
            self.cell(56, 8, ar(str(actual_desc)[:30]), 1, 0, 'R', True)
            self.cell(26, 8, ar(str(proj)[:14]), 1, 0, 'C', True)

            self.set_font('Amiri', 'B', 9.5)
            self.set_text_color(185, 28, 28)
            self.cell(26, 8, f"{amt:,.2f}", 1, 1, 'C', True)
            self.set_font('Amiri', '', 9.5)

            total_amount += amt

        # بطاقة الإجمالي
        self.set_fill_color(241, 245, 249)
        self.set_text_color(27, 54, 93)
        self.set_font('Amiri', 'B', 11)
        self.cell(164, 9, ar(f"الإجمالي الكلي لسندات اليوم ({len(vouchers)} سند)"), 1, 0, 'C', True)
        self.set_text_color(185, 28, 28)
        self.cell(26, 9, f"{total_amount:,.2f}", 1, 1, 'C', True)

    def draw_daily_footer(self, date):
        """تذييل الكشف اليومي والتواقيع"""
        y_sig = 235
        self.set_xy(10, y_sig)

        boxes = ["إعداد المحاسب", "المراجعة الداخلية", "الاعتماد المالي"]
        for i, b in enumerate(boxes):
            bx = 15 + (i * 62)
            self.set_draw_color(203, 213, 225)
            self.set_fill_color(248, 250, 252)
            self.rect(bx, y_sig, 56, 22, 'DF')
            self.set_fill_color(27, 54, 93)
            self.rect(bx, y_sig, 56, 2, 'F')
            self.set_xy(bx, y_sig + 3)
            self.set_font('Amiri', 'B', 10)
            self.set_text_color(27, 54, 93)
            self.cell(56, 5, ar(b), 0, 1, 'C')
            self.set_xy(bx, y_sig + 11)
            self.set_font('Amiri', '', 8)
            self.set_text_color(100, 116, 139)
            self.cell(56, 5, ar("التوقيع: ....................."), 0, 1, 'C')

        self.set_xy(10, 264)
        self.set_font('Amiri', '', 8.5)
        self.set_text_color(100, 116, 139)
        self.cell(190, 5, ar(f"نظام فواتيري للمحاسبة والمشاريع - طبع بتاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), 0, 1, 'C')

    def add_daily_vouchers_data(self, date, vouchers):
        """إضافة بيانات السندات اليومية"""
        self.draw_daily_header(date)
        self.draw_daily_table(vouchers)
        self.draw_daily_footer(date)

    def add_daily_journal_vouchers_data(self, date, vouchers):
        """إضافة بيانات سندات اليومية اليومية"""
        self.draw_daily_journal_header(date)
        self.draw_daily_journal_table(vouchers)
        self.draw_daily_footer(date)

    def draw_daily_journal_header(self, date):
        """رأس كشف سندات اليومية المجمعة"""
        self.set_draw_color(27, 54, 93)
        self.rect(8, 8, 194, 281)

        co_ar = self.company_settings.get('company_name_ar', 'FAWATEERY')
        self.set_fill_color(27, 54, 93)
        self.rect(10, 10, 190, 24, 'F')
        self.set_fill_color(201, 151, 0)
        self.rect(10, 34, 190, 1.5, 'F')

        self.set_text_color(255, 255, 255)
        self.set_font('Amiri', 'B', 16)
        self.set_xy(10, 13)
        self.cell(190, 7, ar("كـشـف قـيـود الـيـومـيـة"), 0, 1, 'C')
        self.set_font('Amiri', '', 10)
        self.cell(190, 6, ar(f"{co_ar}   |   تاريخ الكشف: {date}"), 0, 1, 'C')
        self.set_y(44)

    def draw_daily_journal_table(self, vouchers):
        """جدول كشف قيود اليومية المجمعة"""
        self.set_fill_color(27, 54, 93)
        self.set_text_color(255, 255, 255)
        self.set_font('Amiri', 'B', 10)

        self.cell(20, 8.5, ar('رقم القيد'), 1, 0, 'C', True)
        self.cell(45, 8.5, ar('حساب مدين'), 1, 0, 'C', True)
        self.cell(45, 8.5, ar('حساب دائن'), 1, 0, 'C', True)
        self.cell(25, 8.5, ar('مدين'), 1, 0, 'C', True)
        self.cell(25, 8.5, ar('دائن'), 1, 0, 'C', True)
        self.cell(30, 8.5, ar('البيان'), 1, 1, 'C', True)

        self.set_font('Amiri', '', 9.5)
        total = 0.0
        for idx, v in enumerate(vouchers, 1):
            deb_acc = v.get('debit_account', '')[:16]
            crd_acc = v.get('credit_account', '')[:16]
            deb = float(v.get('debit', 0.0))
            crd = float(v.get('credit', 0.0))
            desc = v.get('description', '')[:16]
            num = v.get('number', str(idx))

            if idx % 2 == 0:
                self.set_fill_color(248, 250, 252)
            else:
                self.set_fill_color(255, 255, 255)

            self.set_text_color(15, 23, 42)
            self.cell(20, 8, ar(str(num)), 1, 0, 'C', True)
            self.cell(45, 8, ar(deb_acc), 1, 0, 'C', True)
            self.cell(45, 8, ar(crd_acc), 1, 0, 'C', True)
            self.cell(25, 8, f"{deb:,.2f}" if deb else "-", 1, 0, 'C', True)
            self.cell(25, 8, f"{crd:,.2f}" if crd else "-", 1, 0, 'C', True)
            self.cell(30, 8, ar(desc), 1, 1, 'C', True)

            total += deb if deb else crd

        self.set_fill_color(241, 245, 249)
        self.set_font('Amiri', 'B', 10)
        self.set_text_color(27, 54, 93)
        self.cell(110, 9, ar(f"الإجمالي ({len(vouchers)} قيود)"), 1, 0, 'C', True)
        self.cell(25, 9, f"{total:,.2f}", 1, 0, 'C', True)
        self.cell(25, 9, f"{total:,.2f}", 1, 0, 'C', True)
        self.cell(30, 9, "", 1, 1, 'C', True)

class SearchableComboboxCell(ttk.Combobox):
    """قائمة منسدلة ذكية للجدول تدعم البحث أثناء الكتابة وتدعم القائمة المنسدلة الأصلية والتنقل السريع"""
    def __init__(self, master=None, values=None, **kwargs):
        super().__init__(master, **kwargs)
        self._all_values = list(values) if values else []
        self['values'] = self._all_values
        self._popup = None
        self._listbox = None
        self._next_widget = None
        
        self._ignore_keys = {
            'Up', 'Down', 'Return', 'Escape', 'Tab',
            'Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_L', 'Alt_R',
            'Caps_Lock', 'Win_L', 'Win_R'
        }
        
        self.bind('<KeyRelease>', self._on_keyrelease)
        self.bind('<Down>', self._on_down_key)
        self.bind('<Escape>', lambda e: self.hide_popup())
        self.bind('<FocusOut>', self._on_focus_out)
        self.bind('<Button-1>', self._on_click)
        self.bind('<Return>', self._on_return)

    def set_next_widget(self, widget):
        self._next_widget = widget

    def set_values(self, values):
        self._all_values = list(values) if values else []
        self['values'] = self._all_values

    @staticmethod
    def _normalize_ar(text):
        if not text:
            return ''
        s = text.lower()
        replacements = [
            ('أ', 'ا'), ('إ', 'ا'), ('آ', 'ا'), ('ٱ', 'ا'),
            ('ة', 'ه'), ('ى', 'ي'), ('ئ', 'ي'), ('ؤ', 'و')
        ]
        for src, dst in replacements:
            s = s.replace(src, dst)
        return s

    def _get_matches(self, query):
        q = query.strip()
        if not q:
            return list(self._all_values)
        nq = self._normalize_ar(q)
        return [v for v in self._all_values if nq in self._normalize_ar(v)]

    def _show_popup(self, matches):
        if not matches:
            self.hide_popup()
            return
        if not self._popup or not self._popup.winfo_exists():
            self._popup = tk.Toplevel(self)
            self._popup.wm_overrideredirect(True)
            self._popup.attributes('-topmost', True)
            
            frame = tk.Frame(self._popup, bg='#1F3A52', bd=1, relief=tk.SOLID)
            frame.pack(fill='both', expand=True)
            
            scrollbar = ttk.Scrollbar(frame, orient='vertical')
            self._listbox = tk.Listbox(
                frame, font=('Segoe UI', 10), justify='right',
                yscrollcommand=scrollbar.set,
                selectmode='single', exportselection=False,
                bg='#FFFFFF', fg='#1F3A52',
                selectbackground='#2980B9', selectforeground='#FFFFFF',
                activestyle='none', relief=tk.FLAT, bd=0
            )
            scrollbar.config(command=self._listbox.yview)
            scrollbar.pack(side='left', fill='y')
            self._listbox.pack(side='right', fill='both', expand=True)
            
            self._listbox.bind('<ButtonRelease-1>', self._on_listbox_select)
            self._listbox.bind('<Return>', self._on_listbox_select)
            self._listbox.bind('<Escape>', lambda e: self.hide_popup())

        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 1
        w = max(self.winfo_width(), 260)
        screen_w = self.winfo_screenwidth()
        if x + w > screen_w - 10:
            x = max(10, screen_w - w - 10)
            
        item_count = min(7, len(matches))
        h = max(35, item_count * 26 + 6)
        screen_h = self.winfo_screenheight()
        if y + h > screen_h - 40:
            y = max(10, self.winfo_rooty() - h - 1)
        self._popup.geometry(f'{w}x{h}+{x}+{y}')
        
        self._listbox.delete(0, 'end')
        for item in matches:
            self._listbox.insert('end', f'  {item}  ')
        self._listbox.config(height=item_count)

    def hide_popup(self):
        if self._popup and self._popup.winfo_exists():
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None
            self._listbox = None

    def _on_click(self, event):
        self.hide_popup()
        # عند الضغط على السهم أو الحقل نعيد كامل القيم المتاحة ليراها المستخدم في القائمة المنسدلة
        self['values'] = self._all_values

    def _on_keyrelease(self, event):
        if event.keysym in self._ignore_keys:
            return
        typed = self.get()
        matches = self._get_matches(typed)
        self['values'] = matches
        if typed.strip():
            self._show_popup(matches)
        else:
            self.hide_popup()

    def _on_down_key(self, event):
        if self._popup and self._listbox and self._listbox.size() > 0:
            self._listbox.focus_set()
            self._listbox.selection_clear(0, 'end')
            self._listbox.selection_set(0)
            self._listbox.activate(0)
            return 'break'

    def _on_listbox_select(self, event=None):
        if self._listbox:
            sel = self._listbox.curselection()
            if sel:
                val = self._listbox.get(sel[0]).strip()
                self.set(val)
                self.event_generate('<<ComboboxSelected>>')
        self.hide_popup()
        if self._next_widget:
            self._next_widget.focus_set()
        else:
            self.focus_set()
        return 'break'

    def _on_return(self, event):
        # إذا كانت قائمة الاقتراحات مفتوحة
        if self._popup and self._popup.winfo_exists() and self._listbox and self._listbox.size() > 0:
            typed = self.get().strip()
            matches = self._get_matches(typed)
            if matches and typed not in self._all_values:
                self.set(matches[0])
                self.event_generate('<<ComboboxSelected>>')
        self.hide_popup()
        if self._next_widget:
            self._next_widget.focus_set()
            return 'break'

    def _on_focus_out(self, event):
        self.after(200, self._check_focus)

    def _check_focus(self):
        if self._popup and self._popup.winfo_exists():
            try:
                focused = self.winfo_toplevel().focus_get()
                if focused != self and focused != self._listbox:
                    self.hide_popup()
            except Exception:
                self.hide_popup()


class BatchPaymentItemsDialog(tk.Toplevel):
    """نافذة لإدخال عدة بنود لسند الصرف دفعة واحدة في جدول سريع"""
    def __init__(self, parent, account_options, project_options=None, on_save_callback=None):
        super().__init__(parent)
        self.title("📋 إدخال عدة بنود لسند الصرف دفعة واحدة")
        
        # توافق مع الاستدعاء القديم في حال تم تمرير الدالة كمعامل ثالث
        if callable(project_options) and on_save_callback is None:
            on_save_callback = project_options
            project_options = None
            
        self.account_options = account_options or []
        if not self.account_options:
            try:
                from database import Database
                db = Database()
                accs = db.execute_query("SELECT name FROM account_items ORDER BY name")
                emps = db.execute_query("SELECT id, name FROM employees ORDER BY name")
                self.account_options = [a[0] for a in accs] + [f"{e[0]} - {e[1]}" for e in emps]
            except Exception:
                self.account_options = []
        if project_options is None:
            try:
                from database import Database
                db = Database()
                projs = db.execute_query("SELECT id, name FROM projects ORDER BY name")
                self.project_options = [f"{p[0]} - {p[1]}" for p in projs]
            except Exception:
                self.project_options = []
        else:
            self.project_options = list(project_options)
            
        self.on_save_callback = on_save_callback
        self.rows = []
        
        # تكبير النافذة بشكل مريح ومتوسط في الشاشة دون وضع التكبير المطلق
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(1220, max(1060, int(screen_w * 0.85)))
        win_h = min(730, max(580, int(screen_h * 0.80)))
        x = max(10, (screen_w - win_w) // 2)
        y = max(10, (screen_h - win_h) // 2)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.minsize(1020, 520)
        
        self.transient(parent)
        self.grab_set()
        
        # رأس النافذة والتعليمات
        header_frame = tk.Frame(self, bg='#1F3A52', pady=10)
        header_frame.pack(fill='x')
        tk.Label(header_frame, text="📋 جدول إدخال بنود سند الصرف السريع", font=('Segoe UI', 13, 'bold'), fg='white', bg='#1F3A52').pack()
        tk.Label(header_frame, text="أدخل بنود سند الصرف سطراً بسطر (استخدم Enter أو Tab للتنقل السريع بين الخلايا)، ثم اضغط 'إضافة كل البنود لسند الصرف'", 
                 font=('Segoe UI', 9), fg='#D5DBDB', bg='#1F3A52').pack(pady=(2, 0))
        
        # إطار الجدول القابل للتمرير
        container = ttk.Frame(self)
        container.pack(fill='both', expand=True, padx=15, pady=10)
        
        self.canvas = tk.Canvas(container, bg='#F8F9F9', highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical", command=self._on_scroll)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_canvas_scroll)
        
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # ربط إخفاء القوائم المنبثقة عند التمرير بالماوس أو النقر خارجها
        self.bind('<Button-1>', self._on_dialog_click)
        self.canvas.bind('<MouseWheel>', lambda e: self.hide_all_popups())
        self.scrollable_frame.bind('<MouseWheel>', lambda e: self.hide_all_popups())
        
        # ضبط أوزان وعروض الأعمدة بدقة داخل نفس الـ Frame لضمان محاذاة 100% بين العنوان والخلايا
        self.scrollable_frame.columnconfigure(0, weight=0, minsize=45)   # #
        self.scrollable_frame.columnconfigure(1, weight=3, minsize=260)  # الحساب
        self.scrollable_frame.columnconfigure(2, weight=3, minsize=230)  # المشروع
        self.scrollable_frame.columnconfigure(3, weight=4, minsize=320)  # البيان / الوصف
        self.scrollable_frame.columnconfigure(4, weight=1, minsize=130)  # المبلغ
        
        # إنشاء عناوين الأعمدة في السطر 0 مباشرة لضمان تطابق المحاذاة التام
        headers = [
            ("#", 45),
            ("الحساب (بند حساب / موظف) *", 260),
            ("المشروع", 230),
            ("البيان / الوصف *", 320),
            ("المبلغ *", 130)
        ]
        for col_idx, (title, min_w) in enumerate(headers):
            lbl = tk.Label(self.scrollable_frame, text=title, font=('Segoe UI', 10, 'bold'),
                           bg='#1F3A52', fg='white', pady=8, padx=5, relief=tk.FLAT)
            lbl.grid(row=0, column=col_idx, sticky='nsew', padx=2, pady=(0, 4))
        
        # إضافة 8 أسطر مبدئياً
        for _ in range(8):
            self.add_row()
            
        if self.rows:
            self.rows[0]['account'].focus_set()
            
        # أزرار التحكم في الأسفل
        btn_frame = tk.Frame(self, pady=10, bg='#EAEDED')
        btn_frame.pack(fill='x')
        
        tk.Button(btn_frame, text="➕ إضافة 5 أسطر إضافية", command=lambda: [self.add_row() for _ in range(5)],
                  bg='#5D6D7E', fg='white', font=('Segoe UI', 10), padx=10, pady=5, relief=tk.FLAT, cursor='hand2').pack(side='right', padx=10)
                  
        tk.Button(btn_frame, text="💾 إضافة كل البنود لسند الصرف", command=self.save_and_close,
                  bg='#27AE60', fg='white', font=('Segoe UI', 11, 'bold'), padx=15, pady=6, relief=tk.FLAT, cursor='hand2').pack(side='left', padx=10)
                  
        tk.Button(btn_frame, text="❌ إلغاء", command=self.destroy,
                  bg='#95A5A6', fg='white', font=('Segoe UI', 10), padx=10, pady=5, relief=tk.FLAT, cursor='hand2').pack(side='left', padx=5)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_scroll(self, *args):
        self.hide_all_popups()
        self.canvas.yview(*args)

    def _on_canvas_scroll(self, *args):
        self.hide_all_popups()
        self.scrollbar.set(*args)

    def hide_all_popups(self, event=None):
        for r in self.rows:
            for k in ('account', 'project'):
                cb = r.get(k)
                if cb and hasattr(cb, 'hide_popup'):
                    cb.hide_popup()

    def _on_dialog_click(self, event):
        for r in self.rows:
            for k in ('account', 'project'):
                cb = r.get(k)
                if cb and hasattr(cb, 'hide_popup') and cb._popup:
                    if event.widget != cb and (not cb._popup or event.widget != cb._listbox):
                        cb.hide_popup()

    def destroy(self):
        self.hide_all_popups()
        super().destroy()

    def add_row(self):
        row_idx = len(self.rows) + 1
        
        # العمود 0: الرقم
        lbl_num = tk.Label(self.scrollable_frame, text=str(row_idx), font=('Segoe UI', 10, 'bold'),
                           bg='#EAEDED', fg='#2C3E50', width=4)
        lbl_num.grid(row=row_idx, column=0, sticky='nsew', padx=2, pady=2)
        
        # العمود 1: الحساب مع قائمة منسدلة ذكية تدعم البحث
        acc_combo = SearchableComboboxCell(self.scrollable_frame, values=self.account_options, font=('Segoe UI', 10))
        acc_combo.grid(row=row_idx, column=1, sticky='ew', padx=2, pady=2)
        
        # العمود 2: المشروع مع قائمة منسدلة ذكية تدعم البحث
        proj_combo = SearchableComboboxCell(self.scrollable_frame, values=self.project_options, font=('Segoe UI', 10))
        proj_combo.grid(row=row_idx, column=2, sticky='ew', padx=2, pady=2)
        
        # العمود 3: البيان / الوصف
        desc_e = ttk.Entry(self.scrollable_frame, font=('Segoe UI', 10))
        desc_e.grid(row=row_idx, column=3, sticky='ew', padx=2, pady=2)
        
        # العمود 4: المبلغ
        amount_e = ttk.Entry(self.scrollable_frame, font=('Segoe UI', 10))
        amount_e.grid(row=row_idx, column=4, sticky='ew', padx=2, pady=2)
        
        row_dict = {
            'num_lbl': lbl_num,
            'account': acc_combo,
            'project': proj_combo,
            'desc': desc_e,
            'amount': amount_e
        }
        self.rows.append(row_dict)
        
        # ربط التنقل السريع بالـ Enter والـ Tab
        acc_combo.set_next_widget(proj_combo)
        proj_combo.set_next_widget(desc_e)
        desc_e.bind('<Return>', lambda e, a=amount_e: a.focus_set())
        
        curr_idx = len(self.rows) - 1
        def on_amount_enter(e, r_idx=curr_idx):
            if r_idx + 1 < len(self.rows):
                self.rows[r_idx + 1]['account'].focus_set()
            else:
                self.add_row()
                self.rows[-1]['account'].focus_set()
                self.update_idletasks()
                self.canvas.yview_moveto(1.0)
                
        amount_e.bind('<Return>', on_amount_enter)

    def save_and_close(self):
        self.hide_all_popups()
        items_to_add = []
        for r in self.rows:
            acc = r['account'].get().strip()
            proj = r['project'].get().strip()
            desc = r['desc'].get().strip()
            amt = r['amount'].get().strip()
            
            # إذا كان السطر فارغاً بالكامل يتم تجاوزه
            if not acc and not proj and not desc and not amt:
                continue
                
            # إذا كتب شيئاً، فالحساب والبيان والمبلغ مطلوبة
            if not acc or not desc or not amt:
                messagebox.showwarning("تحذير", f"⚠️ البند '{desc or acc or 'غير محدد'}' يجب ملء الحساب والبيان والمبلغ معاً.")
                if not acc:
                    r['account'].focus_set()
                elif not desc:
                    r['desc'].focus_set()
                else:
                    r['amount'].focus_set()
                return
            try:
                amt_val = float(amt)
                if amt_val <= 0:
                    messagebox.showwarning("تحذير", f"⚠️ المبلغ في البند '{desc}' يجب أن يكون أكبر من الصفر")
                    r['amount'].focus_set()
                    return
                # تنظيف خيار المشروع الفارغ أو الافتراضي
                if proj in ("-- بدون مشروع --", "-- اختر المشروع --"):
                    proj = ""
                items_to_add.append((acc, proj, desc, amt_val))
            except ValueError:
                messagebox.showerror("خطأ", f"❌ المبلغ غير صحيح في البند '{desc}'")
                r['amount'].focus_set()
                return
                
        if not items_to_add:
            messagebox.showwarning("تنبيه", "⚠️ لم يتم إدخال أي بند للإضافة")
            return
            
        self.on_save_callback(items_to_add)
        self.destroy()

class TreasuryModule:
    def __init__(self, notebook, status_callback):
        self.notebook = notebook
        self.status_callback = status_callback
        self.db = Database()
        
        # إطار السندات
        self.frame = ttk.Frame(notebook)
        
        # إطار الصندوق المستقل
        self.cash_frame = ttk.Frame(notebook)
        self.create_cash_tab(self.cash_frame)
        
        # إنشاء ScrollArea ومحتوى السندات
        self.create_scrollable_content()
        self.create_widgets()
        
        # تحديث البيانات بعد إنشاء جميع العناصر
        self.load_cash_data()
    
    def create_scrollable_content(self):
        """إنشاء محتوى قابل للتمرير"""
        # إنشاء إطار رئيسي للتمرير
        self.scroll_frame = ttk.Frame(self.frame)
        self.scroll_frame.pack(fill='both', expand=True)
        
        # إنشاء Canvas للتمرير
        self.canvas = tk.Canvas(self.scroll_frame)
        self.canvas.pack(side='left', fill='both', expand=True)
        
        # إنشاء شريط تمرير عمودي
        scrollbar = ttk.Scrollbar(self.scroll_frame, orient='vertical', command=self.canvas.yview)
        scrollbar.pack(side='right', fill='y')
        
        # ربط Canvas مع شريط التمرير
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # إنشاء إطار المحتوى الفعلي
        self.content_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor='nw')
        
        # تحديث حجم التمرير عند تغيير المحتوى
        self.content_frame.bind('<Configure>', self.on_frame_configure)
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        # تفعيل التمرير بالعجلة
        self.canvas.bind('<MouseWheel>', self.on_mousewheel)
    
    def on_frame_configure(self, event):
        """تحديث منطقة التمرير عند تغيير حجم الإطار"""
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def on_canvas_configure(self, event):
        """تحديث عرض الإطار عند تغيير حجم Canvas"""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
    
    def on_mousewheel(self, event):
        """معالجة تمرير العجلة"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
    
    def create_widgets(self):
        """إنشاء عناصر واجهة السندات"""
        # إطار رئيسي
        main_container = ttk.Frame(self.content_frame)
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # عنوان
        title_label = tk.Label(main_container, text="📑 إدارة السندات المالية", 
                              font=('Segoe UI', 16, 'bold'))
        title_label.pack(pady=10)
        
        # إنشاء دفتر ملاحظات للتبويبات الفرعية للسندات
        self.sub_notebook = ttk.Notebook(main_container)
        self.sub_notebook.pack(fill='both', expand=True)
        
        # تبويب سند الصرف (أصبح التبويب الأول بعد فصل الصندوق)
        self.create_payment_voucher_tab(self.sub_notebook)
        
        # تبويب سند اليومية
        self.create_journal_voucher_tab(self.sub_notebook)
        
        # تبويب بنود الحسابات
        self.create_account_items_tab(self.sub_notebook)
        
        # ربط حدث التبديل
        self.sub_notebook.bind('<<NotebookTabChanged>>', self.on_sub_tab_changed)

    def on_sub_tab_changed(self, event):
        """تحديث بيانات التبويب الفرعي النشط في السندات"""
        try:
            selected_tab = self.sub_notebook.index("current")
            if selected_tab == 0:
                pass # سند الصرف
            elif selected_tab == 1:
                pass # سند اليومية
            elif selected_tab == 2:
                if hasattr(self, 'load_account_items'):
                    self.load_account_items()
        except Exception as e:
            print(f"Error refreshing sub_tab {selected_tab}: {e}")
    
    def create_cash_tab(self, parent_frame):
        """إنشاء محتوى تبويب الصندوق المستقل"""
        cash_container = ttk.Frame(parent_frame)
        cash_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # عنوان رئيسي
        title_label = tk.Label(cash_container, text="💵 إدارة وحركات الصندوق", 
                              font=('Segoe UI', 16, 'bold'))
        title_label.pack(pady=10)
        
        # إطار معلومات الرصيد
        balance_frame = ttk.LabelFrame(cash_container, text="معلومات الرصيد")
        balance_frame.pack(fill='x', padx=5, pady=10)
        
        # عرض الرصيد
        self.cash_balance_label = tk.Label(balance_frame, text="الرصيد الحالي: 0.00 ريال", 
                                     font=('Segoe UI', 15, 'bold'), fg='#27AE60')
        self.cash_balance_label.pack(pady=12)
        
        # إطار الحركات
        movements_frame = ttk.LabelFrame(cash_container, text="حركات الصندوق")
        movements_frame.pack(fill='both', expand=True, padx=5, pady=10)
        
        # شريط أدوات سريع
        toolbar_frame = ttk.Frame(movements_frame)
        toolbar_frame.pack(fill='x', padx=10, pady=(5, 5))
        
        refresh_btn = ttk.Button(toolbar_frame, text="🔄 تحديث حركات الصندوق", command=self.load_cash_data)
        refresh_btn.pack(side='right', padx=5)
        
        # جدول الحركات
        columns = ('id', 'date', 'type', 'description', 'amount', 'account_name')
        self.cash_tree = ttk.Treeview(movements_frame, columns=columns, show='headings', height=15)
        
        # إعدادات الأعمدة
        self.cash_tree.heading('id', text='الرقم')
        self.cash_tree.heading('date', text='التاريخ')
        self.cash_tree.heading('type', text='النوع')
        self.cash_tree.heading('description', text='الوصف')
        self.cash_tree.heading('amount', text='المبلغ')
        self.cash_tree.heading('account_name', text='الحساب')
        
        self.cash_tree.column('id', width=60, anchor='center')
        self.cash_tree.column('date', width=110, anchor='center')
        self.cash_tree.column('type', width=90, anchor='center')
        self.cash_tree.column('description', width=260, anchor='w')
        self.cash_tree.column('amount', width=120, anchor='center')
        self.cash_tree.column('account_name', width=180, anchor='w')
        
        self.cash_tree.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=10)
        
        # شريط تمرير
        scrollbar = ttk.Scrollbar(movements_frame, orient="vertical", command=self.cash_tree.yview)
        scrollbar.pack(side='right', fill='y', padx=(0, 10), pady=10)
        self.cash_tree.configure(yscrollcommand=scrollbar.set)
        
        # تحديث البيانات
        self.update_cash_data()
    
    def create_payment_voucher_tab(self, notebook):
        """إنشاء تبويب سند الصرف بتصميم متكامل كالفاتورة، مع جدول السندات المسجلة وأزرارها مباشرة في نفس الشاشة"""
        payment_frame = ttk.Frame(notebook)
        notebook.add(payment_frame, text="📝 سند الصرف")
        
        main_container = ttk.Frame(payment_frame)
        main_container.pack(fill='both', expand=True, padx=15, pady=10)
        
        # تتبع حالة السند الحالي (إنشاء جديد أم تعديل)
        self.editing_voucher_data = None
        
        # ========================================================
        # القسم الأول: تحرير سند الصرف (إدخال وتعديل البنود كالفاتورة)
        # ========================================================
        form_frame = ttk.LabelFrame(main_container, text="📝 بيانات سند الصرف (إدخال وتعديل البنود كالفاتورة)")
        form_frame.pack(fill='x', padx=5, pady=(0, 10))
        
        # شريط الحالة العلوي وزر سند جديد
        top_bar = ttk.Frame(form_frame)
        top_bar.pack(fill='x', padx=10, pady=5)
        
        self.voucher_mode_label = tk.Label(top_bar, text="📝 إنشاء سند صرف جديد", font=('Segoe UI', 12, 'bold'), fg='#1B4F72')
        self.voucher_mode_label.pack(side='right', padx=5)
        
        ttk.Button(top_bar, text="➕ سند صرف جديد", command=self.clear_payment_form, width=16).pack(side='left', padx=5)
        
        # حقول رأس السند (التاريخ، الرقم، المشروع)
        header_fields_frame = ttk.Frame(form_frame)
        header_fields_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(header_fields_frame, text="التاريخ:", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=(10, 5))
        self.payment_date_entry = ttk.Entry(header_fields_frame, width=13, font=('Segoe UI', 10))
        self.payment_date_entry.pack(side='right', padx=5)
        self.payment_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        
        tk.Label(header_fields_frame, text="رقم السند:", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=(15, 5))
        self.payment_number_entry = ttk.Entry(header_fields_frame, width=10, font=('Segoe UI', 10, 'bold'), justify='center')
        self.payment_number_entry.pack(side='right', padx=5)
        self.payment_number_entry.configure(state='readonly')
        
        tk.Label(header_fields_frame, text="المشروع العام:", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=(15, 5))
        self.payment_project_combo = ttk.Combobox(header_fields_frame, width=28, state='readonly', font=('Segoe UI', 10))
        self.payment_project_combo.pack(side='right', padx=5)
        
        # سطر إضافة البند السريع
        item_input_frame = ttk.Frame(form_frame)
        item_input_frame.pack(fill='x', padx=10, pady=6)
        
        tk.Label(item_input_frame, text="الحساب (موظف / بند):", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=(5, 2))
        
        account_search_frame = ttk.Frame(item_input_frame)
        account_search_frame.pack(side='right', padx=5)
        
        account_entry_frame = ttk.Frame(account_search_frame)
        account_entry_frame.pack(side='top', fill='x')
        
        self.payment_account_entry = ttk.Entry(account_entry_frame, width=22, font=('Segoe UI', 10))
        self.payment_account_entry.pack(side='right', fill='x', expand=True)
        
        def toggle_account_dropdown():
            if self.account_listbox.winfo_ismapped():
                self.account_listbox.pack_forget()
            else:
                self.account_listbox.delete(0, tk.END)
                for item in getattr(self, 'payment_account_data', []):
                    self.account_listbox.insert(tk.END, item)
                self.account_listbox.pack(side='top', fill='x')
        
        tk.Button(account_entry_frame, text="▼", width=1, height=1, 
                 command=toggle_account_dropdown, 
                 relief='flat', bg='#E0E0E0', fg='black', font=('Segoe UI', 8)).pack(side='right', padx=(1, 0))
        
        self.account_listbox = tk.Listbox(account_search_frame, width=25, height=5, font=('Segoe UI', 9))
        self.account_listbox.pack(side='top', fill='x')
        self.account_listbox.pack_forget()
        
        def on_account_select(event):
            selection = self.account_listbox.curselection()
            if selection:
                selected_value = self.account_listbox.get(selection[0])
                self.payment_account_entry.delete(0, tk.END)
                self.payment_account_entry.insert(0, selected_value)
                self.account_listbox.pack_forget()
                self.payment_desc_entry.focus_set()
        
        self.account_listbox.bind('<<ListboxSelect>>', on_account_select)
        
        def on_account_search(event):
            search_text = self.payment_account_entry.get().strip()
            if search_text:
                matches = [item for item in getattr(self, 'payment_account_data', []) if search_text.lower() in item.lower()]
                self.account_listbox.delete(0, tk.END)
                for match in matches:
                    self.account_listbox.insert(tk.END, match)
                if matches:
                    self.account_listbox.pack(side='top', fill='x')
                else:
                    self.account_listbox.pack_forget()
            else:
                self.account_listbox.pack_forget()
        
        self.payment_account_entry.bind('<KeyRelease>', on_account_search)
        
        tk.Label(item_input_frame, text="البيان / الوصف:", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=(10, 2))
        self.payment_desc_entry = ttk.Entry(item_input_frame, width=26, font=('Segoe UI', 10))
        self.payment_desc_entry.pack(side='right', padx=5)
        
        tk.Label(item_input_frame, text="المبلغ (ريال):", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=(10, 2))
        self.payment_amount_entry = ttk.Entry(item_input_frame, width=12, font=('Segoe UI', 10), justify='center')
        self.payment_amount_entry.pack(side='right', padx=5)
        
        ttk.Button(item_input_frame, text="➕ إضافة للبند (Enter)", command=self.add_payment_item).pack(side='right', padx=5)
        ttk.Button(item_input_frame, text="📋 إدخال عدة بنود معاً", command=self.open_batch_payment_dialog).pack(side='right', padx=5)
        
        self.payment_account_entry.bind('<Return>', lambda e: self.payment_desc_entry.focus_set())
        self.payment_desc_entry.bind('<Return>', lambda e: self.payment_amount_entry.focus_set())
        self.payment_amount_entry.bind('<Return>', lambda e: self.add_payment_item())
        
        # جدول بنود السند الحالي
        tree_container = ttk.Frame(form_frame)
        tree_container.pack(fill='both', expand=True, padx=10, pady=5)
        
        columns = ('account', 'project', 'description', 'amount')
        self.payment_tree = ttk.Treeview(tree_container, columns=columns, show='headings', height=5)
        self.payment_tree.heading('account', text='الحساب / المستفيد')
        self.payment_tree.heading('project', text='المشروع')
        self.payment_tree.heading('description', text='البيان / الوصف')
        self.payment_tree.heading('amount', text='المبلغ (ريال)')
        
        self.payment_tree.column('account', width=200)
        self.payment_tree.column('project', width=160)
        self.payment_tree.column('description', width=280)
        self.payment_tree.column('amount', width=120, anchor='center')
        
        self.payment_tree.pack(side='left', fill='both', expand=True)
        payment_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.payment_tree.yview)
        payment_scrollbar.pack(side='right', fill='y')
        self.payment_tree.configure(yscrollcommand=payment_scrollbar.set)
        
        # شريط أزرار وملخص السند الحالي
        voucher_action_frame = ttk.Frame(form_frame)
        voucher_action_frame.pack(fill='x', padx=10, pady=8)
        
        self.save_btn = ttk.Button(voucher_action_frame, text="💾 حفظ السند", command=self.save_payment_voucher)
        self.save_btn.pack(side='right', padx=5)
        
        self.save_and_print_btn = ttk.Button(voucher_action_frame, text="🖨️ حفظ وطباعة", command=lambda: self.save_payment_voucher(and_print=True))
        self.save_and_print_btn.pack(side='right', padx=5)
        
        ttk.Button(voucher_action_frame, text="🗑️ حذف البند المحدد", command=self.delete_payment_item).pack(side='right', padx=5)
        ttk.Button(voucher_action_frame, text="🔄 تفريغ النموذج", command=self.clear_payment_form).pack(side='right', padx=5)
        
        self.cancel_edit_btn = ttk.Button(voucher_action_frame, text="❌ إلغاء التعديل", command=self.cancel_edit_voucher)
        
        # ملخص بنود السند
        summary_box = ttk.Frame(voucher_action_frame)
        summary_box.pack(side='left', padx=10)
        
        self.payment_items_count_label = tk.Label(summary_box, text="عدد البنود: 0", font=('Segoe UI', 10, 'bold'), fg='#555555')
        self.payment_items_count_label.pack(side='left', padx=10)
        
        tk.Label(summary_box, text="إجمالي السند:", font=('Segoe UI', 12, 'bold')).pack(side='left', padx=5)
        self.total_label = tk.Label(summary_box, text="0.00 ريال", font=('Segoe UI', 13, 'bold'), fg='#1E8449')
        self.total_label.pack(side='left', padx=5)
        
        # =========================================================
        # القسم الثاني: سجل سندات الصرف المسجلة (مباشرة في نفس الشاشة)
        # =========================================================
        saved_frame = ttk.LabelFrame(main_container, text="📋 سجل سندات الصرف المحفوظة (معروضة ومباشرة للتحكم والطباعة)")
        saved_frame.pack(fill='both', expand=True, padx=5, pady=(5, 5))
        
        # شريط البحث والفلترة
        filter_bar = ttk.Frame(saved_frame)
        filter_bar.pack(fill='x', padx=10, pady=6)
        
        tk.Label(filter_bar, text="🔍 بحث سريع:", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        self.voucher_filter_entry = ttk.Entry(filter_bar, width=22, font=('Segoe UI', 10))
        self.voucher_filter_entry.pack(side='right', padx=5)
        self.voucher_filter_entry.bind('<KeyRelease>', lambda e: self.load_saved_payment_vouchers())
        
        tk.Label(filter_bar, text="📅 التاريخ:", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=(15, 5))
        self.voucher_filter_date = ttk.Entry(filter_bar, width=12, font=('Segoe UI', 10))
        self.voucher_filter_date.pack(side='right', padx=5)
        self.voucher_filter_date.bind('<KeyRelease>', lambda e: self.load_saved_payment_vouchers())
        
        def set_filter_today():
            self.voucher_filter_date.delete(0, tk.END)
            self.voucher_filter_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
            self.load_saved_payment_vouchers()
            
        def clear_filter_date():
            self.voucher_filter_date.delete(0, tk.END)
            self.load_saved_payment_vouchers()
            
        ttk.Button(filter_bar, text="اليوم", command=set_filter_today, width=8).pack(side='right', padx=3)
        ttk.Button(filter_bar, text="عرض الكل", command=clear_filter_date, width=10).pack(side='right', padx=3)
        ttk.Button(filter_bar, text="تحديث السجل 🔄", command=lambda: self.load_saved_payment_vouchers(), width=14).pack(side='right', padx=5)
        
        self.saved_vouchers_summary_label = tk.Label(filter_bar, text="عدد السندات: 0 | الإجمالي: 0.00 ريال", font=('Segoe UI', 10, 'bold'), fg='#2471A3')
        self.saved_vouchers_summary_label.pack(side='left', padx=10)
        
        # جدول السندات المحفوظة
        saved_tree_container = ttk.Frame(saved_frame)
        saved_tree_container.pack(fill='both', expand=True, padx=10, pady=5)
        
        v_cols = ('number', 'date', 'account', 'description', 'project', 'items_count', 'total')
        self.saved_vouchers_tree = ttk.Treeview(saved_tree_container, columns=v_cols, show='headings', height=7)
        
        self.saved_vouchers_tree.heading('number', text='رقم السند')
        self.saved_vouchers_tree.heading('date', text='التاريخ')
        self.saved_vouchers_tree.heading('account', text='الحساب / المستفيد')
        self.saved_vouchers_tree.heading('description', text='البيان / الوصف')
        self.saved_vouchers_tree.heading('project', text='المشروع')
        self.saved_vouchers_tree.heading('items_count', text='عدد البنود')
        self.saved_vouchers_tree.heading('total', text='المبلغ الإجمالي')
        
        self.saved_vouchers_tree.column('number', width=90, anchor='center')
        self.saved_vouchers_tree.column('date', width=100, anchor='center')
        self.saved_vouchers_tree.column('account', width=180)
        self.saved_vouchers_tree.column('description', width=220)
        self.saved_vouchers_tree.column('project', width=140)
        self.saved_vouchers_tree.column('items_count', width=80, anchor='center')
        self.saved_vouchers_tree.column('total', width=110, anchor='center')
        
        self.saved_vouchers_tree.pack(side='left', fill='both', expand=True)
        saved_scrollbar = ttk.Scrollbar(saved_tree_container, orient="vertical", command=self.saved_vouchers_tree.yview)
        saved_scrollbar.pack(side='right', fill='y')
        self.saved_vouchers_tree.configure(yscrollcommand=saved_scrollbar.set)
        
        # ربط النقر المزدوج للتعديل الفوري
        self.saved_vouchers_tree.bind('<Double-1>', lambda e: self.load_selected_voucher_for_edit())
        
        # أزرار العمليات المباشرة على السندات المسجلة
        saved_buttons_bar = ttk.Frame(saved_frame)
        saved_buttons_bar.pack(fill='x', padx=10, pady=8)
        
        ttk.Button(saved_buttons_bar, text="✏️ تعديل السند المحدد", command=self.load_selected_voucher_for_edit).pack(side='right', padx=5)
        ttk.Button(saved_buttons_bar, text="🖨️ طباعة السند (PDF)", command=self.print_selected_payment_voucher).pack(side='right', padx=5)
        ttk.Button(saved_buttons_bar, text="🗑️ حذف السند بالكامل", command=self.delete_selected_payment_voucher).pack(side='right', padx=5)
        ttk.Button(saved_buttons_bar, text="🖨️ طباعة كشف اليوم", command=self.print_daily_payment_report).pack(side='right', padx=5)
        
        # تحديث الحسابات وبيانات السندات
        self.update_payment_voucher_number()
        self.payment_tree.bind('<ButtonRelease-1>', self.update_payment_total)
        self.load_payment_data()
        self.load_saved_payment_vouchers()
    
    def create_journal_voucher_tab(self, notebook):
        """إنشاء تبويب سند اليومية مطابق للصورة - سطرين: مدين ودائن"""
        journal_frame = ttk.Frame(notebook)
        notebook.add(journal_frame, text="📒 سند اليومية")
        
        # إطار رئيسي
        main_container = ttk.Frame(journal_frame)
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # عنوان
        title_label = tk.Label(main_container, text="📒 سند اليومية", 
                              font=('Segoe UI', 16, 'bold'))
        title_label.pack(pady=10)
        
        # إطار معلومات السند
        info_frame = ttk.LabelFrame(main_container, text="معلومات السند")
        info_frame.pack(fill='x', pady=10)
        
        # التاريخ والرقم والمشروع
        date_frame = ttk.Frame(info_frame)
        date_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(date_frame, text="التاريخ:", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        self.journal_date_entry = ttk.Entry(date_frame, width=15)
        self.journal_date_entry.pack(side='right', padx=5)
        self.journal_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        
        tk.Label(date_frame, text="رقم السند:", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        self.journal_number_entry = ttk.Entry(date_frame, width=15, state='readonly')
        self.journal_number_entry.pack(side='right', padx=5)
        
        tk.Label(date_frame, text="المشروع:", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        self.journal_project_combo = ttk.Combobox(date_frame, width=25, state='readonly')
        self.journal_project_combo.pack(side='right', padx=5)
        
        # حقل اختيار من بنود الحسابات (مثل سند الصرف)
        tk.Label(date_frame, text="اختر من بنود الحسابات:", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        
        # إطار الوصف مع البحث
        desc_search_frame = ttk.Frame(date_frame)
        desc_search_frame.pack(side='right', padx=5)
        
        # إطار للـ Entry والزر
        desc_entry_frame = ttk.Frame(desc_search_frame)
        desc_entry_frame.pack(side='top', fill='x')
        
        self.journal_desc_search_entry = ttk.Entry(desc_entry_frame, width=20)
        self.journal_desc_search_entry.pack(side='right', fill='x', expand=True)
        
        # زر Dropdown
        def toggle_journal_desc_dropdown():
            if self.journal_desc_listbox.winfo_ismapped():
                self.journal_desc_listbox.pack_forget()
            else:
                self.journal_desc_listbox.delete(0, tk.END)
                for item in self.journal_desc_listbox_data:
                    self.journal_desc_listbox.insert(tk.END, item)
                self.journal_desc_listbox.pack(side='top', fill='x')
        
        tk.Button(desc_entry_frame, text="▼", width=1, height=1, 
                 command=toggle_journal_desc_dropdown, 
                 relief='flat', bg='#E0E0E0', fg='black', font=('Segoe UI', 8)).pack(side='right', padx=(1, 0))
        
        # Listbox للنتائج
        self.journal_desc_listbox = tk.Listbox(desc_search_frame, width=25, height=5, font=('Segoe UI', 10))
        self.journal_desc_listbox.pack(side='top', fill='x')
        self.journal_desc_listbox.pack_forget()
        
        # ربط اختيار من القائمة - يملأ الوصف تلقائياً
        def on_journal_desc_select(event):
            selection = self.journal_desc_listbox.curselection()
            if selection:
                selected_value = self.journal_desc_listbox.get(selection[0])
                self.journal_desc_search_entry.delete(0, tk.END)
                self.journal_desc_search_entry.insert(0, selected_value)
                # ملء الوصف تلقائياً في حقول المدين والدائن
                self.journal_debit_desc_entry.delete(0, tk.END)
                self.journal_debit_desc_entry.insert(0, selected_value)
                self.journal_credit_desc_entry.delete(0, tk.END)
                self.journal_credit_desc_entry.insert(0, selected_value)
                self.journal_desc_listbox.pack_forget()
        
        self.journal_desc_listbox.bind('<<ListboxSelect>>', on_journal_desc_select)
        
        # تحميل بنود الحسابات للبحث
        self.journal_desc_listbox_data = []
        account_items = self.db.execute_query("SELECT number, name FROM account_items ORDER BY number")
        for item in account_items:
            self.journal_desc_listbox_data.append(f"{item[0]} - {item[1]}")
        
        # البحث الفوري - يدعم البحث بالكود أو الاسم
        def on_journal_desc_search(event):
            search_text = self.journal_desc_search_entry.get()
            if search_text:
                # البحث في الكود أو الاسم
                matches = []
                for item in self.journal_desc_listbox_data:
                    # تقسيم العنصر لفصل الكود عن الاسم
                    parts = item.split(' - ', 1)
                    code = parts[0] if parts else ""
                    name = parts[1] if len(parts) > 1 else item
                    
                    # البحث بالكود أو الاسم
                    if search_text.lower() in code.lower() or search_text.lower() in name.lower():
                        matches.append(item)
                
                self.journal_desc_listbox.delete(0, tk.END)
                for match in matches:
                    self.journal_desc_listbox.insert(tk.END, match)
                if matches:
                    self.journal_desc_listbox.pack(side='top', fill='x')
                else:
                    self.journal_desc_listbox.pack_forget()
            else:
                self.journal_desc_listbox.pack_forget()
        
        self.journal_desc_search_entry.bind('<KeyRelease>', on_journal_desc_search)
        
        # إطار بنود السند
        items_frame = ttk.LabelFrame(main_container, text="بنود السند")
        items_frame.pack(fill='both', expand=True, pady=10)
        
        # جدول البنود - 6 أعمدة: الرقم، حساب مدين، مبلغ مدين، حساب دائن، مبلغ دائن، الوصف، المشروع
        columns = ('row_num', 'debit_account', 'debit_amount', 'credit_account', 'credit_amount', 'description', 'project')
        self.journal_tree = ttk.Treeview(items_frame, columns=columns, show='headings', height=10)
        
        self.journal_tree.heading('row_num', text='#')
        self.journal_tree.heading('debit_account', text='الحساب (مدين)')
        self.journal_tree.heading('debit_amount', text='مدين')
        self.journal_tree.heading('credit_account', text='الحساب (دائن)')
        self.journal_tree.heading('credit_amount', text='دائن')
        self.journal_tree.heading('description', text='البيان')
        self.journal_tree.heading('project', text='المشروع')
        
        self.journal_tree.column('row_num', width=30, anchor='center')
        self.journal_tree.column('debit_account', width=180)
        self.journal_tree.column('debit_amount', width=80)
        self.journal_tree.column('credit_account', width=180)
        self.journal_tree.column('credit_amount', width=80)
        self.journal_tree.column('description', width=200)
        self.journal_tree.column('project', width=120)
        
        self.journal_tree.pack(side='left', fill='both', expand=True)
        
        # شريط تمرير
        journal_scrollbar = ttk.Scrollbar(items_frame, orient="vertical", command=self.journal_tree.yview)
        journal_scrollbar.pack(side='right', fill='y')
        self.journal_tree.configure(yscrollcommand=journal_scrollbar.set)
        
        # إطار إضافة بند جديد - سطر المدين
        debit_frame = ttk.Frame(items_frame)
        debit_frame.pack(fill='x', pady=5)
        
        tk.Label(debit_frame, text="الحساب (مدين):", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        
        # إطار الحساب مع البحث والDropdown
        debit_account_frame = ttk.Frame(debit_frame)
        debit_account_frame.pack(side='right', padx=5)
        
        # إطار للـ Entry والزر
        debit_entry_frame = ttk.Frame(debit_account_frame)
        debit_entry_frame.pack(side='top', fill='x')
        
        self.journal_debit_account_entry = ttk.Entry(debit_entry_frame, width=20)
        self.journal_debit_account_entry.pack(side='right', fill='x', expand=True)
        
        # زر Dropdown
        def toggle_debit_dropdown():
            if self.journal_debit_listbox.winfo_ismapped():
                self.journal_debit_listbox.pack_forget()
            else:
                self.journal_debit_listbox.delete(0, tk.END)
                for item in self.journal_account_data:
                    self.journal_debit_listbox.insert(tk.END, item)
                self.journal_debit_listbox.pack(side='top', fill='x')
        
        tk.Button(debit_entry_frame, text="▼", width=1, height=1, 
                 command=toggle_debit_dropdown, 
                 relief='flat', bg='#E0E0E0', fg='black', font=('Segoe UI', 8)).pack(side='right', padx=(1, 0))
        
        # Listbox للنتائج
        self.journal_debit_listbox = tk.Listbox(debit_account_frame, width=25, height=5, font=('Segoe UI', 10))
        self.journal_debit_listbox.pack(side='top', fill='x')
        self.journal_debit_listbox.pack_forget()
        
        # ربط اختيار من القائمة
        def on_debit_select(event):
            selection = self.journal_debit_listbox.curselection()
            if selection:
                selected_value = self.journal_debit_listbox.get(selection[0])
                self.journal_debit_account_entry.delete(0, tk.END)
                self.journal_debit_account_entry.insert(0, selected_value)
                self.journal_debit_listbox.pack_forget()
        
        self.journal_debit_listbox.bind('<<ListboxSelect>>', on_debit_select)
        
        # البحث الفوري
        def on_debit_search(event):
            search_text = self.journal_debit_account_entry.get()
            if search_text:
                matches = [item for item in self.journal_account_data if search_text.lower() in item.lower()]
                self.journal_debit_listbox.delete(0, tk.END)
                for match in matches:
                    self.journal_debit_listbox.insert(tk.END, match)
                if matches:
                    self.journal_debit_listbox.pack(side='top', fill='x')
                else:
                    self.journal_debit_listbox.pack_forget()
            else:
                self.journal_debit_listbox.pack_forget()
        
        self.journal_debit_account_entry.bind('<KeyRelease>', on_debit_search)
        
        tk.Label(debit_frame, text="مدين:", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        self.journal_debit_entry = ttk.Entry(debit_frame, width=15)
        self.journal_debit_entry.pack(side='right', padx=5)
        
        tk.Label(debit_frame, text="الوصف:", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        self.journal_debit_desc_entry = ttk.Entry(debit_frame, width=30)
        self.journal_debit_desc_entry.pack(side='right', padx=5)
        
        # إطار إضافة بند جديد - سطر الدائن
        credit_frame = ttk.Frame(items_frame)
        credit_frame.pack(fill='x', pady=5)
        
        tk.Label(credit_frame, text="الحساب (دائن):", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        
        # إطار الحساب مع البحث والDropdown
        credit_account_frame = ttk.Frame(credit_frame)
        credit_account_frame.pack(side='right', padx=5)
        
        # إطار للـ Entry والزر
        credit_entry_frame = ttk.Frame(credit_account_frame)
        credit_entry_frame.pack(side='top', fill='x')
        
        self.journal_credit_account_entry = ttk.Entry(credit_entry_frame, width=20)
        self.journal_credit_account_entry.pack(side='right', fill='x', expand=True)
        
        # زر Dropdown
        def toggle_credit_dropdown():
            if self.journal_credit_listbox.winfo_ismapped():
                self.journal_credit_listbox.pack_forget()
            else:
                self.journal_credit_listbox.delete(0, tk.END)
                for item in self.journal_account_data:
                    self.journal_credit_listbox.insert(tk.END, item)
                self.journal_credit_listbox.pack(side='top', fill='x')
        
        tk.Button(credit_entry_frame, text="▼", width=1, height=1, 
                 command=toggle_credit_dropdown, 
                 relief='flat', bg='#E0E0E0', fg='black', font=('Segoe UI', 8)).pack(side='right', padx=(1, 0))
        
        # Listbox للنتائج
        self.journal_credit_listbox = tk.Listbox(credit_account_frame, width=25, height=5, font=('Segoe UI', 10))
        self.journal_credit_listbox.pack(side='top', fill='x')
        self.journal_credit_listbox.pack_forget()
        
        # ربط اختيار من القائمة
        def on_credit_select(event):
            selection = self.journal_credit_listbox.curselection()
            if selection:
                selected_value = self.journal_credit_listbox.get(selection[0])
                self.journal_credit_account_entry.delete(0, tk.END)
                self.journal_credit_account_entry.insert(0, selected_value)
                self.journal_credit_listbox.pack_forget()
        
        self.journal_credit_listbox.bind('<<ListboxSelect>>', on_credit_select)
        
        # البحث الفوري
        def on_credit_search(event):
            search_text = self.journal_credit_account_entry.get()
            if search_text:
                matches = [item for item in self.journal_account_data if search_text.lower() in item.lower()]
                self.journal_credit_listbox.delete(0, tk.END)
                for match in matches:
                    self.journal_credit_listbox.insert(tk.END, match)
                if matches:
                    self.journal_credit_listbox.pack(side='top', fill='x')
                else:
                    self.journal_credit_listbox.pack_forget()
            else:
                self.journal_credit_listbox.pack_forget()
        
        self.journal_credit_account_entry.bind('<KeyRelease>', on_credit_search)
        
        tk.Label(credit_frame, text="دائن:", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        self.journal_credit_entry = ttk.Entry(credit_frame, width=15, state='readonly')
        self.journal_credit_entry.pack(side='right', padx=5)
        
        tk.Label(credit_frame, text="الوصف:", font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        self.journal_credit_desc_entry = ttk.Entry(credit_frame, width=30)
        self.journal_credit_desc_entry.pack(side='right', padx=5)
        
        # ⚠️ ربط حدث تغيير المبلغ في المدين لنسخه تلقائياً للدائن
        def on_debit_amount_change(event=None):
            """عند تغيير مبلغ المدين، ينسخ تلقائياً للدائن"""
            try:
                debit_amount = self.journal_debit_entry.get()
                if debit_amount:
                    self.journal_credit_entry.configure(state='normal')
                    self.journal_credit_entry.delete(0, tk.END)
                    self.journal_credit_entry.insert(0, debit_amount)
                    self.journal_credit_entry.configure(state='readonly')
            except:
                pass
        
        self.journal_debit_entry.bind('<KeyRelease>', on_debit_amount_change)
        self.journal_debit_entry.bind('<FocusOut>', on_debit_amount_change)
        
        # أزرار
        btn_frame = ttk.Frame(main_container)
        btn_frame.pack(fill='x', pady=10)
        
        ttk.Button(btn_frame, text="➕ إضافة بند", command=self.add_journal_item).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="💾 حفظ السند", command=self.save_journal_voucher).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="🗑️ حذف بند", command=self.delete_journal_item).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="🔄 مسح الكل", command=self.clear_journal_form).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="👁️ عرض السندات", command=self.view_journal_vouchers).pack(side='right', padx=5)
        
        # إطار عرض التوازن
        balance_display_frame = ttk.Frame(main_container)
        balance_display_frame.pack(fill='x', pady=5)
        
        tk.Label(balance_display_frame, text="⚖️ المدين = الدائن (توازن تلقائي)", 
                font=('Segoe UI', 11, 'bold'), fg='green').pack(side='right', padx=10)
        
        # تحميل البيانات
        self.load_journal_data()
    
    def create_account_items_tab(self, notebook):
        """إنشاء تبويب بنود الحسابات"""
        account_frame = ttk.Frame(notebook)
        notebook.add(account_frame, text="📋 بنود الحسابات")
        
        # إطار رئيسي
        main_container = ttk.Frame(account_frame)
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # عنوان
        title_label = tk.Label(main_container, text="📋 بنود الحسابات", 
                              font=('Segoe UI', 16, 'bold'))
        title_label.pack(pady=10)
        
        # إطار الأزرار
        btn_frame = ttk.Frame(main_container)
        btn_frame.pack(fill='x', pady=10)
        
        ttk.Button(btn_frame, text="➕ إضافة بند جديد", command=self.add_account_item).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="📋 إضافة عدة بنود معاً", command=self.add_multiple_account_items).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="✏️ تعديل", command=self.edit_account_item).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="🗑️ حذف", command=self.delete_account_item).pack(side='right', padx=5)
        
        # إطار الجدول
        table_frame = ttk.LabelFrame(main_container, text="قائمة بنود الحسابات")
        table_frame.pack(fill='both', expand=True, pady=10)
        
        # جدول بنود الحسابات
        columns = ('id', 'number', 'name')
        self.account_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        self.account_tree.heading('id', text='الرقم')
        self.account_tree.heading('number', text='كود البند')
        self.account_tree.heading('name', text='اسم بند الحساب')
        
        self.account_tree.column('id', width=60, anchor='center')
        self.account_tree.column('number', width=120, anchor='center')
        self.account_tree.column('name', width=350, anchor='e')
        
        self.account_tree.pack(side='left', fill='both', expand=True)
        
        # شريط تمرير
        account_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.account_tree.yview)
        account_scrollbar.pack(side='right', fill='y')
        self.account_tree.configure(yscrollcommand=account_scrollbar.set)
        
        # تحميل البيانات
        self.load_account_items()
    
    def load_cash_data(self):
        """تحميل بيانات الصندوق"""
        try:
            # تحديث الرصيد
            income_result = self.db.execute_query("SELECT COALESCE(SUM(amount), 0) FROM treasury_transactions WHERE type = 'income'")
            expense_result = self.db.execute_query("SELECT COALESCE(SUM(amount), 0) FROM treasury_transactions WHERE type = 'expense'")
            
            total_income = income_result[0][0] if income_result else 0
            total_expense = expense_result[0][0] if expense_result else 0
            balance = total_income - total_expense
            
            if hasattr(self, 'cash_balance_label'):
                self.cash_balance_label.config(text=f"الرصيد الحالي: {balance:.2f} ريال")
            
            # تحميل الحركات
            self.update_cash_data()
            
        except Exception as e:
            print(f"خطأ في تحديث بيانات الصندوق: {e}")
    
    def update_cash_data(self):
        """update cash data table"""
        try:
            # clear table
            for item in self.cash_tree.get_children():
                self.cash_tree.delete(item)
            
            # load data
            transactions = self.db.execute_query("""
                SELECT id, date, type, description, amount, account_name 
                FROM treasury_transactions 
                ORDER BY date DESC, id DESC
            """)
            
            for trans in transactions:
                self.cash_tree.insert('', 'end', values=trans)
            
            # update payment voucher number if payment_number_entry exists
            if hasattr(self, 'payment_number_entry'):
                from datetime import datetime
                today = datetime.now().strftime('%Y-%m-%d')
                
                # get distinct days with vouchers
                result = self.db.execute_query('''
                    SELECT DISTINCT date 
                    FROM treasury_transactions 
                    WHERE type = 'expense' AND description LIKE 'voucher #%'
                    ORDER BY date ASC
                ''')
                
                # calculate days before today
                distinct_days_before_today = 0
                if result:
                    for row in result:
                        voucher_date = row[0]
                        if voucher_date < today:
                            distinct_days_before_today += 1
                        else:
                            break
                
                # calculate new number
                new_number = distinct_days_before_today + 1
                
                # check if today has vouchers
                today_has_vouchers = self.db.execute_query('''
                    SELECT 1 FROM treasury_transactions 
                    WHERE date = ? AND type = 'expense' AND description LIKE 'voucher #%'
                    LIMIT 1
                ''', (today,))
                
                # if today has vouchers, get today's number
                if today_has_vouchers:
                    today_voucher = self.db.execute_query('''
                        SELECT description 
                        FROM treasury_transactions 
                        WHERE date = ? AND type = 'expense' AND description LIKE 'voucher #%'
                        ORDER BY id ASC LIMIT 1
                    ''', (today,))
                    if today_voucher and today_voucher[0][0]:
                        import re
                        match = re.search(r'#(\d+)', today_voucher[0][0])
                        if match:
                            new_number = int(match.group(1))
                
                self.payment_number_entry.configure(state='normal')
                self.payment_number_entry.delete(0, tk.END)
                self.payment_number_entry.insert(0, str(new_number))
                self.payment_number_entry.configure(state='readonly')
            
        except Exception as e:
            print(f"error updating cash data: {e}")
            # set default number if payment_number_entry exists
            if hasattr(self, 'payment_number_entry'):
                try:
                    self.payment_number_entry.configure(state='normal')
                    self.payment_number_entry.delete(0, tk.END)
                    self.payment_number_entry.insert(0, "1")
                    self.payment_number_entry.configure(state='readonly')
                except:
                    pass
    
    def update_payment_total(self, event=None):
        """تحديث المجموع تلقائياً"""
        try:
            total = 0.0
            for child in self.payment_tree.get_children():
                values = self.payment_tree.item(child, 'values')
                if values:
                    try:
                        total += float(values[-1])
                    except (ValueError, TypeError):
                        pass
            
            if hasattr(self, 'payment_balance_label'):
                self.payment_balance_label.config(text=f"{total:.2f} ريال")
            
            # تحديث الإجمالي
            if hasattr(self, 'total_label'):
                self.total_label.config(text=f"{total:.2f} ريال")
            
        except Exception as e:
            print(f"خطأ في تحديث المجموع: {e}")
    
    def load_payment_data(self):
        """load payment voucher data - projects, customers, account items, employees"""
        try:
            # load projects
            projects = self.db.execute_query("SELECT id, name FROM projects ORDER BY name")
            project_names = [f"{proj[0]} - {proj[1]}" for proj in projects]
            
            # load customers
            customers = self.db.execute_query("SELECT id, name FROM customers ORDER BY name")
            customer_names = [f"{cust[0]} - {cust[1]}" for cust in customers]
            
            # load account items
            accounts = self.db.execute_query("SELECT name FROM account_items ORDER BY name")
            account_names = [acc[0] for acc in accounts]
            
            # load employees
            employees = self.db.execute_query("SELECT id, name FROM employees ORDER BY name")
            employee_names = [f"{emp[0]} - {emp[1]}" for emp in employees]
            
            # دمج بنود الحسابات والموظفين فقط (بدون مشاريع أو عملاء بناءً على طلب المستخدم)
            self.payment_account_data = account_names + employee_names
            
            # load projects for main project
            if hasattr(self, 'payment_project_combo'):
                self.payment_project_combo['values'] = ["-- select project --"] + project_names if project_names else ["-- select project --"]
                if self.payment_project_combo['values']:
                    self.payment_project_combo.current(0)
            
            # load account items for description
            if hasattr(self, 'desc_listbox_data'):
                self.desc_listbox_data = account_names
            # تحديث القائمة الفعلية في الواجهة
            if hasattr(self, 'desc_listbox'):
                self.desc_listbox.delete(0, tk.END)
                for item in account_names:
                    self.desc_listbox.insert(tk.END, item)
            
            # update voucher number automatically
            self.update_payment_voucher_number()
            
        except Exception as e:
            print(f"error loading payment voucher data: {e}")
    
    def get_account_items_list(self):
        """الحصول على قائمة بنود الحسابات للقوائم المنسدلة"""
        try:
            return self.db.execute_query("SELECT id, number, name FROM account_items ORDER BY number")
        except Exception as e:
            print(f"error loading account items: {e}")
            return []
    
    def get_next_payment_voucher_number(self):
        """الحصول على رقم السند التالي تلقائياً متسلسل"""
        try:
            import re
            rows = self.db.execute_query('''
                SELECT description FROM treasury_transactions 
                WHERE (description LIKE 'سند صرف #%' OR description LIKE 'سند خزينة #%' OR description LIKE '%سند%#%')
            ''')
            max_num = 0
            if rows:
                for r in rows:
                    desc = r[0] or ""
                    m = re.search(r'#(\d+)', desc)
                    if m:
                        num = int(m.group(1))
                        if num > max_num:
                            max_num = num
            return max_num + 1
        except Exception as e:
            print(f"Error calculating next voucher number: {e}")
            return 1

    def update_payment_voucher_number(self):
        """تحديث رقم سند الصرف تلقائياً برقم متسلسل جديد"""
        try:
            if not hasattr(self, 'payment_number_entry'):
                return
            if getattr(self, 'editing_voucher_data', None):
                return
            new_number = self.get_next_payment_voucher_number()
            self.payment_number_entry.configure(state='normal')
            self.payment_number_entry.delete(0, tk.END)
            self.payment_number_entry.insert(0, str(new_number))
            self.payment_number_entry.configure(state='readonly')
        except Exception as e:
            print(f"error updating payment voucher number: {e}")
            if hasattr(self, 'payment_number_entry'):
                try:
                    self.payment_number_entry.configure(state='normal')
                    self.payment_number_entry.delete(0, tk.END)
                    self.payment_number_entry.insert(0, "1")
                    self.payment_number_entry.configure(state='readonly')
                except:
                    pass

    def load_saved_payment_vouchers(self):
        """تحميل وعرض جميع سندات الصرف في الجدول المباشر كفاتورة موحدة"""
        try:
            if not hasattr(self, 'saved_vouchers_tree'):
                return
            
            self.saved_vouchers_tree.delete(*self.saved_vouchers_tree.get_children())
            self.cached_saved_vouchers = {}
            
            rows = self.db.execute_query('''
                SELECT t.id, t.date, t.description, t.amount, t.account_name, t.project_id, p.name as project_name
                FROM treasury_transactions t
                LEFT JOIN projects p ON t.project_id = p.id
                WHERE t.type = 'expense' AND (t.description LIKE 'سند صرف #%' OR t.description LIKE 'سند خزينة #%')
                ORDER BY t.date DESC, t.id DESC
            ''')
            
            import re
            vouchers = {}
            if rows:
                for r in rows:
                    tid, tdate, tdesc, tamt, taccount, tproj_id, tproj_name = r
                    m = re.search(r'#(\d+)', tdesc or '')
                    vnum = m.group(1) if m else str(tid)
                    key = (vnum, tdate)
                    if key not in vouchers:
                        vouchers[key] = {
                            'number': vnum,
                            'date': tdate,
                            'items': [],
                            'total': 0.0,
                            'accounts': [],
                            'descriptions': [],
                            'project_name': tproj_name or 'غير محدد',
                            'project_id': tproj_id
                        }
                    
                    clean_desc = tdesc.split('-', 1)[1].strip() if '-' in tdesc else tdesc
                    if '(مشروع:' in clean_desc:
                        clean_desc = clean_desc.split('(مشروع:')[0].strip()
                        
                    vouchers[key]['items'].append({
                        'id': tid,
                        'account': taccount or 'غير محدد',
                        'description': clean_desc,
                        'amount': float(tamt) if tamt else 0.0,
                        'project_name': tproj_name or 'غير محدد',
                        'project_id': tproj_id
                    })
                    vouchers[key]['total'] += float(tamt) if tamt else 0.0
                    
                    if taccount and taccount not in vouchers[key]['accounts']:
                        vouchers[key]['accounts'].append(taccount)
                    if clean_desc and clean_desc not in vouchers[key]['descriptions']:
                        vouchers[key]['descriptions'].append(clean_desc)
                    if tproj_name and vouchers[key]['project_name'] == 'غير محدد':
                        vouchers[key]['project_name'] = tproj_name
                        vouchers[key]['project_id'] = tproj_id

            self.cached_saved_vouchers = vouchers
            
            filter_date_str = (self.voucher_filter_date.get() if hasattr(self, 'voucher_filter_date') else '').strip()
            search_query_str = (self.voucher_filter_entry.get() if hasattr(self, 'voucher_filter_entry') else '').strip().lower()
            
            total_all = 0.0
            count_all = 0
            
            for key, v in vouchers.items():
                if filter_date_str and filter_date_str != 'الكل' and filter_date_str != '':
                    if v['date'] != filter_date_str:
                        continue
                        
                acc_str = '، '.join(v['accounts'])
                desc_str = '، '.join(v['descriptions'])
                proj_str = v['project_name']
                num_str = f"#{v['number']}"
                
                if search_query_str:
                    matched = (
                        search_query_str in num_str.lower() or
                        search_query_str in v['number'].lower() or
                        search_query_str in v['date'].lower() or
                        search_query_str in acc_str.lower() or
                        search_query_str in desc_str.lower() or
                        search_query_str in proj_str.lower()
                    )
                    if not matched:
                        continue
                        
                items_count = len(v['items'])
                total_fmt = f"{v['total']:,.2f} ريال"
                row_id = f"{v['number']}_{v['date']}"
                
                self.saved_vouchers_tree.insert('', 'end', iid=row_id, values=(
                    num_str,
                    v['date'],
                    acc_str[:30] + ('...' if len(acc_str) > 30 else ''),
                    desc_str[:35] + ('...' if len(desc_str) > 35 else ''),
                    proj_str,
                    f"{items_count} بنود",
                    total_fmt
                ))
                total_all += v['total']
                count_all += 1
                
            if hasattr(self, 'saved_vouchers_summary_label'):
                self.saved_vouchers_summary_label.config(
                    text=f"عدد السندات: {count_all}  |  الإجمالي: {total_all:,.2f} ريال"
                )
        except Exception as e:
            print(f"Error loading saved payment vouchers: {e}")

    def load_selected_voucher_for_edit(self):
        """تحميل السند المحدد مع كافة بنوده في نموذج الإدخال للتعديل عليه كالفاتورة"""
        if not hasattr(self, 'saved_vouchers_tree'):
            return
        selected = self.saved_vouchers_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار سند من الجدول لتعديله")
            return
            
        row_iid = selected[0]
        parts = row_iid.split('_', 1)
        vnum = parts[0]
        vdate = parts[1] if len(parts) > 1 else ""
        voucher = self.cached_saved_vouchers.get((vnum, vdate))
        if not voucher:
            messagebox.showerror("خطأ", "❌ تعذر العثور على بيانات السند المحدد")
            return
            
        self.editing_voucher_data = {
            'original_number': vnum,
            'original_date': vdate
        }
        
        self.payment_number_entry.configure(state='normal')
        self.payment_number_entry.delete(0, tk.END)
        self.payment_number_entry.insert(0, str(vnum))
        self.payment_number_entry.configure(state='readonly')
        
        self.payment_date_entry.delete(0, tk.END)
        self.payment_date_entry.insert(0, str(vdate))
        
        proj_name = voucher.get('project_name', '')
        if proj_name and proj_name != 'غير محدد' and hasattr(self, 'payment_project_combo'):
            for idx, val in enumerate(self.payment_project_combo['values']):
                if proj_name in val:
                    self.payment_project_combo.current(idx)
                    break
        else:
            if hasattr(self, 'payment_project_combo') and self.payment_project_combo['values']:
                self.payment_project_combo.current(0)
                
        for item in self.payment_tree.get_children():
            self.payment_tree.delete(item)
            
        for item in voucher['items']:
            self.payment_tree.insert('', 'end', values=(
                item['account'],
                item['project_name'],
                item['description'],
                f"{item['amount']:.2f}"
            ))
            
        self.update_payment_total()
        
        if hasattr(self, 'voucher_mode_label'):
            self.voucher_mode_label.config(
                text=f"✏️ جاري تعديل سند صرف #{vnum} بتاريخ {vdate}", 
                fg='#D35400'
            )
        if hasattr(self, 'save_btn'):
            self.save_btn.config(text="💾 حفظ التعديلات")
        if hasattr(self, 'cancel_edit_btn'):
            self.cancel_edit_btn.pack(side='right', padx=5)
            
        try:
            self.canvas.yview_moveto(0.0)
        except:
            pass

    def cancel_edit_voucher(self):
        """إلغاء وضع التعديل والعودة لوضع إنشاء سند جديد"""
        self.editing_voucher_data = None
        self.clear_payment_form()
        if hasattr(self, 'voucher_mode_label'):
            self.voucher_mode_label.config(text="📝 إنشاء سند صرف جديد", fg='#1B4F72')
        if hasattr(self, 'save_btn'):
            self.save_btn.config(text="💾 حفظ السند")
        if hasattr(self, 'cancel_edit_btn'):
            self.cancel_edit_btn.pack_forget()

    def print_selected_payment_voucher(self):
        """طباعة السند المحدد من الجدول كـ PDF بكل بنوده"""
        if not hasattr(self, 'saved_vouchers_tree'):
            return
        selected = self.saved_vouchers_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار سند من الجدول لطباعته")
            return
            
        row_iid = selected[0]
        parts = row_iid.split('_', 1)
        vnum = parts[0]
        vdate = parts[1] if len(parts) > 1 else ""
        voucher = self.cached_saved_vouchers.get((vnum, vdate))
        if not voucher:
            messagebox.showerror("خطأ", "❌ تعذر العثور على بيانات السند المحدد")
            return
            
        self.generate_voucher_pdf(voucher)

    def generate_voucher_pdf(self, voucher):
        """توليد ملف PDF لسند الصرف مع جميع بنوده وفتحه"""
        try:
            vnum = voucher.get('number', '1')
            vdate = voucher.get('date', datetime.now().strftime('%Y-%m-%d'))
            filename = f"voucher_{vnum}_{vdate.replace('-', '_')}.pdf"
            
            company_settings = self.load_company_settings()
            pdf = CustomVoucherPDF(company_settings)
            pdf.add_page()
            pdf.add_voucher_data(voucher)
            pdf.output(filename)
            
            if os.path.exists(filename):
                try:
                    import webbrowser
                    webbrowser.open(f"file://{os.path.abspath(filename)}")
                except Exception as open_err:
                    print(f"Error opening PDF: {open_err}")
                messagebox.showinfo("نجاح", f"✅ تم إصدار وطباعة سند الصرف #{vnum} بنجاح!\nاسم الملف: {filename}")
            else:
                messagebox.showerror("خطأ", "❌ فشل في حفظ ملف PDF")
        except Exception as e:
            messagebox.showerror("خطأ في الطباعة", f"فشل في إنشاء ملف PDF للسند: {str(e)}")

    def delete_selected_payment_voucher(self):
        """حذف السند المحدد وجميع بنوده بالكامل من الصندوق والمعاملات"""
        if not hasattr(self, 'saved_vouchers_tree'):
            return
        selected = self.saved_vouchers_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار سند من الجدول لحذفه")
            return
            
        row_iid = selected[0]
        parts = row_iid.split('_', 1)
        vnum = parts[0]
        vdate = parts[1] if len(parts) > 1 else ""
        voucher = self.cached_saved_vouchers.get((vnum, vdate))
        if not voucher:
            return
            
        confirm = messagebox.askyesno(
            "تأكيد الحذف",
            f"هل أنت متأكد من حذف سند الصرف #{vnum} بالكامل؟\n\n"
            f"التاريخ: {vdate}\n"
            f"عدد البنود: {len(voucher['items'])}\n"
            f"الإجمالي: {voucher['total']:,.2f} ريال\n\n"
            f"⚠️ هذا الإجراء سيحذف جميع بنود السند من الصندوق ولا يمكن التراجع عنه."
        )
        if not confirm:
            return
            
        try:
            self.db.execute_query('''
                DELETE FROM treasury_transactions 
                WHERE date = ? AND (description LIKE ? OR description LIKE ?)
            ''', (vdate, f'سند صرف #{vnum} - %', f'سند صرف #{vnum}'))
            
            self.db.execute_query('''
                DELETE FROM transactions 
                WHERE date = ? AND (description LIKE ? OR description LIKE ?)
            ''', (vdate, f'سند صرف #{vnum} - %', f'سند صرف #{vnum}'))
            
            try:
                from central_refresh import emit_treasury_change
                emit_treasury_change()
            except:
                pass
                
            self.update_cash_data()
            self.load_saved_payment_vouchers()
            self.update_payment_voucher_number()
            
            if self.editing_voucher_data and self.editing_voucher_data.get('original_number') == vnum:
                self.cancel_edit_voucher()
                
            messagebox.showinfo("نجاح", f"✅ تم حذف سند الصرف #{vnum} وجميع بنوده بنجاح")
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في حذف السند: {str(e)}")

    def print_daily_payment_report(self):
        """طباعة تقرير سندات الصرف اليومية"""
        target_date = (self.voucher_filter_date.get() if hasattr(self, 'voucher_filter_date') else '').strip()
        if not target_date or target_date == 'الكل':
            target_date = datetime.now().strftime('%Y-%m-%d')
        self.print_daily_vouchers(target_date)
    
    def update_payment_summary(self):
        """تحديث ملخص السند"""
        self.update_payment_total()
    
    def view_payment_vouchers(self):
        """عرض جميع سندات الصرف مع مميزات متقدمة"""
        try:
            # إنشاء نافذة جديدة لعرض السندات
            view_window = tk.Toplevel(self.frame)
            view_window.title("📋 عرض سندات الصرف")
            
            # ضبط حجم النافذة لتفتح بحجم كبير مريح ومتناسق مع الشاشة
            screen_w = view_window.winfo_screenwidth()
            screen_h = view_window.winfo_screenheight()
            win_w = min(1600, max(1200, int(screen_w * 0.94)))
            win_h = min(980, max(720, int(screen_h * 0.90)))
            x = max(10, (screen_w - win_w) // 2)
            y = max(10, (screen_h - win_h) // 2)
            view_window.geometry(f"{win_w}x{win_h}+{x}+{y}")
            view_window.minsize(1050, 600)
            view_window.transient(self.frame.master)
            
            # إطار رئيسي بدون Scrollable
            main_frame = ttk.Frame(view_window)
            main_frame.pack(fill='both', expand=True, padx=20, pady=20)
            
            # عنوان
            title_label = tk.Label(main_frame, text="📋 سندات الصرف", 
                                  font=('Segoe UI', 16, 'bold'))
            title_label.pack(pady=15)
            
            # إطار الأزرار - في الأعلى تماماً
            button_frame = ttk.LabelFrame(main_frame, text="العمليات")
            button_frame.pack(fill='x', pady=(0, 15))
            
            button_content = ttk.Frame(button_frame)
            button_content.pack(fill='x', padx=15, pady=10)
            
            # إطار التحكم في التاريخ
            date_frame = ttk.LabelFrame(main_frame, text="التحكم في التاريخ")
            date_frame.pack(fill='x', pady=(0, 15))
            
            date_controls = ttk.Frame(date_frame)
            date_controls.pack(fill='x', padx=15, pady=10)
            
            # متغيرات لتخزين المراجع
            date_entry_var = tk.StringVar()
            date_entry_var.set(datetime.now().strftime('%Y-%m-%d'))
            
            # تعريف search_entry قبل استخدامه
            search_entry = ttk.Entry(date_controls, textvariable=date_entry_var, width=15, font=('Segoe UI', 11))
            
            # دوال التنقل - إصلاح المشكلة
            def go_previous_day():
                """الانتقال ليوم السابق"""
                try:
                    current_date_str = search_entry.get()
                    if not current_date_str:
                        current_date = datetime.now()
                    else:
                        current_date = datetime.strptime(current_date_str, '%Y-%m-%d')
                    
                    new_date = current_date - timedelta(days=1)
                    new_date_str = new_date.strftime('%Y-%m-%d')
                    
                    # تحديث حقل التاريخ
                    date_entry_var.set(new_date_str)
                    
                    # تحميل السندات للتاريخ الجديد
                    print(f"Debug - Loading vouchers for previous day: {new_date_str}")
                    load_vouchers(new_date_str)
                    
                except Exception as e:
                    print(f"Debug - Error in go_previous_day: {e}")
                    messagebox.showerror("خطأ", f"فشل في الانتقال ليوم السابق: {str(e)}")
            
            def go_next_day():
                """الانتقال ليوم التالي"""
                try:
                    current_date_str = search_entry.get()
                    if not current_date_str:
                        current_date = datetime.now()
                    else:
                        current_date = datetime.strptime(current_date_str, '%Y-%m-%d')
                    
                    new_date = current_date + timedelta(days=1)
                    new_date_str = new_date.strftime('%Y-%m-%d')
                    
                    # تحديث حقل التاريخ
                    date_entry_var.set(new_date_str)
                    
                    # تحميل السندات للتاريخ الجديد
                    print(f"Debug - Loading vouchers for next day: {new_date_str}")
                    load_vouchers(new_date_str)
                    
                except Exception as e:
                    print(f"Debug - Error in go_next_day: {e}")
                    messagebox.showerror("خطأ", f"فشل في الانتقال ليوم التالي: {str(e)}")
            
            def go_today():
                """الانتقال ليوم اليوم"""
                try:
                    today = datetime.now()
                    today_str = today.strftime('%Y-%m-%d')
                    
                    # تحديث حقل التاريخ
                    date_entry_var.set(today_str)
                    
                    # تحميل السندات ليوم اليوم
                    print(f"Debug - Loading vouchers for today: {today_str}")
                    load_vouchers(today_str)
                    
                except Exception as e:
                    print(f"Debug - Error in go_today: {e}")
                    messagebox.showerror("خطأ", f"فشل في الانتقال ليوم اليوم: {str(e)}")
            
            def search_vouchers():
                """البحث عن سندات بتاريخ معين"""
                try:
                    date = search_entry.get()
                    if date:
                        print(f"Debug - Searching vouchers for date: {date}")
                        load_vouchers(date)
                    else:
                        messagebox.showwarning("تحذير", "⚠️ يرجى إدخال تاريخ صحيح")
                except Exception as e:
                    print(f"Debug - Error in search_vouchers: {e}")
                    messagebox.showerror("خطأ", f"فشل في البحث: {str(e)}")
            
            def on_date_click(event):
                """عند الضغط على حقل التاريخ، عرض التقويم"""
                try:
                    current_date = search_entry.get()
                    calendar = CalendarDialog(search_entry.winfo_toplevel(), current_date)
                    selected_date = calendar.show()
                    
                    if selected_date:
                        date_entry_var.set(selected_date)
                        load_vouchers(selected_date)
                        
                except Exception as e:
                    print(f"Debug - Error in calendar: {e}")
            
            search_entry.bind('<Button-1>', on_date_click)
            
            # أزرار التنقل في التاريخ
            ttk.Button(date_controls, text="⬅️ يوم", command=go_previous_day, width=10).pack(side='right', padx=5)
            ttk.Button(date_controls, text="➡️ يوم", command=go_next_day, width=10).pack(side='right', padx=5)
            
            tk.Label(date_controls, text="التاريخ:", font=('Segoe UI', 11, 'bold')).pack(side='right', padx=5)
            search_entry.pack(side='right', padx=5)
            
            ttk.Button(date_controls, text="بحث", command=search_vouchers, width=8).pack(side='right', padx=5)
            ttk.Button(date_controls, text="اليوم", command=go_today, width=8).pack(side='right', padx=5)
            
            # إطار الملخص
            summary_frame = ttk.LabelFrame(main_frame, text="ملخص اليوم")
            summary_frame.pack(fill='x', pady=(0, 15))
            
            summary_content = ttk.Frame(summary_frame)
            summary_content.pack(fill='x', padx=15, pady=10)
            
            tk.Label(summary_content, text="إجمالي السندات:", font=('Segoe UI', 13, 'bold')).pack(side='right', padx=15)
            total_label = tk.Label(summary_content, text="0.00 ريال", font=('Segoe UI', 13, 'bold'), fg='blue')
            total_label.pack(side='right', padx=15)
            
            tk.Label(summary_content, text="عدد السندات:", font=('Segoe UI', 13, 'bold')).pack(side='right', padx=15)
            count_label = tk.Label(summary_content, text="0", font=('Segoe UI', 13, 'bold'), fg='green')
            count_label.pack(side='right', padx=15)
            
            tk.Label(summary_content, text="التاريخ الحالي:", font=('Segoe UI', 13, 'bold')).pack(side='right', padx=15)
            date_label = tk.Label(summary_content, text=search_entry.get(), font=('Segoe UI', 13, 'bold'), fg='darkblue')
            date_label.pack(side='right', padx=15)
            
            # جدول السندات
            tree_frame = ttk.LabelFrame(main_frame, text="المعاملات الخزينة")
            tree_frame.pack(fill='both', expand=True, pady=(0, 15))
            
            columns = ('date', 'number', 'account', 'description', 'amount', 'project')
            vouchers_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=25)
            
            vouchers_tree.heading('date', text='التاريخ')
            vouchers_tree.heading('number', text='رقم السند')
            vouchers_tree.heading('account', text='الحساب')
            vouchers_tree.heading('description', text='الوصف')
            vouchers_tree.heading('amount', text='المبلغ')
            vouchers_tree.heading('project', text='المشروع')
            
            vouchers_tree.column('date', width=100)
            vouchers_tree.column('number', width=80)
            vouchers_tree.column('account', width=150)
            vouchers_tree.column('description', width=200)
            vouchers_tree.column('amount', width=100)
            vouchers_tree.column('project', width=120)
            
            vouchers_tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
            
            # شريط تمرير للجدول
            tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=vouchers_tree.yview)
            tree_scrollbar.pack(side='right', fill='y')
            vouchers_tree.configure(yscrollcommand=tree_scrollbar.set)
            
            def load_vouchers(date=None):
                """تحميل السندات"""
                try:
                    vouchers_tree.delete(*vouchers_tree.get_children())
                    
                    if date:
                        vouchers = self.db.execute_query('''
                            SELECT t.date, t.description, t.amount, t.account_name, t.project_id, p.name as project_name
                            FROM treasury_transactions t
                            LEFT JOIN projects p ON t.project_id = p.id
                            WHERE t.date = ? AND (t.description LIKE 'سند خزينة #%' OR t.description LIKE 'سند صرف #%')
                            ORDER BY t.date, t.description
                        ''', (date,))
                    else:
                        vouchers = self.db.execute_query('''
                            SELECT t.date, t.description, t.amount, t.account_name, t.project_id, p.name as project_name
                            FROM treasury_transactions t
                            LEFT JOIN projects p ON t.project_id = p.id
                            WHERE t.description LIKE 'سند خزينة #%' OR t.description LIKE 'سند صرف #%'
                            ORDER BY t.date DESC, t.description
                        ''')
                    
                    total_amount = 0.0
                    voucher_count = 0
                    
                    for voucher in vouchers:
                        date_str = voucher[0]
                        desc = voucher[1]
                        amount = voucher[2]
                        account = voucher[3]
                        project_id = voucher[4]
                        project_name = voucher[5] or "غير محدد"
                        
                        # استخراج رقم السند من الوصف
                        if 'سند خزينة #' in desc or 'سند صرف #' in desc:
                            number = desc.split('#')[1].split()[0]
                            # استخراج الوصف الفعلي
                            actual_desc = desc.split('-', 1)[1].strip() if '-' in desc else desc
                            # إزالة اسم المشروع من الوصف إذا كان موجوداً
                            if '(مشروع:' in actual_desc:
                                actual_desc = actual_desc.split('(مشروع:')[0].strip()
                        else:
                            number = "N/A"
                            actual_desc = desc
                        
                        vouchers_tree.insert('', 'end', values=(date_str, number, account, actual_desc, f"{amount:.2f}", project_name))
                        total_amount += float(amount)
                        voucher_count += 1
                    
                    # تحديث الملخص
                    total_label.config(text=f"{total_amount:.2f} ريال")
                    count_label.config(text=str(voucher_count))
                    if date:
                        date_label.config(text=date)
                
                except Exception as e:
                    messagebox.showerror("خطأ", f"فشل في تحميل السندات: {str(e)}")
            
            # دوال العمليات - إصلاح المشاكل
            def print_selected():
                self.print_selected_voucher(vouchers_tree)
            
            def edit_selected():
                self.edit_selected_voucher(vouchers_tree, view_window, load_vouchers, search_entry.get())
            
            def delete_selected():
                self.delete_selected_voucher(vouchers_tree, load_vouchers, search_entry.get())
            
            def print_daily():
                self.print_daily_vouchers(search_entry.get())
            
            def add_voucher():
                self.add_voucher_for_date(search_entry.get(), view_window)
            
            # أزرار العمليات على السند المحدد - في الأعلى
            ttk.Button(button_content, text="🖨️ طباعة السند", command=print_selected, width=15).pack(side='right', padx=8, ipady=5)
            ttk.Button(button_content, text="✏️ تعديل السند", command=edit_selected, width=15).pack(side='right', padx=8, ipady=5)
            ttk.Button(button_content, text="🗑️ حذف البند", command=delete_selected, width=15).pack(side='right', padx=8, ipady=5)
            ttk.Button(button_content, text="🗑️ حذف السند بالكامل", command=lambda: self.delete_all_daily_vouchers(load_vouchers, search_entry.get()), width=22).pack(side='right', padx=8, ipady=5)
            ttk.Button(button_content, text="🖨️ طباعة كل اليوم", command=print_daily, width=18).pack(side='right', padx=8, ipady=5)
            ttk.Button(button_content, text="➕ إضافة سند ليوم", command=add_voucher, width=18).pack(side='right', padx=8, ipady=5)
            
            # إغلاق النافذة
            ttk.Button(button_content, text="إغلاق", command=view_window.destroy, width=12).pack(side='left', padx=8, ipady=5)
            
            # تحميل السندات الحالية تلقائياً
            load_vouchers(datetime.now().strftime('%Y-%m-%d'))
            
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في فتح عرض السندات: {str(e)}")
    
    def change_date(self, days, entry_widget, load_func):
        """تغيير التاريخ بالأيام"""
        try:
            current_date_str = entry_widget.get()
            current_date = datetime.strptime(current_date_str, '%Y-%m-%d')
            new_date = current_date + timedelta(days=days)
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, new_date.strftime('%Y-%m-%d'))
            load_func(new_date.strftime('%Y-%m-%d'))
        except:
            pass
    
    def set_today(self, entry_widget, load_func):
        """تعيين التاريخ ليوم اليوم"""
        today = datetime.now().strftime('%Y-%m-%d')
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, today)
        load_func(today)
    
    def print_selected_voucher(self, tree):
        """طباعة السند المحدد ك PDF بالعربي"""
        try:
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("تحذير", "⚠️ يرجى اختيار سند للطباعة")
                return
            
            item = tree.item(selected[0], 'values')
            voucher_number = item[1]
            date = item[0]
            account = item[2]
            description = item[3]
            amount = item[4]
            project = item[5]
            
            print(f"Debug - Voucher data: {voucher_number}, {date}, {account}, {description}, {amount}, {project}")
            
            # إنشاء ملف PDF عربي
            from fpdf import FPDF
            import os
            
            # استخدم مجلد البرنامج مباشرة
            filename = f"voucher_{voucher_number}_{date.replace('-', '_')}.pdf"
            
            try:
                # استخدام إعدادات الشركة من قاعدة البيانات
                company_settings = self.load_company_settings()
                
                pdf = CustomVoucherPDF(company_settings)
                pdf.add_page()
                pdf.add_voucher_data([date, voucher_number, account, description, amount, project])
                
                # حفظ الملف مباشرة
                pdf.output(filename)
                print(f"Debug - PDF saved to: {filename}")
                
                # التحقق من وجود الملف
                if os.path.exists(filename):
                    messagebox.showinfo("نجاح", f"✅ تم حفظ السند ك PDF بنجاح!\nاسم الملف: {filename}\nالمسار: {os.path.abspath(filename)}")
                    
                    # فتح الملف
                    try:
                        import webbrowser
                        webbrowser.open(f"file://{os.path.abspath(filename)}")
                    except Exception as open_error:
                        print(f"خطأ في فتح الملف: {open_error}")
                        messagebox.showinfo("معلومات", f"تم حفظ الملف في: {os.path.abspath(filename)}")
                else:
                    messagebox.showerror("خطأ", "❌ فشل في حفظ الملف")
                    
            except Exception as pdf_error:
                print(f"خطأ في إنشاء PDF: {pdf_error}")
                messagebox.showerror("خطأ في الطباعة", f"❌ فشل في إنشاء ملف PDF: {str(pdf_error)}")
            
        except Exception as e:
            print(f"خطأ عام في الطباعة: {e}")
            messagebox.showerror("خطأ", f"فشل في طباعة السند: {str(e)}")
    
    def print_daily_vouchers(self, date):
        """طباعة جميع سندات اليوم ك PDF بالعربي"""
        try:
            # جلب بيانات اليوم
            vouchers = self.db.execute_query('''
                SELECT t.description, t.amount, t.account_name, p.name as project_name
                FROM treasury_transactions t
                LEFT JOIN projects p ON t.project_id = p.id
                WHERE t.date = ? AND t.type = 'expense' AND t.description LIKE 'سند صرف #%'
                ORDER BY t.description
            ''', (date,))
            
            if not vouchers:
                messagebox.showwarning("تحذير", f"⚠️ لا توجد سندات في يوم {date}")
                return
            
            print(f"Debug - Found {len(vouchers)} vouchers for date {date}")
            
            # إنشاء ملف PDF عربي
            from fpdf import FPDF
            import os
            
            # استخدم مجلد البرنامج مباشرة
            filename = f"daily_vouchers_{date.replace('-', '_')}.pdf"
            
            try:
                # استخدام إعدادات الشركة من قاعدة البيانات
                company_settings = self.load_company_settings()
                
                pdf = CustomDailyVouchersPDF(company_settings)
                pdf.add_page()
                pdf.add_daily_vouchers_data(date, vouchers)
                
                # حفظ الملف مباشرة
                pdf.output(filename)
                print(f"Debug - Daily PDF saved to: {filename}")
                
                # التحقق من وجود الملف
                if os.path.exists(filename):
                    messagebox.showinfo("نجاح", f"✅ تم حفظ سندات اليوم ك PDF بنجاح!\nاسم الملف: {filename}\nالمسار: {os.path.abspath(filename)}\nعدد السندات: {len(vouchers)}")
                    
                    # فتح الملف
                    try:
                        import webbrowser
                        webbrowser.open(f"file://{os.path.abspath(filename)}")
                    except Exception as open_error:
                        print(f"خطأ في فتح الملف: {open_error}")
                        messagebox.showinfo("معلومات", f"تم حفظ الملف في: {os.path.abspath(filename)}")
                else:
                    messagebox.showerror("خطأ", "❌ فشل في حفظ الملف")
                    
            except Exception as pdf_error:
                print(f"خطأ في إنشاء PDF اليومي: {pdf_error}")
                messagebox.showerror("خطأ في الطباعة", f"❌ فشل في إنشاء ملف PDF: {str(pdf_error)}")
            
        except Exception as e:
            print(f"خطأ عام في الطباعة اليومية: {e}")
            messagebox.showerror("خطأ", f"فشل في طباعة سندات اليوم: {str(e)}")
    
    def load_company_settings(self):
        """تحميل إعدادات الشركة من قاعدة البيانات"""
        try:
            from company_settings import get_company_settings
            return get_company_settings(self.db)
        except Exception as e:
            print(f"Error loading company settings: {e}")
            return {
                'company_name_ar': 'محمد بن منير بن محمد سعيد دغستاني',
                'company_name_en': 'Mohammed bin Munir bin Mohammed Saeed Daghestani',
                'commercial_register': '4030330926',
                'tax_number': '300262161400003',
                'address': 'جدة - أبحر الشمالية - شارع أبي محمد العطار',
                'phone1': '0582224122',
                'phone2': '0538833640',
                'po_box': '117332',
                'postal_code': '21391',
                'email': 'seapearl.est@gmail.com',
                'owner_name': 'محمد بن منير دغستاني',
                'owner_name_en': 'Mohammed bin Munir Daghestani'
            }
    
    def add_voucher_for_date(self, date, parent_window):
        """إضافة سند لتاريخ محدد"""
        try:
            # إغلاق نافذة العرض
            parent_window.destroy()
            
            # تعيين التاريخ في نموذج سند اليومية
            self.journal_date_entry.delete(0, tk.END)
            self.journal_date_entry.insert(0, date)
            
            # تحديث رقم السند للتاريخ المحدد
            self.update_journal_voucher_number_for_date(date)
            
            # التركيز على تبويب سند اليومية
            # هنا يمكن إضافة كود للانتقال إلى تبويب سند اليومية
            
            messagebox.showinfo("إضافة سند", f"تم فتح إضافة سند جديد لتاريخ {date}")
            
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في فتح إضافة السند: {str(e)}")
    
    def update_journal_voucher_number_for_date(self, date):
        """تحديث رقم سند اليومية تلقائياً لتاريخ محدد - كل سند جديد بياخذ رقم فريد"""
        try:
            # ✅ كل سند جديد بياخذ رقم فريد (مش مستمر)
            # 1. نحصل على أكبر رقم سند في كل النظام
            max_voucher_result = self.db.execute_query('''
                SELECT MAX(CAST(SUBSTR(description, 
                    INSTR(description, '#') + 1, 
                    INSTR(description, ' - ') - INSTR(description, '#') - 1
                ) AS INTEGER)) as max_voucher
                FROM treasury_transactions 
                WHERE description LIKE 'سند يومية #%'
            ''')
            
            # 2. الرقم الجديد = أكبر رقم + 1
            new_number = 1
            if max_voucher_result and max_voucher_result[0][0]:
                try:
                    new_number = int(max_voucher_result[0][0]) + 1
                except:
                    new_number = 1
            
            self.journal_number_entry.configure(state='normal')
            self.journal_number_entry.delete(0, tk.END)
            self.journal_number_entry.insert(0, str(new_number))
            self.journal_number_entry.configure(state='readonly')
            
        except Exception as e:
            # في حالة الخطأ، استخدم رقم 1
            self.journal_number_entry.configure(state='normal')
            self.journal_number_entry.delete(0, tk.END)
            self.journal_number_entry.insert(0, "1")
            self.journal_number_entry.configure(state='readonly')
    
    def update_payment_voucher_number_for_date(self, date):
        """تحديث رقم السند تلقائياً لتاريخ محدد - يزيد حسب اليوم وليس العملية"""
        try:
            # ✅ النظام الجديد: العد يزيد حسب عدد الأيام المختلفة وليس العمليات
            # 1. نحصل على جميع الأيام الفريدة التي بها سندات صرف (مرتبة)
            result = self.db.execute_query('''
                SELECT DISTINCT date 
                FROM treasury_transactions 
                WHERE type = 'expense' AND description LIKE 'سند صرف #%'
                ORDER BY date ASC
            ''')
            
            # 2. نحسب عدد الأيام الفريدة قبل التاريخ المحدد
            distinct_days_before_date = 0
            if result:
                for row in result:
                    voucher_date = row[0]
                    if voucher_date < date:
                        distinct_days_before_date += 1
                    else:
                        break
            
            # 3. الرقم = عدد الأيام الفريدة السابقة + 1
            new_number = distinct_days_before_date + 1
            
            # 4. نتحقق إذا كان التاريخ المحدد لديه سندات - إذا نعم نستخدم نفس الرقم
            date_has_vouchers = self.db.execute_query('''
                SELECT 1 FROM treasury_transactions 
                WHERE date = ? AND type = 'expense' AND description LIKE 'سند صرف #%'
                LIMIT 1
            ''', (date,))
            
            # إذا كان التاريخ لديه سندات، نحصل على رقم التاريخ الحالي
            if date_has_vouchers:
                date_voucher = self.db.execute_query('''
                    SELECT description 
                    FROM treasury_transactions 
                    WHERE date = ? AND type = 'expense' AND description LIKE 'سند صرف #%'
                    ORDER BY id ASC LIMIT 1
                ''', (date,))
                if date_voucher and date_voucher[0][0]:
                    import re
                    match = re.search(r'#(\d+)', date_voucher[0][0])
                    if match:
                        new_number = int(match.group(1))
            
            self.payment_number_entry.configure(state='normal')
            self.payment_number_entry.delete(0, tk.END)
            self.payment_number_entry.insert(0, str(new_number))
            self.payment_number_entry.configure(state='readonly')
            
        except Exception as e:
            # في حالة الخطأ، استخدم رقم 1
            self.payment_number_entry.configure(state='normal')
            self.payment_number_entry.delete(0, tk.END)
            self.payment_number_entry.insert(0, "1")
            self.payment_number_entry.configure(state='readonly')
    
    def load_journal_data(self):
        """تحميل بيانات سند اليومية - المشاريع والعملاء والصندوق والموظفين"""
        try:
            # تحميل المشاريع
            projects = self.db.execute_query("SELECT id, name FROM projects ORDER BY name")
            project_names = [f"{proj[0]} - {proj[1]}" for proj in projects]
            
            # تحميل العملاء
            customers = self.db.execute_query("SELECT id, name FROM customers ORDER BY name")
            customer_names = [f"{cust[0]} - {cust[1]}" for cust in customers]
            
            # تحميل الصندوق
            treasury = self.db.execute_query("SELECT name FROM account_items WHERE name LIKE '%الصندوق%' ORDER BY name")
            treasury_names = [tre[0] for tre in treasury]
            
            # دمج المشاريع والعملاء والصندوق للحساب (بدون الموظفين)
            self.journal_account_data = project_names + customer_names + treasury_names
            
            # تحميل المشاريع للمشروع الرئيسي
            self.journal_project_combo['values'] = ["-- اختر المشروع --"] + project_names if project_names else ["-- اختر المشروع --"]
            if self.journal_project_combo['values']:
                self.journal_project_combo.current(0)
            
            # تحميل بنود الحسابات للوصف (مثل سند الصرف)
            accounts = self.db.execute_query("SELECT name FROM account_items ORDER BY name")
            account_names = [acc[0] for acc in accounts]
            self.journal_desc_listbox_data = account_names
            # تحديث القائمة الفعلية في الواجهة
            if hasattr(self, 'journal_desc_listbox'):
                self.journal_desc_listbox.delete(0, tk.END)
                for item in account_names:
                    self.journal_desc_listbox.insert(tk.END, item)
            
            # تحديث رقم السند تلقائياً
            self.update_journal_voucher_number()
            
        except Exception as e:
            print(f"خطأ في تحميل بيانات سند اليومية: {e}")
    
    def update_journal_voucher_number(self):
        """تحديث رقم سند اليومية تلقائياً - كل سند جديد بياخذ رقم فريد"""
        try:
            # ✅ كل سند جديد بياخذ رقم فريد (مش مستمر)
            # 1. نحصل على أكبر رقم سند في كل النظام
            max_voucher_result = self.db.execute_query('''
                SELECT MAX(CAST(SUBSTR(description, 
                    INSTR(description, '#') + 1, 
                    INSTR(description, ' - ') - INSTR(description, '#') - 1
                ) AS INTEGER)) as max_voucher
                FROM treasury_transactions 
                WHERE description LIKE 'سند يومية #%'
            ''')
            
            # 2. الرقم الجديد = أكبر رقم + 1
            new_number = 1
            if max_voucher_result and max_voucher_result[0][0]:
                try:
                    new_number = int(max_voucher_result[0][0]) + 1
                except:
                    new_number = 1
            
            self.journal_number_entry.configure(state='normal')
            self.journal_number_entry.delete(0, tk.END)
            self.journal_number_entry.insert(0, str(new_number))
            self.journal_number_entry.configure(state='readonly')
            
        except Exception as e:
            # في حالة الخطأ، استخدم رقم 1
            self.journal_number_entry.configure(state='normal')
            self.journal_number_entry.delete(0, tk.END)
            self.journal_number_entry.insert(0, "1")
            self.journal_number_entry.configure(state='readonly')
    
    def load_account_items(self):
        """تحميل بنود الحسابات"""
        try:
            if hasattr(self, 'account_tree') and self.account_tree.winfo_exists():
                # مسح الجدول
                for item in self.account_tree.get_children():
                    self.account_tree.delete(item)
                
                # تحميل البيانات (3 أعمدة id, number, name)
                items = self.db.execute_query("SELECT id, number, name FROM account_items ORDER BY id DESC")
                for item in items:
                    self.account_tree.insert('', 'end', values=item)
        except Exception as e:
            print(f"خطأ في تحميل بنود الحسابات: {e}")
    
    def edit_selected_voucher(self, tree, parent_window, load_func, current_date):
        """تعديل السند المحدد"""
        try:
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("تحذير", "⚠️ يرجى اختيار سند للتعديل")
                return
            
            item = tree.item(selected[0], 'values')
            if not item:
                return
            
            # فحص إذا كان السند هو سند صرف (6 أعمدة) أم سند يومية (9 أعمدة)
            if len(item) <= 6:
                date = item[0] if len(item) > 0 else ""
                voucher_number = item[1] if len(item) > 1 else ""
                account = item[2] if len(item) > 2 else ""
                actual_desc = item[3] if len(item) > 3 else ""
                amount = item[4] if len(item) > 4 else "0"
                project = item[5] if len(item) > 5 else ""
                
                # إنشاء نافذة تعديل سند الصرف
                edit_window = tk.Toplevel(parent_window)
                edit_window.title(f"✏️ تعديل سند صرف #{voucher_number}")
                edit_window.geometry("550x380")
                edit_window.transient(parent_window)
                
                main_frame = ttk.Frame(edit_window, padding=20)
                main_frame.pack(fill='both', expand=True)
                
                ttk.Label(main_frame, text=f"تعديل بيانات سند صرف #{voucher_number}", font=('Segoe UI', 13, 'bold')).pack(pady=(0, 15))
                
                # الحساب
                acc_f = ttk.Frame(main_frame)
                acc_f.pack(fill='x', pady=5)
                ttk.Label(acc_f, text="الحساب:", font=('Segoe UI', 10, 'bold'), width=12).pack(side='right')
                acc_entry = ttk.Entry(acc_f, width=35, font=('Segoe UI', 10))
                acc_entry.pack(side='right', fill='x', expand=True, padx=5)
                acc_entry.insert(0, account)
                
                # البيان
                desc_f = ttk.Frame(main_frame)
                desc_f.pack(fill='x', pady=5)
                ttk.Label(desc_f, text="البيان / الوصف:", font=('Segoe UI', 10, 'bold'), width=12).pack(side='right')
                desc_entry = ttk.Entry(desc_f, width=35, font=('Segoe UI', 10))
                desc_entry.pack(side='right', fill='x', expand=True, padx=5)
                desc_entry.insert(0, actual_desc)
                
                # المبلغ
                amt_f = ttk.Frame(main_frame)
                amt_f.pack(fill='x', pady=5)
                ttk.Label(amt_f, text="المبلغ (ريال):", font=('Segoe UI', 10, 'bold'), width=12).pack(side='right')
                amt_entry = ttk.Entry(amt_f, width=35, font=('Segoe UI', 10))
                amt_entry.pack(side='right', fill='x', expand=True, padx=5)
                amt_entry.insert(0, str(amount))
                
                def save_payment_edit():
                    try:
                        n_acc = acc_entry.get().strip()
                        n_desc = desc_entry.get().strip()
                        n_amt = float(amt_entry.get().strip())
                        
                        # تحديث في قاعدة البيانات
                        recs = self.db.execute_query('''
                            SELECT id FROM treasury_transactions 
                            WHERE date = ? AND (description LIKE ? OR description LIKE ?)
                        ''', (date, f'سند صرف #{voucher_number} - %', f'سند صرف #{voucher_number}'))
                        
                        if recs:
                            tid = recs[0][0]
                            full_desc = f"سند صرف #{voucher_number} - {n_desc}"
                            self.db.execute_query('''
                                UPDATE treasury_transactions 
                                SET account_name = ?, description = ?, amount = ?
                                WHERE id = ?
                            ''', (n_acc, full_desc, n_amt, tid))
                            
                            self.db.execute_query('''
                                UPDATE transactions 
                                SET description = ?, amount = ?
                                WHERE date = ? AND description LIKE ?
                            ''', (full_desc, n_amt, date, f'%سند صرف #{voucher_number}%'))
                        
                        messagebox.showinfo("نجاح", "✅ تم حفظ التعديلات بنجاح")
                        if load_func:
                            load_func(current_date)
                        if hasattr(self, 'load_saved_payment_vouchers'):
                            self.load_saved_payment_vouchers()
                        self.update_cash_data()
                        edit_window.destroy()
                    except Exception as err:
                        messagebox.showerror("خطأ", f"فشل في حفظ التعديل: {err}")
                
                btn_f = ttk.Frame(main_frame)
                btn_f.pack(fill='x', pady=20)
                ttk.Button(btn_f, text="💾 حفظ التعديل", command=save_payment_edit, width=15).pack(side='right', padx=5)
                ttk.Button(btn_f, text="❌ إلغاء", command=edit_window.destroy, width=15).pack(side='left', padx=5)
                return
            
            # ترتيب الأعمدة لسند اليومية: date, number, debit_account, debit, credit_account, credit, description, project, id
            voucher_number = item[1] if len(item) > 1 else ""
            date = item[0] if len(item) > 0 else ""
            debit_account = item[2] if len(item) > 2 else ""
            debit_amount = item[3] if len(item) > 3 else "0"
            credit_account = item[4] if len(item) > 4 else ""
            credit_amount = item[5] if len(item) > 5 else "0"
            description = item[6] if len(item) > 6 else ""
            project = item[7] if len(item) > 7 else ""
            record_id = item[8] if len(item) > 8 else None
            
            # إنشاء نافذة تعديل
            edit_window = tk.Toplevel(parent_window)
            edit_window.title(f"✏️ تعديل سند #{voucher_number}")
            edit_window.geometry("600x500")
            edit_window.transient(parent_window)
            
            # إطار رئيسي
            main_frame = ttk.Frame(edit_window)
            main_frame.pack(fill='both', expand=True, padx=20, pady=20)
            
            # حقول التعديل
            ttk.Label(main_frame, text="تعديل بيانات سند اليومية", font=('Segoe UI', 14, 'bold')).pack(pady=10)
            
            # المدين
            debit_frame = ttk.LabelFrame(main_frame, text="المدين")
            debit_frame.pack(fill='x', pady=10)
            
            debit_account_frame = ttk.Frame(debit_frame)
            debit_account_frame.pack(fill='x', padx=10, pady=5)
            ttk.Label(debit_account_frame, text="الحساب:", font=('Segoe UI', 11, 'bold')).pack(side='right', padx=5)
            debit_account_entry = ttk.Entry(debit_account_frame, width=30)
            debit_account_entry.pack(side='right', padx=5)
            debit_account_entry.insert(0, debit_account)
            
            debit_amount_frame = ttk.Frame(debit_frame)
            debit_amount_frame.pack(fill='x', padx=10, pady=5)
            ttk.Label(debit_amount_frame, text="المبلغ:", font=('Segoe UI', 11, 'bold')).pack(side='right', padx=5)
            debit_amount_entry = ttk.Entry(debit_amount_frame, width=30)
            debit_amount_entry.pack(side='right', padx=5)
            debit_amount_entry.insert(0, debit_amount)
            
            # الدائن
            credit_frame = ttk.LabelFrame(main_frame, text="الدائن")
            credit_frame.pack(fill='x', pady=10)
            
            credit_account_frame = ttk.Frame(credit_frame)
            credit_account_frame.pack(fill='x', padx=10, pady=5)
            ttk.Label(credit_account_frame, text="الحساب:", font=('Segoe UI', 11, 'bold')).pack(side='right', padx=5)
            credit_account_entry = ttk.Entry(credit_account_frame, width=30)
            credit_account_entry.pack(side='right', padx=5)
            credit_account_entry.insert(0, credit_account)
            
            credit_amount_frame = ttk.Frame(credit_frame)
            credit_amount_frame.pack(fill='x', padx=10, pady=5)
            ttk.Label(credit_amount_frame, text="المبلغ:", font=('Segoe UI', 11, 'bold')).pack(side='right', padx=5)
            credit_amount_entry = ttk.Entry(credit_amount_frame, width=30)
            credit_amount_entry.pack(side='right', padx=5)
            credit_amount_entry.insert(0, credit_amount)
            
            # الوصف
            desc_frame = ttk.Frame(main_frame)
            desc_frame.pack(fill='x', pady=5)
            ttk.Label(desc_frame, text="البيان:", font=('Segoe UI', 11, 'bold')).pack(side='right', padx=5)
            desc_entry = ttk.Entry(desc_frame, width=40)
            desc_entry.pack(side='right', padx=5)
            desc_entry.insert(0, description)
            
            # المشروع
            project_frame = ttk.Frame(main_frame)
            project_frame.pack(fill='x', pady=5)
            ttk.Label(project_frame, text="المشروع:", font=('Segoe UI', 11, 'bold')).pack(side='right', padx=5)
            project_entry = ttk.Entry(project_frame, width=40)
            project_entry.pack(side='right', padx=5)
            project_entry.insert(0, project)
            
            def save_changes():
                try:
                    new_debit_account = debit_account_entry.get()
                    new_debit_amount = debit_amount_entry.get()
                    new_credit_account = credit_account_entry.get()
                    new_credit_amount = credit_amount_entry.get()
                    new_desc = desc_entry.get()
                    new_project = project_entry.get()
                    
                    if not new_debit_account or not new_credit_account or not new_desc:
                        messagebox.showerror("خطأ", "❌ يرجى ملء جميع الحقول المطلوبة")
                        return
                    
                    # التحقق من التوازن
                    try:
                        debit_val = float(new_debit_amount) if new_debit_amount else 0
                        credit_val = float(new_credit_amount) if new_credit_amount else 0
                        if abs(debit_val - credit_val) > 0.01:
                            messagebox.showerror("خطأ", "❌ يجب أن يتساوى المدين والدائن")
                            return
                    except ValueError:
                        messagebox.showerror("خطأ", "❌ المبالغ يجب أن تكون أرقاماً")
                        return
                    
                    # تحديث السند في قاعدة البيانات - حذف القديم وإضافة جديد
                    self.db.execute_query('''
                        DELETE FROM treasury_transactions 
                        WHERE date = ? AND description LIKE ?
                    ''', (date, f'سند يومية #{voucher_number}%'))
                    
                    # حفظ المدين الجديد
                    if new_debit_account and debit_val > 0:
                        desc = f"سند يومية #{voucher_number} - {new_desc}"
                        customer_id = None
                        if " - " in new_debit_account:
                            first_part = new_debit_account.split(' - ')[0].strip()
                            if first_part.isdigit():
                                customer_id = int(first_part)
                        
                        project_id = None
                        if new_project and new_project != "-- اختر المشروع --":
                            if " - " in new_project:
                                first_part = new_project.split(' - ')[0].strip()
                                if first_part.isdigit():
                                    project_id = int(first_part)
                        
                        self.db.execute_query('''
                            INSERT INTO treasury_transactions 
                            (date, type, description, amount, account_name, project_id, customer_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (date, 'expense', desc, debit_val, new_debit_account, project_id, customer_id))
                    
                    # حفظ الدائن الجديد
                    if new_credit_account and credit_val > 0:
                        desc = f"سند يومية #{voucher_number} - {new_desc}"
                        customer_id = None
                        if " - " in new_credit_account:
                            first_part = new_credit_account.split(' - ')[0].strip()
                            if first_part.isdigit():
                                customer_id = int(first_part)
                        
                        project_id = None
                        if new_project and new_project != "-- اختر المشروع --":
                            if " - " in new_project:
                                first_part = new_project.split(' - ')[0].strip()
                                if first_part.isdigit():
                                    project_id = int(first_part)
                        
                        self.db.execute_query('''
                            INSERT INTO treasury_transactions 
                            (date, type, description, amount, account_name, project_id, customer_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (date, 'income', desc, credit_val, new_credit_account, project_id, customer_id))
                    
                    messagebox.showinfo("نجاح", f"✅ تم تحديث سند #{voucher_number} بنجاح")
                    load_func(current_date)
                    edit_window.destroy()
                    
                except Exception as e:
                    messagebox.showerror("خطأ", f"فشل في حفظ التعديلات: {str(e)}")
            
            # أزرار
            btn_frame = ttk.Frame(main_frame)
            btn_frame.pack(fill='x', pady=20)
            
            ttk.Button(btn_frame, text="💾 حفظ التعديلات", command=save_changes, width=15).pack(side='right', padx=5)
            ttk.Button(btn_frame, text="❌ إلغاء", command=edit_window.destroy, width=15).pack(side='left', padx=5)
            
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في تعديل السند: {str(e)}")
    
    def delete_all_daily_vouchers(self, load_func, current_date):
        """حذف جميع سندات اليوم"""
        try:
            result = messagebox.askyesno("تأكيد الحذف", f"هل تريد حذف جميع سندات يوم {current_date}؟\n\nهذا الإجراء سيحذف كل السندات في هذا اليوم ولا يمكن التراجع عنه!")
            if result:
                # حذف جميع سندات اليوم من قاعدة البيانات
                self.db.execute_query('''
                    DELETE FROM treasury_transactions 
                    WHERE date = ? AND type = 'expense' AND description LIKE 'سند صرف #%'
                ''', (current_date,))
                
                messagebox.showinfo("نجاح", f"✅ تم حذف جميع سندات يوم {current_date} بنجاح")
                load_func(current_date)
            
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في حذف سندات اليوم: {str(e)}")
    
    def delete_selected_voucher(self, tree, load_func, current_date):
        """حذف البند المحدد من قاعدة البيانات والجدول"""
        try:
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("تحذير", "⚠️ يرجى اختيار بند للحذف")
                return
            
            # الحصول على بيانات البند المحدد
            item = tree.item(selected[0], 'values')
            date = item[0]
            voucher_number = item[1]
            account = item[2]
            description = item[3]
            amount = item[4]
            
            print(f"Debug - Attempting to delete: date={date}, desc={description}, amount={amount}, account={account}")
            
            # تأكيد الحذف
            confirm = messagebox.askyesno(
                "تأكيد الحذف", 
                f"هل أنت متأكد من حذف هذا البند؟\n\n"
                f"التاريخ: {date}\n"
                f"رقم السند: {voucher_number}\n"
                f"الحساب: {account}\n"
                f"الوصف: {description}\n"
                f"المبلغ: {amount} ريال"
            )
            
            if not confirm:
                return
            
            # حذف البند من قاعدة البيانات باستخدام المعرف الفريد
            # البحث عن السجل المطابق باستخدام رقم السند والمبلغ والحساب
            records = self.db.execute_query('''
                SELECT id, description, amount, account_name FROM treasury_transactions 
                WHERE date = ? AND type = 'expense' AND description LIKE ?
            ''', (date, f'%سند صرف #{voucher_number}%'))
            
            print(f"Debug - Found {len(records)} potential records for voucher #{voucher_number}")
            
            found_record = None
            for record in records:
                record_id, record_desc, record_amount, record_account = record
                print(f"Debug - Checking record: id={record_id}, desc={record_desc}, amount={record_amount}, account={record_account}")
                
                # مقارنة مرنة للمبلغ والحساب
                if (abs(float(record_amount) - float(amount)) < 0.01 and 
                    str(record_account).strip() == str(account).strip()):
                    found_record = record
                    break
            
            if found_record:
                record_id = found_record[0]
                print(f"Debug - Found matching record with ID: {record_id}")
                
                # حذف باستخدام المعرف الفريد
                self.db.execute_query('DELETE FROM treasury_transactions WHERE id = ?', (record_id,))
                print(f"Debug - Deleted record with ID: {record_id}")
            else:
                print(f"Debug - No matching record found")
                messagebox.showerror("خطأ", "❌ لم يتم العثور على السجل المحدد")
                return
            
            # حذف البند من الجدول
            tree.delete(selected[0])
            
            # تحديث المجموع
            self.update_payment_total()
            
            # إعادة تحميل السندات
            load_func(current_date)
            
            messagebox.showinfo("نجاح", "✅ تم حذف البند بنجاح")
            
        except Exception as e:
            print(f"Debug - Error in delete: {e}")
            messagebox.showerror("خطأ", f"فشل في حذف البند: {str(e)}")
    
    def add_journal_item(self):
        """إضافة قيد محاسبي - سطر واحد يجمع المدين والدائن"""
        try:
            debit_account = self.journal_debit_account_entry.get()
            credit_account = self.journal_credit_account_entry.get()
            amount = self.journal_debit_entry.get()
            description = self.journal_debit_desc_entry.get() or self.journal_credit_desc_entry.get()
            project = self.journal_project_combo.get()
            
            # التحقق من البيانات
            if not debit_account or not credit_account:
                messagebox.showerror("خطأ", "❌ يرجى اختيار حساب المدين وحساب الدائن")
                return
            
            try:
                amount_val = float(amount)
                if amount_val <= 0:
                    messagebox.showerror("خطأ", "❌ المبلغ يجب أن يكون أكبر من صفر")
                    return
            except ValueError:
                messagebox.showerror("خطأ", "❌ المبلغ يجب أن يكون رقمًا")
                return
            
            # ⚠️ الترقيم الفريد للبنود - كل بند جديد بياخذ الرقم التالي
            # الحصول على رقم السند الحالي
            current_voucher_number = self.journal_number_entry.get()
            
            # البحث عن أكبر رقم بند فريد في قاعدة البيانات (لكل السندات)
            max_item_result = self.db.execute_query('''
                SELECT MAX(CAST(SUBSTR(description, 
                    INSTR(description, '- البند #') + 7, 
                    LENGTH(description) - INSTR(description, '- البند #') - 6
                ) AS INTEGER)) as max_item
                FROM treasury_transactions 
                WHERE description LIKE 'سند يومية #% - البند #%'
            ''')
            
            # البند التالي = أكبر رقم + 1
            next_item_num = 1
            if max_item_result and max_item_result[0][0]:
                try:
                    next_item_num = int(max_item_result[0][0]) + 1
                except:
                    next_item_num = 1
            
            # ⚠️ إضافة سطر واحد يجمع المدين والدائن مع رقم البند الفريد
            item_desc = f"{description}"  # الوصف بدون رقم البند
            self.journal_tree.insert('', 'end', values=(
                next_item_num,  # رقم البند الفريد
                debit_account,
                f"{amount_val:.2f}",
                credit_account,
                f"{amount_val:.2f}",
                item_desc,  # الوصف فقط
                project
            ))
            
            # مسح حقول المبالغ فقط - يبقى الوصف ثابتاً
            self.journal_debit_entry.delete(0, tk.END)
            self.journal_credit_entry.configure(state='normal')
            self.journal_credit_entry.delete(0, tk.END)
            self.journal_credit_entry.configure(state='readonly')
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في إضافة القيد: {str(e)}")
    
    def delete_journal_item(self):
        """حذف بند من سند اليومية"""
        try:
            selected = self.journal_tree.selection()
            if not selected:
                messagebox.showwarning("تحذير", "⚠️ يرجى اختيار بند للحذف")
                return
            
            self.journal_tree.delete(selected[0])
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حذف البند: {str(e)}")
    
    def clear_journal_form_after_save(self):
        """مسح حقول الإدخال بعد الحفظ - يبقي الوصف والمشروع، يمسح فقط المبالغ والحسابات"""
        try:
            # ⚠️ لا نمسح الجدول - يبقى لعرض التفاصيل المحفوظة
            
            # مسح حقول المدين
            self.journal_debit_account_entry.delete(0, tk.END)
            self.journal_debit_entry.delete(0, tk.END)
            self.journal_debit_desc_entry.delete(0, tk.END)
            
            # مسح حقول الدائن
            self.journal_credit_account_entry.delete(0, tk.END)
            self.journal_credit_entry.configure(state='normal')
            self.journal_credit_entry.delete(0, tk.END)
            self.journal_credit_entry.configure(state='readonly')
            self.journal_credit_desc_entry.delete(0, tk.END)
            
            # ⚠️ لا نمسح المشروع - يبقى ثابتاً
            # ⚠️ لا نمسح الوصف المختار من بنود الحسابات
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في مسح حقول الإدخال: {str(e)}")
    
    def clear_journal_form(self):
        """مسح نموذج سند اليومية بالكامل - للزر "مسح الكل"""
        try:
            # مسح الجدول
            for item in self.journal_tree.get_children():
                self.journal_tree.delete(item)
            
            # مسح حقول المدين
            self.journal_debit_account_entry.delete(0, tk.END)
            self.journal_debit_entry.delete(0, tk.END)
            self.journal_debit_desc_entry.delete(0, tk.END)
            
            # مسح حقول الدائن
            self.journal_credit_account_entry.delete(0, tk.END)
            self.journal_credit_entry.delete(0, tk.END)
            self.journal_credit_desc_entry.delete(0, tk.END)
            
            # مسح الوصف المختار من بنود الحسابات
            self.journal_desc_search_entry.delete(0, tk.END)
            
            # إعادة تعيين المشروع
            if self.journal_project_combo['values']:
                self.journal_project_combo.current(0)
            
            # تحديث الرقم التلقائي
            self.update_journal_voucher_number()
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في مسح النموذج: {str(e)}")

    def open_batch_payment_dialog(self):
        """فتح نافذة إدخال عدة بنود لسند الصرف دفعة واحدة"""
        account_options = getattr(self, 'payment_account_data', [])
        if not account_options:
            try:
                accs = self.db.execute_query("SELECT name FROM account_items ORDER BY name")
                emps = self.db.execute_query("SELECT id, name FROM employees ORDER BY name")
                account_options = [a[0] for a in accs] + [f"{e[0]} - {e[1]}" for e in emps]
            except Exception:
                account_options = []
        project_options = []
        try:
            projects = self.db.execute_query("SELECT id, name FROM projects ORDER BY name")
            project_options = [f"{proj[0]} - {proj[1]}" for proj in projects]
        except Exception as e:
            print(f"Error loading projects for batch dialog: {e}")
        BatchPaymentItemsDialog(self.frame, account_options, project_options, self.add_batch_payment_items)

    def add_batch_payment_items(self, new_items):
        """إضافة قائمة بنود دفعة واحدة لسند الصرف"""
        if not new_items:
            return
        for item in new_items:
            if len(item) == 4:
                account, project, description, amount = item
            else:
                account, description, amount = item
                project = ""
            self.payment_tree.insert('', 'end', values=(account, project, description, f"{amount:.2f}"))
        self.update_payment_total()
        self.payment_account_entry.focus_set()

    def add_payment_item(self, silent=False):
        """إضافة بند لسند الصرف والتحضير للبند التالي فوراً"""
        try:
            account = self.payment_account_entry.get().strip()
            description = self.payment_desc_entry.get().strip()
            amount = self.payment_amount_entry.get().strip()
            
            # التقاط المشروع المحدد من القائمة العلوية إن وجد
            project = ""
            if hasattr(self, 'payment_project_combo') and self.payment_project_combo.current() > 0:
                p_val = self.payment_project_combo.get().strip()
                if p_val and p_val != "-- select project --":
                    project = p_val
            
            if not account and not description and not amount:
                if not silent:
                    self.payment_account_entry.focus_set()
                return False
                
            if not account or not description or not amount:
                if not silent:
                    messagebox.showerror("خطأ", "❌ يرجى ملء الحساب والوصف والمبلغ")
                    if not account:
                        self.payment_account_entry.focus_set()
                    elif not description:
                        self.payment_desc_entry.focus_set()
                    else:
                        self.payment_amount_entry.focus_set()
                return False
            
            try:
                amount_num = float(amount)
                if amount_num <= 0:
                    if not silent:
                        messagebox.showerror("خطأ", "❌ المبلغ يجب أن يكون أكبر من الصفر")
                        self.payment_amount_entry.focus_set()
                    return False
            except ValueError:
                if not silent:
                    messagebox.showerror("خطأ", "❌ المبلغ يجب أن يكون رقمًا")
                    self.payment_amount_entry.focus_set()
                return False
            
            # إضافة البند للجدول
            self.payment_tree.insert('', 'end', values=(account, project, description, f"{amount_num:.2f}"))
            
            # مسح الوصف والمبلغ فقط - للبدء في البند التالي
            self.payment_desc_entry.delete(0, tk.END)
            self.payment_amount_entry.delete(0, tk.END)
            
            # تحديد نص الحساب والتركيز عليه حتى يستطيع المستخدم إما تعديله أو الضغط على Enter لإبقائه
            self.payment_account_entry.focus_set()
            self.payment_account_entry.selection_range(0, tk.END)
            
            # تحديث المجموع
            self.update_payment_total()
            return True
            
        except Exception as e:
            if not silent:
                messagebox.showerror("خطأ", f"❌ فشل في إضافة البند: {str(e)}")
            return False

    def delete_payment_item(self):
        """حذف بند من سند الصرف"""
        try:
            selected = self.payment_tree.selection()
            if not selected:
                messagebox.showwarning("تحذير", "⚠️ يرجى اختيار بند للحذف")
                return
            
            self.payment_tree.delete(selected[0])
            
            # تحديث المجموع
            self.update_payment_total()
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حذف البند: {str(e)}")

    def clear_payment_form(self):
        """مسح نموذج سند الصرف وإعادته لوضع إنشاء سند جديد"""
        try:
            self.editing_voucher_data = None
            
            # مسح الجدول
            for item in self.payment_tree.get_children():
                self.payment_tree.delete(item)
            
            # مسح الحقول
            self.payment_desc_entry.delete(0, tk.END)
            self.payment_amount_entry.delete(0, tk.END)
            if hasattr(self, 'payment_account_entry'):
                self.payment_account_entry.delete(0, tk.END)
            
            # التاريخ لليوم
            if hasattr(self, 'payment_date_entry'):
                self.payment_date_entry.delete(0, tk.END)
                self.payment_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
            
            # إعادة تعيين المشروع
            if hasattr(self, 'payment_project_combo') and self.payment_project_combo['values']:
                self.payment_project_combo.current(0)
            
            # إعادة أزرار وعنوان الوضع
            if hasattr(self, 'voucher_mode_label'):
                self.voucher_mode_label.config(text="📝 إنشاء سند صرف جديد", fg='#1B4F72')
            if hasattr(self, 'save_btn'):
                self.save_btn.config(text="💾 حفظ السند")
            if hasattr(self, 'cancel_edit_btn'):
                self.cancel_edit_btn.pack_forget()
            
            # تحديث الرقم التلقائي والمجموع
            self.update_payment_voucher_number()
            self.update_payment_total()
            
        except Exception as e:
            print(f"خطأ في مسح النموذج: {e}")

    def save_payment_voucher(self, and_print=False):
        """حفظ سند الصرف بنظام موحد كالفاتورة - جميع البنود تابعة لنفس السند"""
        try:
            # التقاط البند الأخير تلقائياً إذا كان مكتوباً في الحقول ولم يضغط المستخدم على إضافة بعد
            if self.payment_account_entry.get().strip() and self.payment_desc_entry.get().strip() and self.payment_amount_entry.get().strip():
                self.add_payment_item(silent=True)
            
            date = self.payment_date_entry.get().strip()
            number = self.payment_number_entry.get().strip()
            
            # الحصول على المشروع المحدد
            project_id = None
            project_name = "غير محدد"
            if hasattr(self, 'payment_project_combo') and self.payment_project_combo.current() > 0:
                project_text = self.payment_project_combo.get()
                if " - " in project_text:
                    first_part = project_text.split(' - ')[0].strip()
                    if first_part.isdigit():
                        project_id = int(first_part)
                        project_name = ' - '.join(project_text.split(' - ')[1:])
            
            if not date or not number:
                messagebox.showerror("خطأ", "❌ يرجى التأكد من التاريخ ورقم السند")
                return
            
            # الحصول على البنود
            items = []
            for child in self.payment_tree.get_children():
                values = self.payment_tree.item(child, 'values')
                items.append(values)
            
            if not items:
                messagebox.showerror("خطأ", "❌ يرجى إضافة بنود للسند أولاً قبل الحفظ")
                return
            
            # في حالة التعديل، نحذف السجلات السابقة لهذا السند أولاً
            if getattr(self, 'editing_voucher_data', None):
                orig_num = self.editing_voucher_data.get('original_number', number)
                orig_date = self.editing_voucher_data.get('original_date', date)
                self.db.execute_query('''
                    DELETE FROM treasury_transactions 
                    WHERE date = ? AND (description LIKE ? OR description LIKE ?)
                ''', (orig_date, f'سند صرف #{orig_num} - %', f'سند صرف #{orig_num}'))
                self.db.execute_query('''
                    DELETE FROM transactions 
                    WHERE date = ? AND (description LIKE ? OR description LIKE ?)
                ''', (orig_date, f'سند صرف #{orig_num} - %', f'سند صرف #{orig_num}'))
            
            saved_voucher_items = []
            total_saved = 0.0
            
            # حفظ البنود - جميعها بنفس رقم السند
            for item in items:
                if len(item) >= 4:
                    account, item_project, description, amount = item[0], item[1], item[2], item[3]
                else:
                    account, description, amount = item[0], item[1], item[2]
                    item_project = ""
                amount_val = float(amount) if amount else 0.0
                
                if account and amount_val > 0:
                    trans_desc = f"سند صرف #{number} - {description}"
                    
                    customer_id = None
                    if " - " in account:
                        first_part = account.split(' - ')[0].strip()
                        if first_part.isdigit():
                            customer_id = int(first_part)
                    
                    row_project_id = project_id
                    if item_project and item_project not in ("-- select project --", "-- بدون مشروع --", "غير محدد", ""):
                        if " - " in item_project:
                            first_part = item_project.split(' - ')[0].strip()
                            if first_part.isdigit():
                                row_project_id = int(first_part)
                    
                    trans_type = 'expense'
                    
                    self.db.execute_query('''
                        INSERT INTO treasury_transactions 
                        (date, type, description, amount, account_name, project_id, customer_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (date, trans_type, trans_desc, amount_val, account, row_project_id, customer_id))
                    
                    self.db.execute_query('''
                        INSERT INTO transactions (type, amount, description, date, category)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (trans_type, amount_val, trans_desc, date, 'سندات صرف'))
                    
                    saved_voucher_items.append({
                        'account': account,
                        'description': description,
                        'amount': amount_val,
                        'project_name': item_project or project_name
                    })
                    total_saved += amount_val

            try:
                from central_refresh import emit_treasury_change
                emit_treasury_change()
            except:
                pass
            
            current_voucher_obj = {
                'number': number,
                'date': date,
                'project_name': project_name,
                'items': saved_voucher_items,
                'total': total_saved
            }
            
            # تحديث الصندوق وسجل السندات
            self.update_cash_data()
            if hasattr(self, 'load_saved_payment_vouchers'):
                self.load_saved_payment_vouchers()
            
            # مسح الجدول والحقول وتجهيز السند التالي
            self.clear_payment_form()
            
            if and_print:
                self.generate_voucher_pdf(current_voucher_obj)
            else:
                messagebox.showinfo("نجاح", f"✅ تم حفظ سند الصرف #{number} بنجاح!\nعدد البنود: {len(saved_voucher_items)}\nالإجمالي: {total_saved:,.2f} ريال\n\nتم تجهيز رقم السند التالي تلقائياً.")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Full error details: {error_details}")
            messagebox.showerror("خطأ", f"❌ فشل في حفظ السند: {str(e)}\n\nتفاصيل الخطأ:\n{error_details}")
    
    def save_journal_voucher(self):
        """حفظ سند اليومية"""
        try:
            date = self.journal_date_entry.get()
            number = self.journal_number_entry.get()
            description = self.journal_desc_search_entry.get()
            project = self.journal_project_combo.get()
            
            if not date or not number or not description:
                messagebox.showerror("خطأ", "❌ يرجى التأكد من التاريخ ورقم السند والبيان")
                return
            
            # الحصول على البنود
            items = []
            for child in self.journal_tree.get_children():
                values = self.journal_tree.item(child, 'values')
                items.append(values)
            
            if not items:
                messagebox.showerror("خطأ", "❌ يرجى إضافة بنود السند")
                return
            
            # التحقق من التوازن
            total_debit = sum(float(item[2]) for item in items)
            total_credit = sum(float(item[4]) for item in items)
            if abs(total_debit - total_credit) > 0.01:
                messagebox.showerror("خطأ", "❌ يجب أن يتساوى إجمالي المدين والدائن")
                return
            
            # استخراج معرف المشروع
            project_id = None
            
            if project and project != "-- اختر المشروع --":
                if " - " in project:
                    first_part = project.split(' - ')[0].strip()
                    if first_part.isdigit():
                        project_id = int(first_part)
            
            # حفظ البنود - حفظ المدين (expense) والدائن (income) مع ترقيم فريد
            item_counter = 1
            for item in items:
                row_num, debit_account, debit_amount, credit_account, credit_amount, description, project = item
                
                # البحث عن أكبر رقم بند فريد لتحديد الرقم التالي
                max_unique_item = self.db.execute_query('''
                    SELECT MAX(CAST(SUBSTR(description, 
                        INSTR(description, '- البند #') + 7, 
                        LENGTH(description) - INSTR(description, '- البند #') - 6
                    ) AS INTEGER)) as max_item
                    FROM treasury_transactions 
                    WHERE description LIKE 'سند يومية #% - البند #%'
                ''')
                
                next_unique_num = 1
                if max_unique_item and max_unique_item[0][0]:
                    try:
                        next_unique_num = int(max_unique_item[0][0]) + item_counter
                    except:
                        next_unique_num = item_counter
                else:
                    next_unique_num = item_counter
                
                # حفظ المدين (يعني زيادة للصندوق / أصل، لذلك نسجله income)
                if debit_account and debit_amount and float(debit_amount) > 0:
                    desc = f"سند يومية #{number} - {description} - البند #{next_unique_num}"
                    
                    # استخراج معرف العميل من الحساب المدين
                    customer_id = None
                    if " - " in debit_account:
                        first_part = debit_account.split(' - ')[0].strip()
                        if first_part.isdigit():
                            customer_id = int(first_part)
                    
                    self.db.execute_query('''
                        INSERT INTO treasury_transactions 
                        (date, type, description, amount, account_name, project_id, customer_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (date, 'income', desc, debit_amount, debit_account, project_id, customer_id))
                    
                    print(f"Debug: Saved journal voucher #{number} - income: {debit_amount} for {debit_account}")
                
                # حفظ الدائن (يعني نقص للصندوق / أصل، لذلك نسجله expense)
                if credit_account and credit_amount and float(credit_amount) > 0:
                    desc = f"سند يومية #{number} - {description} - البند #{next_unique_num}"
                    
                    # استخراج معرف العميل من الحساب الدائن
                    customer_id = None
                    if " - " in credit_account:
                        first_part = credit_account.split(' - ')[0].strip()
                        if first_part.isdigit():
                            customer_id = int(first_part)
                    
                    self.db.execute_query('''
                        INSERT INTO treasury_transactions 
                        (date, type, description, amount, account_name, project_id, customer_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (date, 'expense', desc, credit_amount, credit_account, project_id, customer_id))
                    
                    print(f"Debug: Saved journal voucher #{number} - expense: {credit_amount} for {credit_account}")
                
                item_counter += 1
            
            # مسح الجدول فقط بعد الحفظ - يبقى الوصف والمشروع
            for item in self.journal_tree.get_children():
                self.journal_tree.delete(item)
            
            # مسح حقول المبالغ فقط - يبقى الوصف والمشروع ثابتين
            self.journal_debit_entry.delete(0, tk.END)
            self.journal_credit_entry.configure(state='normal')
            self.journal_credit_entry.delete(0, tk.END)
            self.journal_credit_entry.configure(state='readonly')
            
            # تحديث الرقم التلقائي
            self.update_journal_voucher_number()
            
            messagebox.showinfo("نجاح", f"✅ تم حفظ السند بنجاح!\nرقم السند: #{number}\nالإجمالي: {total_debit:.2f} ريال\nعدد البنود: {len(items)}\n\nيمكنك إضافة سند جديد الآن")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Full error details: {error_details}")
            messagebox.showerror("خطأ", f"❌ فشل في حفظ السند: {str(e)}\n\nتفاصيل الخطأ:\n{error_details}")
    
    def view_journal_vouchers(self):
        """عرض جميع سندات اليومية بنفس مميزات سند الصرف"""
        try:
            # إنشاء نافذة جديدة لعرض السندات
            view_window = tk.Toplevel(self.frame)
            view_window.title("📋 عرض سندات اليومية")
            
            # ضبط حجم النافذة لتفتح بحجم كبير مريح ومتناسق مع الشاشة
            screen_w = view_window.winfo_screenwidth()
            screen_h = view_window.winfo_screenheight()
            win_w = min(1600, max(1200, int(screen_w * 0.94)))
            win_h = min(980, max(720, int(screen_h * 0.90)))
            x = max(10, (screen_w - win_w) // 2)
            y = max(10, (screen_h - win_h) // 2)
            view_window.geometry(f"{win_w}x{win_h}+{x}+{y}")
            view_window.minsize(1050, 600)
            view_window.transient(self.frame.master)
            
            # إطار رئيسي
            main_frame = ttk.Frame(view_window)
            main_frame.pack(fill='both', expand=True, padx=20, pady=20)
            
            # عنوان
            title_label = tk.Label(main_frame, text="📋 سندات اليومية", 
                                  font=('Segoe UI', 16, 'bold'))
            title_label.pack(pady=15)
            
            # إطار الأزرار
            button_frame = ttk.LabelFrame(main_frame, text="العمليات")
            button_frame.pack(fill='x', pady=(0, 15))
            
            button_content = ttk.Frame(button_frame)
            button_content.pack(fill='x', padx=15, pady=10)
            
            # إطار التحكم في التاريخ
            date_frame = ttk.LabelFrame(main_frame, text="التحكم في التاريخ")
            date_frame.pack(fill='x', pady=(0, 15))
            
            date_controls = ttk.Frame(date_frame)
            date_controls.pack(fill='x', padx=15, pady=10)
            
            # متغيرات لتخزين المراجع
            date_entry_var = tk.StringVar()
            date_entry_var.set(datetime.now().strftime('%Y-%m-%d'))
            
            # تعريف search_entry
            search_entry = ttk.Entry(date_controls, textvariable=date_entry_var, width=15, font=('Segoe UI', 11))
            
            # دوال التنقل
            def go_previous_day():
                """الانتقال ليوم السابق"""
                try:
                    current_date_str = search_entry.get()
                    if not current_date_str:
                        current_date = datetime.now()
                    else:
                        current_date = datetime.strptime(current_date_str, '%Y-%m-%d')
                    
                    new_date = current_date - timedelta(days=1)
                    new_date_str = new_date.strftime('%Y-%m-%d')
                    date_entry_var.set(new_date_str)
                    load_vouchers(new_date_str)
                except Exception as e:
                    messagebox.showerror("خطأ", f"فشل في الانتقال ليوم السابق: {str(e)}")
            
            def go_next_day():
                """الانتقال ليوم التالي"""
                try:
                    current_date_str = search_entry.get()
                    if not current_date_str:
                        current_date = datetime.now()
                    else:
                        current_date = datetime.strptime(current_date_str, '%Y-%m-%d')
                    
                    new_date = current_date + timedelta(days=1)
                    new_date_str = new_date.strftime('%Y-%m-%d')
                    date_entry_var.set(new_date_str)
                    load_vouchers(new_date_str)
                except Exception as e:
                    messagebox.showerror("خطأ", f"فشل في الانتقال ليوم التالي: {str(e)}")
            
            def go_today():
                """الانتقال ليوم اليوم"""
                try:
                    today = datetime.now()
                    today_str = today.strftime('%Y-%m-%d')
                    date_entry_var.set(today_str)
                    load_vouchers(today_str)
                except Exception as e:
                    messagebox.showerror("خطأ", f"فشل في الانتقال ليوم اليوم: {str(e)}")
            
            def search_vouchers():
                """البحث عن سندات بتاريخ معين"""
                try:
                    date = search_entry.get()
                    if date:
                        load_vouchers(date)
                    else:
                        messagebox.showwarning("تحذير", "⚠️ يرجى إدخال تاريخ صحيح")
                except Exception as e:
                    messagebox.showerror("خطأ", f"فشل في البحث: {str(e)}")
            
            # أزرار التنقل في التاريخ
            ttk.Button(date_controls, text="⬅️ يوم", command=go_previous_day, width=10).pack(side='right', padx=5)
            ttk.Button(date_controls, text="➡️ يوم", command=go_next_day, width=10).pack(side='right', padx=5)
            
            tk.Label(date_controls, text="التاريخ:", font=('Segoe UI', 11, 'bold')).pack(side='right', padx=5)
            search_entry.pack(side='right', padx=5)
            
            ttk.Button(date_controls, text="بحث", command=search_vouchers, width=8).pack(side='right', padx=5)
            ttk.Button(date_controls, text="اليوم", command=go_today, width=8).pack(side='right', padx=5)
            
            # إطار الملخص
            summary_frame = ttk.LabelFrame(main_frame, text="ملخص اليوم")
            summary_frame.pack(fill='x', pady=(0, 15))
            
            summary_content = ttk.Frame(summary_frame)
            summary_content.pack(fill='x', padx=15, pady=10)
            
            tk.Label(summary_content, text="إجمالي السندات:", font=('Segoe UI', 13, 'bold')).pack(side='right', padx=15)
            journal_total_label = tk.Label(summary_content, text="0.00 ريال", font=('Segoe UI', 13, 'bold'), fg='blue')
            journal_total_label.pack(side='right', padx=15)
            
            tk.Label(summary_content, text="عدد السندات:", font=('Segoe UI', 13, 'bold')).pack(side='right', padx=15)
            journal_count_label = tk.Label(summary_content, text="0", font=('Segoe UI', 13, 'bold'), fg='green')
            journal_count_label.pack(side='right', padx=15)
            
            tk.Label(summary_content, text="التاريخ الحالي:", font=('Segoe UI', 13, 'bold')).pack(side='right', padx=15)
            journal_date_label = tk.Label(summary_content, text=search_entry.get(), font=('Segoe UI', 13, 'bold'), fg='darkblue')
            journal_date_label.pack(side='right', padx=15)
            
            # جدول السندات
            tree_frame = ttk.LabelFrame(main_frame, text="قائمة سندات اليومية")
            tree_frame.pack(fill='both', expand=True, pady=(0, 15))
            
            # ⚠️ جدول السندات - أعمدة أوضح لعرض المدين والدائن
            columns = ('date', 'number', 'debit_account', 'debit', 'credit_account', 'credit', 'description', 'project', 'id')
            vouchers_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=25)
            
            vouchers_tree.heading('date', text='التاريخ')
            vouchers_tree.heading('number', text='رقم السند')
            vouchers_tree.heading('debit_account', text='حساب المدين')
            vouchers_tree.heading('debit', text='مدين (ريال)')
            vouchers_tree.heading('credit_account', text='حساب الدائن')
            vouchers_tree.heading('credit', text='دائن (ريال)')
            vouchers_tree.heading('description', text='البيان')
            vouchers_tree.heading('project', text='المشروع')
            vouchers_tree.heading('id', text='')  # عمود مخفي للمعرف
            
            vouchers_tree.column('date', width=90)
            vouchers_tree.column('number', width=70)
            vouchers_tree.column('debit_account', width=150)
            vouchers_tree.column('debit', width=80)
            vouchers_tree.column('credit_account', width=150)
            vouchers_tree.column('credit', width=80)
            vouchers_tree.column('description', width=180)
            vouchers_tree.column('project', width=100)
            vouchers_tree.column('id', width=0, stretch=False)  # إخفاء عمود المعرف
            
            vouchers_tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
            
            # شريط تمرير للجدول
            tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=vouchers_tree.yview)
            tree_scrollbar.pack(side='right', fill='y')
            vouchers_tree.configure(yscrollcommand=tree_scrollbar.set)
            
            # دالة لتحديث الإجمالي والمبلغ عند اختيار سند
            def on_tree_select(event):
                try:
                    selected = vouchers_tree.selection()
                    if selected:
                        item = vouchers_tree.item(selected[0], 'values')
                        date = item[0]
                        number = item[1]
                        
                        # البحث عن إجمالي ومبلغ السند المحدد
                        voucher_total = self.db.execute_query('''
                            SELECT SUM(amount) as total
                            FROM treasury_transactions 
                            WHERE date = ? AND description LIKE ?
                        ''', (date, f'سند يومية #{number}%'))
                        
                        if voucher_total and voucher_total[0][0]:
                            total = float(voucher_total[0][0])
                            journal_total_label.config(text=f"{total:.2f} ريال")
                            journal_date_label.config(text=date)
                except Exception as e:
                    print(f"Error updating totals: {e}")
            
            # ربط الحدث بالاختيار
            vouchers_tree.bind('<<TreeviewSelect>>', on_tree_select)
            
            def load_vouchers(date=None):
                """تحميل سندات اليومية - عرض المدين والدائن في سطر واحد"""
                try:
                    vouchers_tree.delete(*vouchers_tree.get_children())
                    
                    # دايماً جلب كل السندات بدون تحديد تاريخ
                    vouchers = self.db.execute_query('''
                        SELECT id, date, description, amount, account_name, type, project_id
                        FROM treasury_transactions 
                        WHERE description LIKE 'سند يومية #%'
                        ORDER BY date DESC, id ASC
                    ''')
                    
                    total_amount = 0.0
                    voucher_count = 0
                    
                    # تجميع السندات حسب رقم السند (المدين والدائن معاً)
                    voucher_groups = {}
                    for voucher in vouchers:
                        record_id = voucher[0]
                        date_str = voucher[1]
                        desc = voucher[2]
                        amount = voucher[3]
                        account = voucher[4]
                        trans_type = voucher[5]
                        project_id = voucher[6]
                        
                        # استخراج رقم السند من الوصف
                        if 'سند يومية #' in desc:
                            number = desc.split('#')[1].split()[0]
                            actual_desc = desc.split('-', 1)[1].strip() if '-' in desc else desc
                        else:
                            number = "N/A"
                            actual_desc = desc
                        
                        # مفتاح فريد لكل سند (التاريخ + رقم السند فقط)
                        voucher_key = f"{date_str}_{number}"
                        
                        if voucher_key not in voucher_groups:
                            voucher_groups[voucher_key] = {
                                'date': date_str,
                                'number': number,
                                'debit_account': '',
                                'debit_amount': 0,
                                'credit_account': '',
                                'credit_amount': 0,
                                'description': actual_desc,
                                'project_id': project_id,
                                'debit_id': None,
                                'credit_id': None
                            }
                        
                        # تخزين المدين أو الدائن
                        if trans_type == 'expense':
                            voucher_groups[voucher_key]['debit_account'] = account
                            voucher_groups[voucher_key]['debit_amount'] = float(amount)
                            voucher_groups[voucher_key]['debit_id'] = record_id
                            total_amount += float(amount)
                        elif trans_type == 'income':
                            voucher_groups[voucher_key]['credit_account'] = account
                            voucher_groups[voucher_key]['credit_amount'] = float(amount)
                            voucher_groups[voucher_key]['credit_id'] = record_id
                    
                    # عرض السندات المجمعة
                    for voucher_key, data in voucher_groups.items():
                        # الحصول على اسم المشروع
                        project_name = ""
                        if data['project_id']:
                            project_result = self.db.execute_query(
                                "SELECT name FROM projects WHERE id = ?", (data['project_id'],)
                            )
                            if project_result:
                                project_name = project_result[0][0]
                        
                        # استخدام معرف المدين كمعرف أساسي للسند
                        record_id = data['debit_id'] if data['debit_id'] else data['credit_id']
                        
                        vouchers_tree.insert('', 'end', values=(
                            data['date'], 
                            data['number'], 
                            data['debit_account'],
                            f"{data['debit_amount']:.2f}" if data['debit_amount'] > 0 else "",
                            data['credit_account'],
                            f"{data['credit_amount']:.2f}" if data['credit_amount'] > 0 else "",
                            data['description'],
                            project_name,
                            record_id
                        ))
                        voucher_count += 1
                    
                    # تحديث الملخص
                    journal_total_label.config(text=f"{total_amount:.2f} ريال")
                    journal_count_label.config(text=str(voucher_count))
                    # تحديث التاريخ ليعمل مع كل السندات
                    if date:
                        journal_date_label.config(text=date)
                    else:
                        # عرض آخر تاريخ موجود في السندات
                        if voucher_groups:
                            last_date = list(voucher_groups.keys())[0] if voucher_groups else ""
                            journal_date_label.config(text=last_date)
                
                except Exception as e:
                    messagebox.showerror("خطأ", f"فشل في تحميل السندات: {str(e)}")
            
            # دوال العمليات
            def delete_selected():
                """حذف السند المحدد"""
                try:
                    selected = vouchers_tree.selection()
                    if not selected:
                        messagebox.showwarning("تحذير", "⚠️ يرجى اختيار سند للحذف")
                        return
                    
                    item = vouchers_tree.item(selected[0], 'values')
                    record_id = item[8] if len(item) > 8 else None  # معرف السجل
                    date = item[0]
                    number = item[1]
                    account = item[2]
                    amount = item[3]
                    
                    if not record_id:
                        messagebox.showerror("خطأ", "❌ لا يمكن تحديد السجل للحذف")
                        return
                    
                    if messagebox.askyesno("تأكيد الحذف", f"هل أنت متأكد من حذف هذا السند؟\n\nالتاريخ: {date}\nرقم السند: {number}\nالحساب: {account}\nالمبلغ: {amount} ريال"):
                        # ✅ حذف السجل المحدد فقط باستخدام المعرف الفريد
                        self.db.execute_query(
                            'DELETE FROM treasury_transactions WHERE id = ?',
                            (record_id,)
                        )
                        
                        load_vouchers(search_entry.get())
                        messagebox.showinfo("نجاح", "✅ تم حذف السند بنجاح")
                except Exception as e:
                    messagebox.showerror("خطأ", f"فشل في حذف السند: {str(e)}")
            
            def delete_all():
                """حذف جميع سندات اليوم"""
                try:
                    current_date = search_entry.get()
                    if messagebox.askyesno("تأكيد الحذف", f"هل تريد حذف جميع سندات يوم {current_date}؟\n\nهذا الإجراء لا يمكن التراجع عنه!"):
                        self.db.execute_query('''
                            DELETE FROM treasury_transactions 
                            WHERE date = ? AND description LIKE 'سند يومية #%'
                        ''', (current_date,))
                        
                        load_vouchers(current_date)
                        messagebox.showinfo("نجاح", f"✅ تم حذف جميع سندات يوم {current_date}")
                except Exception as e:
                    messagebox.showerror("خطأ", f"فشل في حذف السندات: {str(e)}")
            
            def print_selected():
                """طباعة السند المحدد"""
                try:
                    selected = vouchers_tree.selection()
                    if not selected:
                        messagebox.showwarning("تحذير", "⚠️ يرجى اختيار سند للطباعة")
                        return
                    
                    item = vouchers_tree.item(selected[0], 'values')
                    # ⚠️ ترتيب الأعمدة: date, number, debit_account, debit, credit_account, credit, description, project
                    date = item[0]
                    number = item[1]
                    debit_account = item[2]
                    debit = item[3]
                    credit_account = item[4]
                    credit = item[5]
                    description = item[6]
                    project = item[7] if len(item) > 7 else ""
                    
                    # إنشاء ملف PDF
                    from fpdf import FPDF
                    import os
                    
                    filename = f"journal_voucher_{number}_{date.replace('-', '_')}.pdf"
                    
                    try:
                        company_settings = self.load_company_settings()
                        pdf = CustomVoucherPDF(company_settings)
                        pdf.add_page()
                        
                        # إضافة بيانات سند اليومية - تمرير جميع البيانات
                        data = [date, number, debit_account, description, debit, credit, project, credit_account]
                        pdf.add_journal_voucher_data(data)
                        
                        pdf.output(filename)
                        
                        if os.path.exists(filename):
                            messagebox.showinfo("نجاح", f"✅ تم حفظ السند ك PDF بنجاح!\nاسم الملف: {filename}")
                            try:
                                import webbrowser
                                webbrowser.open(f"file://{os.path.abspath(filename)}")
                            except Exception as open_error:
                                print(f"خطأ في فتح الملف: {open_error}")
                        else:
                            messagebox.showerror("خطأ", "❌ فشل في حفظ الملف")
                            
                    except Exception as pdf_error:
                        print(f"خطأ في إنشاء PDF: {pdf_error}")
                        messagebox.showerror("خطأ في الطباعة", f"❌ فشل في إنشاء ملف PDF: {str(pdf_error)}")
                        
                except Exception as e:
                    print(f"خطأ عام في الطباعة: {e}")
                    messagebox.showerror("خطأ", f"فشل في طباعة السند: {str(e)}")
            
            def print_daily():
                """طباعة جميع سندات اليوم"""
                try:
                    current_date = search_entry.get()
                    
                    # جلب بيانات اليوم
                    vouchers = self.db.execute_query('''
                        SELECT date, description, amount, account_name, type,
                               CASE WHEN type = 'expense' THEN amount ELSE 0 END as debit,
                               CASE WHEN type = 'income' THEN amount ELSE 0 END as credit
                        FROM treasury_transactions 
                        WHERE date = ? AND description LIKE 'سند يومية #%'
                        ORDER BY description, type DESC
                    ''', (current_date,))
                    
                    if not vouchers:
                        messagebox.showwarning("تحذير", f"⚠️ لا توجد سندات في يوم {current_date}")
                        return
                    
                    # تجميع السندات
                    processed_vouchers = {}
                    for voucher in vouchers:
                        date_str = voucher[0]
                        desc = voucher[1]
                        amount = voucher[2]
                        account = voucher[3]
                        trans_type = voucher[4]
                        debit = voucher[5] if voucher[5] else 0
                        credit = voucher[6] if voucher[6] else 0
                        
                        if 'سند يومية #' in desc:
                            number = desc.split('#')[1].split()[0]
                            actual_desc = desc.split('-', 1)[1].strip() if '-' in desc else desc
                            project_name = ""
                            if '(مشروع:' in actual_desc:
                                project_name = actual_desc.split('(مشروع:')[1].split(')')[0]
                                actual_desc = actual_desc.split('(مشروع:')[0].strip()
                        else:
                            number = "N/A"
                            actual_desc = desc
                            project_name = ""
                        
                        voucher_key = f"{date_str}_{number}"
                        
                        if voucher_key not in processed_vouchers:
                            processed_vouchers[voucher_key] = {
                                'date': date_str,
                                'number': number,
                                'debit_account': '',
                                'credit_account': '',
                                'debit': 0,
                                'credit': 0,
                                'description': actual_desc,
                                'project': project_name
                            }
                        
                        if trans_type == 'expense' and debit > 0:
                            processed_vouchers[voucher_key]['debit'] = float(debit)
                            processed_vouchers[voucher_key]['debit_account'] = account
                        elif trans_type == 'income' and credit > 0:
                            processed_vouchers[voucher_key]['credit'] = float(credit)
                            processed_vouchers[voucher_key]['credit_account'] = account
                    
                    # إنشاء ملف PDF
                    from fpdf import FPDF
                    import os
                    
                    filename = f"daily_journal_vouchers_{current_date.replace('-', '_')}.pdf"
                    
                    try:
                        company_settings = self.load_company_settings()
                        pdf = CustomDailyVouchersPDF(company_settings)
                        pdf.add_page()
                        
                        # إضافة بيانات سندات اليومية
                        pdf.add_daily_journal_vouchers_data(current_date, list(processed_vouchers.values()))
                        
                        pdf.output(filename)
                        
                        if os.path.exists(filename):
                            messagebox.showinfo("نجاح", f"✅ تم حفظ سندات اليوم ك PDF بنجاح!\nاسم الملف: {filename}\nعدد السندات: {len(processed_vouchers)}")
                            try:
                                import webbrowser
                                webbrowser.open(f"file://{os.path.abspath(filename)}")
                            except Exception as open_error:
                                print(f"خطأ في فتح الملف: {open_error}")
                        else:
                            messagebox.showerror("خطأ", "❌ فشل في حفظ الملف")
                            
                    except Exception as pdf_error:
                        print(f"خطأ في إنشاء PDF اليومي: {pdf_error}")
                        messagebox.showerror("خطأ في الطباعة", f"❌ فشل في إنشاء ملف PDF: {str(pdf_error)}")
                        
                except Exception as e:
                    print(f"خطأ عام في الطباعة اليومية: {e}")
                    messagebox.showerror("خطأ", f"فشل في طباعة سندات اليوم: {str(e)}")
            
            # أزرار العمليات
            ttk.Button(button_content, text="🖨️ طباعة السند", command=print_selected, width=15).pack(side='right', padx=8, ipady=5)
            ttk.Button(button_content, text="✏️ تعديل السند", command=lambda: self.edit_selected_voucher(vouchers_tree, view_window, load_vouchers, search_entry.get()), width=15).pack(side='right', padx=8, ipady=5)
            ttk.Button(button_content, text="🗑️ حذف البند", command=delete_selected, width=15).pack(side='right', padx=8, ipady=5)
            ttk.Button(button_content, text="🗑️ حذف السند بالكامل", command=delete_all, width=22).pack(side='right', padx=8, ipady=5)
            ttk.Button(button_content, text="🖨️ طباعة كل اليوم", command=print_daily, width=18).pack(side='right', padx=8, ipady=5)
            ttk.Button(button_content, text="➕ إضافة سند ليوم", command=lambda: self.add_voucher_for_date(search_entry.get(), view_window), width=18).pack(side='right', padx=8, ipady=5)
            
            # إغلاق النافذة
            ttk.Button(button_content, text="إغلاق", command=view_window.destroy, width=12).pack(side='left', padx=8, ipady=5)
            
            # تحميل السندات الحالية تلقائياً
            load_vouchers(datetime.now().strftime('%Y-%m-%d'))
            
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل في فتح عرض السندات: {str(e)}")
    
    def add_account_item(self):
        """إضافة بند حساب جديد (الاسم فقط) مع أزرار واضحة وأنيقة"""
        dialog = tk.Toplevel(self.frame)
        dialog.title("➕ إضافة بند حساب جديد")
        dialog.geometry("560x440")
        dialog.minsize(540, 420)
        dialog.resizable(True, True)
        dialog.transient(self.frame)
        dialog.grab_set()
        dialog.configure(bg='#F8FAFC')
        
        dialog.update_idletasks()
        try:
            x = self.frame.winfo_rootx() + (self.frame.winfo_width() // 2) - 280
            y = self.frame.winfo_rooty() + (self.frame.winfo_height() // 2) - 220
            dialog.geometry(f"560x440+{max(50, x)}+{max(50, y)}")
        except Exception:
            pass

        container = tk.Frame(dialog, bg='#F8FAFC', padx=25, pady=15)
        container.pack(fill='both', expand=True)

        header_frame = tk.Frame(container, bg='#F8FAFC')
        header_frame.pack(fill='x', pady=(0, 15))
        tk.Label(header_frame, text="📋 إضافة بند حساب جديد", font=('Segoe UI', 15, 'bold'), fg='#1E293B', bg='#F8FAFC').pack(anchor='center')
        tk.Label(header_frame, text="أدخل اسم البند لإضافته لشجرة الحسابات واستخدامه في القيود والسندات", font=('Segoe UI', 9), fg='#64748B', bg='#F8FAFC').pack(anchor='center', pady=(2, 0))

        card = tk.Frame(container, bg='white', highlightbackground='#CBD5E1', highlightthickness=1, padx=20, pady=15)
        card.pack(fill='x', pady=(0, 15))

        tk.Label(card, text="اسم بند الحساب *", font=('Segoe UI', 11, 'bold'), fg='#334155', bg='white').pack(anchor='e', pady=(0, 6))
        name_entry = tk.Entry(card, font=('Segoe UI', 12), justify='right', relief='solid', bd=1, highlightthickness=0)
        name_entry.pack(fill='x', ipady=6)
        name_entry.focus_set()

        def save(event=None):
            try:
                name = name_entry.get().strip()
                if not name:
                    messagebox.showwarning("تنبيه", "⚠️ يرجى إدخال اسم بند الحساب")
                    name_entry.focus_set()
                    return

                try:
                    self.db.execute_query('SELECT 1 FROM account_items LIMIT 1')
                except Exception:
                    self.db.execute_query('''
                        CREATE TABLE IF NOT EXISTS account_items
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         number TEXT UNIQUE,
                         name TEXT,
                         type TEXT)
                    ''')

                # حساب رقم البند بدقة استناداً لأعلى رقم ACC موجود
                import re
                rows = self.db.execute_query("SELECT number FROM account_items WHERE number LIKE 'ACC%'")
                max_num = 0
                if rows:
                    for r in rows:
                        if r and r[0]:
                            m = re.search(r'ACC(\d+)', str(r[0]))
                            if m:
                                try:
                                    val = int(m.group(1))
                                    if val > max_num:
                                        max_num = val
                                except Exception:
                                    pass
                number = f"ACC{(max_num + 1):03d}"

                item_type = "عام"
                self.db.execute_query('''
                    INSERT INTO account_items (number, name, type)
                    VALUES (?, ?, ?)
                ''', (number, name, item_type))

                # التحقق من الحفظ لتفادي أي خطأ صامت
                chk = self.db.execute_query("SELECT id FROM account_items WHERE number = ?", (number,))
                if not chk:
                    from datetime import datetime
                    alt_number = f"ACC{datetime.now().strftime('%m%d%H%M%S')}"
                    self.db.execute_query('''
                        INSERT INTO account_items (number, name, type)
                        VALUES (?, ?, ?)
                    ''', (alt_number, name, item_type))

                self.status_callback(f"✅ تم إضافة بند الحساب: {name}")
                if hasattr(self, 'load_account_items'):
                    try:
                        self.load_account_items()
                    except Exception as e_load:
                        print(f"error reloading account items: {e_load}")
                dialog.destroy()
                try:
                    emit_account_items_change()
                except Exception:
                    pass

            except Exception as e:
                messagebox.showerror("خطأ", f"❌ فشل في إضافة البند: {str(e)}")

        name_entry.bind('<Return>', save)

        # سطر الأزرار الرئيسي: حفظ وإلغاء بجوار بعضهما بوضوح
        btn_frame = tk.Frame(container, bg='#F8FAFC')
        btn_frame.pack(fill='x', pady=(0, 12))

        btn_save = tk.Button(btn_frame, text="  💾 حفظ البند  ", command=save,
                             font=('Segoe UI', 11, 'bold'), bg='#10B981', fg='white',
                             activebackground='#059669', activeforeground='white',
                             relief='flat', padx=20, pady=7, cursor='hand2')
        btn_save.pack(side='right', padx=(10, 0))

        btn_cancel = tk.Button(btn_frame, text="  ❌ إلغاء  ", command=dialog.destroy,
                               font=('Segoe UI', 11), bg='#64748B', fg='white',
                               activebackground='#475569', activeforeground='white',
                               relief='flat', padx=18, pady=7, cursor='hand2')
        btn_cancel.pack(side='right')

        # فاصل أنيق
        sep = ttk.Separator(container, orient='horizontal')
        sep.pack(fill='x', pady=(4, 10))

        # زر الإدخال المتعدد في سطر مستقل لمنع أي تداخل نهائياً
        btn_multi = tk.Button(container, text="📋 أو اضغط هنا لإدخال عدة بنود دفعة واحدة في جدول سريع",
                              command=lambda: (dialog.destroy(), self.add_multiple_account_items()),
                              font=('Segoe UI', 10, 'bold'), bg='#EEF2FF', fg='#4F46E5',
                              activebackground='#E0E7FF', activeforeground='#4338CA',
                              relief='flat', bd=1, highlightbackground='#C7D2FE', highlightthickness=1,
                              pady=7, cursor='hand2')
        btn_multi.pack(fill='x')

    def add_multiple_account_items(self):
        """جدول إدخال بنود الحسابات السريع بتصميم شبكة إكسل منظمة ومطابقة لشاشات الإدخال السريع"""
        dialog = tk.Toplevel(self.frame)
        dialog.title("📋 جدول إدخال بنود الحسابات السريع")
        
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()
        win_w = min(1040, max(880, int(screen_w * 0.75)))
        win_h = min(680, max(540, int(screen_h * 0.72)))
        x = max(10, (screen_w - win_w) // 2)
        y = max(10, (screen_h - win_h) // 2)
        dialog.geometry(f"{win_w}x{win_h}+{x}+{y}")
        dialog.minsize(800, 480)
        dialog.transient(self.frame)
        dialog.grab_set()

        # Header banner (dark navy #1F3A52)
        header_frame = tk.Frame(dialog, bg='#1F3A52', pady=10)
        header_frame.pack(fill='x')
        tk.Label(header_frame, text="📋 جدول إدخال بنود الحسابات السريع", font=('Segoe UI', 13, 'bold'), fg='white', bg='#1F3A52').pack()
        tk.Label(header_frame, text='أدخل أسماء بنود الحسابات سطراً بسطر ثم اضغط "حفظ كافة البنود" (للتنقل السريع بين الأسطر اضغط Enter)',
                 font=('Segoe UI', 9), fg='#D5DBDB', bg='#1F3A52').pack(pady=(2, 0))

        # Bottom Bar (packed side='bottom' first to always stay visible!)
        btn_frame = tk.Frame(dialog, pady=10, bg='#EAEDED')
        btn_frame.pack(side='bottom', fill='x')

        # Scrollable table container
        container = ttk.Frame(dialog)
        container.pack(fill='both', expand=True, padx=15, pady=10)

        canvas = tk.Canvas(container, bg='#F8F9F9', highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#F8F9F9')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Column weights and minsize
        scrollable_frame.columnconfigure(0, weight=0, minsize=45)   # #
        scrollable_frame.columnconfigure(1, weight=5, minsize=380)  # اسم بند الحساب
        scrollable_frame.columnconfigure(2, weight=2, minsize=150)  # كود الحساب
        scrollable_frame.columnconfigure(3, weight=2, minsize=150)  # التصنيف / النوع

        # Headers in Row 0
        headers = [
            ("#", 45),
            ("* اسم بند الحساب (الوصف / البيان)", 380),
            ("كود الحساب (تلقائي)", 150),
            ("التصنيف / النوع", 150)
        ]
        for col_idx, (title, min_w) in enumerate(headers):
            lbl = tk.Label(scrollable_frame, text=title, font=('Segoe UI', 9, 'bold'),
                           bg='#1F3A52', fg='white', pady=8, padx=3, relief=tk.FLAT)
            lbl.grid(row=0, column=col_idx, sticky='nsew', padx=1, pady=(0, 4))

        # Determine current base ACC number from database
        try:
            self.db.execute_query('''
                CREATE TABLE IF NOT EXISTS account_items
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 number TEXT UNIQUE,
                 name TEXT,
                 type TEXT)
            ''')
            rows = self.db.execute_query("SELECT number FROM account_items WHERE number LIKE 'ACC%'")
            base_max = max([int(r[0].replace('ACC', '')) for r in rows if r[0].replace('ACC', '').isdigit()] or [0])
        except Exception:
            base_max = 0

        account_rows = []

        def add_acc_row(name="", item_type="عام"):
            row_idx = len(account_rows) + 1
            auto_code = f"ACC{(base_max + row_idx):03d}"

            # 0. Index Label
            lbl_num = tk.Label(scrollable_frame, text=str(row_idx), font=('Segoe UI', 9, 'bold'),
                               bg='#EAEDED', fg='#2C3E50', relief='solid', bd=1)
            lbl_num.grid(row=row_idx, column=0, sticky='nsew', padx=1, pady=1)

            # 1. Name Entry
            name_e = tk.Entry(scrollable_frame, font=('Segoe UI', 10), justify='right',
                              bg='white', relief='solid', bd=1)
            if name:
                name_e.insert(0, str(name))
            name_e.grid(row=row_idx, column=1, sticky='nsew', padx=1, pady=1)

            # 2. Auto Code Label (Light blue #EBF5FB)
            code_lbl = tk.Label(scrollable_frame, text=auto_code, font=('Segoe UI', 10, 'bold'),
                                bg='#EBF5FB', fg='#1A5276', relief='solid', bd=1)
            code_lbl.grid(row=row_idx, column=2, sticky='nsew', padx=1, pady=1)

            # 3. Type Combobox (Light yellow #FEF9E7)
            type_cb = ttk.Combobox(scrollable_frame, values=['عام', 'مصروفات', 'إيرادات', 'أصول', 'خصوم', 'خزينة'],
                                   font=('Segoe UI', 9), justify='center', state='readonly')
            type_cb.set(item_type or 'عام')
            type_cb.grid(row=row_idx, column=3, sticky='nsew', padx=1, pady=1)

            row_data = {
                'num_lbl': lbl_num,
                'name': name_e,
                'code_lbl': code_lbl,
                'type': type_cb
            }
            account_rows.append(row_data)

            # Pressing Enter on name jumps to next row's name, or creates a new row!
            def on_enter(e):
                idx = account_rows.index(row_data)
                if idx < len(account_rows) - 1:
                    account_rows[idx + 1]['name'].focus_set()
                else:
                    add_acc_row()
                    account_rows[-1]['name'].focus_set()

            name_e.bind('<Return>', on_enter)

        # Initial 8 rows
        for _ in range(8):
            add_acc_row()

        if account_rows:
            account_rows[0]['name'].focus_set()

        # Bottom Bar Buttons
        def paste_from_excel():
            try:
                clip = dialog.clipboard_get()
                if not clip:
                    return
            except Exception:
                messagebox.showwarning("تنبيه", "⚠️ الحافظة لا تحتوي على نصوص منسوخة", parent=dialog)
                return

            lines = [l.strip() for l in clip.replace('\r\n', '\n').replace('\r', '\n').split('\n') if l.strip()]
            if not lines:
                return

            r_idx = 0
            for l in lines:
                while r_idx < len(account_rows) and account_rows[r_idx]['name'].get().strip():
                    r_idx += 1
                if r_idx >= len(account_rows):
                    add_acc_row()
                
                parts = l.split('\t') if '\t' in l else l.split(',')
                account_rows[r_idx]['name'].delete(0, 'end')
                account_rows[r_idx]['name'].insert(0, parts[0].strip())
                if len(parts) > 1 and parts[1].strip() in ['عام', 'مصروفات', 'إيرادات', 'أصول', 'خصوم', 'خزينة']:
                    account_rows[r_idx]['type'].set(parts[1].strip())
                r_idx += 1

            messagebox.showinfo("نجاح", f"✅ تم استيراد {len(lines)} بند بنجاح في الجدول!", parent=dialog)

        def save_all():
            valid_items = []
            for r in account_rows:
                nm = r['name'].get().strip()
                if nm:
                    tp = r['type'].get().strip() or "عام"
                    valid_items.append((nm, tp))

            if not valid_items:
                messagebox.showwarning("تنبيه", "⚠️ يرجى كتابة اسم بند حساب واحد على الأقل في الجدول", parent=dialog)
                if account_rows:
                    account_rows[0]['name'].focus_set()
                return

            try:
                # Refresh max_num fresh
                rows = self.db.execute_query("SELECT number FROM account_items WHERE number LIKE 'ACC%'")
                cur_max = max([int(r[0].replace('ACC', '')) for r in rows if r[0].replace('ACC', '').isdigit()] or [0])

                added = 0
                for nm, tp in valid_items:
                    cur_max += 1
                    code = f"ACC{cur_max:03d}"
                    self.db.execute_query(
                        "INSERT INTO account_items (number, name, type) VALUES (?, ?, ?)",
                        (code, nm, tp)
                    )
                    added += 1

                self.status_callback(f"✅ تم إضافة {added} بند حساب بنجاح")
                self.load_account_items()
                emit_account_items_change()
                dialog.destroy()
                messagebox.showinfo("نجاح", f"✅ تم حفظ {added} بند حساب بنجاح في شجرة الحسابات!")

            except Exception as ex:
                messagebox.showerror("خطأ", f"❌ فشل الحفظ: {str(ex)}", parent=dialog)

        # Right buttons
        tk.Button(btn_frame, text="➕ إضافة 5 أسطر إضافية", command=lambda: [add_acc_row() for _ in range(5)],
                  bg='#5D6D7E', fg='white', font=('Segoe UI', 10, 'bold'), padx=14, pady=6, relief=tk.FLAT, cursor='hand2').pack(side='right', padx=10)

        tk.Button(btn_frame, text="📋 لصق من Excel", command=paste_from_excel,
                  bg='#34495E', fg='white', font=('Segoe UI', 9), padx=10, pady=6, relief=tk.FLAT, cursor='hand2').pack(side='right', padx=5)

        # Left buttons
        tk.Button(btn_frame, text="💾 حفظ كافة البنود لشجرة الحسابات", command=save_all,
                  bg='#27AE60', fg='white', font=('Segoe UI', 11, 'bold'), padx=18, pady=6, relief=tk.FLAT, cursor='hand2').pack(side='left', padx=10)

        tk.Button(btn_frame, text="❌ إلغاء", command=dialog.destroy,
                  bg='#95A5A6', fg='white', font=('Segoe UI', 10), padx=12, pady=6, relief=tk.FLAT, cursor='hand2').pack(side='left', padx=5)


    def edit_account_item(self):
        """تعديل بند حساب (الاسم فقط) مع أزرار واضحة وأنيقة"""
        try:
            selected = self.account_tree.selection()
            if not selected:
                messagebox.showwarning("تحذير", "⚠️ يرجى اختيار بند للتعديل")
                return

            item_data = self.account_tree.item(selected[0], 'values')
            item_id = item_data[0]
            current_name = item_data[2] if len(item_data) > 2 else ""

            dialog = tk.Toplevel(self.frame)
            dialog.title("✏️ تعديل بند حساب")
            dialog.geometry("520x330")
            dialog.minsize(520, 330)
            dialog.resizable(False, False)
            dialog.transient(self.frame)
            dialog.grab_set()
            dialog.configure(bg='#F8FAFC')

            dialog.update_idletasks()
            try:
                x = self.frame.winfo_rootx() + (self.frame.winfo_width() // 2) - 260
                y = self.frame.winfo_rooty() + (self.frame.winfo_height() // 2) - 165
                dialog.geometry(f"520x330+{max(50, x)}+{max(50, y)}")
            except Exception:
                pass

            container = tk.Frame(dialog, bg='#F8FAFC', padx=30, pady=20)
            container.pack(fill='both', expand=True)

            header_frame = tk.Frame(container, bg='#F8FAFC')
            header_frame.pack(fill='x', pady=(0, 15))
            tk.Label(header_frame, text="✏️ تعديل اسم بند الحساب", font=('Segoe UI', 15, 'bold'), fg='#1E293B', bg='#F8FAFC').pack(anchor='center')
            tk.Label(header_frame, text="تعديل اسم البند الحالي وتحديثه في كافة العمليات", font=('Segoe UI', 9), fg='#64748B', bg='#F8FAFC').pack(anchor='center', pady=(2, 0))

            card = tk.Frame(container, bg='white', highlightbackground='#CBD5E1', highlightthickness=1, padx=20, pady=15)
            card.pack(fill='x', pady=(0, 20))

            tk.Label(card, text="اسم بند الحساب *", font=('Segoe UI', 11, 'bold'), fg='#334155', bg='white').pack(anchor='e', pady=(0, 6))
            name_entry = tk.Entry(card, font=('Segoe UI', 12), justify='right', relief='solid', bd=1, highlightthickness=0)
            name_entry.pack(fill='x', ipady=6)
            name_entry.insert(0, current_name)
            name_entry.focus_set()

            def save(event=None):
                try:
                    name = name_entry.get().strip()
                    if not name:
                        messagebox.showwarning("تنبيه", "⚠️ يرجى إدخال اسم بند الحساب")
                        name_entry.focus_set()
                        return

                    self.db.execute_query('''
                        UPDATE account_items SET name=?
                        WHERE id=?
                    ''', (name, item_id))

                    self.status_callback(f"✅ تم تحديث بند الحساب: {name}")
                    self.load_account_items()
                    dialog.destroy()
                    emit_account_items_change()

                except Exception as e:
                    messagebox.showerror("خطأ", f"❌ فشل في تعديل البند: {str(e)}")

            name_entry.bind('<Return>', save)

            btn_frame = tk.Frame(container, bg='#F8FAFC')
            btn_frame.pack(fill='x', pady=5)

            btn_save = tk.Button(btn_frame, text="  💾 حفظ التعديل  ", command=save,
                                 font=('Segoe UI', 11, 'bold'), bg='#0284C7', fg='white',
                                 activebackground='#0369A1', activeforeground='white',
                                 relief='flat', padx=20, pady=8, cursor='hand2')
            btn_save.pack(side='right', padx=(10, 0))

            btn_cancel = tk.Button(btn_frame, text="  ❌ إلغاء  ", command=dialog.destroy,
                                   font=('Segoe UI', 11), bg='#64748B', fg='white',
                                   activebackground='#475569', activeforeground='white',
                                   relief='flat', padx=18, pady=8, cursor='hand2')
            btn_cancel.pack(side='right')

        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تعديل البند: {str(e)}")

    def delete_account_item(self):
        """حذف بند حساب"""
        try:
            selected = self.account_tree.selection()
            if not selected:
                messagebox.showwarning("تحذير", "⚠️ يرجى اختيار بند للحذف")
                return
            
            if messagebox.askyesno("تأكيد الحذف", "⚠️ هل أنت متأكد من حذف هذا البند؟"):
                item_data = self.account_tree.item(selected[0], 'values')
                item_id = item_data[0]
                
                self.db.execute_query("DELETE FROM account_items WHERE id=?", (item_id,))
                
                self.status_callback("✅ تم حذف البند بنجاح")
                self.load_account_items()
                
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حذف البند: {str(e)}")
