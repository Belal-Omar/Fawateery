import sys
import os
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import arabic_entry_fix  # Arabic entry selection/RTL fix
# # import arabic_entry_fix  # Arabic entry fix (temporarily disabled)
# import rtl_entry_fix  # removed – Tk 8.6.15 provides proper RTL handling
# import rtl_entry_fix  # not needed with modern Tk
# No custom Arabic entry fix needed – Tk 8.6.15 handles RTL natively
  # removed – Tk 8.6.15 provides proper RTL handling

import arabic_entry_fix  # Arabic entry selection/RTL fix
# import rtl_entry_fix  # removed – Tk 8.6.15 provides proper RTL handling
# import rtl_entry_fix  # not needed with modern Tk
# No custom Arabic entry fix needed – Tk 8.6.15 handles RTL natively

arabic_entry_fix.apply_arabic_entry_fix()
from datetime import datetime, timedelta
import warnings
import sqlite3
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
import webbrowser
from fpdf import FPDF
import pandas as pd
import ctypes
from icon_manager import IconManager, ICONS

# DPI Scaling - أهم نقطة للتعامل مع جميع الشاشات
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

# إجبار إعادة تحميل الوحدة للتأكد من استخدام الكود الجديد
if 'invoices_module' in sys.modules:
    import importlib
    importlib.reload(sys.modules['invoices_module'])

# استيراد الوحدات
from invoices_module import InvoiceModule
from employees import EmployeesModule
from transactions import TransactionsModule
from projects import ProjectsModule
from reports import ReportsModule
from company_settings import CompanySettingsDialog
from database import Database, get_db_path
from accounts_receivable_module import AccountsReceivableModule
from accounts_payable_module import AccountsPayableModule
from treasury_module import TreasuryModule
from customer_project_module import CustomerProjectModule
from authorizations_module import AuthorizationsModule
from central_refresh import central_refresh, refresh_all, emit_customer_change, emit_project_change, emit_employee_change, emit_invoice_change, emit_transaction_change
from updater import check_for_updates, CURRENT_VERSION

warnings.filterwarnings("ignore", message="You have both PyFPDF & fpdf2 installed")

class ModernButton(tk.Button):
    """زر عصري محسن مع تأثيرات بصرية"""
    def __init__(self, master=None, **kwargs):
        # استخراج المعاملات المهمة
        text = kwargs.get('text', '')
        bg = kwargs.get('bg', '#3498DB')
        fg = kwargs.get('fg', 'white')
        command = kwargs.get('command', None)
        
        # إزالة المعاملات التي سنستخدمها بشكل مخصص
        for key in ['style', 'text', 'bg', 'fg', 'command']:
            kwargs.pop(key, None)
        
        # استدعاء المنشئ الأصلي مع النص
        super().__init__(master, text=text, bg=bg, fg=fg, command=command, **kwargs)
        
        # تعزيز النص والألوان لضمان الوضوح
        self.configure(
            relief=tk.RAISED,
            bd=2,
            cursor='hand2',
            font=('Arial', 11, 'bold'),  # استخدام Arial بدلاً من Segoe UI
            padx=20,
            pady=10,
            activebackground=bg,
            activeforeground=fg,
            highlightbackground=bg,
            highlightthickness=1
        )
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
    
    def on_enter(self, e):
        self.configure(relief=tk.GROOVE, bd=3)
    
    def on_leave(self, e):
        self.configure(relief=tk.RAISED, bd=2)

class DashboardCard(tk.Frame):
    """بطاقة إحصائية للوحدة التحكم"""
    def __init__(self, parent, title, value, icon, color, command=None):
        super().__init__(parent, bg='white', relief=tk.RAISED, bd=1)
        self.configure(cursor='hand2' if command else 'arrow')
        self.value_label = None  # حفظ مرجع label القيمة
        
        # الحصول على scale factor من الـ parent
        self.scale = getattr(parent, 'scale', 1.0)
        
        # إعداد Grid للبطاقة - زيادة مساحة المحتوى
        self.grid_rowconfigure(0, weight=1)  # inner_frame
        self.grid_rowconfigure(1, weight=4)  # content_frame - زيادة الوزن
        self.grid_columnconfigure(0, weight=1)
        
        # إطار داخلي
        inner_frame = tk.Frame(self, bg=color)
        inner_frame.grid(row=0, column=0, sticky='ew')
        
        content_frame = tk.Frame(self, bg='white')
        content_frame.grid(row=1, column=0, sticky='nsew', padx=15, pady=15)  # زيادة الهوامش
        
        # إعداد Grid للمحتوى
        content_frame.grid_rowconfigure(0, weight=1)  # top_frame
        content_frame.grid_rowconfigure(1, weight=1)  # title
        content_frame.grid_columnconfigure(0, weight=1)
        
        # الأيقونة والقيمة
        top_frame = tk.Frame(content_frame, bg='white')
        top_frame.grid(row=0, column=0, sticky='ew')
        
        # إعداد Grid للأيقونة والقيمة
        top_frame.grid_columnconfigure(0, weight=1)  # أيقونة
        top_frame.grid_columnconfigure(1, weight=2)  # قيمة
        
        icon_label = tk.Label(top_frame, text=icon, font=('Segoe MDL2 Assets', int(24 * self.scale)),  # خط متجاوب ومناسب للأيقونات
                             bg='white', fg=color)
        icon_label.grid(row=0, column=0, sticky='e', padx=(0, 5))
        
        self.value_label = tk.Label(top_frame, text=str(value), font=('Segoe UI', int(18 * self.scale), 'bold'),  # خط متجاوب
                              bg='white', fg='#2C3E50')
        self.value_label.grid(row=0, column=1, sticky='w')
        
        # العنوان - خط متجاوب
        title_label = tk.Label(content_frame, text=title, font=('Segoe UI', int(11 * self.scale), 'bold'),  # خط متجاوب
                              bg='white', fg='#7F8C8D')
        title_label.grid(row=1, column=0, sticky='ew', pady=(10, 0))  # زيادة المسافة العلوية
        
        if command:
            self.bind('<Button-1>', lambda e: command())
            for widget in [self, inner_frame, content_frame, top_frame, icon_label, self.value_label, title_label]:
                widget.bind('<Button-1>', lambda e: command())
    
    def update_value(self, new_value):
        """تحديث قيمة البطاقة"""
        if self.value_label:
            self.value_label.config(text=str(new_value))

class AccountingApp:
    def __init__(self, root):
        self.root = root
        arabic_entry_fix.apply_arabic_entry_fix(self.root)
        self.root.title("فواتيري | Fawateery - نظام الفواتير والمحاسبة الذكي")
        self.icon_mgr = IconManager()
        
        # الحصول على حجم الشاشة وضبط النافذة بشكل متجاوب بالكامل
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Scale factor based on screen width - أهم نقطة للخطوط المتجاوبة
        self.scale = screen_width / 1366  # 1366 هو المقاس القياسي
        
        # ضبط حجم النافذة بشكل متجاوب بناءً على حجم الشاشة (نسب مئوية)
        if screen_width < 1024:  # شاشات صغيرة جداً
            window_width = int(screen_width * 0.95)
            window_height = int(screen_height * 0.9)
            min_width = 800
            min_height = 600
        elif screen_width < 1366:  # شاشات صغيرة
            window_width = int(screen_width * 0.9)
            window_height = int(screen_height * 0.85)
            min_width = 900
            min_height = 650
        elif screen_width < 1920:  # شاشات متوسطة
            window_width = int(screen_width * 0.85)
            window_height = int(screen_height * 0.8)
            min_width = 1000
            min_height = 700
        else:  # شاشات كبيرة
            window_width = int(screen_width * 0.8)
            window_height = int(screen_height * 0.75)
            min_width = 1200
            min_height = 800
        
        # توسيط النافذة
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        
        # فتح البرنامج في وضع الشاشة الكاملة
        self.root.state('zoomed')
        
        # تحديد الحد الأدنى بناءً على حجم الشاشة
        self.root.minsize(min_width, min_height)
        
        # تفعيل التمرير العالمي للبرنامج
        self.setup_global_scrolling()
        
        # السماح بتغيير الحجم
        self.root.resizable(True, True)
        
        # إعادة توزيع العناصر عند تغيير حجم النافذة
        self.root.bind("<Configure>", self.on_window_resize)
        
        # إعداد أيقونة التطبيق
        self.setup_icon()
        
        # ألوان النظام الجديدة - تصميم احترافي وحديث (Premium Slate/Blue)
        self.colors = {
            'primary': '#2563EB',      # أزرق ملكي حديث
            'secondary': '#64748B',     # رمادي مزرق
            'success': '#10B981',       # أخضر نقي
            'warning': '#F59E0B',       # برتقالي دافئ
            'danger': '#EF4444',       # أحمر واضح
            'info': '#3B82F6',         # أزرق فاتح
            'dark': '#0F172A',         # كحلي داكن جداً
            'light': '#F1F5F9',         # خلفية فاتحة جداً
            'bg': '#F8FAFC',           # خلفية النظام
            'card': '#FFFFFF',          # خلفية البطاقات (أبيض ناصع)
            'text': '#1E293B',          # نص رئيسي داكن
            'text_light': '#64748B'     # نص ثانوي
        }
        
        # إعداد الأنماط
        self.setup_styles()
        
        # إنشاء القوائم
        self.create_menu()
        
        # إنشاء شريط الحالة
        self.create_status_bar()
        
        # إنشاء الواجهة الرئيسية
        self.setup_main_interface()
        
        # التحقق من قاعدة البيانات
        self.check_database()
        
        # تحديث Dashboard
        self.update_dashboard()

        # فحص وجود تحديثات سحابية في الخلفية بهدوء بعد 5 ثوانٍ من بدء التشغيل
        try:
            self.root.after(5000, lambda: check_for_updates(self.root, silent=True))
        except Exception:
            pass
    
    def on_window_resize(self, event):
        """إعادة توزيع العناصر عند تغيير حجم النافذة"""
        # Prevent too many calls
        if event.widget == self.root:
            self.root.update_idletasks()
    
    def setup_global_scrolling(self):
        """إعداد التمرير العالمي للبرنامج"""
        # تفعيل التمرير بالعجلة في جميع أنحاء البرنامج
        self.root.bind('<MouseWheel>', self.global_mousewheel)
        self.root.bind_all('<MouseWheel>', self.global_mousewheel)
        
        # تفعيل التمرير لجميع النوافذ المستقبلية
        self.root.bind('<Map>', self.on_window_mapped)
    
    def global_mousewheel(self, event):
        """handle global mousewheel scrolling safely without drifting unscrollable canvases"""
        try:
            widget = event.widget
            while widget and hasattr(widget, 'master'):
                # Ignore Matplotlib or widgets explicitly marked not to scroll
                if getattr(widget, '_no_scroll', False) or getattr(widget, '_is_matplotlib', False):
                    break
                if hasattr(widget, 'canvas') and hasattr(widget, 'on_mousewheel'):
                    widget.on_mousewheel(event)
                    break
                elif hasattr(widget, 'yview'):
                    # Canvases must have a valid scrollregion to be scrolled; otherwise they scroll into infinity
                    if isinstance(widget, tk.Canvas):
                        sr = widget.cget('scrollregion')
                        if not sr:
                            break
                    widget.yview_scroll(int(-1*(event.delta/120)), 'units')
                    break
                widget = widget.master
        except Exception:
            pass
    
    def on_window_mapped(self, event):
        """تفعيل التمرير للنوافذ الجديدة"""
        if event.widget != self.root:
            event.widget.bind('<MouseWheel>', self.global_mousewheel)
    
    def setup_styles(self):
        """إعداد الأنماط والألوان بشكل متجاوب"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # الحصول على حجم الشاشة لضبط الأحجام بشكل متجاوب
        screen_width = self.root.winfo_screenwidth()
        
        if screen_width < 1024:  # شاشات صغيرة جداً
            font_size = 8
            button_padding = (8, 4)
            row_height = 22
            tab_padding = (10, 4)
        elif screen_width < 1366:  # شاشات صغيرة
            font_size = 9
            button_padding = (10, 6)
            row_height = 25
            tab_padding = (12, 6)
        elif screen_width < 1920:  # شاشات متوسطة
            font_size = 10
            button_padding = (12, 8)
            row_height = 28
            tab_padding = (15, 8)
        else:  # شاشات كبيرة
            font_size = 11
            button_padding = (14, 10)
            row_height = 30
            tab_padding = (18, 10)
        
        # تخصيص الأنماط المتجاوبة
        self.style.configure('TFrame', background=self.colors['bg'])
        self.style.configure('TLabel', background=self.colors['bg'], 
                           font=('Segoe UI', font_size), foreground=self.colors['text'])
        self.style.configure('TButton', font=('Segoe UI', font_size), padding=button_padding)
        self.style.configure('Treeview', font=('Segoe UI', font_size), 
                           background='white', rowheight=row_height)
        self.style.configure('Treeview.Heading', font=('Segoe UI', font_size + 1, 'bold'),
                           background=self.colors['primary'], foreground='white')
        self.style.configure('TLabelframe', background=self.colors['bg'],
                           font=('Segoe UI', font_size + 1, 'bold'))
        self.style.configure('TLabelframe.Label', background=self.colors['bg'],
                           font=('Segoe UI', font_size + 1, 'bold'))
        self.style.configure('TNotebook', background=self.colors['bg'], borderwidth=0)
        self.style.configure('TNotebook.Tab', font=('Segoe UI', font_size, 'bold'),
                           padding=tab_padding, background=self.colors['light'])
        self.style.map('TNotebook.Tab',
                      background=[('selected', self.colors['primary'])],
                      foreground=[('selected', 'white')])
        self.style.configure('TEntry', font=('Segoe UI', font_size), padding=5,
                           fieldbackground='white')
        self.style.configure('TCombobox', font=('Segoe UI', font_size), padding=5,
                           fieldbackground='white')
    
    def setup_icon(self):
        """إعداد أيقونة التطبيق"""
        try:
            import os
            import sys
            from PIL import Image, ImageTk
            
            search_dirs = []
            if getattr(sys, 'frozen', False):
                if hasattr(sys, '_MEIPASS'):
                    search_dirs.append(sys._MEIPASS)
                search_dirs.append(os.path.dirname(sys.executable))
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            search_dirs.append(current_dir)
            search_dirs.append(os.getcwd())
            
            ico_loaded = False
            for d in search_dirs:
                ico_path = os.path.join(d, 'fawateery_icon.ico')
                if os.path.exists(ico_path):
                    try:
                        self.root.iconbitmap(ico_path)
                        ico_loaded = True
                        print(f"✅ Icon loaded: {ico_path}")
                        break
                    except Exception as e:
                        print(f"⚠️ Failed to load ico {ico_path}: {e}")
            
            # Also set iconphoto for taskbar and high-DPI displays
            for d in search_dirs:
                for img_name in ['fawateery_icon_256.png', 'أيقونة إف للحسابات والنمو.png', 'fawateery_icon.ico']:
                    img_path = os.path.join(d, img_name)
                    if os.path.exists(img_path):
                        try:
                            pil_img = Image.open(img_path)
                            self._app_icon_img = ImageTk.PhotoImage(pil_img)
                            self.root.iconphoto(False, self._app_icon_img)
                            break
                        except Exception as e:
                            pass
                if hasattr(self, '_app_icon_img'):
                    break
        except Exception as e:
            print(f"⚠️ Icon setup error: {e}")
    
    def setup_keyboard_shortcuts(self):
        """إعداد اختصارات لوحة المفاتيح"""
        # اختصارات النسخ واللصق
        self.root.bind('<Control-c>', lambda e: self.copy_text())
        self.root.bind('<Control-C>', lambda e: self.copy_text())
        self.root.bind('<Control-v>', lambda e: self.paste_text())
        self.root.bind('<Control-V>', lambda e: self.paste_text())
        self.root.bind('<Control-x>', lambda e: self.cut_text())
        self.root.bind('<Control-X>', lambda e: self.cut_text())
        
        # Enter للتنقل بين الحقول
        self.root.bind('<Return>', lambda e: self.handle_enter_key(e))
        self.root.bind('<KP_Enter>', lambda e: self.handle_enter_key(e))  # Enter من لوحة الأرقام
    
    def copy_text(self):
        """نسخ النص المحدد"""
        try:
            focused = self.root.focus_get()
            if focused and hasattr(focused, 'selection_get'):
                selected = focused.selection_get()
                self.root.clipboard_clear()
                self.root.clipboard_append(selected)
                self.update_status("✅ تم نسخ النص")
        except:
            pass
    
    def paste_text(self):
        """لصق النص"""
        try:
            focused = self.root.focus_get()
            if focused and hasattr(focused, 'insert'):
                text = self.root.clipboard_get()
                focused.insert(tk.INSERT, text)
                self.update_status("✅ تم لصق النص")
        except:
            pass
    
    def cut_text(self):
        """قص النص المحدد"""
        try:
            focused = self.root.focus_get()
            if focused and hasattr(focused, 'selection_get'):
                selected = focused.selection_get()
                self.root.clipboard_clear()
                self.root.clipboard_append(selected)
                # حذف النص المحدد
                if hasattr(focused, 'delete'):
                    focused.delete(tk.SEL_FIRST, tk.SEL_LAST)
                self.update_status("✅ تم قص النص")
        except:
            pass
    
    def handle_enter_key(self, event):
        """معالجة ضغط Enter للتنقل بين الحقول"""
        try:
            widget = event.widget
            if widget and hasattr(widget, 'tk'):
                widget.tk_focusNext().focus()
                return 'break'  # منع السلوك الافتراضي
        except:
            pass
    
    def create_status_bar(self):
        """إنشاء شريط الحالة بشكل متجاوب"""
        # الحصول على حجم الشاشة لضبط الحجم بشكل متجاوب
        screen_width = self.root.winfo_screenwidth()
        
        if screen_width < 1024:  # شاشات صغيرة جداً
            status_height = 25
            font_size = 7
            padx_value = 10
        elif screen_width < 1366:  # شاشات صغيرة
            status_height = 28
            font_size = 8
            padx_value = 12
        else:  # شاشات متوسطة وكبيرة
            status_height = 30
            font_size = 9
            padx_value = 15
        
        status_frame = tk.Frame(self.root, bg=self.colors['primary'], height=status_height)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(status_frame, text="فواتيري جاهز للاستخدام",
                                    bg=self.colors['primary'], fg='white',
                                    font=('Segoe UI', font_size))
        self.status_label.pack(side='right', padx=padx_value, pady=5)
        
        # الوقت والتاريخ
        self.time_label = tk.Label(status_frame, text="", bg=self.colors['primary'],
                                   fg='white', font=('Segoe UI', font_size))
        self.time_label.pack(side='left', padx=padx_value, pady=5)
        self.update_time()
    
    def update_time(self):
        """تحديث الوقت في شريط الحالة"""
        try:
            if not hasattr(self, 'root') or not self.root.winfo_exists():
                return
            now = datetime.now()
            time_str = now.strftime("%Y-%m-%d | %H:%M:%S")
            if hasattr(self, 'time_label') and self.time_label.winfo_exists():
                self.time_label.config(text=time_str)
                self._time_after_id = self.root.after(1000, self.update_time)
        except Exception:
            pass
    
    def setup_main_interface(self):
        """إنشاء الواجهة الرئيسية بشكل متجاوب"""
        # الحصول على حجم الشاشة لضبط الهوامش بشكل متجاوب
        screen_width = self.root.winfo_screenwidth()
        
        if screen_width < 1024:  # شاشات صغيرة جداً
            main_padx = 2
            main_pady = 2
            content_padx = 2
            content_pady = 2
            notebook_padx = 2
            notebook_pady = 2
        elif screen_width < 1366:  # شاشات صغيرة
            main_padx = 3
            main_pady = 3
            content_padx = 3
            content_pady = 3
            notebook_padx = 3
            notebook_pady = 3
        else:  # شاشات متوسطة وكبيرة
            main_padx = 5
            main_pady = 5
            content_padx = 5
            content_pady = 5
            notebook_padx = 5
            notebook_pady = 5
        
        # إطار رئيسي
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill='both', expand=True, padx=main_padx, pady=main_pady)
        
        # شريط علوي
        self.create_top_bar(main_container)
        
        # المحتوى الرئيسي - مع تحسين للأحجام المختلفة
        content_frame = tk.Frame(main_container, bg=self.colors['bg'])
        content_frame.pack(fill='both', expand=True, padx=content_padx, pady=content_pady)
        
        # التبويبات
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(fill='both', expand=True, padx=notebook_padx, pady=notebook_pady)
        
        # إنشاء Dashboard كأول تبويب
        self.create_dashboard_tab()
        
        # إنشاء الوحدات أولاً
        self.invoice_module = InvoiceModule(self.notebook, self.update_status)
        self.accounts_receivable_module = AccountsReceivableModule(self.notebook, self.update_status)
        self.accounts_payable_module = AccountsPayableModule(self.notebook, self.update_status)
        self.employees_module = EmployeesModule(self.notebook, self.update_status)
        self.transactions_module = TransactionsModule(self.notebook, self.update_status)
        self.projects_module = ProjectsModule(self.notebook, self.update_status)
        self.treasury_module = TreasuryModule(self.notebook, self.update_status)
        self.reports_module = ReportsModule(self.notebook, self.update_status, self.invoice_module, self.employees_module, self.transactions_module, self.projects_module)
        self.customer_project_module = CustomerProjectModule(self.notebook, self.update_status, Database())
        
        # إعداد نظام التحديث المركزي بعد إنشاء جميع الوحدات
        self.setup_central_refresh_system()
        
        # إعداد تحديث وحدة العملاء والمشاريع
        self.setup_customer_project_refresh()
        
        # إنشاء الصور للتبويبات
        tab_color = '#2C3E50'
        icon_size = 18
        self.icon_dash = self.icon_mgr.get_icon(ICONS['dashboard'], size=icon_size, color=tab_color)
        self.icon_inv = self.icon_mgr.get_icon(ICONS['invoice'], size=icon_size, color=tab_color)
        self.icon_ar = self.icon_mgr.get_icon(ICONS['accounts_rec'], size=icon_size, color=tab_color)
        self.icon_ap = self.icon_mgr.get_icon(ICONS['accounts_pay'], size=icon_size, color=tab_color)
        self.icon_emp = self.icon_mgr.get_icon(ICONS['employees'], size=icon_size, color=tab_color)
        self.icon_txn = self.icon_mgr.get_icon(ICONS['transactions'], size=icon_size, color=tab_color)
        self.icon_cust = self.icon_mgr.get_icon(ICONS['customers'], size=icon_size, color=tab_color)
        self.icon_cash = self.icon_mgr.get_icon(ICONS['treasury'], size=icon_size, color=tab_color)
        self.icon_vouchers = self.icon_mgr.get_icon(ICONS['invoice'], size=icon_size, color=tab_color)
        self.icon_rpt = self.icon_mgr.get_icon(ICONS['reports'], size=icon_size, color=tab_color)
        self.icon_set = self.icon_mgr.get_icon(ICONS['settings'], size=icon_size, color=tab_color)

        # إضافة التبويبات
        self.notebook.add(self.dashboard_frame, text=" لوحة التحكم", image=self.icon_dash, compound='left')
        self.notebook.add(self.invoice_module.frame, text=" الفواتير", image=self.icon_inv, compound='left')
        self.notebook.add(self.accounts_receivable_module.frame, text=" الحسابات المدينة", image=self.icon_ar, compound='left')
        self.notebook.add(self.accounts_payable_module.frame, text=" الحسابات الدائنة", image=self.icon_ap, compound='left')
        self.notebook.add(self.employees_module.frame, text=" الموظفين", image=self.icon_emp, compound='left')
        self.notebook.add(self.transactions_module.frame, text=" المعاملات", image=self.icon_txn, compound='left')
        self.notebook.add(self.customer_project_module.frame, text=" العملاء والمشاريع", image=self.icon_cust, compound='left')
        self.notebook.add(self.treasury_module.cash_frame, text=" الصندوق", image=self.icon_cash, compound='left')
        self.notebook.add(self.treasury_module.frame, text=" السندات", image=self.icon_vouchers, compound='left')
        self.notebook.add(self.reports_module.frame, text=" التقارير", image=self.icon_rpt, compound='left')
        
        # تبويب الإعدادات
        self.create_settings_tab()
        
        # ربط حدث تغيير التبويبات
        self.notebook.bind('<<NotebookTabChanged>>', self.on_tab_changed)
    
    def on_tab_changed(self, event):
        """يتم استدعاؤها عند تغيير التبويب النشط لتحديث البيانات"""
        try:
            selected_tab = self.notebook.index("current")
            if selected_tab == 0:
                self.update_dashboard()
            elif selected_tab == 1:
                self.invoice_module.load_invoices()
            elif selected_tab == 2:
                self.accounts_receivable_module.load_accounts()
            elif selected_tab == 3:
                self.accounts_payable_module.load_accounts()
            elif selected_tab == 4:
                self.employees_module.load_employees()
            elif selected_tab == 5:
                self.transactions_module.load_transactions()
            elif selected_tab == 6:
                self.customer_project_module.load_data()
            elif selected_tab == 7:
                self.treasury_module.load_cash_data()
            elif selected_tab == 8:
                if hasattr(self.treasury_module, 'load_payment_data'):
                    self.treasury_module.load_payment_data()
                if hasattr(self.treasury_module, 'load_journal_data'):
                    self.treasury_module.load_journal_data()
                if hasattr(self.treasury_module, 'load_account_items'):
                    self.treasury_module.load_account_items()
            elif selected_tab == 9:
                if hasattr(self.reports_module, 'load_reports'):
                    self.reports_module.load_reports()
        except Exception as e:
            print(f"Error refreshing tab {selected_tab}: {e}")
            
    def create_top_bar(self, parent):
        """إنشاء الشريط العلوي"""
        top_bar = tk.Frame(parent, bg=self.colors['primary'], height=60)
        top_bar.pack(fill='x')
        top_bar.pack_propagate(False)
        
        # إعداد Grid للشريط العلوي
        top_bar.grid_columnconfigure(0, weight=3)  # العنوان
        top_bar.grid_columnconfigure(1, weight=1)  # الأزرار السريعة
        
        # العنوان
        title_frame = tk.Frame(top_bar, bg=self.colors['primary'])
        title_frame.grid(row=0, column=0, padx=20, pady=10, sticky='ew')
        
        title_label = tk.Label(title_frame, text="فواتيري | Fawateery",
                               bg=self.colors['primary'], fg='white',
                               font=('Segoe UI', int(20 * self.scale), 'bold'))
        title_label.pack()
        
        # شعار فرعي
        subtitle_label = tk.Label(title_frame, text="نظام الفواتير والمحاسبة الذكي",
                                  bg=self.colors['primary'], fg='#BDC3C7',
                                  font=('Segoe UI', int(10 * self.scale)))
        subtitle_label.pack()
        
        subtitle_label = tk.Label(title_frame, text="Accounting Management System",
                                  bg=self.colors['primary'], fg='#BDC3C7',
                                  font=('Segoe UI', int(9 * self.scale)))
        subtitle_label.pack()
        
        # أزرار سريعة
        quick_actions = tk.Frame(top_bar, bg=self.colors['primary'])
        quick_actions.grid(row=0, column=1, padx=20, pady=10, sticky='e')
        
        # إعداد Grid للأزرار
        quick_actions.grid_columnconfigure(0, weight=1)
        quick_actions.grid_columnconfigure(1, weight=1)
        quick_actions.grid_columnconfigure(2, weight=1)
        
        self.icon_btn1 = self.icon_mgr.get_icon(ICONS['treasury'], size=16, color='white')
        btn1 = ModernButton(quick_actions, text=" الصندوق", image=self.icon_btn1, compound='left',
                           bg=self.colors['success'], fg='white',
                           command=lambda: self.notebook.select(7))
        btn1.grid(row=0, column=0, padx=5, pady=2, sticky='ew')
        
        self.icon_btn2 = self.icon_mgr.get_icon(ICONS['add'], size=16, color='white')
        btn2 = ModernButton(quick_actions, text=" فاتورة سريعة", image=self.icon_btn2, compound='left',
                           bg=self.colors['info'], fg='white',
                           command=self.quick_invoice)
        btn2.grid(row=0, column=1, padx=5, pady=2, sticky='ew')
        
        self.icon_btn3 = self.icon_mgr.get_icon(ICONS['search'], size=16, color='white')
        btn3 = ModernButton(quick_actions, text=" بحث شامل", image=self.icon_btn3, compound='left',
                           bg=self.colors['warning'], fg='white',
                           command=self.global_search)
        btn3.grid(row=0, column=2, padx=5, pady=2, sticky='ew')
    
    def create_dashboard_tab(self):
        """إنشاء تبويب Dashboard مع دعم الشاشات المختلفة"""
        self.dashboard_frame = tk.Frame(self.notebook, bg=self.colors['bg'])
        
        # إطار التمرير الرئيسي
        canvas = tk.Canvas(self.dashboard_frame, bg=self.colors['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.dashboard_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg'])
        
        # ربط التمرير
        scrollable_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window(0, 0, window=scrollable_frame, anchor="nw", width=canvas.winfo_width())
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # تحديث عرض النافذة عند تغيير الحجم
        def on_canvas_resize(event):
            canvas.itemconfig(1, width=event.width)
        canvas.bind('<Configure>', on_canvas_resize)
        
        # إطار المحتوى الرئيسي
        content_frame = tk.Frame(scrollable_frame, bg=self.colors['bg'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # العنوان
        title_frame = tk.Frame(content_frame, bg=self.colors['bg'])
        title_frame.pack(fill='x', pady=(0, 15))
        
        title_label = tk.Label(title_frame, text=" لوحة التحكم",
                               font=('Segoe UI', int(18 * self.scale), 'bold'),
                               bg=self.colors['bg'], fg=self.colors['text'])
        title_label.pack(side='left')
        
        icon_dash_title = tk.Label(title_frame, text=ICONS['dashboard'], font=('Segoe MDL2 Assets', int(18 * self.scale)),
                                  bg=self.colors['bg'], fg=self.colors['text'])
        icon_dash_title.pack(side='left', padx=(0, 10))
        
        # بطاقات الإحصائيات - استخدام Grid للتكيف مع الحجم
        cards_container = tk.Frame(content_frame, bg=self.colors['bg'])
        cards_container.pack(fill='x', pady=20)  # زيادة المسافة العمودية
        
        self.dashboard_cards = {}
        
        # تحديد عدد الأعمدة بناءً على حجم الشاشة
        screen_width = self.root.winfo_screenwidth()
        if screen_width < 1024:
            cols = 2  # شاشات صغيرة
        elif screen_width < 1366:
            cols = 3  # شاشات متوسطة
        else:
            cols = 3  # شاشات كبيرة
            
        # إنشاء البطاقات في Grid
        cards_data = [
            ('treasury', "رصيد الصندوق", "0", ICONS['treasury'], self.colors['success'], 7),
            ('customers', "إجمالي العملاء", "0", ICONS['customers'], self.colors['info'], 6),
            ('invoices', "إجمالي الفواتير", "0", ICONS['invoice'], self.colors['warning'], 1),
            ('revenue', "إجمالي الإيرادات", "0", ICONS['revenue'], self.colors['info'], 5),
            ('expenses', "إجمالي المصروفات", "0", ICONS['expenses'], self.colors['danger'], self.navigate_to_expenses),
        ]
        for i, (key, title, value, icon, color, action) in enumerate(cards_data):
            if isinstance(action, int):
                cmd = lambda idx=action: self.notebook.select(idx)
            else:
                cmd = action
            
            self.dashboard_cards[key] = DashboardCard(
                cards_container, title, value, icon, color,
                command=cmd
            )
            self.dashboard_cards[key].grid(row=i // cols, column=i % cols, padx=10, pady=10, sticky='nsew')
        
        
        # توزيع الأعمدة بالتساوي
        for i in range(cols):
            cards_container.columnconfigure(i, weight=1)
        for i in range((len(cards_data) + cols - 1) // cols):
            cards_container.rowconfigure(i, weight=1)
        
        # قسم الإحصائيات السريعة - استخدام Grid للتجاوب
        stats_frame = tk.Frame(content_frame, bg=self.colors['bg'])
        stats_frame.pack(fill='both', expand=True, pady=10)
        
        # إحصائيات اليوم
        today_frame = tk.LabelFrame(stats_frame, text=" إحصائيات اليوم",
                                    font=('Segoe UI', int(12 * self.scale), 'bold'),
                                    bg=self.colors['card'], fg=self.colors['text'])
        today_frame.grid(row=0, column=0, padx=5, pady=5, sticky='nsew')
        
        self.today_stats = tk.Frame(today_frame, bg=self.colors['card'])
        self.today_stats.pack(fill='both', expand=True, padx=10, pady=10)
        
        # إحصائيات هذا الشهر
        month_frame = tk.LabelFrame(stats_frame, text=" إحصائيات هذا الشهر",
                                     font=('Segoe UI', int(12 * self.scale), 'bold'),
                                     bg=self.colors['card'], fg=self.colors['text'])
        month_frame.grid(row=0, column=1, padx=5, pady=5, sticky='nsew')
        
        self.month_stats = tk.Frame(month_frame, bg=self.colors['card'])
        self.month_stats.pack(fill='both', expand=True, padx=10, pady=10)
        
        # توزيع الأعمدة بالتساوي
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.rowconfigure(0, weight=1)
        
        # ترتيب العناصر
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def navigate_to_expenses(self):
        """الانتقال إلى تبويب سند الصرف في السندات"""
        self.notebook.select(8) # السندات
        try:
            self.treasury_module.sub_notebook.select(0) # سند الصرف (أصبح التبويب 0 بعد فصل الصندوق)
        except Exception:
            pass
    
    def update_dashboard(self):
        """تحديث بيانات Dashboard"""
        try:
            if not hasattr(self, 'root') or not self.root.winfo_exists():
                return
            db = Database()
            
            # رصيد الصندوق
            income_result = db.execute_query("SELECT COALESCE(SUM(amount), 0) FROM treasury_transactions WHERE type = 'income'")
            expense_result = db.execute_query("SELECT COALESCE(SUM(amount), 0) FROM treasury_transactions WHERE type = 'expense'")
            
            total_income = income_result[0][0] if income_result else 0
            total_expense = expense_result[0][0] if expense_result else 0
            balance = total_income - total_expense
            
            self.update_card('treasury', f"\u202B{balance:,.0f} ر.س\u202C")
            
            # إجمالي العملاء
            customers_count = len(db.execute_query("SELECT id FROM customers"))
            self.update_card('customers', customers_count)
            
            # إجمالي الفواتير
            invoices_count = len(db.execute_query("SELECT id FROM invoices"))
            self.update_card('invoices', invoices_count)
            
            # إجمالي الإيرادات
            revenue = db.execute_query("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'income'")
            revenue_amount = revenue[0][0] if revenue else 0
            self.update_card('revenue', f"\u202B{revenue_amount:,.0f} ر.س\u202C")
            
            # إجمالي المصروفات
            expenses = db.execute_query("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'expense'")
            expenses_amount = expenses[0][0] if expenses else 0
            self.update_card('expenses', f"\u202B{expenses_amount:,.0f} ر.س\u202C")
            
            # إحصائيات اليوم
            today = datetime.now().strftime('%Y-%m-%d')
            today_invoices = len(db.execute_query("SELECT id FROM invoices WHERE date = ?", (today,)))
            today_revenue = db.execute_query("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'income' AND date = ?", (today,))
            today_revenue_amount = today_revenue[0][0] if today_revenue else 0
            
            self.update_stats_frame(self.today_stats, [
                ("فواتير اليوم", today_invoices),
                ("إيرادات اليوم", f"\u202B{today_revenue_amount:,.0f} ر.س\u202C")
            ])
            
            # إحصائيات الشهر
            current_month = datetime.now().strftime('%Y-%m')
            month_invoices = len(db.execute_query("SELECT id FROM invoices WHERE strftime('%Y-%m', date) = ?", (current_month,)))
            month_revenue = db.execute_query("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'income' AND strftime('%Y-%m', date) = ?", (current_month,))
            month_revenue_amount = month_revenue[0][0] if month_revenue else 0
            month_expenses = db.execute_query("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'expense' AND strftime('%Y-%m', date) = ?", (current_month,))
            month_expenses_amount = month_expenses[0][0] if month_expenses else 0
            
            self.update_stats_frame(self.month_stats, [
                ("فواتير الشهر", month_invoices),
                ("إيرادات الشهر", f"\u202B{month_revenue_amount:,.0f} ر.س\u202C"),
                ("مصروفات الشهر", f"\u202B{month_expenses_amount:,.0f} ر.س\u202C"),
                ("صافي الربح", f"\u202B{month_revenue_amount - month_expenses_amount:,.0f} ر.س\u202C")
            ])
            
        except Exception as e:
            print(f"خطأ في تحديث Dashboard: {e}")
        
        # إلغاء أي مؤقت سابق لـ update_dashboard لمنع التراكم
        if hasattr(self, '_dashboard_after_id') and self._dashboard_after_id:
            try:
                self.root.after_cancel(self._dashboard_after_id)
                self._dashboard_after_id = None
            except Exception:
                pass
        
        # تحديث كل 30 ثانية بأمان
        try:
            if hasattr(self, 'root') and self.root.winfo_exists():
                self._dashboard_after_id = self.root.after(30000, self.update_dashboard)
        except Exception:
            pass
    
    def update_card(self, card_name, value):
        """تحديث قيمة بطاقة"""
        if card_name in self.dashboard_cards:
            card = self.dashboard_cards[card_name]
            # استخدام الدالة الجديدة لتحديث القيمة
            if hasattr(card, 'update_value'):
                card.update_value(value)
    
    def update_stats_frame(self, frame, stats):
        """تحديث إطار الإحصائيات"""
        # مسح المحتوى القديم
        for widget in frame.winfo_children():
            widget.destroy()
        
        # إضافة الإحصائيات الجديدة - أكبر وأوضح
        for label, value in stats:
            stat_frame = tk.Frame(frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
            stat_frame.pack(fill='x', pady=10, padx=5)
            
            inner_frame = tk.Frame(stat_frame, bg=self.colors['card'])
            inner_frame.pack(fill='x', padx=15, pady=12)
            
            tk.Label(inner_frame, text=label + ":", font=('Segoe UI', int(11 * self.scale), 'bold'),
                    bg=self.colors['card'], fg=self.colors['text_light']).pack(side='right', padx=10)
            
            tk.Label(inner_frame, text=str(value), font=('Segoe UI', int(13 * self.scale), 'bold'),
                    bg=self.colors['card'], fg=self.colors['text']).pack(side='right', padx=10)
    
    def create_settings_tab(self):
        """إنشاء تبويب الإعدادات مع دعم الشاشات المختلفة"""
        settings_frame = tk.Frame(self.notebook, bg=self.colors['bg'])
        self.notebook.add(settings_frame, text=" الإعدادات", image=self.icon_set, compound='left')
        
        # إطار التمرير
        canvas = tk.Canvas(settings_frame, bg=self.colors['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(settings_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg'])
        
        scrollable_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window(0, 0, window=scrollable_frame, anchor="nw", width=canvas.winfo_width())
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def on_canvas_resize(event):
            canvas.itemconfig(1, width=event.width)
        canvas.bind('<Configure>', on_canvas_resize)
        
        # إطار الإعدادات
        settings_container = tk.Frame(scrollable_frame, bg=self.colors['card'])
        settings_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # العنوان
        title_label = tk.Label(settings_container, text="⚙️ إعدادات النظام",
                              font=('Segoe UI', int(14 * self.scale), 'bold'),
                              bg=self.colors['card'], fg=self.colors['text'])
        title_label.pack(pady=(0, 20))
        
        # شبكة الأزرار
        buttons_frame = tk.Frame(settings_container, bg=self.colors['card'])
        buttons_frame.pack(fill='both', expand=True)
        
        buttons_data = [
            ("🏢 إعدادات الشركة والفاتورة", self.colors['primary'], self.open_company_settings),
            ("💰 إعدادات الضريبة", self.colors['success'], self.open_tax_settings),
            ("⚙️ إعدادات النسخ الاحتياطي التلقائي", self.colors['secondary'], self.open_backup_settings),
            ("💾 نسخ احتياطي فوري", self.colors['info'], self.backup_database),
            ("🔄 استعادة نسخة", self.colors['warning'], self.restore_database),
        ]
        
        for i, (text, color, command) in enumerate(buttons_data):
            btn = ModernButton(buttons_frame, text=text, bg=color, fg='white', command=command)
            btn.pack(pady=10, ipadx=15, ipady=8)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_menu(self):
        """إنشاء القوائم"""
        menubar = tk.Menu(self.root, bg=self.colors['primary'], fg='white')
        
        # قائمة ملف
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="💾 نسخ احتياطي فوري", command=self.backup_database)
        file_menu.add_command(label="🔄 استعادة نسخة", command=self.restore_database)
        file_menu.add_command(label="⚙️ إعدادات النسخ الاحتياطي التلقائي", command=self.open_backup_settings)
        file_menu.add_separator()
        file_menu.add_command(label="🚪 خروج", command=self.root.quit)
        menubar.add_cascade(label="الملف", menu=file_menu)
        
        # قائمة عرض
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="🔄 تحديث كل البيانات", command=self.refresh_all)
        view_menu.add_command(label="📊 لوحة التحكم", command=lambda: self.notebook.select(0))
        menubar.add_cascade(label="العرض", menu=view_menu)
        
        # قائمة التقارير
        report_menu = tk.Menu(menubar, tearoff=0)
        report_menu.add_command(label="📈 التقارير المالية", command=lambda: self.notebook.select(9))
        report_menu.add_command(label="👥 تقارير العملاء", command=lambda: self.notebook.select(1))
        menubar.add_cascade(label="التقارير", menu=report_menu)
        
        # قائمة مساعدة
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="🔄 فحص التحديثات الآن (سحابياً)", command=lambda: check_for_updates(self.root, silent=False))
        help_menu.add_command(label="ℹ️ عن البرنامج", command=self.about)
        help_menu.add_command(label="📖 دليل الاستخدام", command=self.show_help)
        help_menu.add_separator()
        help_menu.add_command(label="⚠️ مسح الكل (إعادة ضبط المصنع)", command=self.factory_reset)
        menubar.add_cascade(label="المساعدة", menu=help_menu)
        
        self.root.config(menu=menubar)

    def factory_reset(self):
        """مسح كافة بيانات البرنامج وإعادة ضبط المصنع"""
        from tkinter import messagebox
        from database import Database, get_db_path
        if messagebox.askyesno("تأكيد خطير", "⚠️ تحذير: هل أنت متأكد أنك تريد مسح جميع البيانات؟ هذا الإجراء لا يمكن التراجع عنه!"):
            if messagebox.askyesno("تأكيد نهائي", "هل أنت متأكد تماماً؟ سيتم مسح كل الفواتير والعملاء وجميع البيانات الأخرى ولن تتمكن من استعادتها."):
                try:
                    db = Database()
                    tables = db.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
                    for table in tables:
                        table_name = table[0]
                        if table_name != "sqlite_sequence":
                            db.execute_query(f"DELETE FROM {table_name}")
                            
                    # تصفير العدادات
                    db.execute_query("DELETE FROM sqlite_sequence")
                    
                    messagebox.showinfo("نجاح", "✅ تم مسح جميع البيانات وإعادة ضبط المصنع بنجاح. سيتم إغلاق البرنامج الآن لتطبيق التغييرات. يرجى إعادة فتحه.")
                    self.root.quit()
                except Exception as e:
                    messagebox.showerror("خطأ", f"حدث خطأ أثناء مسح البيانات: {str(e)}")
    
    def quick_invoice(self):
        """إنشاء فاتورة سريعة"""
        self.notebook.select(2)  # تبويب الفواتير
        if hasattr(self.invoice_module, 'create_new_invoice'):
            self.invoice_module.create_new_invoice()
    
    def global_search(self):
        """بحث شامل في النظام"""
        search_window = tk.Toplevel(self.root)
        search_window.title("بحث شامل")
        search_window.geometry("800x600")
        search_window.transient(self.root)
        search_window.grab_set()
        
        main_frame = tk.Frame(search_window, bg=self.colors['bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Header
        header_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        header_frame.pack(fill='x', pady=(0, 20))
        
        tk.Label(header_frame, text=ICONS['search'], font=('Segoe MDL2 Assets', int(24 * self.scale)),
                bg=self.colors['bg'], fg=self.colors['primary']).pack(side='right', padx=10)
        tk.Label(header_frame, text="البحث الشامل",
                font=('Segoe UI', int(20 * self.scale), 'bold'),
                bg=self.colors['bg'], fg=self.colors['text']).pack(side='right')
        
        # Search Bar
        search_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        search_frame.pack(fill='x', pady=10)
        
        search_entry = ttk.Entry(search_frame, width=50, font=('Segoe UI', int(12 * self.scale)))
        search_entry.pack(side='right', padx=10, ipady=8, expand=True, fill='x')
        search_entry.focus()
        
        # Results area
        results_frame = tk.Frame(main_frame, bg='white', relief=tk.SUNKEN, bd=1)
        results_frame.pack(fill='both', expand=True, pady=10)
        
        scrollbar = ttk.Scrollbar(results_frame)
        scrollbar.pack(side='right', fill='y')
        
        results_text = tk.Text(results_frame, font=('Segoe UI', int(11 * self.scale)), wrap=tk.WORD, 
                               bg='white', fg=self.colors['text'], yscrollcommand=scrollbar.set,
                               padx=15, pady=15, spacing1=5, spacing3=5)
        results_text.pack(fill='both', expand=True)
        scrollbar.config(command=results_text.yview)
        
        # Tags for styling
        results_text.tag_configure('header', font=('Segoe UI', int(14 * self.scale), 'bold'), foreground=self.colors['primary'], spacing1=15, spacing3=10)
        results_text.tag_configure('item', font=('Segoe UI', int(12 * self.scale)), foreground=self.colors['text'])
        results_text.tag_configure('no_result', font=('Segoe UI', int(12 * self.scale), 'italic'), foreground=self.colors['text_light'])
        
        def perform_search():
            search_term = search_entry.get().strip()
            if not search_term:
                return
            
            results_text.delete('1.0', tk.END)
            db = Database()
            found_any = False
            
            # البحث في العملاء
            customers = db.execute_query(
                "SELECT name, phone, email FROM customers WHERE name LIKE ? OR phone LIKE ?",
                (f'%{search_term}%', f'%{search_term}%')
            )
            if customers:
                found_any = True
                results_text.insert(tk.END, f"{ICONS['customers']} العملاء:\n", 'header')
                for cust in customers:
                    results_text.insert(tk.END, f"  • {cust[0]} | 📞 {cust[1]}\n", 'item')
            
            # البحث في الفواتير
            invoices = db.execute_query(
                "SELECT invoice_number, date, grand_total FROM invoices WHERE invoice_number LIKE ?",
                (f'%{search_term}%',)
            )
            if invoices:
                found_any = True
                results_text.insert(tk.END, f"{ICONS['invoice']} الفواتير:\n", 'header')
                for inv in invoices:
                    results_text.insert(tk.END, f"  • فاتورة رقم: {inv[0]} | 📅 {inv[1]} | 💰 \u202B{inv[2]:,.2f} ر.س\u202C\n", 'item')
            
            # البحث في المعاملات
            transactions = db.execute_query(
                "SELECT description, amount, date FROM transactions WHERE description LIKE ?",
                (f'%{search_term}%',)
            )
            if transactions:
                found_any = True
                results_text.insert(tk.END, f"{ICONS['transactions']} المعاملات:\n", 'header')
                for trans in transactions:
                    results_text.insert(tk.END, f"  • {trans[0]} | 📅 {trans[2]} | 💰 \u202B{trans[1]:,.2f} ر.س\u202C\n", 'item')
                    
            if not found_any:
                results_text.insert(tk.END, f"\n\nلم يتم العثور على أية نتائج مطابقة لـ '{search_term}'", 'no_result')
        
        search_entry.bind('<Return>', lambda e: perform_search())
        
        btn = ModernButton(search_frame, text="بحث", bg=self.colors['primary'],
                          fg='white', command=perform_search)
        btn.pack(side='left', padx=10)
    
    def check_database(self):
        """التحقق من قاعدة البيانات"""
        db_path = get_db_path()
        if not os.path.exists(db_path):
            self.create_database()
            self.update_status("✅ تم إنشاء قاعدة بيانات جديدة")
        else:
            # تحديث هيكل الجداول إذا لزم الأمر
            self.migrate_database()
            self.update_status("✅ تم تحميل قاعدة البيانات بنجاح")
    
    def migrate_database(self):
        """ترحيل قاعدة البيانات لتحديث الهيكل"""
        try:
            conn = sqlite3.connect(get_db_path())
            c = conn.cursor()
            
            # التحقق من وجود عمود customer_id في جدول treasury_transactions
            try:
                c.execute("PRAGMA table_info(treasury_transactions)")
                columns = [col[1] for col in c.fetchall()]
                
                if 'customer_id' not in columns:
                    print("🔄 Adding customer_id column to treasury_transactions...")
                    c.execute('ALTER TABLE treasury_transactions ADD COLUMN customer_id INTEGER')
                    conn.commit()
                    print("✅ customer_id column added successfully")
            except Exception as e:
                print(f"⚠️ Migration warning for treasury_transactions: {e}")
            
            # التحقق من وجود جدول company_settings القديم وتحديثه
            try:
                c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='company_settings'")
                result = c.fetchone()
                if result:
                    table_sql = result[0]
                    # التحقق إذا كان الجدول يحتوي على الأعمدة القديمة (company_name, phone)
                    if 'company_name TEXT' in table_sql and 'phone TEXT' in table_sql:
                        print("🔄 Migrating company_settings table...")
                        # حفظ البيانات القديمة
                        c.execute("SELECT company_name_ar, tax_number, address, phone1, email FROM company_settings WHERE id = 1")
                        old_data = c.fetchone()
                        
                        # حذف الجدول القديم وإنشاء الجديد
                        c.execute("DROP TABLE company_settings")
                        c.execute('''CREATE TABLE company_settings
                           (id INTEGER PRIMARY KEY AUTOINCREMENT,
                            company_name_ar TEXT,
                            company_name_en TEXT,
                            owner_name TEXT,
                            tax_number TEXT,
                            commercial_register TEXT,
                            address TEXT,
                            address_en TEXT,
                            phone1 TEXT,
                            phone2 TEXT,
                            po_box TEXT,
                            postal_code TEXT,
                            email TEXT,
                            website TEXT)''')
                        
                        # إعادة إدخال البيانات القديمة في الأعمدة الجديدة
                        if old_data:
                            c.execute('''INSERT INTO company_settings 
                                (id, company_name_ar, company_name_en, tax_number, address, phone1, email) 
                                VALUES (1, ?, ?, ?, ?, ?, ?)''',
                                (old_data[0], old_data[0], old_data[1], old_data[2], old_data[3], old_data[4]))
                        
                        conn.commit()
                        print("✅ Migration completed successfully")
            except Exception as e:
                print(f"⚠️ Migration warning: {e}")
            
            conn.close()
        except Exception as e:
            print(f"⚠️ Database migration error: {e}")
    
    def create_database(self):
        """إنشاء قاعدة البيانات"""
        conn = sqlite3.connect(get_db_path())
        c = conn.cursor()
        
        tables = [
            '''CREATE TABLE customers
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                tax_number TEXT,
                address TEXT,
                phone TEXT,
                email TEXT)''',
            
            '''CREATE TABLE invoices
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT UNIQUE,
                customer_id INTEGER,
                date TEXT,
                items TEXT,
                total REAL,
                tax REAL,
                discount REAL,
                grand_total REAL,
                project_id INTEGER,
                FOREIGN KEY (customer_id) REFERENCES customers (id))''',
            
            '''CREATE TABLE employees
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                position TEXT,
                salary REAL,
                hire_date TEXT,
                phone TEXT,
                address TEXT,
                project_id INTEGER)''',
            
            '''CREATE TABLE salaries
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                month_year TEXT,
                basic_salary REAL,
                bonuses REAL,
                deductions REAL,
                net_salary REAL,
                payment_date TEXT)''',
            
            '''CREATE TABLE transactions
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                amount REAL,
                description TEXT,
                date TEXT,
                category TEXT,
                project_id INTEGER)''',
            
            '''CREATE TABLE projects
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                start_date TEXT,
                end_date TEXT,
                budget REAL,
                status TEXT,
                client_name TEXT,
                description TEXT)''',
            
            '''CREATE TABLE settings
               (key TEXT PRIMARY KEY,
                value TEXT)''',
            
            '''CREATE TABLE treasury_transactions
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                type TEXT,
                description TEXT,
                amount REAL,
                account_name TEXT,
                project_id INTEGER,
                customer_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP)''',
            
            '''CREATE TABLE account_items
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT UNIQUE,
                name TEXT,
                type TEXT)''',
            
            '''CREATE TABLE company_settings
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name_ar TEXT,
                company_name_en TEXT,
                owner_name TEXT,
                tax_number TEXT,
                commercial_register TEXT,
                address TEXT,
                address_en TEXT,
                phone1 TEXT,
                phone2 TEXT,
                po_box TEXT,
                postal_code TEXT,
                email TEXT,
                website TEXT)'''
        ]
        
        for table_sql in tables:
            try:
                c.execute(table_sql)
            except:
                pass
        
        # بيانات أولية
        c.execute('''INSERT OR IGNORE INTO customers (name, tax_number, address, phone) 
                     VALUES (?, ?, ?, ?)''',
                  ('مؤسسة ميار العربية لتنمية المعلومات', '310431653500003',
                   'طريق المدينة المنورة حتى السلامة جدة 8256', '0555555555'))
        
        # إعدادات أولية
        c.execute('''INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)''',
                  ('tax_rate', '15'))
        
        # بنود حسابات أولية
        c.execute('''INSERT OR IGNORE INTO account_items (number, name, type) VALUES (?, ?, ?)''',
                  ('100', 'الصندوق', 'دائن'))
        c.execute('''INSERT OR IGNORE INTO account_items (number, name, type) VALUES (?, ?, ?)''',
                  ('200', 'المصاريف الإدارية', 'مدين'))
        c.execute('''INSERT OR IGNORE INTO account_items (number, name, type) VALUES (?, ?, ?)''',
                  ('300', 'مصاريف التشغيل', 'مدين'))
        c.execute('''INSERT OR IGNORE INTO account_items (number, name, type) VALUES (?, ?, ?)''',
                  ('400', 'مصاريف متنوعة', 'مدين'))
        c.execute('''INSERT OR IGNORE INTO account_items (number, name, type) VALUES (?, ?, ?)''',
                  ('500', 'الإيرادات', 'دائن'))
        
        conn.commit()
        conn.close()
    
    def backup_database(self):
        """نسخ احتياطي لقاعدة البيانات"""
        try:
            backup_dir = filedialog.askdirectory(title="📁 اختر مجلد لحفظ النسخة الاحتياطية")
            if backup_dir:
                backup_path = os.path.join(backup_dir,
                                          f"accounting_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
                conn = sqlite3.connect(get_db_path())
                bck = sqlite3.connect(backup_path)
                with bck:
                    conn.backup(bck)
                conn.close()
                bck.close()
                self.update_status(f"✅ تم إنشاء نسخة احتياطية في: {backup_path}")
                messagebox.showinfo("نجاح", "✅ تم إنشاء النسخة الاحتياطية بنجاح")
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في إنشاء النسخة الاحتياطية: {str(e)}")
    
    def restore_database(self):
        """استعادة نسخة احتياطية"""
        try:
            backup_file = filedialog.askopenfilename(
                title="📂 اختر ملف النسخة الاحتياطية",
                filetypes=[("ملفات قاعدة البيانات", "*.db"), ("كل الملفات", "*.*")]
            )
            if backup_file:
                if messagebox.askyesno("تأكيد",
                                     "⚠️ هل تريد استعادة النسخة الاحتياطية؟ سيتم استبدال جميع البيانات الحالية"):
                    conn = sqlite3.connect(get_db_path())
                    bck = sqlite3.connect(backup_file)
                    with conn:
                        bck.backup(conn)
                    conn.close()
                    bck.close()
                    self.update_status(f"✅ تم استعادة النسخة الاحتياطية من: {backup_file}")
                    self.refresh_all()
                    messagebox.showinfo("نجاح", "✅ تم استعادة النسخة الاحتياطية بنجاح")
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في استعادة النسخة الاحتياطية: {str(e)}")
    
    def setup_central_refresh_system(self):
        """إعداد نظام التحديث المركزي"""
        # تسجيل جميع الوحدات في نظام التحديث
        central_refresh.register_refresh_callback("invoices", self.invoice_module.load_invoices)
        central_refresh.register_refresh_callback("customers", self.invoice_module.load_customers)
        central_refresh.register_refresh_callback("employees", self.employees_module.load_employees)
        central_refresh.register_refresh_callback("transactions", self.transactions_module.load_transactions)
        central_refresh.register_refresh_callback("projects", self.projects_module.load_projects)
        central_refresh.register_refresh_callback("treasury", self.treasury_module.update_cash_data)
        central_refresh.register_refresh_callback("reports", self.reports_module.load_reports)
        central_refresh.register_refresh_callback("dashboard", self.update_dashboard)
        
        # register signal listeners
        central_refresh.register_data_changed_signal("customer_changed", self.on_customer_changed)
        central_refresh.register_data_changed_signal("project_changed", self.on_project_changed)
        central_refresh.register_data_changed_signal("employee_changed", self.on_employee_changed)
        central_refresh.register_data_changed_signal("invoice_changed", self.on_invoice_changed)
        central_refresh.register_data_changed_signal("transaction_changed", self.on_transaction_changed)
        central_refresh.register_data_changed_signal("account_items_changed", self.on_account_items_changed)

        print("✅ Central Refresh System initialized successfully")

    def setup_customer_project_refresh(self):
        """setup customer project module refresh"""
        if hasattr(self, 'customer_project_module'):
            central_refresh.register_refresh_callback("customers_projects", self.customer_project_module.load_customers)
            central_refresh.register_refresh_callback("customers_projects", self.customer_project_module.load_projects)
            print("Customer Project Module refresh callbacks registered")

    def on_customer_changed(self, customer_id=None):
        """عند تغيير بيانات العميل"""
        self.invoice_module.load_customers()
        self.customer_project_module.load_customers()
        self.accounts_receivable_module.load_customers()
        self.accounts_payable_module.load_customers()
        self.transactions_module.load_customers()
        self.treasury_module.load_payment_data()
        self.treasury_module.load_journal_data()
        self.treasury_module.load_account_items()
        self.update_dashboard()

    def on_project_changed(self, project_id=None):
        """عند تغيير بيانات المشروع"""
        self.projects_module.load_projects()
        self.customer_project_module.load_projects()
        self.transactions_module.load_projects()
        self.invoice_module.load_projects()
        self.accounts_receivable_module.load_projects()
        self.accounts_payable_module.load_projects()
        self.treasury_module.load_payment_data()
        self.treasury_module.load_journal_data()
        self.treasury_module.load_account_items()
        self.update_dashboard()

    def on_employee_changed(self, employee_id=None):
        """when employee data changes"""
        self.employees_module.load_employees()
        self.update_dashboard()

    def on_invoice_changed(self, invoice_id=None):
        """when invoice data changes"""
        self.invoice_module.load_invoices()
        self.reports_module.load_reports()
        self.update_dashboard()

    def on_transaction_changed(self, transaction_id=None):
        """when transaction data changes"""
        self.transactions_module.load_transactions()
        self.treasury_module.update_cash_data()
        self.reports_module.load_reports()
        self.update_dashboard()

    def on_account_items_changed(self, item_id=None):
        """عند تغيير بيانات بنود الحسابات"""
        self.treasury_module.load_account_items()
        self.treasury_module.load_journal_data()
        self.treasury_module.load_payment_data()
        self.transactions_module.load_account_items()
        self.accounts_receivable_module.load_account_items()
        self.accounts_payable_module.load_account_items()
        self.update_dashboard()

    def refresh_all(self):
        """refresh all data"""
        try:
            self.invoice_module.load_invoices()
            self.invoice_module.load_customers()
            self.employees_module.load_employees()
            self.transactions_module.load_transactions()
            self.projects_module.load_projects()
            self.treasury_module.update_cash_data()
            self.reports_module.load_reports()
            self.update_dashboard()
            self.update_status("refresh all data successful")
        except Exception as e:
            messagebox.showerror("error", f"failed to refresh data: {str(e)}")

    def update_status(self, message):
        """update status bar"""
        self.status_label.config(text=message)
        try:
            self.root.after(5000, lambda: self.status_label.config(text="ready"))
        except Exception:
            pass

    def show_financial_reports(self):
        """show financial reports"""
        self.notebook.select(6)

    def show_customer_reports(self):
        """show customer reports"""
        self.notebook.select(1)
    
    def show_help(self):
        """show user guide"""
        help_text = """
user guide:

1. dashboard: quick system stats

2. customers: manage customer data
   - add new customer
   - edit customer data
   - view customer invoices

3. invoices: create and manage invoices
   - create new invoice
   - print invoices
   - export data

4. employees: manage employees and salaries
   - add new employee
   - pay salaries
   - salary records

5. transactions: record income and expenses
   - add new transaction
   - filter transactions
   - financial reports

6. projects: track projects
   - add new project
   - track budgets
   - project reports

7. reports: comprehensive financial and statistical reports

8. settings: customize system settings

tips:
- use global search to find any data quickly
- use dashboard to monitor performance
- backup regularly
        """
        messagebox.showinfo("user guide", help_text)
    
    def about(self):
        """نافذة عن البرنامج"""
        about_window = tk.Toplevel(self.root)
        about_window.title("ℹ️ عن البرنامج")
        about_window.geometry("500x450")
        about_window.resizable(False, False)
        about_window.configure(bg=self.colors['bg'])
        about_window.transient(self.root)
        about_window.grab_set()
        
        main_frame = tk.Frame(about_window, bg=self.colors['bg'])
        main_frame.pack(fill='both', expand=True, padx=30, pady=30)
        
        tk.Label(main_frame, text="🧾 فواتيري | Fawateery",
                font=('Segoe UI', int(24 * self.scale), 'bold'),
                bg=self.colors['bg'], fg=self.colors['primary']).pack(pady=20)
        
        tk.Label(main_frame, text="نظام الفواتير والمحاسبة الذكي - الإصدار 3.0",
                font=('Segoe UI', int(12 * self.scale)),
                bg=self.colors['bg'], fg=self.colors['text_light']).pack(pady=10)
        
        info_text = """
🎯 نظام الفواتير والمحاسبة الذكي المتكامل

✨ المميزات الرئيسية:
• إدارة الفواتير وعروض الأسعار
• إدارة العملاء والموردين
• إدارة الموظفين والرواتب
• إدارة الخزينة والبنود
• تقارير شاملة وإحصائيات
• بحث شامل في جميع البيانات
• واجهة متجاوبة مع جميع الشاشات

🔧 التقنيات المستخدمة:
• Python + Tkinter
• SQLite لقاعدة البيانات
• FPDF لتوليد التقارير
• Pandas للتحليل

📧 للتواصل والدعم:
belalmedhat.eg@gmail.com

© 2024 جميع الحقوق محفوظة
تم التطوير بواسطة Belal Medhat Ahmed
        """
        
        tk.Label(main_frame, text=info_text, font=('Segoe UI', int(10 * self.scale)),
                bg=self.colors['bg'], fg=self.colors['text'],
                justify='center').pack(pady=20)
        
        btn = ModernButton(main_frame, text="إغلاق", bg=self.colors['primary'],
                          fg='white', command=about_window.destroy)
        btn.pack(pady=15, ipadx=20, ipady=8)
    
    def zoom_window(self, window, factor):
        """تكبير أو تصغير النافذة"""
        try:
            current_geometry = window.geometry()
            # استخراج الأبعاد الحالية
            if 'x' in current_geometry:
                width, height = current_geometry.split('x')[0], current_geometry.split('x')[1].split('+')[0]
                new_width = int(width * factor)
                new_height = int(height * factor)
                window.geometry(f"{new_width}x{new_height}")
        except Exception as e:
            print(f"Zoom error: {e}")
    
    def reset_window_size(self, window, default_size):
        """استعادة الحجم الافتراضي للنافذة"""
        try:
            window.geometry(default_size)
        except Exception as e:
            print(f"Reset size error: {e}")
    
    def open_company_settings(self):
        """فتح نافذة إعدادات الشركة"""
        try:
            db = Database()
            CompanySettingsDialog(self.root, db, self.update_status)
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في فتح إعدادات الشركة: {str(e)}")
    
    def open_tax_settings(self):
        """فتح نافذة إعدادات الضريبة"""
        dialog_window = tk.Toplevel(self.root)
        dialog_window.title("💰 إعدادات الضريبة")
        dialog_window.geometry("600x450")
        dialog_window.resizable(False, False)
        dialog_window.transient(self.root)
        dialog_window.grab_set()
        dialog_window.configure(bg=self.colors['bg'])
        
        # إطار رئيسي مع ظل
        main_container = tk.Frame(dialog_window, bg=self.colors['bg'])
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # إطار العنوان
        header_frame = tk.Frame(main_container, bg=self.colors['primary'], height=60)
        header_frame.pack(fill='x', pady=(0, 20))
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="💰 إعدادات الضريبة",
                font=('Segoe UI', int(18 * self.scale), 'bold'),
                bg=self.colors['primary'], fg='white').pack(expand=True)
        
        # إطار المحتوى
        content_frame = tk.Frame(main_container, bg=self.colors['card'], relief='flat', bd=0)
        content_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # إطار الإعدادات
        settings_frame = tk.Frame(content_frame, bg=self.colors['card'])
        settings_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # إطار الضريبة
        tax_frame = tk.Frame(settings_frame, bg=self.colors['card'])
        tax_frame.pack(fill='x', pady=15)
        
        tk.Label(tax_frame, text="نسبة الضريبة (%):",
                font=('Segoe UI', int(12 * self.scale), 'bold'),
                bg=self.colors['card'], fg=self.colors['text']).pack(side='right', padx=(0, 15))
        
        tax_entry = ttk.Entry(tax_frame, width=15, font=('Segoe UI', int(12 * self.scale)))
        tax_entry.pack(side='right', padx=5)
        tax_entry.insert(0, "15")
        
        # وصف
        desc_label = tk.Label(settings_frame, text="⚠️ نسبة الضريبة يجب أن تكون بين 0 و 100",
                           font=('Segoe UI', int(10 * self.scale)),
                           bg=self.colors['card'], fg=self.colors['text_light'])
        desc_label.pack(pady=(0, 20))
        
        # إطار الأزرار - وضعه في main_container ليكون متناسقاً
        btn_frame = tk.Frame(main_container, bg=self.colors['bg'])
        btn_frame.pack(fill='x', pady=15)
        
        save_btn = ModernButton(btn_frame, text="💾 حفظ الإعدادات",
                               bg=self.colors['success'], fg='white',
                               command=lambda: self.save_tax_settings(tax_entry.get(), dialog_window))
        save_btn.pack(side='right', padx=5, ipadx=20, ipady=10)
        
        cancel_btn = ModernButton(btn_frame, text="❌ إلغاء",
                                 bg=self.colors['danger'], fg='white',
                                 command=dialog_window.destroy)
        cancel_btn.pack(side='right', padx=5, ipadx=20, ipady=10)
    
    def save_tax_settings(self, tax_rate, window):
        """حفظ إعدادات الضريبة"""
        try:
            tax_rate = float(tax_rate)
            if tax_rate < 0 or tax_rate > 100:
                messagebox.showerror("خطأ", "❌ نسبة الضريبة يجب أن تكون بين 0 و 100")
                return
            
            db = Database()
            db.execute_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                           ('tax_rate', str(tax_rate)))
            
            self.update_status(f"✅ تم تحديث نسبة الضريبة إلى {tax_rate}%")
            messagebox.showinfo("نجاح", f"✅ تم حفظ نسبة الضريبة: {tax_rate}%")
            window.destroy()
            
        except ValueError:
            messagebox.showerror("خطأ", "❌ يرجى إدخال رقم صحيح لنسبة الضريبة")
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حفظ الإعدادات: {str(e)}")
    
    def get_tax_rate(self):
        """الحصول على نسبة الضريبة"""
        try:
            db = Database()
            result = db.execute_query("SELECT value FROM settings WHERE key = 'tax_rate'")
            if result:
                return float(result[0][0])
            return 15.0
        except:
            return 15.0

    def open_backup_settings(self):
        """فتح نافذة إعدادات النسخ الاحتياطي التلقائي بتصميم حديث واحترافي"""
        try:
            db = Database()
            cfg = db.get_backup_settings()
            db.close()
        except Exception:
            cfg = {'enabled': True, 'interval': 'daily', 'folder': '', 'last_backup': ''}

        dialog = tk.Toplevel(self.root)
        dialog.title("🛡️ إعدادات النسخ الاحتياطي التلقائي والأمان")
        dialog.geometry("640x660")
        dialog.minsize(600, 580)
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg='#F8FAFC')

        # توسيط النافذة على الشاشة
        dialog.update_idletasks()
        try:
            screen_w = dialog.winfo_screenwidth()
            screen_h = dialog.winfo_screenheight()
            x = max(20, (screen_w - 640) // 2)
            y = max(20, (screen_h - 660) // 2)
            dialog.geometry(f"640x660+{x}+{y}")
        except Exception:
            pass

        # 1. شريط العنوان العلوي الأنيق
        header_frame = tk.Frame(dialog, bg='#1E293B', padx=20, pady=12)
        header_frame.pack(fill='x')

        tk.Label(header_frame, text="🛡️ إدارة النسخ الاحتياطي التلقائي",
                 font=('Segoe UI', 14, 'bold'),
                 bg='#1E293B', fg='white').pack(anchor='center')
        tk.Label(header_frame, text="حماية بيانات فواتيرك وحساباتك بجدولة ذكية تمنع أي فقدان للمعلومات",
                 font=('Segoe UI', 9),
                 bg='#1E293B', fg='#94A3B8').pack(anchor='center', pady=(3, 0))

        # منطقة المحتوى مع شريط تمرير للأمان في جميع الشاشات
        scroll_container = tk.Frame(dialog, bg='#F8FAFC')
        scroll_container.pack(fill='both', expand=True)

        canvas = tk.Canvas(scroll_container, bg='#F8FAFC', highlightthickness=0)
        v_scroll = ttk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg='#F8FAFC', padx=20, pady=12)

        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=v_scroll.set)

        def on_canvas_configure(e):
            canvas.itemconfig(canvas_window, width=e.width)
        canvas.bind('<Configure>', on_canvas_configure)

        canvas.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

        # دالة مساعدة لإنشاء بطاقات احترافية
        def make_card(parent, title):
            card = tk.Frame(parent, bg='white', highlightbackground='#E2E8F0', highlightthickness=1, padx=16, pady=12)
            card.pack(fill='x', pady=(0, 10))
            if title:
                t_lbl = tk.Label(card, text=title, font=('Segoe UI', 11, 'bold'), fg='#0F172A', bg='white')
                t_lbl.pack(anchor='e', pady=(0, 8))
            return card

        # ================= البطاقة 1: تفعيل النسخ التلقائي =================
        card1 = make_card(content, None)
        enabled_var = tk.BooleanVar(value=cfg.get('enabled', True))

        chk_row = tk.Frame(card1, bg='white')
        chk_row.pack(fill='x')

        chk = tk.Checkbutton(chk_row, text="  تفعيل النسخ الاحتياطي التلقائي لقاعدة البيانات",
                             variable=enabled_var, font=('Segoe UI', 11, 'bold'),
                             bg='white', fg='#0F172A', activebackground='white',
                             selectcolor='white', cursor='hand2')
        chk.pack(side='right')

        tk.Label(card1, text="ينصح بإبقاء هذا الخيار مفعلاً لضمان أخذ نسخ دورية وحفظ العمل تلقائياً.",
                 font=('Segoe UI', 9), fg='#64748B', bg='white').pack(anchor='e', pady=(4, 0))

        # ================= البطاقة 2: جدولة وتوقيت النسخ =================
        card2 = make_card(content, "📅 وتيرة وجدولة النسخ الاحتياطي:")
        interval_var = tk.StringVar(value=cfg.get('interval', 'daily'))

        options = [
            ("each_close", "عند كل إغلاق للبرنامج", "حماية فورية مستمرة لكل عملية تسجيل جديدة"),
            ("daily", "يومياً (مرة واحدة كل يوم عند الإغلاق)", "الخيار الأفضل والموصى به للعمل اليومي المستقر"),
            ("weekly", "أسبوعياً (مرة كل 7 أيام)", "مناسب للاستخدام الخفيف أو الشركات محدودة المعاملات"),
            ("monthly", "شهرياً (مرة كل 30 يوماً)", "نسخ احتياطي خفيف شهري")
        ]

        for val, title, desc in options:
            opt_frame = tk.Frame(card2, bg='white', pady=4)
            opt_frame.pack(fill='x')

            rb = tk.Radiobutton(opt_frame, text=f" {title}", variable=interval_var, value=val,
                                font=('Segoe UI', 10, 'bold'), fg='#1E293B', bg='white',
                                activebackground='white', selectcolor='white', cursor='hand2')
            rb.pack(side='right')

            tk.Label(card2, text=f"   • {desc}", font=('Segoe UI', 8), fg='#64748B', bg='white').pack(anchor='e', pady=(0, 4))

        # ================= البطاقة 3: مجلد الحفظ =================
        card3 = make_card(content, "📁 مسار مجلد حفظ النسخ الاحتياطية:")
        folder_var = tk.StringVar(value=cfg.get('folder', ''))

        folder_entry = ttk.Entry(card3, textvariable=folder_var, font=('Segoe UI', 9), state='readonly')
        folder_entry.pack(fill='x', pady=(0, 8), ipady=3)

        btn_row = tk.Frame(card3, bg='white')
        btn_row.pack(fill='x')

        def browse_folder():
            selected = filedialog.askdirectory(title="اختر مجلد النسخ الاحتياطية", initialdir=folder_var.get())
            if selected:
                folder_var.set(selected)

        def open_folder():
            p = folder_var.get()
            if os.path.exists(p):
                os.startfile(p)
            else:
                messagebox.showwarning("تنبيه", "المجلد المحدد غير موجود حالياً")

        b1 = tk.Button(btn_row, text="📂 استعراض وتغيير المجلد", command=browse_folder,
                       font=('Segoe UI', 9, 'bold'), bg='#F1F5F9', fg='#1E293B',
                       relief='solid', bd=1, padx=10, pady=4, cursor='hand2')
        b1.pack(side='right', padx=(0, 8))

        b2 = tk.Button(btn_row, text="🔍 فتح المجلد في الويندوز", command=open_folder,
                       font=('Segoe UI', 9), bg='#F1F5F9', fg='#475569',
                       relief='solid', bd=1, padx=10, pady=4, cursor='hand2')
        b2.pack(side='right')

        # ================= البطاقة 4: حالة النظام ومعلومات الأمان =================
        card4 = make_card(content, "ℹ️ حالة النسخ الاحتياطي:")
        last_str = cfg.get('last_backup') or 'لا يوجد حتى الآن'

        tk.Label(card4, text=f"• آخر نسخة احتياطية تمت بنجاح: {last_str}",
                 font=('Segoe UI', 9, 'bold'), fg='#0284C7', bg='white').pack(anchor='e')
        tk.Label(card4, text="• نظام التدوير التلقائي: يحتفظ البرنامج بآخر 30 نسخة تلقائياً لتفادي استهلاك مساحة القرص.",
                 font=('Segoe UI', 8), fg='#64748B', bg='white').pack(anchor='e', pady=(3, 0))

        # ================= شريط الأزرار السفلي =================
        footer = tk.Frame(dialog, bg='#F1F5F9', highlightbackground='#CBD5E1', highlightthickness=1, padx=20, pady=12)
        footer.pack(fill='x', side='bottom')

        def save():
            try:
                db_inst = Database()
                db_inst.save_backup_settings(enabled_var.get(), interval_var.get(), folder_var.get())
                db_inst.close()
                self.update_status("✅ تم حفظ إعدادات النسخ الاحتياطي بنجاح")
                messagebox.showinfo("نجاح", "✅ تم حفظ إعدادات النسخ الاحتياطي التلقائي بنجاح")
                dialog.destroy()
            except Exception as ex:
                messagebox.showerror("خطأ", f"❌ فشل حفظ الإعدادات: {ex}")

        def backup_now():
            try:
                db_inst = Database()
                b_path = db_inst.backup_database()
                db_inst.close()
                if b_path:
                    messagebox.showinfo("نجاح", f"✅ تم إنشاء نسخة احتياطية فورية بنجاح:\n{b_path}")
                else:
                    messagebox.showerror("خطأ", "فشل إنشاء النسخة الاحتياطية")
            except Exception as ex:
                messagebox.showerror("خطأ", f"❌ حدث خطأ: {ex}")

        save_btn = tk.Button(footer, text="  💾 حفظ الإعدادات  ", bg='#10B981', fg='white',
                             font=('Segoe UI', 10, 'bold'), relief='flat', padx=15, pady=6, cursor='hand2',
                             activebackground='#059669', activeforeground='white', command=save)
        save_btn.pack(side='right', padx=(10, 0))

        now_btn = tk.Button(footer, text="⚡ أخذ نسخة فورية الآن", bg='#3B82F6', fg='white',
                            font=('Segoe UI', 10, 'bold'), relief='flat', padx=12, pady=6, cursor='hand2',
                            activebackground='#2563EB', activeforeground='white', command=backup_now)
        now_btn.pack(side='right', padx=(10, 0))

        close_btn = tk.Button(footer, text="  إغلاق  ", bg='#64748B', fg='white',
                              font=('Segoe UI', 10), relief='flat', padx=15, pady=6, cursor='hand2',
                              activebackground='#475569', activeforeground='white', command=dialog.destroy)
        close_btn.pack(side='right')
    
    def on_closing(self):
        """معالج إغلاق البرنامج - عمل نسخ احتياطي تلقائي"""
        if hasattr(self, '_time_after_id') and self._time_after_id:
            try:
                self.root.after_cancel(self._time_after_id)
                self._time_after_id = None
            except Exception:
                pass
        if hasattr(self, '_dashboard_after_id') and self._dashboard_after_id:
            try:
                self.root.after_cancel(self._dashboard_after_id)
                self._dashboard_after_id = None
            except Exception:
                pass
        try:
            # عمل نسخة احتياطية تلقائية
            db = Database()
            backup_path = db.auto_backup()
            if backup_path:
                print(f"✅ نسخة احتياطية تلقائية: {backup_path}")
            db.close()
        except Exception as e:
            print(f"⚠️ خطأ في النسخ الاحتياطي التلقائي: {e}")
        
        # إغلاق البرنامج
        try:
            self.root.destroy()
        except Exception:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = AccountingApp(root)
    # ربط معالج الإغلاق
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    if '--selftest' in sys.argv:
        # وضع الفحص الآلي (للمطور فقط) - يكتب تقريرًا ثم يغلق
        _idx = sys.argv.index('--selftest')
        _report = sys.argv[_idx + 1] if len(sys.argv) > _idx + 1 else 'selftest_report.json'
        import selftest_ui
        root.after(2500, lambda: selftest_ui.run(root, app, _report))
    root.mainloop()
