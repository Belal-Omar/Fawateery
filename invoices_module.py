import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import os
import sys
import json
import ctypes
import subprocess
from datetime import datetime, timedelta
from fpdf import FPDF
from classic_pdf_template import ClassicInvoicePDF
from database import Database
import tempfile
import pandas as pd
from central_refresh import emit_customer_change, emit_invoice_change, emit_project_change


def set_widget_state(widget, state):
    """Apply a widget state safely without raising on unsupported widgets."""
    if widget is None:
        return False
    try:
        widget.config(**{'state': state})
        return True
    except Exception:
        return False


def choose_pdf_save_path(default_name, title="حفظ الملف كـ"):
    """اختيار مسار لحفظ ملف PDF"""
    from tkinter import filedialog

    initial_dir = os.path.join(os.path.expanduser('~'), 'Documents')
    if not os.path.exists(initial_dir):
        initial_dir = os.path.expanduser('~')

    filepath = filedialog.asksaveasfilename(
        defaultextension='.pdf',
        initialfile=default_name,
        title=title,
        filetypes=[('PDF files', '*.pdf')],
        initialdir=initial_dir
    )
    if not filepath:
        return None
    if not filepath.lower().endswith('.pdf'):
        filepath += '.pdf'
    return filepath


def save_pdf_document(pdf, filepath):
    """حفظ ملف PDF مع دعم بديل عند وجود مشاكل Unicode"""
    if not filepath:
        return None

    try:
        pdf.output(filepath)
    except UnicodeEncodeError:
        print('⚠️ خطأ Unicode، محاولة الحل البديل...')
        pdf_bytes = pdf.output(dest='S').encode('latin-1', errors='replace')
        with open(filepath, 'wb') as f:
            f.write(pdf_bytes)
    return filepath


def open_pdf_document(filepath):
    """فتح ملف PDF بعد حفظه"""
    if not filepath or not os.path.exists(filepath):
        return False

    try:
        if os.name == 'nt':
            result = ctypes.windll.shell32.ShellExecuteW(None, 'open', filepath, None, None, 1)
            return result > 32
        elif os.name == 'posix':
            os.system(f'xdg-open "{filepath}"')
            return True
    except Exception as e:
        print(f'لا يمكن فتح الملف تلقائياً: {e}')
        return False


def _find_acrobat_executable():
    """البحث عن مسار Adobe Acrobat أو Adobe Reader في السجل أو المسارات الشائعة"""
    if os.name != 'nt':
        return None

    # البحث في السجل - InstallPath قد يكون subkey بدلاً من value مباشر
    registry_searches = [
        (r'SOFTWARE\Adobe\Adobe Acrobat',              'DC'),
        (r'SOFTWARE\WOW6432Node\Adobe\Adobe Acrobat',  'DC'),
        (r'SOFTWARE\Adobe\Acrobat Reader',             'DC'),
        (r'SOFTWARE\WOW6432Node\Adobe\Acrobat Reader', 'DC'),
    ]
    try:
        import winreg
        for reg_base, version in registry_searches:
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                # جرب إصدار DC أولاً ثم كل الإصدارات
                for ver_key in (version, None):
                    try:
                        path = reg_base if ver_key is None else reg_base + '\\' + ver_key
                        key = winreg.OpenKey(hive, path + '\\InstallPath')
                        install_path, _ = winreg.QueryValueEx(key, '')
                        winreg.CloseKey(key)
                        for exe in ('Acrobat.exe', 'AcroRd32.exe'):
                            full = os.path.join(install_path, exe)
                            if os.path.isfile(full):
                                return full
                    except (FileNotFoundError, OSError):
                        pass
                    # جرب قراءة subkeys للإصدارات المختلفة
                    try:
                        key = winreg.OpenKey(hive, reg_base)
                        i = 0
                        while True:
                            try:
                                sub_name = winreg.EnumKey(key, i)
                                try:
                                    ip_key = winreg.OpenKey(hive, reg_base + '\\' + sub_name + '\\InstallPath')
                                    install_path, _ = winreg.QueryValueEx(ip_key, '')
                                    winreg.CloseKey(ip_key)
                                    for exe in ('Acrobat.exe', 'AcroRd32.exe'):
                                        full = os.path.join(install_path, exe)
                                        if os.path.isfile(full):
                                            return full
                                except (FileNotFoundError, OSError):
                                    pass
                                i += 1
                            except OSError:
                                break
                        winreg.CloseKey(key)
                    except (FileNotFoundError, OSError):
                        pass
    except ImportError:
        pass

    # مسارات ثابتة شائعة كحل احتياطي
    common_paths = [
        r'C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe',
        r'C:\Program Files (x86)\Adobe\Acrobat DC\Acrobat\Acrobat.exe',
        r'C:\Program Files\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe',
        r'C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe',
        r'C:\Program Files\Adobe\Reader 11.0\Reader\AcroRd32.exe',
        r'C:\Program Files (x86)\Adobe\Reader 11.0\Reader\AcroRd32.exe',
    ]
    for path in common_paths:
        if os.path.isfile(path):
            return path

    return None


def print_pdf_document(filepath):
    """فتح نافذة الطباعة مباشرة لملف PDF"""
    if not filepath or not os.path.exists(filepath):
        return False

    try:
        if os.name == 'nt':
            # محاولة 1: استخدام Adobe Acrobat/Reader مباشرة بـ flag /p لفتح نافذة الطباعة
            acrobat = _find_acrobat_executable()
            if acrobat:
                subprocess.Popen([acrobat, '/p', filepath])
                return True

            # محاولة 2: PowerShell Start-Process -Verb Print
            try:
                subprocess.Popen(
                    ['powershell', '-WindowStyle', 'Hidden', '-Command',
                     f'Start-Process -FilePath "{filepath}" -Verb Print'],
                    shell=False,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                return True
            except Exception:
                pass

            # محاولة 3: ShellExecuteW كحل أخير
            result = ctypes.windll.shell32.ShellExecuteW(None, 'print', filepath, None, None, 0)
            return result > 32
        else:
            return open_pdf_document(filepath)
    except Exception as e:
        print(f'لا يمكن إرسال الملف إلى الطابعة: {e}')
        return False


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

# استيراد مكتبة QR Code
try:
    import qrcode
    from PIL import Image
    QR_AVAILABLE = True
except ImportError:
    print("⚠️ يرجى تثبيت مكتبة QR Code: pip install qrcode[pil] Pillow")
    QR_AVAILABLE = False

# دالة تحويل الأرقام إلى حروف عربية
def number_to_arabic_text(number):
    """تحويل الأرقام إلى نص عربي v37"""
    if not number or number == 0:
        return "صفر"
    
    number = round(float(number), 2)
    integer_part = int(number)
    decimal_part = round((number - integer_part) * 100)
    
    units = ["", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة"]
    tens = ["", "عشرة", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"]
    hundreds = ["", "مائة", "مئتان", "ثلاثمائة", "أربعمائة", "خمسمائة", "ستمائة", "سبعمائة", "ثمانمائة", "تسعمائة"]
    
    def convert_less_than_1000(n):
        if n == 0:
            return ""
        elif n < 10:
            return units[n]
        elif n < 20:
            if n == 10: return "عشرة"
            elif n == 11: return "أحد عشر"
            elif n == 12: return "اثنا عشر"
            else: return units[n - 10] + " عشر"
        elif n < 100:
            ten = n // 10
            unit = n % 10
            return tens[ten] if unit == 0 else units[unit] + " و " + tens[ten]
        else:
            hundred = n // 100
            remainder = n % 100
            return hundreds[hundred] if remainder == 0 else hundreds[hundred] + " و " + convert_less_than_1000(remainder)
    
    def convert_to_arabic(n):
        if n == 0: return "صفر"
        
        parts = []
        # Millions
        millions = n // 1000000
        n %= 1000000
        if millions > 0:
            if millions == 1: parts.append("مليون")
            elif millions == 2: parts.append("مليونان")
            elif millions <= 10: parts.append(convert_less_than_1000(millions) + " ملايين")
            else: parts.append(convert_less_than_1000(millions) + " مليونًا")
            
        # Thousands
        thousands = n // 1000
        n %= 1000
        if thousands > 0:
            if thousands == 1: parts.append("ألف")
            elif thousands == 2: parts.append("ألفان")
            elif thousands <= 10: parts.append(convert_less_than_1000(thousands) + " آلاف")
            else: parts.append(convert_less_than_1000(thousands) + " ألفًا")
            
        # Less than 1000
        if n > 0:
            parts.append(convert_less_than_1000(n))
            
        return " و ".join(parts)
    
    integer_text = convert_to_arabic(integer_part)
    
    if decimal_part > 0:
        decimal_text = convert_to_arabic(decimal_part)
        return f"{integer_text} ريال و {decimal_text} هللة فقط لا غير"
    else:
        return f"{integer_text} ريال فقط لا غير"


class SearchableDropdown(ttk.Combobox):
    """قائمة منسدلة ذكية تدعم البحث أثناء الكتابة وتطابق الأسماء مع الحفاظ على القائمة المنسدلة الأصلية"""
    def __init__(self, master=None, **kwargs):
        init_values = kwargs.pop('values', None)
        super().__init__(master, **kwargs)
        self._all_values = list(init_values) if init_values is not None else []
        if init_values is not None:
            self['values'] = self._all_values
        self._popup = None
        self._listbox = None
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
        self.bind('<Unmap>', lambda e: self.hide_popup())
        self.bind('<Destroy>', lambda e: self.hide_popup())

    def configure(self, cnf=None, **kw):
        if 'values' in kw:
            self._all_values = list(kw['values'])
        return super().configure(cnf, **kw)
    config = configure

    def set_values(self, values):
        self._all_values = list(values)
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
        matches = []
        for v in self._all_values:
            nv = self._normalize_ar(v)
            if nq in nv:
                matches.append(v)
        return matches

    def _show_popup(self, matches):
        if not matches:
            self.hide_popup()
            return

        if not self._popup or not self._popup.winfo_exists():
            self._popup = tk.Toplevel(self)
            self._popup.wm_overrideredirect(True)
            self._popup.attributes('-topmost', True)
            
            frame = tk.Frame(self._popup, bg='#1A5276', bd=2, relief=tk.SOLID)
            frame.pack(fill='both', expand=True)
            
            scrollbar = ttk.Scrollbar(frame, orient='vertical')
            self._listbox = tk.Listbox(
                frame, font=('Segoe UI', 11, 'bold'), justify='right',
                yscrollcommand=scrollbar.set,
                selectmode='single', exportselection=False,
                bg='#FFFFFF', fg='#1A5276',
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
        y = self.winfo_rooty() + self.winfo_height() + 2
        
        # عرض أكبر ومريح جداً لاستيعاب أسماء المشاريع والعملاء كاملة دون قص
        w = max(self.winfo_width() + 180, 520)
        screen_w = self.winfo_screenwidth()
        if x + w > screen_w - 20:
            x = max(10, screen_w - w - 20)
        
        item_count = min(9, len(matches))
        h = max(45, item_count * 32 + 10)
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
        if not self.get().strip():
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
        self.focus_set()
        self.icursor('end')

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


# كلاس PDF لفاتورة عرض السعر
class PriceQuotePDF(FPDF):
    def __init__(self, company_settings=None):
        super().__init__()
        self.company_settings = company_settings or {}
        self.set_auto_page_break(auto=False) 
        
        try:
            amiri_regular = get_font_path('Amiri-Regular.ttf')
            amiri_bold = get_font_path('Amiri-Bold.ttf')
            
            if os.path.exists(amiri_regular):
                self.add_font('Amiri', '', amiri_regular, uni=True)
            if os.path.exists(amiri_bold):
                self.add_font('Amiri', 'B', amiri_bold, uni=True)
        except Exception as e:
            print(f"⚠️ خطأ في تحميل خطوط: {e}")

        self.set_margins(10, 10, 10)
    
    def header(self):
        self.set_fill_color(254, 254, 250)
        self.rect(0, 0, 210, 297, 'F')

    def draw_quote_header(self, quote_data):
        """رأس عرض السعر - بنفس تصميم الفاتورة الضريبية"""
        start_y = 10
        self.set_y(start_y)
        
        default_ar_name = "مؤسسه لؤلؤه البحر للمقاولات"
        default_en_name = "Sea Pearl Contracting"
        default_owner_ar = "محمد بن منير دغستاني"
        default_owner_en = "Mohammed bin Munir Daghestani"
        default_cr = "4030330926"
        default_vat = "300262161400003"
        
        cust_name_ar = self.company_settings.get('company_name_ar', default_ar_name)
        cust_name_en = self.company_settings.get('company_name_en', default_en_name)
        owner_name_ar = self.company_settings.get('owner_name', default_owner_ar)
        owner_name_en = self.company_settings.get('owner_name_en', default_owner_en)
        cr_no = self.company_settings.get('commercial_register', default_cr)
        vat_no = self.company_settings.get('tax_number', default_vat)
        
        # Company Header Box - نفس تصميم الفاتورة الضريبية
        box_w, box_h = 190, 25
        self.set_xy(10, start_y)
        self.set_fill_color(76, 117, 163)
        self.rect(10, start_y, box_w, box_h, 'F')
        
        # Company info
        self.set_font('Amiri', '', 9)
        self.set_text_color(255, 255, 255)
        self.set_xy(15, start_y + 2)
        self.cell(85, 4.5, ar(cust_name_ar), 0, 1, 'R')
        self.set_x(113)
        self.cell(85, 4.5, ar(f"س.ت: {cr_no}"), 0, 1, 'R')
        self.set_x(113)
        self.cell(85, 4.5, ar(f"الرقم الضريبي: {vat_no}"), 0, 1, 'R')
        
        # Title - عرض سعر بدلاً من فاتورة ضريبية
        self.set_xy(80, start_y + 13)
        self.set_font('Amiri', 'B', 13)
        self.cell(50, 6, ar("عرض سعر"), 0, 1, 'C')
        self.set_x(80)
        try: self.set_font('Arial', 'B', 11)
        except: self.set_font('Helvetica', 'B', 11)
        self.cell(50, 5, "PRICE QUOTE", 0, 1, 'C')
        
        self.set_y(start_y + box_h + 5)
        return start_y + box_h + 5
    
    def draw_customer_details(self, quote_data):
        """بيانات العميل - بنفس تصميم الفاتورة الضريبية"""
        start_y = self.get_y()
        main_rgb = (1, 27, 64) 
        label_rgb = (46, 80, 144)
        
        customer_name = quote_data.get('customer_name', '---')
        
        quote_fields = [
            ("Date", "التاريخ", quote_data.get('date', '')),
            ("Time", "الوقت", datetime.now().strftime('%H:%M:%S')),
            ("Quote No.", "رقم عرض السعر", quote_data.get('quote_number', '')),
            ("Valid Until", "صالح حتى", quote_data.get('valid_until', ''))
        ]
        
        customer_fields = [
            ("Customer Name", "اسم العميل", customer_name),
            ("Quote Type", "نوع العرض", "PRICE QUOTE")
        ]
        
        def draw_flow_section(fields, current_y, box_h, is_customer=False):
            current_x = 10
            fixed_box_w = 46 if is_customer else 43 
            gap = 1.6 if is_customer else 5.5
            
            # Calculate max lines required for this row
            max_lines = 1
            for label_en, label_ar, value in fields:
                self.set_font('Amiri', '', 9)
                words = str(value).split()
                lines = 1
                curr_line = ""
                for word in words:
                    if not curr_line:
                        curr_line = word
                    else:
                        test_line = curr_line + " " + word
                        if self.get_string_width(ar(test_line)) > 43 - 2:
                            lines += 1
                            curr_line = word
                        else:
                            curr_line = test_line
                if lines > max_lines:
                    max_lines = lines
            
            # Adjust box height dynamically based on max lines
            dynamic_box_h = (max_lines * 5) + 2
            box_h = max(box_h, dynamic_box_h)
            
            for label_en, label_ar, value in fields:
                label_text = f"{label_en} / {ar(label_ar)}"
                
                # Split value into lines
                self.set_font('Amiri', '', 9)
                words = str(value).split()
                val_lines = []
                curr_line = ""
                for word in words:
                    if not curr_line:
                        curr_line = word
                    else:
                        test_line = curr_line + " " + word
                        if self.get_string_width(ar(test_line)) > 43 - 2:
                            val_lines.append(ar(curr_line))
                            curr_line = word
                        else:
                            curr_line = test_line
                if curr_line:
                    val_lines.append(ar(curr_line))
                if not val_lines:
                    val_lines = [""]
                
                # Label box
                self.set_xy(current_x, current_y)
                self.set_fill_color(*label_rgb)
                self.set_line_width(0.5)
                self.rect(current_x, current_y, fixed_box_w, box_h, 'FD')
                self.set_text_color(255, 255, 255)
                self.set_font('Amiri', '', 8)
                self.set_xy(current_x, current_y + (box_h - 4) / 2)
                self.cell(fixed_box_w, 4, label_text, 0, 0, 'C')
                
                # Value box
                self.set_xy(current_x + fixed_box_w, current_y)
                self.set_fill_color(244, 244, 244)
                self.set_line_width(0.5)
                self.rect(current_x + fixed_box_w, current_y, 43, box_h, 'FD')
                self.set_text_color(0, 0, 0)
                self.set_font('Amiri', '', 9)
                
                y_offset = current_y + (box_h - (len(val_lines) * 5)) / 2
                for v_line in val_lines:
                    self.set_xy(current_x + fixed_box_w, y_offset)
                    self.cell(43, 5, v_line, 0, 0, 'C')
                    y_offset += 5
                
                current_x += fixed_box_w + 43 + gap
            return current_y + box_h + 2
        
        # Draw quote info section
        draw_flow_section(quote_fields, start_y, 6)
        self.set_y(start_y + 8)
        
        # Draw customer section
        draw_flow_section(customer_fields, self.get_y(), 6, is_customer=True)
        self.set_y(self.get_y() + 8)
    
    def draw_quote_items(self, items_data):
        """جدول بنود عرض السعر - نفس تصميم الفاتورة الضريبية"""
        # تحويل العناصر إلى نفس تنسقت الفاتورة
        items_json = []
        for item in items_data:
            items_json.append({
                'description': item.get('description', ''),
                'unit': item.get('unit', ''), 
                'quantity': str(item.get('quantity', 0)),
                'price': str(item.get('unit_price', 0)),
                'total': str(item.get('total', 0))
            })
        
        # استخدام نفس دالة draw_items_table من الفاتورة
        self.draw_items_table(json.dumps(items_json))

        # Get current Y position after drawing items and add spacing
        current_y = self.get_y()
        return current_y + 10
    
    def draw_quote_totals(self, totals_data):
        """ملخص عرض السعر - نفس تصميم الفاتورة"""
        # استخدام نفس دالة draw_totals_section من الفاتورة
        self.draw_totals_section(
            totals_data.get('subtotal', 0),
            totals_data.get('discount', 0),
            totals_data.get('tax', 0),
            totals_data.get('grand_total', 0)
        )
    
    def draw_quote_footer(self, quote_data):
        """تذييل عرض السعر - نفس تصميم الفاتورة"""
        # استخدام نفس دالة draw_footer من الفاتورة مع تعديل العنوان
        self.draw_footer(quote_data.get('quote_number', ''), quote_data.get('grand_total', 0))


# كلاس PDF بتصميم حديث v40 المطابق لنموذج PDF
class CustomInvoicePDF(FPDF):
    def __init__(self, company_settings=None, is_quote=False):
        super().__init__()
        self.company_settings = company_settings or {}
        self.is_quote = is_quote
        # Enforce one page strictly
        self.set_auto_page_break(auto=False) 
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            amiri_regular = os.path.join(current_dir, 'Amiri', 'Amiri-Regular.ttf')
            amiri_bold = os.path.join(current_dir, 'Amiri', 'Amiri-Bold.ttf')
            
            self.add_font('Amiri', '', amiri_regular, uni=True)
            self.add_font('Amiri', 'B', amiri_bold, uni=True)
            
            try:
                self.add_font('Arial', '', 'arial.ttf', uni=True)
                self.add_font('Arial', 'B', 'arialbd.ttf', uni=True)
            except:
                pass
        except Exception as e:
            print(f"⚠️ خطأ في تحميل خطوط: {e}")

        self.set_margins(10, 10, 10)
        
    def rounded_rect(self, x, y, w, h, r, style='', corners='1234'):
        k = self.k
        hp = self.h
        if(style=='F'): op='f'
        elif(style=='FD' or style=='DF'): op='B'
        else: op='S'
        myArc = 4/3 * (2**0.5 - 1) * r
        self._out('%.2F %.2F m' % ((x+r)*k,(hp-y)*k ))

        xc = x+w-r
        yc = y+r
        self._out('%.2F %.2F l' % (xc*k,(hp-y)*k ))
        if '2' in corners:
            self._out('%.2F %.2F %.2F %.2F %.2F %.2F c' % ((xc+myArc)*k,(hp-y)*k, (xc+r)*k,(hp-(y+myArc))*k, (xc+r)*k,(hp-yc)*k))
        else:
            self._out('%.2F %.2F l' % ((x+w)*k,(hp-y)*k))
            self._out('%.2F %.2F l' % ((x+w)*k,(hp-(y+r))*k))

        xc = x+w-r
        yc = y+h-r
        self._out('%.2F %.2F l' % ((x+w)*k,(hp-yc)*k))
        if '3' in corners:
            self._out('%.2F %.2F %.2F %.2F %.2F %.2F c' % ((x+w)*k,(hp-(yc+myArc))*k, (xc+myArc)*k,(hp-(y+h))*k, xc*k,(hp-(y+h))*k))
        else:
            self._out('%.2F %.2F l' % ((x+w)*k,(hp-(y+h))*k))
            self._out('%.2F %.2F l' % ((x+w-r)*k,(hp-(y+h))*k))

        xc = x+r
        yc = y+h-r
        self._out('%.2F %.2F l' % (xc*k,(hp-(y+h))*k))
        if '4' in corners:
            self._out('%.2F %.2F %.2F %.2F %.2F %.2F c' % ((xc-myArc)*k,(hp-(y+h))*k, x*k,(hp-(yc+myArc))*k, x*k,(hp-yc)*k))
        else:
            self._out('%.2F %.2F l' % (x*k,(hp-(y+h))*k))
            self._out('%.2F %.2F l' % (x*k,(hp-(y+h-r))*k))

        xc = x+r
        yc = y+r
        self._out('%.2F %.2F l' % (x*k,(hp-yc)*k ))
        if '1' in corners:
            self._out('%.2F %.2F %.2F %.2F %.2F %.2F c' % (x*k,(hp-(yc-myArc))*k, (xc-myArc)*k,(hp-y)*k, xc*k,(hp-y)*k))
        else:
            self._out('%.2F %.2F l' % (x*k,(hp-y)*k))
            self._out('%.2F %.2F l' % ((x+r)*k,(hp-y)*k))
        self._out(op)

    def header(self):
        self.set_fill_color(254, 254, 250)
        self.rect(0, 0, 210, 297, 'F')

    def draw_invoice_header(self, invoice_data):
        start_y = 10
        self.set_y(start_y)
        
        default_ar_name = "مؤسسة لؤلؤة البحر للمقاولات"
        default_en_name = "Sea Pearl Contracting EST."
        default_owner_ar = "محمد بن منير دغستاني"
        default_owner_en = "Mohammed bin Munir Daghestani"
        default_cr = "4030330926"
        default_vat = "300262161400003"
        
        cust_name_ar = self.company_settings.get('company_name_ar', default_ar_name)
        cust_name_en = self.company_settings.get('company_name_en', default_en_name)
        owner_name_ar = self.company_settings.get('owner_name', default_owner_ar)
        owner_name_en = self.company_settings.get('owner_name_en', default_owner_en)
        cr_no = self.company_settings.get('commercial_register', default_cr)
        vat_no = self.company_settings.get('tax_number', default_vat)
        
        bg_rgb = (76, 117, 163) 
        box_h = 32 
        self.set_fill_color(*bg_rgb)
        self.rounded_rect(10, start_y, 190, box_h, 3, 'F')
        
        self.set_text_color(255, 255, 255)
        
        # English Side
        self.set_xy(12, start_y + 3)
        try: self.set_font('Arial', 'B', 15)
        except: self.set_font('Helvetica', 'B', 15)
        self.cell(85, 7, cust_name_en, 0, 1, 'L')
        
        try: self.set_font('Arial', '', 9)
        except: self.set_font('Helvetica', '', 9)
        self.set_x(12)
        self.cell(85, 4.5, owner_name_en, 0, 1, 'L')
        self.set_x(12)
        self.cell(85, 4.5, f"CR: {cr_no}", 0, 1, 'L')
        self.set_x(12)
        self.cell(85, 4.5, f"VAT: {vat_no}", 0, 1, 'L')
        
        # Arabic Side
        self.set_xy(113, start_y + 3)
        self.set_font('Amiri', 'B', 15)
        self.cell(85, 7, ar(cust_name_ar), 0, 1, 'R')
        
        self.set_font('Amiri', 'B', 9)
        self.set_x(113)
        self.cell(85, 4.5, ar(owner_name_ar), 0, 1, 'R')
        self.set_x(113)
        self.cell(85, 4.5, ar(f"س.ت: {cr_no}"), 0, 1, 'R')
        self.set_x(113)
        self.cell(85, 4.5, ar(f"الرقم الضريبي: {vat_no}"), 0, 1, 'R')
        
        # Title
        self.set_xy(80, start_y + 11)
        self.set_font('Amiri', 'B', 14)
        title_ar = "عرض سعر" if self.is_quote else "فاتورة ضريبية"
        self.cell(50, 6, ar(title_ar), 0, 1, 'C')
        self.set_x(80)
        try: self.set_font('Arial', 'B', 11)
        except: self.set_font('Helvetica', 'B', 11)
        title_en = "PRICE QUOTE" if self.is_quote else "TAX INVOICE"
        self.cell(50, 5, title_en, 0, 1, 'C')
        
        self.set_y(start_y + box_h + 4)

    def draw_customer_details(self, invoice_data, customer_data):
        main_rgb = (1, 27, 64) 
        label_rgb = (46, 80, 144)
        
        cust_name = customer_data[1] if customer_data and len(customer_data) > 1 and customer_data[1] else '---'
        cust_vat = customer_data[2] if customer_data and len(customer_data) > 2 and customer_data[2] else '---'
        cust_address = customer_data[3] if customer_data and len(customer_data) > 3 and customer_data[3] else '---'
        
        doc_no_label = ("Quote No.", "رقم عرض السعر") if self.is_quote else ("Invoice No.", "رقم الفاتورة")
        
        inv_fields = [
            (doc_no_label[0], doc_no_label[1], invoice_data[1]),
            ("Cust. VAT", "الرقم الضريبي", cust_vat),
            ("Date", "التاريخ", invoice_data[3]),
            ("Time", "الوقت", datetime.now().strftime('%H:%M:%S'))
        ]
        
        current_y = self.get_y()
        box_w = 44.5
        box_h = 14
        gap = (190 - (4 * box_w)) / 3
        
        current_x = 10
        for label_en, label_ar, value in inv_fields:
            label_text = f"{label_en} / {ar(label_ar)}"
            value_text = ar(str(value))
            
            self.set_draw_color(200, 200, 200)
            self.set_fill_color(255, 255, 255)
            self.rounded_rect(current_x, current_y, box_w, box_h, 3, 'FD')
            
            self.set_xy(current_x, current_y + 2)
            self.set_font('Amiri', 'B', 8.5)
            self.set_text_color(*label_rgb)
            self.cell(box_w, 4.5, label_text, 0, 0, 'C')
            
            self.set_xy(current_x, current_y + 7)
            self.set_font('Amiri', 'B', 11)
            self.set_text_color(*main_rgb)
            self.cell(box_w, 6, value_text, 0, 0, 'C')
            
            current_x += box_w + gap
            
        current_y += box_h + 3.5
        
        # Row 2: Customer Name (Aligned to right edge at x=200, width=150mm)
        name_w = 150
        name_x = 200 - name_w # 50mm (starts at right edge)
        right_margin = 196
        
        self.set_draw_color(200, 200, 200)
        self.set_fill_color(255, 255, 255)
        self.rounded_rect(name_x, current_y, name_w, 10, 3, 'FD')
        
        label_name = ar("اسم العميل / Customer Name :")
        val_name = ar(str(cust_name))
        
        self.set_font('Amiri', 'B', 9.5)
        l_w = self.get_string_width(label_name)
        self.set_font('Amiri', 'B', 11)
        v_w = self.get_string_width(val_name)
        
        label_x = right_margin - l_w
        val_x = label_x - v_w - 2
        if val_x < name_x + 3:
            val_x = name_x + 3
            v_w = label_x - val_x - 1
            
        # Value on the left, Label on the right (reads properly RTL: اسم العميل / Customer Name : <Name>)
        self.set_xy(val_x, current_y + 2)
        self.set_font('Amiri', 'B', 11)
        self.set_text_color(*main_rgb)
        self.cell(v_w, 6, val_name, 0, 0, 'R')
        
        self.set_xy(label_x, current_y + 2)
        self.set_font('Amiri', 'B', 9.5)
        self.set_text_color(*label_rgb)
        self.cell(l_w, 6, label_name, 0, 0, 'R')
        
        current_y += 10 + 2.5
        
        # Row 3: Customer Address (Aligned to right edge at x=200, width=150mm)
        self.set_draw_color(200, 200, 200)
        self.set_fill_color(255, 255, 255)
        self.rounded_rect(name_x, current_y, name_w, 10, 3, 'FD')
        
        label_addr = ar("العنوان / Address :")
        val_addr = ar(str(cust_address))
        
        self.set_font('Amiri', 'B', 9.5)
        l_w_addr = self.get_string_width(label_addr)
        self.set_font('Amiri', 'B', 10.5)
        v_w_addr = self.get_string_width(val_addr)
        
        label_addr_x = right_margin - l_w_addr
        val_addr_x = label_addr_x - v_w_addr - 2
        if val_addr_x < name_x + 3:
            val_addr_x = name_x + 3
            v_w_addr = label_addr_x - val_addr_x - 1
            
        # Value on the left, Label on the right (reads properly RTL: العنوان / Address : <Address>)
        self.set_xy(val_addr_x, current_y + 2)
        self.set_font('Amiri', 'B', 10.5)
        self.set_text_color(*main_rgb)
        self.cell(v_w_addr, 6, val_addr, 0, 0, 'R')
        
        self.set_xy(label_addr_x, current_y + 2)
        self.set_font('Amiri', 'B', 9.5)
        self.set_text_color(*label_rgb)
        self.cell(l_w_addr, 6, label_addr, 0, 0, 'R')
        
        self.set_y(current_y + 10 + 3.5)

    def draw_items_table(self, items_json):
        main_rgb = (1, 27, 64)
        label_rgb = (46, 80, 144) 
        if isinstance(items_json, str):
            try:
                items = json.loads(items_json)
            except:
                import ast
                items = ast.literal_eval(items_json)
        else:
            items = items_json or []
        
        # Headers matching PDF: م, البيان, الوحدة, الكمية, سعر الوحدة, الإجمالي
        headers = [ar('م'), ar('البيان'), ar('الوحدة'), ar('الكمية'), ar('سعر الوحدة'), ar('الإجمالي')]
        col_widths = [10, 95, 18, 20, 23, 24] # Total = 190mm
        
        start_y = self.get_y()
        current_x = 10
        
        self.set_font('Amiri', 'B', 11.5) 
        self.set_text_color(*label_rgb)
        for i, header in enumerate(headers):
            self.set_draw_color(200, 200, 200)
            self.set_fill_color(245, 245, 245)
            self.rounded_rect(current_x, start_y, col_widths[i], 9, 2, 'FD') 
            self.set_xy(current_x, start_y + 1.5)
            self.cell(col_widths[i], 6, header, 0, 0, 'C')
            current_x += col_widths[i]
        
        row_y = start_y + 10.5
        
        self.set_font('Amiri', 'B', 10.5) 
        self.set_text_color(*main_rgb)
        for idx, item in enumerate(items, 1):
            if isinstance(item, dict):
                desc = item.get('description', item.get('name', ''))
                unit = item.get('unit', '')
                qty = float(item.get('quantity', 0))
                price = float(item.get('price', item.get('unit_price', 0)))
                total = float(item.get('total', qty * price))
            else:
                desc = item[0]
                unit = item[1]
                qty = float(item[2])
                price = float(item[3])
                total = float(item[4])
                
            row_data = [
                str(idx),
                ar(desc),
                ar(unit),
                f"{qty:.3f}" if qty % 1 != 0 else f"{int(qty)}",
                f"{price:.3f}" if price % 1 != 0 else f"{int(price):.2f}",
                f"{total:.2f}"
            ]
            
            current_x = 10
            for i, data in enumerate(row_data):
                self.set_draw_color(220, 220, 220)
                self.set_fill_color(255, 255, 255)
                self.rounded_rect(current_x, row_y, col_widths[i], 8.5, 2, 'FD') 
                self.set_xy(current_x, row_y + 1.2)
                self.cell(col_widths[i], 6, str(data), 0, 0, 'C')
                current_x += col_widths[i]
            row_y += 9.5 
            
        self.set_y(row_y + 4)

    def draw_totals_section(self, total, discount, tax, grand_total):
        main_rgb = (1, 27, 64)
        label_rgb = (46, 80, 144)
        
        # 2x2 Grid matching PDF:
        # Top-Left: Discount Amount | Top-Right: Total
        # Bottom-Left: Grand Total  | Bottom-Right: VAT Amount 15%
        box_w = 56
        box_h = 11.5
        gap_x = 3
        gap_y = 2.5
        
        x_right = 200 - box_w # 144
        x_left = x_right - gap_x - box_w # 85
        
        # Place section at the very bottom right before footer (footer starts at y=248)
        target_y = 209
        start_y = max(target_y, self.get_y() + 3)
        
        # 1. Total (Top-Right)
        self._draw_total_box(x_right, start_y, box_w, box_h, "Total", "الإجمالي", f"{total:.2f}")
        # 2. Discount Amount (Top-Left)
        self._draw_total_box(x_left, start_y, box_w, box_h, "Discount Amount", "قيمة الخصم", f"{discount:.2f}")
        
        row2_y = start_y + box_h + gap_y
        # 3. VAT Amount 15% (Bottom-Right)
        self._draw_total_box(x_right, row2_y, box_w, box_h, "VAT Amount 15%", "%15 الضريبة", f"{tax:.2f}")
        # 4. Grand Total (Bottom-Left)
        self._draw_total_box(x_left, row2_y, box_w, box_h, "Grand Total", "الإجمالي النهائي", f"{grand_total:.2f}")
        
        # Amount in words below grid
        words_y = row2_y + box_h + 3
        amount_in_words = number_to_arabic_text(grand_total)
        self.set_xy(10, words_y)
        self.set_font('Amiri', 'B', 11) 
        self.set_text_color(*main_rgb)
        self.cell(190, 6, ar(f"المبلغ بالحروف: {amount_in_words}"), 0, 1, 'R')
        self.set_y(words_y + 8)

    def _draw_total_box(self, x, y, w, h, label_en, label_ar, value):
        main_rgb = (1, 27, 64)
        label_rgb = (46, 80, 144)
        self.set_draw_color(200, 200, 200)
        self.set_fill_color(255, 255, 255)
        self.rounded_rect(x, y, w, h, 3, 'FD')
        
        label_text = f"{label_en} / {ar(label_ar)}"
        self.set_xy(x, y + 1.2)
        self.set_font('Amiri', 'B', 8.5)
        self.set_text_color(*label_rgb)
        self.cell(w, 4.5, label_text, 0, 0, 'C')
        
        self.set_xy(x, y + 5.5)
        self.set_font('Amiri', 'B', 11.5)
        self.set_text_color(*main_rgb)
        self.cell(w, 5.5, value, 0, 0, 'C')

    def draw_footer(self, invoice_no, grand_total):
        main_rgb = (1, 27, 64)
        footer_bg = (76, 117, 163) 
        
        qr_y = 248
        if QR_AVAILABLE:
            qr_path = self.create_qr_code(f"Doc:{invoice_no}, Tot:{grand_total}")
            if qr_path:
                self.image(qr_path, x=10, y=qr_y, w=22, h=22)
        
        sig_y = 252
        center_x = 60
        self.set_xy(center_x, sig_y)
        self.set_font('Amiri', 'B', 10)
        self.set_text_color(*main_rgb)
        self.cell(40, 5, "Salesman / " + ar("البائع"), 0, 0, 'L')
        self.set_x(center_x + 60)
        self.cell(40, 5, "Received By / " + ar("المستلم"), 0, 1, 'L')
        self.ln(10)
        self.line(center_x, self.get_y(), center_x + 40, self.get_y())
        self.line(center_x + 60, self.get_y(), center_x + 100, self.get_y())
        
        footer_y = 277 
        self.set_y(footer_y)
        self.set_fill_color(*footer_bg)
        self.rounded_rect(10, footer_y, 190, 15, 3, 'F')
        
        company = self.company_settings
        addr_ar = company.get('address', 'جدة - أبحر الشمالية - شارع أبي محمد العطار')
        addr_en = company.get('address_en', 'Jeddah - Obhur Al Shamaliah - Abi Mohammed Al Attar St.')
        mob1 = company.get('phone1', '0582224122')
        mob2 = company.get('phone2', '0538833640')
        email = company.get('email', 'seapearl.est@gmail.com')
        
        self.set_text_color(255, 255, 255)
        self.set_xy(10, footer_y + 1.5)
        self.set_font('Amiri', '', 7.5) 
        address_line = f"{ar(addr_ar)}  |  {addr_en}"
        self.cell(190, 4, address_line, 0, 1, 'C')
        
        self.set_x(10)
        self.set_font('Amiri', 'B', 8.5)
        contact_line = f"Mobile: {mob1} - {mob2}  |  Email: {email}"
        self.cell(190, 5, contact_line, 0, 1, 'C')

    def add_invoice_data(self, invoice, customer_data):
        self.draw_invoice_header(invoice)
        self.draw_customer_details(invoice, customer_data)
        self.draw_items_table(invoice[4])
        self.draw_totals_section(invoice[5], invoice[7], invoice[6], invoice[8])
        self.draw_footer(invoice[1], invoice[8])

    def create_qr_code(self, data):
        if not QR_AVAILABLE: return None
        try:
            qr = qrcode.QRCode(version=1, box_size=3, border=1)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            img.save(temp_file.name)
            temp_file.close()
            return temp_file.name
        except: return None

# نافذة إنشاء وتعديل الفواتير

# =========================================================================
# نافذة اختيار وبحث العميل والمشروع مع إمكانية التعديل والإضافة المباشرة
# =========================================================================
class CustomerProjectSelectorDialog(tk.Toplevel):
    """نافذة متطورة للبحث واختيار وتعديل وإضافة العميل والمشروع"""
    def __init__(self, parent, db, callback, status_callback=None):
        super().__init__(parent)
        self.db = db
        self.callback = callback
        self.status_callback = status_callback
        
        self.title("🔍 اختيار العميل والمشروع")
        self.geometry("860x600")
        self.minsize(760, 500)
        self.transient(parent)
        self.grab_set()
        self.configure(bg='#F8FAFC')
        
        self.update_idletasks()
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 430
            y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 300
            self.geometry(f"860x600+{max(50, x)}+{max(50, y)}")
        except Exception:
            pass
            
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        container = tk.Frame(self, bg='#F8FAFC', padx=20, pady=15)
        container.pack(fill='both', expand=True)

        # Header
        hdr = tk.Frame(container, bg='#1E293B', padx=15, pady=10)
        hdr.pack(fill='x', pady=(0, 10))
        tk.Label(hdr, text="🔍 البحث واختيار وتعديل العميل والمشروع للفاتورة", font=('Segoe UI', 12, 'bold'), fg='white', bg='#1E293B').pack(side='right')

        # Search bar
        search_bar = tk.Frame(container, bg='#F8FAFC')
        search_bar.pack(fill='x', pady=(0, 10))
        tk.Label(search_bar, text="بحث سريع:", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(side='right', padx=5)
        self.search_entry = ttk.Entry(search_bar, font=('Segoe UI', 10), width=35)
        self.search_entry.pack(side='right', padx=5, ipady=3)
        self.search_entry.bind('<KeyRelease>', lambda e: self.filter_data())
        self.search_entry.focus_set()

        # Notebook for Customers & Projects
        self.nb = ttk.Notebook(container)
        self.nb.pack(fill='both', expand=True, pady=(0, 10))

        # ----------------- Customers Tab -----------------
        cust_frame = ttk.Frame(self.nb)
        self.nb.add(cust_frame, text="🏢 قائمة العملاء")
        
        cust_tree_frame = tk.Frame(cust_frame)
        cust_tree_frame.pack(fill='both', expand=True)
        
        self.cust_tree = ttk.Treeview(cust_tree_frame, columns=('id', 'name', 'phone', 'tax'), show='headings', height=10)
        self.cust_tree.heading('id', text='ID')
        self.cust_tree.heading('name', text='اسم العميل')
        self.cust_tree.heading('phone', text='الهاتف')
        self.cust_tree.heading('tax', text='الرقم الضريبي')
        self.cust_tree.column('id', width=60, anchor='center')
        self.cust_tree.column('name', width=280, anchor='e')
        self.cust_tree.column('phone', width=150, anchor='center')
        self.cust_tree.column('tax', width=180, anchor='center')
        
        cust_scroll = ttk.Scrollbar(cust_tree_frame, orient='vertical', command=self.cust_tree.yview)
        self.cust_tree.configure(yscrollcommand=cust_scroll.set)
        self.cust_tree.pack(side='left', fill='both', expand=True)
        cust_scroll.pack(side='right', fill='y')
        self.cust_tree.bind('<Double-1>', lambda e: self.apply_selection())

        # Customer Action Bar (Edit / Add)
        cust_act_bar = tk.Frame(cust_frame, bg='#F1F5F9', padx=10, pady=8)
        cust_act_bar.pack(fill='x', side='bottom')
        
        tk.Button(cust_act_bar, text="✏️ تعديل بيانات العميل المحدد", command=self.edit_selected_customer,
                  font=('Segoe UI', 9, 'bold'), bg='#0284C7', fg='white', relief='flat', padx=12, pady=5, cursor='hand2').pack(side='right', padx=5)
                  
        tk.Button(cust_act_bar, text="➕ إضافة عميل جديد", command=self.add_new_customer,
                  font=('Segoe UI', 9, 'bold'), bg='#10B981', fg='white', relief='flat', padx=12, pady=5, cursor='hand2').pack(side='right', padx=5)

        # ----------------- Projects Tab -----------------
        proj_frame = ttk.Frame(self.nb)
        self.nb.add(proj_frame, text="🏗️ قائمة المشاريع")
        
        proj_tree_frame = tk.Frame(proj_frame)
        proj_tree_frame.pack(fill='both', expand=True)
        
        self.proj_tree = ttk.Treeview(proj_tree_frame, columns=('id', 'name', 'cust_id', 'cust_name', 'budget'), show='headings', height=10)
        self.proj_tree.heading('id', text='ID')
        self.proj_tree.heading('name', text='اسم المشروع')
        self.proj_tree.heading('cust_id', text='رقم العميل')
        self.proj_tree.heading('cust_name', text='العميل المرتبط')
        self.proj_tree.heading('budget', text='الميزانية')
        self.proj_tree.column('id', width=50, anchor='center')
        self.proj_tree.column('name', width=240, anchor='e')
        self.proj_tree.column('cust_id', width=70, anchor='center')
        self.proj_tree.column('cust_name', width=220, anchor='e')
        self.proj_tree.column('budget', width=120, anchor='center')
        
        proj_scroll = ttk.Scrollbar(proj_tree_frame, orient='vertical', command=self.proj_tree.yview)
        self.proj_tree.configure(yscrollcommand=proj_scroll.set)
        self.proj_tree.pack(side='left', fill='both', expand=True)
        proj_scroll.pack(side='right', fill='y')
        self.proj_tree.bind('<Double-1>', lambda e: self.apply_selection())

        # Project Action Bar (Edit / Add)
        proj_act_bar = tk.Frame(proj_frame, bg='#F1F5F9', padx=10, pady=8)
        proj_act_bar.pack(fill='x', side='bottom')
        
        tk.Button(proj_act_bar, text="✏️ تعديل بيانات المشروع المحدد", command=self.edit_selected_project,
                  font=('Segoe UI', 9, 'bold'), bg='#0284C7', fg='white', relief='flat', padx=12, pady=5, cursor='hand2').pack(side='right', padx=5)
                  
        tk.Button(proj_act_bar, text="➕ إضافة مشروع جديد", command=self.add_new_project,
                  font=('Segoe UI', 9, 'bold'), bg='#10B981', fg='white', relief='flat', padx=12, pady=5, cursor='hand2').pack(side='right', padx=5)

        # Footer Buttons
        btn_box = tk.Frame(container, bg='#F8FAFC')
        btn_box.pack(fill='x')
        tk.Button(btn_box, text="  ✅ اختيار وتطبيق على الفاتورة  ", command=self.apply_selection, font=('Segoe UI', 10, 'bold'),
                  bg='#10B981', fg='white', relief='flat', padx=18, pady=7, cursor='hand2').pack(side='right', padx=5)
        tk.Button(btn_box, text="  ❌ إلغاء  ", command=self.destroy, font=('Segoe UI', 10),
                  bg='#64748B', fg='white', relief='flat', padx=14, pady=7, cursor='hand2').pack(side='right')

    def load_data(self):
        try:
            self.customers_data = self.db.execute_query("SELECT id, name, phone, tax_number FROM customers ORDER BY name") or []
            self.projects_data = self.db.execute_query("""
                SELECT p.id, p.name, p.customer_id, COALESCE(c.name, '---'), p.budget
                FROM projects p
                LEFT JOIN customers c ON p.customer_id = c.id
                ORDER BY p.name
            """) or []
        except Exception:
            self.customers_data = []
            self.projects_data = []
        self.populate_trees(self.customers_data, self.projects_data)

    def populate_trees(self, custs, projs):
        self.cust_tree.delete(*self.cust_tree.get_children())
        for c in custs:
            self.cust_tree.insert('', 'end', values=(c[0], c[1], c[2] or '---', c[3] or '---'))
            
        self.proj_tree.delete(*self.proj_tree.get_children())
        for p in projs:
            self.proj_tree.insert('', 'end', values=(p[0], p[1], p[2] or '---', p[3] or '---', f"{p[4]:,.2f}" if p[4] else '0.00'))

    def filter_data(self):
        term = self.search_entry.get().strip().lower()
        if not term:
            self.populate_trees(self.customers_data, self.projects_data)
            return
            
        filt_custs = [c for c in self.customers_data if term in str(c[0]).lower() or term in str(c[1]).lower() or term in str(c[2] or '').lower() or term in str(c[3] or '').lower()]
        filt_projs = [p for p in self.projects_data if term in str(p[0]).lower() or term in str(p[1]).lower() or term in str(p[3] or '').lower()]
        self.populate_trees(filt_custs, filt_projs)

    def edit_selected_customer(self):
        sel = self.cust_tree.selection()
        if not sel:
            messagebox.showwarning("تنبيه", "⚠️ يرجى تحديد عميل من القائمة أولاً لتعديله", parent=self)
            return
        vals = self.cust_tree.item(sel[0], 'values')
        cust_id = int(vals[0])
        
        row = self.db.execute_query("SELECT name, phone, tax_number, address FROM customers WHERE id = ?", (cust_id,))
        if not row:
            messagebox.showerror("خطأ", "❌ تعذر العثور على بيانات العميل", parent=self)
            return
        cust = row[0]
        
        d = tk.Toplevel(self)
        d.title(f"✏️ تعديل بيانات العميل #{cust_id}")
        d.geometry("480x360")
        d.transient(self)
        d.grab_set()
        d.configure(bg='#F8FAFC')
        
        f = tk.Frame(d, bg='#F8FAFC', padx=25, pady=20)
        f.pack(fill='both', expand=True)
        
        tk.Label(f, text="اسم العميل *", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        name_e = ttk.Entry(f, font=('Segoe UI', 10))
        name_e.pack(fill='x', pady=(2, 10))
        name_e.insert(0, str(cust[0] or ''))
        
        tk.Label(f, text="رقم الهاتف", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        phone_e = ttk.Entry(f, font=('Segoe UI', 10))
        phone_e.pack(fill='x', pady=(2, 10))
        phone_e.insert(0, str(cust[1] or ''))
        
        tk.Label(f, text="الرقم الضريبي", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        tax_e = ttk.Entry(f, font=('Segoe UI', 10))
        tax_e.pack(fill='x', pady=(2, 10))
        tax_e.insert(0, str(cust[2] or ''))
        
        tk.Label(f, text="العنوان", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        addr_e = ttk.Entry(f, font=('Segoe UI', 10))
        addr_e.pack(fill='x', pady=(2, 15))
        addr_e.insert(0, str(cust[3] or ''))
        
        def save():
            name = name_e.get().strip()
            if not name:
                messagebox.showwarning("تنبيه", "⚠️ يرجى إدخال اسم العميل", parent=d)
                return
            phone = phone_e.get().strip()
            tax = tax_e.get().strip()
            addr = addr_e.get().strip()
            
            try:
                self.db.execute_query("UPDATE customers SET name=?, phone=?, tax_number=?, address=? WHERE id=?",
                                      (name, phone, tax, addr, cust_id))
                emit_customer_change(cust_id)
                self.load_data()
                d.destroy()
                messagebox.showinfo("نجاح", f"✅ تم تحديث بيانات العميل: {name}", parent=self)
            except Exception as ex:
                messagebox.showerror("خطأ", f"❌ فشل التحديث: {ex}", parent=d)

        btn_box = tk.Frame(f, bg='#F8FAFC')
        btn_box.pack(fill='x')
        tk.Button(btn_box, text="💾 حفظ التعديلات", command=save, font=('Segoe UI', 10, 'bold'),
                  bg='#10B981', fg='white', relief='flat', padx=15, pady=6, cursor='hand2').pack(side='right', padx=5)
        tk.Button(btn_box, text="إلغاء", command=d.destroy, font=('Segoe UI', 10),
                  bg='#64748B', fg='white', relief='flat', padx=12, pady=6, cursor='hand2').pack(side='right')

    def add_new_customer(self):
        d = tk.Toplevel(self)
        d.title("➕ إضافة عميل جديد")
        d.geometry("480x360")
        d.transient(self)
        d.grab_set()
        d.configure(bg='#F8FAFC')
        
        f = tk.Frame(d, bg='#F8FAFC', padx=25, pady=20)
        f.pack(fill='both', expand=True)
        
        tk.Label(f, text="اسم العميل *", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        name_e = ttk.Entry(f, font=('Segoe UI', 10))
        name_e.pack(fill='x', pady=(2, 10))
        name_e.focus_set()
        
        tk.Label(f, text="رقم الهاتف", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        phone_e = ttk.Entry(f, font=('Segoe UI', 10))
        phone_e.pack(fill='x', pady=(2, 10))
        
        tk.Label(f, text="الرقم الضريبي", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        tax_e = ttk.Entry(f, font=('Segoe UI', 10))
        tax_e.pack(fill='x', pady=(2, 10))
        
        tk.Label(f, text="العنوان", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        addr_e = ttk.Entry(f, font=('Segoe UI', 10))
        addr_e.pack(fill='x', pady=(2, 15))
        
        def save():
            name = name_e.get().strip()
            if not name:
                messagebox.showwarning("تنبيه", "⚠️ يرجى إدخال اسم العميل", parent=d)
                return
            phone = phone_e.get().strip()
            tax = tax_e.get().strip()
            addr = addr_e.get().strip()
            
            try:
                self.db.execute_query("INSERT INTO customers (name, phone, tax_number, address) VALUES (?, ?, ?, ?)",
                                      (name, phone, tax, addr))
                new_id = self.db.execute_query("SELECT last_insert_rowid()")[0][0]
                emit_customer_change(new_id)
                self.load_data()
                d.destroy()
                messagebox.showinfo("نجاح", f"✅ تم إضافة العميل: {name}", parent=self)
            except Exception as ex:
                messagebox.showerror("خطأ", f"❌ فشل الحفظ: {ex}", parent=d)

        btn_box = tk.Frame(f, bg='#F8FAFC')
        btn_box.pack(fill='x')
        tk.Button(btn_box, text="💾 حفظ العميل", command=save, font=('Segoe UI', 10, 'bold'),
                  bg='#10B981', fg='white', relief='flat', padx=15, pady=6, cursor='hand2').pack(side='right', padx=5)
        tk.Button(btn_box, text="إلغاء", command=d.destroy, font=('Segoe UI', 10),
                  bg='#64748B', fg='white', relief='flat', padx=12, pady=6, cursor='hand2').pack(side='right')

    def edit_selected_project(self):
        sel = self.proj_tree.selection()
        if not sel:
            messagebox.showwarning("تنبيه", "⚠️ يرجى تحديد مشروع من القائمة أولاً لتعديله", parent=self)
            return
        vals = self.proj_tree.item(sel[0], 'values')
        proj_id = int(vals[0])
        
        row = self.db.execute_query("SELECT name, customer_id, budget, status, description FROM projects WHERE id = ?", (proj_id,))
        if not row:
            messagebox.showerror("خطأ", "❌ تعذر العثور على بيانات المشروع", parent=self)
            return
        proj = row[0]
        
        d = tk.Toplevel(self)
        d.title(f"✏️ تعديل بيانات المشروع #{proj_id}")
        d.geometry("520x420")
        d.transient(self)
        d.grab_set()
        d.configure(bg='#F8FAFC')
        
        f = tk.Frame(d, bg='#F8FAFC', padx=25, pady=20)
        f.pack(fill='both', expand=True)
        
        tk.Label(f, text="اسم المشروع *", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        name_e = ttk.Entry(f, font=('Segoe UI', 10))
        name_e.pack(fill='x', pady=(2, 10))
        name_e.insert(0, str(proj[0] or ''))
        
        # Customer Combobox
        tk.Label(f, text="العميل المرتبط", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        custs = self.db.execute_query("SELECT id, name FROM customers ORDER BY name") or []
        cust_map = {f"{c[0]} - {c[1]}": c[0] for c in custs}
        cust_names = ["--- بدون عميل ---"] + list(cust_map.keys())
        cust_cb = ttk.Combobox(f, values=cust_names, font=('Segoe UI', 10), state='readonly')
        cust_cb.pack(fill='x', pady=(2, 10))
        
        cur_c_id = proj[1]
        cur_match = [k for k, v in cust_map.items() if v == cur_c_id]
        cust_cb.set(cur_match[0] if cur_match else "--- بدون عميل ---")
        
        tk.Label(f, text="الميزانية", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        budget_e = ttk.Entry(f, font=('Segoe UI', 10))
        budget_e.pack(fill='x', pady=(2, 10))
        budget_e.insert(0, str(proj[2] or '0'))
        
        tk.Label(f, text="الحالة", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        status_cb = ttk.Combobox(f, values=['قيد التنفيذ', 'مكتمل', 'معلق'], font=('Segoe UI', 10), state='readonly')
        status_cb.pack(fill='x', pady=(2, 15))
        status_cb.set(proj[3] or 'قيد التنفيذ')
        
        def save():
            name = name_e.get().strip()
            if not name:
                messagebox.showwarning("تنبيه", "⚠️ يرجى إدخال اسم المشروع", parent=d)
                return
            sel_c = cust_cb.get()
            c_id = cust_map.get(sel_c, None)
            try:
                budget = float(budget_e.get().strip() or 0)
            except ValueError:
                budget = 0.0
            status = status_cb.get().strip()
            
            try:
                self.db.execute_query("UPDATE projects SET name=?, customer_id=?, budget=?, status=? WHERE id=?",
                                      (name, c_id, budget, status, proj_id))
                emit_project_change(proj_id)
                self.load_data()
                d.destroy()
                messagebox.showinfo("نجاح", f"✅ تم تحديث بيانات المشروع: {name}", parent=self)
            except Exception as ex:
                messagebox.showerror("خطأ", f"❌ فشل التحديث: {ex}", parent=d)

        btn_box = tk.Frame(f, bg='#F8FAFC')
        btn_box.pack(fill='x')
        tk.Button(btn_box, text="💾 حفظ التعديلات", command=save, font=('Segoe UI', 10, 'bold'),
                  bg='#10B981', fg='white', relief='flat', padx=15, pady=6, cursor='hand2').pack(side='right', padx=5)
        tk.Button(btn_box, text="إلغاء", command=d.destroy, font=('Segoe UI', 10),
                  bg='#64748B', fg='white', relief='flat', padx=12, pady=6, cursor='hand2').pack(side='right')

    def add_new_project(self):
        d = tk.Toplevel(self)
        d.title("➕ إضافة مشروع جديد")
        d.geometry("520x420")
        d.transient(self)
        d.grab_set()
        d.configure(bg='#F8FAFC')
        
        f = tk.Frame(d, bg='#F8FAFC', padx=25, pady=20)
        f.pack(fill='both', expand=True)
        
        tk.Label(f, text="اسم المشروع *", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        name_e = ttk.Entry(f, font=('Segoe UI', 10))
        name_e.pack(fill='x', pady=(2, 10))
        name_e.focus_set()
        
        tk.Label(f, text="العميل المرتبط", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        custs = self.db.execute_query("SELECT id, name FROM customers ORDER BY name") or []
        cust_map = {f"{c[0]} - {c[1]}": c[0] for c in custs}
        cust_names = ["--- بدون عميل ---"] + list(cust_map.keys())
        cust_cb = ttk.Combobox(f, values=cust_names, font=('Segoe UI', 10), state='readonly')
        cust_cb.pack(fill='x', pady=(2, 10))
        cust_cb.set("--- بدون عميل ---")
        
        tk.Label(f, text="الميزانية", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        budget_e = ttk.Entry(f, font=('Segoe UI', 10))
        budget_e.pack(fill='x', pady=(2, 10))
        budget_e.insert(0, "0.00")
        
        tk.Label(f, text="الحالة", font=('Segoe UI', 10, 'bold'), bg='#F8FAFC').pack(anchor='e')
        status_cb = ttk.Combobox(f, values=['قيد التنفيذ', 'مكتمل', 'معلق'], font=('Segoe UI', 10), state='readonly')
        status_cb.pack(fill='x', pady=(2, 15))
        status_cb.set('قيد التنفيذ')
        
        def save():
            name = name_e.get().strip()
            if not name:
                messagebox.showwarning("تنبيه", "⚠️ يرجى إدخال اسم المشروع", parent=d)
                return
            sel_c = cust_cb.get()
            c_id = cust_map.get(sel_c, None)
            try:
                budget = float(budget_e.get().strip() or 0)
            except ValueError:
                budget = 0.0
            status = status_cb.get().strip()
            
            try:
                self.db.execute_query("INSERT INTO projects (name, customer_id, budget, status) VALUES (?, ?, ?, ?)",
                                      (name, c_id, budget, status))
                new_id = self.db.execute_query("SELECT last_insert_rowid()")[0][0]
                emit_project_change(new_id)
                self.load_data()
                d.destroy()
                messagebox.showinfo("نجاح", f"✅ تم إضافة المشروع: {name}", parent=self)
            except Exception as ex:
                messagebox.showerror("خطأ", f"❌ فشل الحفظ: {ex}", parent=d)

        btn_box = tk.Frame(f, bg='#F8FAFC')
        btn_box.pack(fill='x')
        tk.Button(btn_box, text="💾 حفظ المشروع", command=save, font=('Segoe UI', 10, 'bold'),
                  bg='#10B981', fg='white', relief='flat', padx=15, pady=6, cursor='hand2').pack(side='right', padx=5)
        tk.Button(btn_box, text="إلغاء", command=d.destroy, font=('Segoe UI', 10),
                  bg='#64748B', fg='white', relief='flat', padx=12, pady=6, cursor='hand2').pack(side='right')

    def apply_selection(self):
        curr_tab = self.nb.index(self.nb.select())
        cust_tuple = None
        proj_tuple = None
        
        if curr_tab == 0:
            sel = self.cust_tree.selection()
            if sel:
                vals = self.cust_tree.item(sel[0], 'values')
                cust_tuple = (int(vals[0]), vals[1])
        else:
            sel = self.proj_tree.selection()
            if sel:
                vals = self.proj_tree.item(sel[0], 'values')
                proj_tuple = (int(vals[0]), vals[1])
                try:
                    c_id = int(vals[2]) if str(vals[2]).isdigit() else None
                    c_name = vals[3] if vals[3] != '---' else ""
                    if c_id:
                        cust_tuple = (c_id, c_name)
                except Exception:
                    pass
                    
        if not cust_tuple and not proj_tuple:
            messagebox.showwarning("تنبيه", "⚠️ يرجى اختيار عميل أو مشروع أولاً", parent=self)
            return
            
        self.callback(cust_tuple, proj_tuple)
        self.destroy()


# =========================================================================
# نافذة إدخال أصناف متعددة دفعة واحدة (مطابقة للشكل المطلوب 100%)
# =========================================================================
class BatchInvoiceItemsDialog(tk.Toplevel):
    """جدول إدخال الأصناف السريع بتصميم شبكة أكسل ملونة ومتطورة"""
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.rows = []
        
        self.title("إدخال أصناف متعددة دفعة واحدة 📋")
        
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        win_w = min(1200, max(1040, int(screen_w * 0.85)))
        win_h = min(720, max(560, int(screen_h * 0.78)))
        x = max(10, (screen_w - win_w) // 2)
        y = max(10, (screen_h - win_h) // 2)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.minsize(980, 520)
        self.transient(parent)
        self.grab_set()
        
        self.setup_ui()

    def setup_ui(self):
        # Header banner (dark navy #1F3A52)
        header_frame = tk.Frame(self, bg='#1F3A52', pady=10)
        header_frame.pack(fill='x')
        tk.Label(header_frame, text="📋 جدول إدخال الأصناف السريع", font=('Segoe UI', 13, 'bold'), fg='white', bg='#1F3A52').pack()
        tk.Label(header_frame, text='أدخل الأصناف سطراً بسطر ثم اضغط "إضافة كل الأصناف للفاتورة" (للتنقل السريع بين الخلايا استخدم Tab أو Enter)',
                 font=('Segoe UI', 9), fg='#D5DBDB', bg='#1F3A52').pack(pady=(2, 0))

        # Scrollable grid container
        container = ttk.Frame(self)
        container.pack(fill='both', expand=True, padx=15, pady=10)

        self.canvas = tk.Canvas(container, bg='#F8F9F9', highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg='#F8F9F9')

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Column weights and minsize
        self.scrollable_frame.columnconfigure(0, weight=0, minsize=40)   # #
        self.scrollable_frame.columnconfigure(1, weight=4, minsize=260)  # الوصف / اسم الصنف
        self.scrollable_frame.columnconfigure(2, weight=1, minsize=80)   # الوحدة
        self.scrollable_frame.columnconfigure(3, weight=1, minsize=75)   # الكمية
        self.scrollable_frame.columnconfigure(4, weight=1, minsize=85)   # السعر
        self.scrollable_frame.columnconfigure(5, weight=1, minsize=95)   # إجمالي الصف
        self.scrollable_frame.columnconfigure(6, weight=1, minsize=70)   # % خصم
        self.scrollable_frame.columnconfigure(7, weight=1, minsize=80)   # خصم مبلغ
        self.scrollable_frame.columnconfigure(8, weight=1, minsize=95)   # الصافي

        # Table Header in Row 0
        headers = [
            ("#", 40),
            ("* الوصف / اسم الصنف", 260),
            ("الوحدة", 80),
            ("* الكمية", 75),
            ("* السعر", 85),
            ("إجمالي الصف", 95),
            ("% خصم", 70),
            ("خصم مبلغ", 80),
            ("الصافي", 95)
        ]
        for col_idx, (title, min_w) in enumerate(headers):
            lbl = tk.Label(self.scrollable_frame, text=title, font=('Segoe UI', 9, 'bold'),
                           bg='#1F3A52', fg='white', pady=8, padx=3, relief=tk.FLAT)
            lbl.grid(row=0, column=col_idx, sticky='nsew', padx=1, pady=(0, 4))

        # Initial 8 rows
        for _ in range(8):
            self.add_row()

        if self.rows:
            self.rows[0]['desc'].focus_set()

        # Bottom Bar
        btn_frame = tk.Frame(self, pady=10, bg='#EAEDED')
        btn_frame.pack(fill='x')

        # Right buttons
        tk.Button(btn_frame, text="➕ إضافة 5 أسطر إضافية", command=lambda: [self.add_row() for _ in range(5)],
                  bg='#5D6D7E', fg='white', font=('Segoe UI', 10, 'bold'), padx=14, pady=6, relief=tk.FLAT, cursor='hand2').pack(side='right', padx=10)

        tk.Button(btn_frame, text="📋 لصق من Excel", command=self.paste_from_excel,
                  bg='#34495E', fg='white', font=('Segoe UI', 9), padx=10, pady=6, relief=tk.FLAT, cursor='hand2').pack(side='right', padx=5)

        # Left buttons
        tk.Button(btn_frame, text="💾 إضافة كل الأصناف للفاتورة", command=self.save_and_close,
                  bg='#27AE60', fg='white', font=('Segoe UI', 11, 'bold'), padx=18, pady=6, relief=tk.FLAT, cursor='hand2').pack(side='left', padx=10)

        tk.Button(btn_frame, text="❌ إلغاء", command=self.destroy,
                  bg='#95A5A6', fg='white', font=('Segoe UI', 10), padx=12, pady=6, relief=tk.FLAT, cursor='hand2').pack(side='left', padx=5)

    def add_row(self, desc="", unit="", qty="", price="0", disc_pct="", disc_val="0"):
        row_idx = len(self.rows) + 1

        # 0. Index Label
        lbl_num = tk.Label(self.scrollable_frame, text=str(row_idx), font=('Segoe UI', 9, 'bold'),
                           bg='#EAEDED', fg='#2C3E50', relief='solid', bd=1)
        lbl_num.grid(row=row_idx, column=0, sticky='nsew', padx=1, pady=1)

        # 1. Description
        desc_e = tk.Entry(self.scrollable_frame, font=('Segoe UI', 9), justify='right',
                          bg='white', relief='solid', bd=1)
        desc_e.insert(0, str(desc))
        desc_e.grid(row=row_idx, column=1, sticky='nsew', padx=1, pady=1)

        # 2. Unit (manual entry - تكتب يدوياً)
        unit_e = tk.Entry(self.scrollable_frame, font=('Segoe UI', 9), justify='center',
                          bg='white', relief='solid', bd=1)
        if unit:
            unit_e.insert(0, str(unit))
        unit_e.grid(row=row_idx, column=2, sticky='nsew', padx=1, pady=1)

        # 3. Quantity (blank by default - بدون رقم 1)
        qty_e = tk.Entry(self.scrollable_frame, font=('Segoe UI', 9), justify='center',
                         bg='white', relief='solid', bd=1)
        if qty and str(qty) != "0":
            qty_e.insert(0, str(qty))
        qty_e.grid(row=row_idx, column=3, sticky='nsew', padx=1, pady=1)

        # 4. Price
        price_e = tk.Entry(self.scrollable_frame, font=('Segoe UI', 9), justify='center',
                           bg='white', relief='solid', bd=1)
        price_e.insert(0, str(price) if str(price) != "0" else "")
        price_e.grid(row=row_idx, column=4, sticky='nsew', padx=1, pady=1)

        # 5. Row Subtotal (Light blue #EBF5FB)
        subtotal_lbl = tk.Label(self.scrollable_frame, font=('Segoe UI', 9, 'bold'),
                                bg='#EBF5FB', fg='#1A5276', relief='solid', bd=1, text="")
        subtotal_lbl.grid(row=row_idx, column=5, sticky='nsew', padx=1, pady=1)

        # 6. Discount % (Light yellow #FEF9E7)
        disc_pct_e = tk.Entry(self.scrollable_frame, font=('Segoe UI', 9), justify='center',
                              bg='#FEF9E7', fg='#7D6608', relief='solid', bd=1)
        if disc_pct:
            disc_pct_e.insert(0, str(disc_pct))
        disc_pct_e.grid(row=row_idx, column=6, sticky='nsew', padx=1, pady=1)

        # 7. Discount Value (Light yellow #FEF9E7)
        disc_val_e = tk.Entry(self.scrollable_frame, font=('Segoe UI', 9), justify='center',
                              bg='#FEF9E7', fg='#7D6608', relief='solid', bd=1)
        if disc_val and str(disc_val) != "0":
            disc_val_e.insert(0, str(disc_val))
        disc_val_e.grid(row=row_idx, column=7, sticky='nsew', padx=1, pady=1)

        # 8. Net Total (Light green #E8F8F5)
        net_lbl = tk.Label(self.scrollable_frame, font=('Segoe UI', 9, 'bold'),
                           bg='#E8F8F5', fg='#1E8449', relief='solid', bd=1, text="")
        net_lbl.grid(row=row_idx, column=8, sticky='nsew', padx=1, pady=1)

        row_dict = {
            'num_lbl': lbl_num,
            'desc': desc_e,
            'unit': unit_e,
            'qty': qty_e,
            'price': price_e,
            'subtotal': subtotal_lbl,
            'disc_pct': disc_pct_e,
            'disc_val': disc_val_e,
            'net': net_lbl
        }
        self.rows.append(row_dict)

        # Calculations
        def calc(event=None, origin=None):
            try:
                q = float(qty_e.get().strip() or 0)
            except ValueError:
                q = 0.0
            try:
                p = float(price_e.get().strip() or 0)
            except ValueError:
                p = 0.0
            
            sub = q * p
            subtotal_lbl.config(text=f"{sub:,.2f}" if sub > 0 else "")

            d_val = 0.0
            if origin == 'pct':
                try:
                    dp = float(disc_pct_e.get().strip() or 0)
                    d_val = sub * (dp / 100.0)
                    disc_val_e.delete(0, 'end')
                    if d_val > 0:
                        disc_val_e.insert(0, f"{d_val:.2f}".rstrip('0').rstrip('.'))
                except ValueError:
                    pass
            else:
                try:
                    d_val = float(disc_val_e.get().strip() or 0)
                    if origin == 'val' and sub > 0:
                        dp = (d_val / sub) * 100.0
                        disc_pct_e.delete(0, 'end')
                        if dp > 0:
                            disc_pct_e.insert(0, f"{dp:.1f}".rstrip('0').rstrip('.'))
                except ValueError:
                    d_val = 0.0

            net = max(0.0, sub - d_val)
            net_lbl.config(text=f"{net:,.2f}" if net > 0 else "")

        qty_e.bind('<KeyRelease>', lambda e: calc(e, 'qty_price'))
        price_e.bind('<KeyRelease>', lambda e: calc(e, 'qty_price'))
        disc_pct_e.bind('<KeyRelease>', lambda e: calc(e, 'pct'))
        disc_val_e.bind('<KeyRelease>', lambda e: calc(e, 'val'))

        # Keyboard Navigation
        desc_e.bind('<Return>', lambda e: unit_e.focus_set())
        unit_e.bind('<Return>', lambda e: qty_e.focus_set())
        qty_e.bind('<Return>', lambda e: price_e.focus_set())
        price_e.bind('<Return>', lambda e: disc_pct_e.focus_set())
        disc_pct_e.bind('<Return>', lambda e: disc_val_e.focus_set())
        
        def on_last_enter(e):
            curr = row_dict
            idx = self.rows.index(curr)
            if idx < len(self.rows) - 1:
                self.rows[idx + 1]['desc'].focus_set()
            else:
                self.add_row()
                self.rows[-1]['desc'].focus_set()

        disc_val_e.bind('<Return>', on_last_enter)

        calc()

    def paste_from_excel(self):
        try:
            clip = self.clipboard_get()
            if not clip:
                return
        except Exception:
            messagebox.showwarning("تنبيه", "⚠️ الحافظة لا تحتوي على نصوص منسوخة", parent=self)
            return

        lines = [line.strip() for line in clip.replace('\r\n', '\n').replace('\r', '\n').split('\n') if line.strip()]
        if not lines:
            return

        row_cursor = 0
        for line in lines:
            parts = line.split('\t') if '\t' in line else line.split(',')
            parts = [p.strip() for p in parts]
            if not parts or not parts[0]:
                continue
            
            # Find next row to populate
            while row_cursor < len(self.rows) and self.rows[row_cursor]['desc'].get().strip():
                row_cursor += 1
            if row_cursor >= len(self.rows):
                self.add_row()
            
            r = self.rows[row_cursor]
            r['desc'].delete(0, 'end')
            r['desc'].insert(0, parts[0])
            
            if len(parts) >= 2 and parts[1].replace('.', '', 1).isdigit():
                r['qty'].delete(0, 'end')
                r['qty'].insert(0, parts[1])
            if len(parts) >= 3 and parts[2].replace('.', '', 1).isdigit():
                r['price'].delete(0, 'end')
                r['price'].insert(0, parts[2])
            if len(parts) >= 4 and parts[3].replace('.', '', 1).isdigit():
                r['disc_val'].delete(0, 'end')
                r['disc_val'].insert(0, parts[3])
                
            # trigger calculation
            r['qty'].event_generate('<KeyRelease>')
            row_cursor += 1

        messagebox.showinfo("نجاح", f"✅ تم استيراد {len(lines)} سطر بنجاح في الجدول!", parent=self)

    def save_and_close(self):
        items = []
        for r in self.rows:
            desc = r['desc'].get().strip()
            if not desc:
                continue
            unit = r['unit'].get().strip() or "قطعة"
            try:
                qty = float(r['qty'].get().strip() or 0)
            except ValueError:
                qty = 1.0
            try:
                price = float(r['price'].get().strip() or 0)
            except ValueError:
                price = 0.0
            try:
                disc_val = float(r['disc_val'].get().strip() or 0)
            except ValueError:
                disc_val = 0.0
            try:
                disc_pct = float(r['disc_pct'].get().strip() or 0)
            except ValueError:
                disc_pct = 0.0

            if qty <= 0:
                qty = 1.0

            subtotal = qty * price
            if disc_val == 0.0 and disc_pct > 0:
                disc_val = subtotal * (disc_pct / 100.0)
            if subtotal > 0 and disc_pct == 0.0 and disc_val > 0:
                disc_pct = (disc_val / subtotal) * 100.0

            net = max(0.0, subtotal - disc_val)

            items.append({
                'description': desc,
                'name': desc,
                'unit': unit,
                'quantity': qty,
                'price': price,
                'unit_price': price,
                'subtotal': subtotal,
                'discount_pct': disc_pct,
                'discount_val': disc_val,
                'total': net
            })

        if not items:
            messagebox.showwarning("تنبيه", "⚠️ يرجى إدخال صنف واحد على الأقل يحتوي على بيان وسعر", parent=self)
            return

        self.callback(items)
        self.destroy()


class InvoiceDialog:
    def __init__(self, parent, db, status_callback, refresh_callback, invoice_id=None, view_only=False, is_quote=False):
        self.parent = parent
        self.db = db
        self.status_callback = status_callback
        self.refresh_callback = refresh_callback
        self.invoice_id = invoice_id
        self.view_only = view_only
        self.is_quote = is_quote
        self.items = []
        
        self.window = tk.Toplevel(parent)
        if self.is_quote:
            w_title = "عرض سعر جديد" if not invoice_id else ("معاينة عرض السعر" if view_only else f"تعديل عرض السعر #{invoice_id}")
        else:
            w_title = "فاتورة جديدة" if not invoice_id else ("عرض الفاتورة" if view_only else f"تعديل الفاتورة #{invoice_id}")
        self.window.title(w_title)
        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        w = min(1640, max(1300, screen_w - 50))
        h = min(990, max(750, screen_h - 65))
        x = max(0, (screen_w - w) // 2)
        y = max(5, (screen_h - h - 40) // 2)
        self.window.geometry(f"{w}x{h}+{x}+{y}")
        self.window.minsize(1080, 600)
        self.window.resizable(True, True)
        self.window.transient(parent)
        self.window.grab_set()
        
        # إنشاء ScrollArea للنافذة
        self.create_scrollable_content()
        
        self.setup_ui()
        
        if invoice_id:
            self.load_invoice_data()
    
    def create_scrollable_content(self):
        """إنشاء محتوى قابل للتمرير"""
        # إنشاء إطار رئيسي للتمرير
        self.scroll_frame = tk.Frame(self.window, bg='#F5F6FA')
        self.scroll_frame.pack(fill='both', expand=True)
        
        # إنشاء Canvas للتمرير
        self.canvas = tk.Canvas(self.scroll_frame, bg='#F5F6FA')
        self.canvas.pack(side='left', fill='both', expand=True)
        
        # إنشاء شريط تمرير عمودي
        scrollbar = ttk.Scrollbar(self.scroll_frame, orient='vertical', command=self.canvas.yview)
        scrollbar.pack(side='right', fill='y')
        
        # ربط Canvas مع شريط التمرير
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # إنشاء إطار المحتوى الفعلي
        self.content_frame = tk.Frame(self.canvas, bg='#F5F6FA')
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor='nw')
        
        # تحديث حجم التمرير عند تغيير المحتوى
        self.content_frame.bind('<Configure>', self.on_frame_configure)
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        # تفعيل التمرير بالعجلة من أي مكان في النافذة
        self.window.bind('<MouseWheel>', self.on_mousewheel)
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
    
    def setup_ui(self):
        # استخدام tk.Frame بدلاً من ttk.Frame لضمان ظهور الأزرار
        main_frame = tk.Frame(self.content_frame, bg='#F5F6FA')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # معلومات الفاتورة / عرض السعر
        info_frame = ttk.LabelFrame(main_frame, text="معلومات عرض السعر" if self.is_quote else "معلومات الفاتورة")
        info_frame.pack(fill='x', pady=(0, 10))
        
        # رقم الفاتورة / عرض السعر والتاريخ
        num_lbl_text = "رقم عرض السعر:" if self.is_quote else "رقم الفاتورة:"
        ttk.Label(info_frame, text=num_lbl_text, font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=8, pady=8)
        self.invoice_number = ttk.Entry(info_frame, width=22, font=('Segoe UI', 10))
        self.invoice_number.grid(row=0, column=1, padx=8, pady=8, ipady=4)
        if self.is_quote:
            try:
                max_quote_num = 0
                rows = self.db.execute_query("SELECT quote_number FROM price_quotes")
                for r in rows:
                    if r and r[0]:
                        val = str(r[0]).strip()
                        m = re.findall(r'\d+', val)
                        if m:
                            try:
                                num = int(m[-1])
                                if num > max_quote_num:
                                    max_quote_num = num
                            except:
                                pass
                next_num = max_quote_num + 1
                self.invoice_number.insert(0, f"{next_num:03d}")
            except Exception:
                self.invoice_number.insert(0, "001")
        else:
            try:
                max_inv_num = 0
                rows = self.db.execute_query("SELECT invoice_number FROM invoices")
                for r in rows:
                    if r and r[0]:
                        val = str(r[0]).strip()
                        m = re.findall(r'\d+', val)
                        if m:
                            try:
                                num = int(m[-1])
                                if num > max_inv_num:
                                    max_inv_num = num
                            except:
                                pass
                next_num = max_inv_num + 1
                self.invoice_number.insert(0, f"{next_num:03d}")
            except Exception:
                self.invoice_number.insert(0, f"{len(self.db.execute_query('SELECT id FROM invoices'))+1:03d}")
        
        ttk.Label(info_frame, text="التاريخ:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=2, sticky='w', padx=8, pady=8)
        try:
            from tkcalendar import DateEntry
            self.date_entry = DateEntry(
                info_frame, width=16, font=('Segoe UI', 10, 'bold'),
                date_pattern='yyyy-mm-dd', background='#2980B9', foreground='white',
                headersbackground='#1F3A52', headersforeground='white',
                selectbackground='#27AE60', borderwidth=1
            )
        except Exception:
            self.date_entry = ttk.Entry(info_frame, width=18, font=('Segoe UI', 10))
            self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.date_entry.grid(row=0, column=3, padx=8, pady=8, ipady=4)
        
        # العميل - حجم مناسب مع بحث فوري وأداة بحث سريعة للعملاء والمشاريع
        ttk.Label(info_frame, text="العميل:", font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, sticky='w', padx=8, pady=8)
        self.customer_var = tk.StringVar()
        
        cust_box = tk.Frame(info_frame)
        cust_box.grid(row=1, column=1, columnspan=3, padx=8, pady=8, sticky='ew')
        
        self.customer_combo = SearchableDropdown(cust_box, textvariable=self.customer_var, font=('Segoe UI', 10))
        self.customer_combo.pack(side='left', fill='x', expand=True, ipady=4)
        
        self.search_cust_proj_btn = tk.Button(
            cust_box, text="🔍 بحث / اختيار عميل ومشاريع", font=('Segoe UI', 9, 'bold'),
            bg='#2980B9', fg='white', relief=tk.FLAT, cursor='hand2', padx=10, pady=4,
            command=self.open_customer_project_selector
        )
        self.search_cust_proj_btn.pack(side='right', padx=(8, 0))
        
        self.selected_customer_id = None
        self.selected_project_id = None
        self.load_customers()
        
        # عناصر الفاتورة / عرض السعر
        items_frame = ttk.LabelFrame(main_frame, text="عناصر وبنود عرض السعر" if self.is_quote else "عناصر الفاتورة")
        items_frame.pack(fill='both', expand=False, pady=(0, 5))
        
        # جدول العناصر (8 أعمدة تشمل إجمالي الصف والخصومات والصافي)
        columns = ('description', 'unit', 'quantity', 'price', 'subtotal', 'discount_pct', 'discount_val', 'total')
        self.items_tree = ttk.Treeview(items_frame, columns=columns, show='headings', height=7)
        
        self.items_tree.heading('description', text='الوصف')
        self.items_tree.heading('unit', text='الوحدة')
        self.items_tree.heading('quantity', text='الكمية')
        self.items_tree.heading('price', text='السعر')
        self.items_tree.heading('subtotal', text='إجمالي الصف')
        self.items_tree.heading('discount_pct', text='خصم %')
        self.items_tree.heading('discount_val', text='خصم مبلغ')
        self.items_tree.heading('total', text='الصافي')
        
        self.items_tree.column('description', width=260, anchor='w')
        self.items_tree.column('unit', width=70, anchor='center')
        self.items_tree.column('quantity', width=70, anchor='center')
        self.items_tree.column('price', width=80, anchor='center')
        self.items_tree.column('subtotal', width=90, anchor='center')
        self.items_tree.column('discount_pct', width=70, anchor='center')
        self.items_tree.column('discount_val', width=80, anchor='center')
        self.items_tree.column('total', width=90, anchor='center')
        
        self.items_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        # أزرار التحكم في العناصر
        self.items_buttons = ttk.Frame(items_frame)
        self.items_buttons.pack(side='right', fill='y', padx=5, pady=5)
        
        self.add_item_button = ttk.Button(self.items_buttons, text="➕ إضافة", command=self.add_item)
        self.add_item_button.pack(pady=2)
        self.edit_item_button = ttk.Button(self.items_buttons, text="✏️ تعديل", command=self.edit_item)
        self.edit_item_button.pack(pady=2)
        self.delete_item_button = ttk.Button(self.items_buttons, text="🗑️ حذف", command=self.delete_item)
        self.delete_item_button.pack(pady=2)
        
        # إضافة عنصر - حجم مناسب
        add_item_frame = ttk.LabelFrame(main_frame, text="إضافة عنصر جديد")
        add_item_frame.pack(fill='x', pady=(0, 0))
        
        # Row 0: الوصف، الوحدة، زر الأصناف المتعددة
        ttk.Label(add_item_frame, text="الوصف:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=8, pady=6)
        self.item_desc = ttk.Entry(add_item_frame, width=32, font=('Segoe UI', 10), justify='right')
        self.item_desc.grid(row=0, column=1, padx=8, pady=6, ipady=3)
        
        ttk.Label(add_item_frame, text="الوحدة:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=2, sticky='w', padx=8, pady=6)
        self.item_unit = ttk.Entry(add_item_frame, width=12, font=('Segoe UI', 10), justify='right')
        self.item_unit.grid(row=0, column=3, padx=8, pady=6, ipady=3)
        self.item_unit.insert(0, "")
        
        self.batch_items_btn = tk.Button(add_item_frame, text="📋 إدخال عدة أصناف معاً", command=self.open_batch_items_dialog,
                                         bg='#34495E', fg='white', font=('Segoe UI', 10, 'bold'), cursor='hand2', relief=tk.FLAT, padx=12, pady=5)
        self.batch_items_btn.grid(row=0, column=4, columnspan=2, padx=8, pady=6, sticky='e')

        # Row 1: الكمية، السعر، إجمالي الصف
        ttk.Label(add_item_frame, text="الكمية:", font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, sticky='w', padx=8, pady=6)
        self.item_qty = ttk.Entry(add_item_frame, width=15, font=('Segoe UI', 10))
        self.item_qty.grid(row=1, column=1, padx=8, pady=6, sticky='w', ipady=3)
        
        ttk.Label(add_item_frame, text="السعر:", font=('Segoe UI', 10, 'bold')).grid(row=1, column=2, sticky='w', padx=8, pady=6)
        self.item_price = ttk.Entry(add_item_frame, width=12, font=('Segoe UI', 10))
        self.item_price.grid(row=1, column=3, padx=8, pady=6, sticky='w', ipady=3)
        
        subtotal_frame = tk.Frame(add_item_frame)
        subtotal_frame.grid(row=1, column=4, padx=8, pady=6, sticky='w')
        ttk.Label(subtotal_frame, text="إجمالي الصف:", font=('Segoe UI', 10, 'bold')).pack(side='left', padx=(0, 4))
        self.item_subtotal_lbl = tk.Label(subtotal_frame, text="0.00", font=('Segoe UI', 10, 'bold'), fg='#1B4F72', bg='#EBF5FB', padx=8, pady=2, relief=tk.SOLID, bd=1)
        self.item_subtotal_lbl.pack(side='left')

        # Row 2: خصم %، خصم مبلغ، الصافي، زر إضافة للفاتورة
        ttk.Label(add_item_frame, text="خصم %:", font=('Segoe UI', 10, 'bold')).grid(row=2, column=0, sticky='w', padx=8, pady=6)
        self.item_disc_pct = ttk.Entry(add_item_frame, width=15, font=('Segoe UI', 10))
        self.item_disc_pct.grid(row=2, column=1, padx=8, pady=6, sticky='w', ipady=3)
        
        ttk.Label(add_item_frame, text="خصم مبلغ:", font=('Segoe UI', 10, 'bold')).grid(row=2, column=2, sticky='w', padx=8, pady=6)
        self.item_disc_val = ttk.Entry(add_item_frame, width=12, font=('Segoe UI', 10))
        self.item_disc_val.grid(row=2, column=3, padx=8, pady=6, sticky='w', ipady=3)
        
        net_frame = tk.Frame(add_item_frame)
        net_frame.grid(row=2, column=4, padx=8, pady=6, sticky='w')
        ttk.Label(net_frame, text="الصافي:", font=('Segoe UI', 10, 'bold')).pack(side='left', padx=(0, 4))
        self.item_net_lbl = tk.Label(net_frame, text="0.00", font=('Segoe UI', 11, 'bold'), fg='#145A32', bg='#EAFAF1', padx=8, pady=2, relief=tk.SOLID, bd=1)
        self.item_net_lbl.pack(side='left')

        self.add_to_invoice_button = tk.Button(add_item_frame, text="➕ إضافة للفاتورة (Enter)", command=self.add_item_to_invoice,
                                               bg='#27AE60', fg='white', font=('Segoe UI', 10, 'bold'), cursor='hand2', relief=tk.FLAT, padx=12, pady=5)
        self.add_to_invoice_button.grid(row=2, column=5, padx=8, pady=6, sticky='e')
        
        # ربط الحساب التلقائي للخصم والمجاميع
        self._single_item_updating = False
        self.item_qty.bind('<KeyRelease>', lambda e: self._calc_single_item('qty_price'))
        self.item_price.bind('<KeyRelease>', lambda e: self._calc_single_item('qty_price'))
        self.item_disc_pct.bind('<KeyRelease>', lambda e: self._calc_single_item('pct'))
        self.item_disc_val.bind('<KeyRelease>', lambda e: self._calc_single_item('val'))

        # ربط مفتاح Enter للتنقل السلس والسريع بين الحقول وإضافة الصنف مباشرة
        self.item_desc.bind('<Return>', lambda e: self.item_unit.focus_set())
        self.item_unit.bind('<Return>', lambda e: self.item_qty.focus_set())
        self.item_qty.bind('<Return>', lambda e: self.item_price.focus_set())
        self.item_price.bind('<Return>', lambda e: self.item_disc_pct.focus_set())
        self.item_disc_pct.bind('<Return>', lambda e: self.item_disc_val.focus_set())
        self.item_disc_val.bind('<Return>', lambda e: self.add_item_to_invoice())
        
        # المجاميع - حجم مناسب
        totals_frame = ttk.LabelFrame(main_frame, text="المجاميع")
        totals_frame.pack(fill='x', pady=(0, 0))
        
        ttk.Label(totals_frame, text="المجموع:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w', padx=8, pady=8)
        self.subtotal_label = ttk.Label(totals_frame, text="0.00", font=('Segoe UI', 10))
        self.subtotal_label.grid(row=0, column=1, sticky='w', padx=8, pady=8)
        
        ttk.Label(totals_frame, text="الضريبة (15%):", font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, sticky='w', padx=8, pady=8)
        self.tax_label = ttk.Label(totals_frame, text="0.00", font=('Segoe UI', 10))
        self.tax_label.grid(row=1, column=1, sticky='w', padx=8, pady=8)
        
        ttk.Label(totals_frame, text="الخصم:", font=('Segoe UI', 10, 'bold')).grid(row=2, column=0, sticky='w', padx=8, pady=8)
        self.discount_entry = ttk.Entry(totals_frame, width=18, font=('Segoe UI', 10))
        self.discount_entry.grid(row=2, column=1, sticky='w', padx=8, pady=8, ipady=4)
        self.discount_entry.insert(0, "0")
        self.discount_entry.bind('<KeyRelease>', self.update_totals)
        
        ttk.Label(totals_frame, text="الإجمالي النهائي:", font=('Segoe UI', 11, 'bold')).grid(row=3, column=0, sticky='w', padx=8, pady=8)
        self.total_label = ttk.Label(totals_frame, text="0.00", font=('Segoe UI', 12, 'bold'))
        self.total_label.grid(row=3, column=1, sticky='w', padx=8, pady=8)
        
        # الأزرار - واضحة ومنظمة بشكل أفضل - في بطاقة منفصلة
        buttons_card = tk.Frame(main_frame, bg='white', relief=tk.RAISED, bd=2)
        buttons_card.pack(fill='x', pady=(15, 25))
        
        buttons_frame = tk.Frame(buttons_card, bg='white')
        buttons_frame.pack(fill='x', padx=20, pady=15)
        
        # أزرار على اليسار
        left_buttons = tk.Frame(buttons_frame, bg='white')
        left_buttons.pack(side='left')
        
        save_text = "💾 حفظ عرض السعر" if self.is_quote else "💾 حفظ"
        self.save_btn = tk.Button(left_buttons, text=save_text, command=lambda: self.save_invoice(close_window=True),
                             bg='#27AE60', fg='white', font=('Segoe UI', 11, 'bold'),
                             relief=tk.FLAT, padx=20, pady=12, cursor='hand2')
        self.save_btn.pack(side='left', padx=8)
        
        self.download_btn = tk.Button(left_buttons, text="📥 تنزيل", command=self.download_invoice,
                             bg='#3498DB', fg='white', font=('Segoe UI', 11, 'bold'),
                             relief=tk.FLAT, padx=20, pady=12, cursor='hand2')
        self.download_btn.pack(side='left', padx=8)

        self.print_btn = tk.Button(left_buttons, text="🖨️ طباعة", command=self.direct_print_invoice,
                             bg='#1A5276', fg='white', font=('Segoe UI', 11, 'bold'),
                             relief=tk.FLAT, padx=20, pady=12, cursor='hand2')
        self.print_btn.pack(side='left', padx=8)

        self.preview_btn = tk.Button(left_buttons, text="👁️ عرض", command=self.preview_invoice,
                             bg='#F39C12', fg='white', font=('Segoe UI', 11, 'bold'),
                             relief=tk.FLAT, padx=20, pady=12, cursor='hand2')
        self.preview_btn.pack(side='left', padx=8)
        
        # أزرار على اليمين
        right_buttons = tk.Frame(buttons_frame, bg='white')
        right_buttons.pack(side='right')
        
        self.cancel_btn = tk.Button(right_buttons, text="❌ إلغاء", command=self.window.destroy,
                              bg='#95A5A6', fg='white', font=('Segoe UI', 11, 'bold'),
                              relief=tk.FLAT, padx=20, pady=12, cursor='hand2')
        self.cancel_btn.pack(side='right', padx=8)

        self.bind_keyboard_shortcuts()

        if self.view_only:
            self.set_view_mode()
    
    def bind_keyboard_shortcuts(self):
        self.window.bind('<Control-p>', self.handle_print_shortcut)
        self.window.bind('<Control-P>', self.handle_print_shortcut)

    def handle_print_shortcut(self, event=None):
        self.print_invoice()
        return 'break'

    def set_view_mode(self):
        widgets = [
            ('invoice_number', 'readonly'),
            ('date_entry', 'readonly'),
            ('customer_combo', 'readonly'),
            ('item_desc', 'readonly'),
            ('item_unit', 'readonly'),
            ('item_qty', 'readonly'),
            ('item_price', 'readonly'),
            ('item_disc_pct', 'readonly'),
            ('item_disc_val', 'readonly'),
            ('discount_entry', 'readonly')
        ]

        for attr_name, state in widgets:
            widget = getattr(self, attr_name, None)
            set_widget_state(widget, state)

        if hasattr(self, 'items_tree'):
            self.items_tree.bind('<Button-1>', lambda e: 'break')
            self.items_tree.bind('<Double-1>', lambda e: 'break')
            self.items_tree.bind('<Key>', lambda e: 'break')

        if hasattr(self, 'items_buttons'):
            for child in self.items_buttons.winfo_children():
                set_widget_state(child, 'disabled')

        if hasattr(self, 'add_to_invoice_button'):
            set_widget_state(self.add_to_invoice_button, 'disabled')

        self.save_btn.config(text='إغلاق', command=self.window.destroy, bg='#95A5A6')
        if hasattr(self, 'download_btn'):
            self.download_btn.config(text='📥 تنزيل', command=self.download_invoice, bg='#3498DB')
        if hasattr(self, 'print_btn'):
            self.print_btn.config(text='🖨️ طباعة', command=self.direct_print_invoice, bg='#1A5276')
        self.preview_btn.config(text='عرض PDF', command=self.preview_invoice, bg='#F39C12')
        self.cancel_btn.config(text='إغلاق', command=self.window.destroy, bg='#95A5A6')

    def load_customers(self):
        try:
            customers = self.db.execute_query("SELECT id, name FROM customers ORDER BY name")
        except Exception:
            customers = []
        try:
            projects = self.db.execute_query("""
                SELECT p.id, p.name, p.customer_id, c.name as customer_name
                FROM projects p
                LEFT JOIN customers c ON p.customer_id = c.id
                ORDER BY p.name
            """)
        except Exception:
            projects = []
            
        customer_list = []
        # إضافة العملاء
        for c in customers:
            customer_list.append(f"{c[0]} - {c[1]}")
            
        # إضافة المشاريع مع اسم العميل المرتبط بها
        for p in projects:
            p_id, p_name, c_id, c_name = p
            c_tag = f" (العميل: {c_name})" if c_name else ""
            customer_list.append(f"مشروع: {p_name}{c_tag} [ID:{p_id}]")
            
        self.customer_combo.set_values(customer_list)

    def open_customer_project_selector(self):
        CustomerProjectSelectorDialog(self.window, self.db, self.on_customer_project_selected, self.status_callback)

    def on_customer_project_selected(self, cust_tuple, proj_tuple):
        c_id = cust_tuple[0] if cust_tuple else None
        c_name = cust_tuple[1] if cust_tuple else ""
        p_id = proj_tuple[0] if proj_tuple else None
        p_name = proj_tuple[1] if proj_tuple else ""
        
        self.selected_customer_id = c_id
        self.selected_project_id = p_id
        self.load_customers()
        
        if c_name and p_name:
            self.customer_var.set(f"{c_id} - {c_name} | مشروع: {p_name}")
        elif p_name:
            self.customer_var.set(f"مشروع: {p_name} [ID:{p_id}]")
        elif c_name:
            self.customer_var.set(f"{c_id} - {c_name}")
    
    def open_batch_items_dialog(self):
        """فتح نافذة إدخال عدة أصناف دفعة واحدة"""
        BatchInvoiceItemsDialog(self.window, self.add_batch_items)

    def add_batch_items(self, new_items):
        """إضافة قائمة أصناف دفعة واحدة للفاتورة"""
        if not new_items:
            return
        for item in new_items:
            self.items.append(item)
            
        total_items_disc = sum(float(it.get('discount_val', 0.0) or 0) for it in self.items)
        if total_items_disc > 0:
            self.discount_entry.delete(0, 'end')
            self.discount_entry.insert(0, f"{total_items_disc:.2f}".rstrip('0').rstrip('.'))
            
        self.update_items_tree()
        self.update_totals()
        self.item_desc.focus_set()

    def _calc_single_item(self, trigger='qty_price', event=None):
        if getattr(self, '_single_item_updating', False):
            return
        self._single_item_updating = True
        try:
            try:
                q = float(self.item_qty.get().strip() or 0)
            except ValueError:
                q = 0.0
            try:
                p = float(self.item_price.get().strip() or 0)
            except ValueError:
                p = 0.0
            
            subtotal = q * p
            self.item_subtotal_lbl.config(text=f"{subtotal:.2f}")
            
            dp_str = self.item_disc_pct.get().strip()
            dv_str = self.item_disc_val.get().strip()
            
            disc_val = 0.0
            disc_pct = 0.0
            
            if trigger == 'val':
                try:
                    disc_val = float(dv_str or 0)
                    if subtotal > 0 and disc_val > 0:
                        disc_pct = (disc_val / subtotal) * 100.0
                        self.item_disc_pct.delete(0, 'end')
                        self.item_disc_pct.insert(0, f"{disc_pct:.2f}".rstrip('0').rstrip('.'))
                    elif not dv_str:
                        self.item_disc_pct.delete(0, 'end')
                except ValueError:
                    pass
            elif trigger == 'pct':
                try:
                    disc_pct = float(dp_str or 0)
                    if subtotal > 0 and disc_pct > 0:
                        disc_val = subtotal * (disc_pct / 100.0)
                        self.item_disc_val.delete(0, 'end')
                        self.item_disc_val.insert(0, f"{disc_val:.2f}".rstrip('0').rstrip('.'))
                    elif not dp_str:
                        self.item_disc_val.delete(0, 'end')
                except ValueError:
                    pass
            else: # 'qty_price'
                if dp_str:
                    try:
                        disc_pct = float(dp_str or 0)
                        disc_val = subtotal * (disc_pct / 100.0)
                        self.item_disc_val.delete(0, 'end')
                        self.item_disc_val.insert(0, f"{disc_val:.2f}".rstrip('0').rstrip('.'))
                    except ValueError:
                        pass
                elif dv_str:
                    try:
                        disc_val = float(dv_str or 0)
                        if subtotal > 0 and disc_val > 0:
                            disc_pct = (disc_val / subtotal) * 100.0
                            self.item_disc_pct.delete(0, 'end')
                            self.item_disc_pct.insert(0, f"{disc_pct:.2f}".rstrip('0').rstrip('.'))
                    except ValueError:
                        pass
            
            net = max(0.0, subtotal - disc_val)
            self.item_net_lbl.config(text=f"{net:.2f}")
        finally:
            self._single_item_updating = False

    def add_item_to_invoice(self, silent=False):
        desc = self.item_desc.get().strip()
        unit = self.item_unit.get().strip()
        qty = self.item_qty.get().strip()
        price = self.item_price.get().strip()
        dp_str = self.item_disc_pct.get().strip()
        dv_str = self.item_disc_val.get().strip()
        
        if not desc and not qty and not price:
            if not silent:
                self.item_desc.focus_set()
            return False

        if not all([desc, qty, price]):
            if not silent:
                messagebox.showwarning("تحذير", "⚠️ يرجى ملء الوصف والكمية والسعر")
                if not desc:
                    self.item_desc.focus_set()
                elif not qty:
                    self.item_qty.focus_set()
                else:
                    self.item_price.focus_set()
            return False
        
        try:
            qty = float(qty)
            price = float(price)
            if qty <= 0:
                if not silent:
                    messagebox.showwarning("تحذير", "⚠️ الكمية يجب أن تكون أكبر من الصفر")
                    self.item_qty.focus_set()
                return False
            
            subtotal = qty * price
            disc_val = 0.0
            disc_pct = 0.0
            
            if dv_str:
                try:
                    disc_val = float(dv_str)
                    disc_pct = (disc_val / subtotal * 100.0) if subtotal > 0 else 0.0
                except ValueError:
                    disc_val = 0.0
            elif dp_str:
                try:
                    disc_pct = float(dp_str)
                    disc_val = subtotal * (disc_pct / 100.0)
                except ValueError:
                    disc_pct = 0.0
                    
            net = max(0.0, subtotal - disc_val)
            
            item = {
                'description': desc,
                'name': desc,
                'unit': unit,
                'quantity': qty,
                'price': price,
                'unit_price': price,
                'subtotal': subtotal,
                'discount_pct': disc_pct,
                'discount_val': disc_val,
                'total': net
            }
            
            self.items.append(item)
            
            total_items_disc = sum(float(it.get('discount_val', 0.0) or 0) for it in self.items)
            if total_items_disc > 0:
                self.discount_entry.delete(0, 'end')
                self.discount_entry.insert(0, f"{total_items_disc:.2f}".rstrip('0').rstrip('.'))
                
            self.update_items_tree()
            self.update_totals()
            
            # مسح الحقول للبدء مباشرة في الصنف التالي
            self.item_desc.delete(0, 'end')
            self.item_qty.delete(0, 'end')
            self.item_price.delete(0, 'end')
            self.item_disc_pct.delete(0, 'end')
            self.item_disc_val.delete(0, 'end')
            self.item_subtotal_lbl.config(text="0.00")
            self.item_net_lbl.config(text="0.00")
            self.item_desc.focus_set()
            return True
            
        except ValueError:
            if not silent:
                messagebox.showerror("خطأ", "❌ يرجى إدخال قيم رقمية صحيحة للكمية والسعر")
            return False
    
    def update_items_tree(self):
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        
        for item in self.items:
            qty = float(item.get('quantity', 0))
            price = float(item.get('price', item.get('unit_price', 0)))
            subtotal = float(item.get('subtotal', qty * price))
            disc_pct = float(item.get('discount_pct', 0.0))
            disc_val = float(item.get('discount_val', 0.0))
            total = float(item.get('total', subtotal - disc_val))
            
            self.items_tree.insert('', 'end', values=(
                item.get('description', item.get('name', '')),
                item.get('unit', ''),
                qty,
                f"{price:.2f}",
                f"{subtotal:.2f}",
                f"{disc_pct:.2f}%" if disc_pct > 0 else "0%",
                f"{disc_val:.2f}",
                f"{total:.2f}"
            ))
    
    def update_totals(self, event=None):
        subtotal = sum(float(item.get('subtotal', item.get('quantity', 0) * item.get('price', item.get('unit_price', 0)))) for item in self.items)
        try:
            discount = float(self.discount_entry.get() or 0)
        except:
            discount = 0.0
        net = max(0.0, subtotal - discount)
        tax = net * 0.15
        grand_total = net + tax
        
        self.subtotal_label.config(text=f"{subtotal:.2f}")
        self.tax_label.config(text=f"{tax:.2f}")
        self.total_label.config(text=f"{grand_total:.2f}")
    
    def add_item(self):
        if self.item_desc.get().strip() and self.item_qty.get().strip() and self.item_price.get().strip():
            self.add_item_to_invoice()
        else:
            self.item_desc.focus_set()
    
    def edit_item(self):
        selected = self.items_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عنصر للتعديل")
            return
        
        index = self.items_tree.index(selected[0])
        item = self.items[index]
        
        self.item_desc.delete(0, 'end')
        self.item_desc.insert(0, item.get('description', item.get('name', '')))
        self.item_unit.delete(0, 'end')
        self.item_unit.insert(0, item.get('unit', ''))
        self.item_qty.delete(0, 'end')
        self.item_qty.insert(0, str(item.get('quantity', '')))
        self.item_price.delete(0, 'end')
        self.item_price.insert(0, str(item.get('price', item.get('unit_price', ''))))
        
        self.item_disc_pct.delete(0, 'end')
        dp = item.get('discount_pct', 0.0)
        if dp > 0:
            self.item_disc_pct.insert(0, f"{dp:.2f}".rstrip('0').rstrip('.'))
            
        self.item_disc_val.delete(0, 'end')
        dv = item.get('discount_val', 0.0)
        if dv > 0:
            self.item_disc_val.insert(0, f"{dv:.2f}".rstrip('0').rstrip('.'))
            
        self._calc_single_item('qty_price')
        
        # حذف العنصر القديم
        del self.items[index]
        total_items_disc = sum(float(it.get('discount_val', 0.0) or 0) for it in self.items)
        self.discount_entry.delete(0, 'end')
        self.discount_entry.insert(0, f"{total_items_disc:.2f}".rstrip('0').rstrip('.') if total_items_disc > 0 else "0")
        self.update_items_tree()
        self.update_totals()
    
    def delete_item(self):
        selected = self.items_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عنصر للحذف")
            return
        
        index = self.items_tree.index(selected[0])
        del self.items[index]
        total_items_disc = sum(float(it.get('discount_val', 0.0) or 0) for it in self.items)
        self.discount_entry.delete(0, 'end')
        self.discount_entry.insert(0, f"{total_items_disc:.2f}".rstrip('0').rstrip('.') if total_items_disc > 0 else "0")
        self.update_items_tree()
        self.update_totals()
    
    def save_invoice(self, close_window=True):
        # التقاط الصنف الأخير تلقائياً إذا كان مكتوباً في الحقول ولم يُضغط على زر الإضافة بعد
        if self.item_desc.get().strip() and (self.item_qty.get().strip() or self.item_price.get().strip()):
            self.add_item_to_invoice(silent=True)
            
        if not self.items:
            messagebox.showwarning("تحذير", "⚠️ يرجى إضافة عناصر للفاتورة")
            return
        
        customer_info = self.customer_var.get().strip()
        if not customer_info:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار العميل")
            return
        
        customer_id = getattr(self, 'selected_customer_id', None)
        project_id = getattr(self, 'selected_project_id', None)
        
        # استخراج العميل والمشروع إن لم يكونا محددين مباشرة
        if not customer_id or not project_id:
            if " | مشروع:" in customer_info:
                parts = customer_info.split(" | مشروع:")
                c_part = parts[0].strip()
                p_part = parts[1].strip()
                try:
                    customer_id = int(c_part.split(' - ')[0])
                except ValueError:
                    pass
                proj_rec = self.db.execute_query("SELECT id, customer_id FROM projects WHERE name = ?", (p_part,))
                if proj_rec:
                    project_id = proj_rec[0][0]
                    if not customer_id and proj_rec[0][1]:
                        customer_id = proj_rec[0][1]
            elif customer_info.startswith("مشروع:") and "[ID:" in customer_info:
                try:
                    p_id_str = customer_info.split("[ID:")[1].split("]")[0]
                    project_id = int(p_id_str)
                    proj_rec = self.db.execute_query("SELECT customer_id FROM projects WHERE id = ?", (project_id,))
                    if proj_rec and proj_rec[0][0]:
                        customer_id = proj_rec[0][0]
                except Exception:
                    pass
            elif " - " in customer_info:
                try:
                    customer_id = int(customer_info.split(' - ')[0])
                except ValueError:
                    pass
                    
        if not customer_id:
            # حاول البحث عن العميل بالاسم
            customer_record = self.db.execute_query("SELECT id FROM customers WHERE name = ?", (customer_info,))
            if customer_record:
                customer_id = customer_record[0][0]
            else:
                # إنشاء عميل جديد تلقائياً
                self.db.execute_query("INSERT INTO customers (name, phone, address, tax_number) VALUES (?, '', '', '')", (customer_info,))
                customer_id = self.db.execute_query("SELECT last_insert_rowid()")[0][0]
                emit_customer_change(customer_id)
        
        invoice_number = self.invoice_number.get()
        date = self.date_entry.get()
        
        subtotal = sum(float(item.get('subtotal', item.get('quantity', 0) * item.get('price', item.get('unit_price', 0)))) for item in self.items)
        try:
            discount = float(self.discount_entry.get() or 0)
        except:
            discount = 0.0
        net = max(0.0, subtotal - discount)
        tax = net * 0.15
        grand_total = net + tax
        
        if self.is_quote:
            quote_number = self.invoice_number.get().strip() or f"QUO-{datetime.now().strftime('%Y%m%d%H%M')}"
            date = self.date_entry.get().strip() if hasattr(self.date_entry, 'get') else datetime.now().strftime('%Y-%m-%d')
            try:
                if self.invoice_id:
                    self.db.execute_query("""
                        UPDATE price_quotes SET 
                        customer_id=?, quote_number=?, date=?, subtotal=?, discount=?, tax=?, grand_total=?, items=?
                        WHERE id=?
                    """, (customer_id, quote_number, date, subtotal, discount, tax, grand_total, json.dumps(self.items), self.invoice_id))
                    self.status_callback(f"✅ تم تحديث عرض السعر #{quote_number}")
                else:
                    self.db.execute_query("""
                        INSERT INTO price_quotes 
                        (customer_id, quote_number, date, valid_until, notes, subtotal, discount, tax, grand_total, items, status, created_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                    """, (customer_id, quote_number, date, date, '', subtotal, discount, tax, grand_total, json.dumps(self.items), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    self.status_callback(f"✅ تم إنشاء عرض السعر #{quote_number} بنجاح")
                
                self.refresh_callback()
                if close_window:
                    messagebox.showinfo("نجاح", f"✅ تم حفظ عرض السعر #{quote_number} بنجاح")
                    self.window.destroy()
                return True
            except Exception as e:
                messagebox.showerror("خطأ", f"❌ فشل في حفظ عرض السعر: {str(e)}")
                return False

        try:
            if self.invoice_id:
                # تعديل فاتورة موجودة
                self.db.execute_query('''
                    UPDATE invoices SET 
                    invoice_number=?, customer_id=?, date=?, items=?, 
                    total=?, tax=?, discount=?, grand_total=?, project_id=?
                    WHERE id=?
                ''', (invoice_number, customer_id, date, json.dumps(self.items),
                      subtotal, tax, discount, grand_total, project_id, self.invoice_id))
                self.status_callback(f"✅ تم تحديث الفاتورة #{invoice_number}")
                
                # تحديث المعاملات المالية والصندوق
                self.db.execute_query('''
                    UPDATE transactions SET amount=?, date=? WHERE description=? AND type='income'
                ''', (grand_total, date, f'فاتورة #{invoice_number}'))
                
                self.db.execute_query('''
                    UPDATE treasury_transactions SET amount=?, date=?, project_id=? WHERE description=? AND type='income'
                ''', (grand_total, date, project_id, f'فاتورة #{invoice_number}'))
                
                # إرسال إشارات التحديث الفوري
                emit_invoice_change(self.invoice_id)
                emit_customer_change(customer_id)
                try:
                    from central_refresh import emit_treasury_change
                    emit_treasury_change()
                except:
                    pass
                
            else:
                # إنشاء فاتورة جديدة
                self.db.execute_query('''
                    INSERT INTO invoices 
                    (invoice_number, customer_id, date, items, total, tax, discount, grand_total, project_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (invoice_number, customer_id, date, json.dumps(self.items),
                      subtotal, tax, discount, grand_total, project_id))
                
                # التقاط المعرف الصحيح للفاتورة
                new_invoice_id = self.db.execute_query("SELECT last_insert_rowid()")[0][0]
                
                # إضافة معاملة مالية
                self.db.execute_query('''
                    INSERT INTO transactions (type, amount, description, date, category)
                    VALUES (?, ?, ?, ?, ?)
                ''', ('income', grand_total, f'فاتورة #{invoice_number}', date, 'الفواتير'))
                
                # إضافة للصندوق (حركة الخزينة) مع ربط المشروع
                self.db.execute_query('''
                    INSERT INTO treasury_transactions (date, type, description, amount, account_name, project_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (date, 'income', f'فاتورة #{invoice_number}', grand_total, 'الصندوق الرئيسي', project_id))
                
                self.status_callback(f"✅ تم إنشاء الفاتورة #{invoice_number} بنجاح")
                
                # إرسال إشارات التحديث الفوري
                emit_invoice_change(new_invoice_id)
                emit_customer_change(customer_id)
                try:
                    from central_refresh import emit_treasury_change
                    emit_treasury_change()
                except:
                    pass
            
            self.refresh_callback()
            
            # إغلاق النافذة عند الحفظ المباشر
            if close_window:
                messagebox.showinfo("نجاح", f"✅ تم حفظ الفاتورة #{invoice_number} بنجاح في البرنامج")
                self.window.destroy()
            
            return True
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حفظ الفاتورة: {str(e)}")
            return False
    
    def load_invoice_data(self):
        if self.is_quote:
            quote = self.db.execute_query("SELECT * FROM price_quotes WHERE id = ?", (self.invoice_id,))
            if quote:
                q = quote[0]
                self.invoice_number.delete(0, 'end')
                self.invoice_number.insert(0, str(q[2] or ''))
                try:
                    self.date_entry.delete(0, 'end')
                    self.date_entry.insert(0, str(q[3] or datetime.now().strftime('%Y-%m-%d')))
                except Exception:
                    pass
                if q[1]:
                    cust = self.db.execute_query("SELECT id, name FROM customers WHERE id = ?", (q[1],))
                    if cust:
                        self.customer_var.set(f"{cust[0][0]} - {cust[0][1]}")
                try:
                    self.items = json.loads(q[10]) if q[10] else []
                except Exception:
                    self.items = []
                self.update_items_tree()
                self.discount_entry.delete(0, 'end')
                self.discount_entry.insert(0, str(q[7] or 0))
                self.update_totals()
            return

        invoice = self.db.execute_query("SELECT * FROM invoices WHERE id = ?", (self.invoice_id,))
        if invoice:
            invoice = invoice[0]
            self.invoice_number.delete(0, 'end')
            self.invoice_number.insert(0, invoice[1])
            self.date_entry.delete(0, 'end')
            self.date_entry.insert(0, invoice[3])
            
            # تحميل العميل
            customer = self.db.execute_query("SELECT * FROM customers WHERE id = ?", (invoice[2],))
            if customer:
                self.customer_var.set(f"{customer[0][0]} - {customer[0][1]}")
            
            # تحميل العناصر
            self.items = json.loads(invoice[4])
            self.update_items_tree()
            
            # تحميل المجاميع
            self.discount_entry.delete(0, 'end')
            self.discount_entry.insert(0, str(invoice[7]))
            self.update_totals()
    
    def download_invoice(self):
        """تنزيل الفاتورة كملف PDF على الجهاز في مكان يختاره المستخدم"""
        self._generate_invoice_pdf(action="save", close_window=False)

    def direct_print_invoice(self):
        """طباعة الفاتورة مباشرة: يولد PDF مؤقت ثم يفتح نافذة الطباعة"""
        self._generate_invoice_pdf(action="print", close_window=False)

    def print_invoice(self):
        """اختصار لوحة المفاتيح - طباعة مباشرة"""
        self.direct_print_invoice()

    def preview_invoice(self):
        """عرض الفاتورة مؤقتاً"""
        self._generate_invoice_pdf(action="preview")

    def _generate_invoice_pdf(self, action="preview", close_window=False):
        if not self.items:
            messagebox.showwarning("تحذير", "⚠️ لا توجد عناصر للتصدير")
            return
        
        choice_dialog = DesignChoiceDialog(self.window)
        self.window.wait_window(choice_dialog)
        design_choice = choice_dialog.choice
        if not design_choice:
            return # User cancelled
        self.design_choice = design_choice

        
        customer_info = self.customer_var.get()
        if not customer_info:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار العميل")
            return
        
        # حفظ الفاتورة في البرنامج أولاً دون إغلاق النافذة
        if not self.save_invoice(close_window=False):
            return

        # الحصول على قيم الحقول
        try:
            customer_id = int(customer_info.split(' - ')[0])
            customer = self.db.execute_query("SELECT * FROM customers WHERE id = ?", (customer_id,))
            customer_data = customer[0] if customer else ("", "غير معروف", "", "", "")
        except ValueError:
            customer = self.db.execute_query("SELECT * FROM customers WHERE name = ?", (customer_info,))
            if customer:
                customer_id = customer[0][0]
                customer_data = customer[0]
            else:
                customer_id = None
                customer_data = ("", customer_info, "", "", "")
        
        invoice_number = self.invoice_number.get()
        date = self.date_entry.get()
        try:
            discount = float(self.discount_entry.get() or 0)
        except:
            discount = 0.0
        subtotal = sum(float(item.get('subtotal', item.get('quantity', 0) * item.get('price', item.get('unit_price', 0)))) for item in self.items)
        net = max(0.0, subtotal - discount)
        tax = net * 0.15
        grand_total = net + tax
        
        invoice_data = (
            self.invoice_id,  # id
            invoice_number,  # invoice_number
            customer_id,  # customer_id
            date,  # date
            json.dumps(self.items),  # items
            subtotal,  # total
            tax,  # tax
            discount,  # discount
            grand_total  # grand_total
        )
        
        try:
            # استخدام إعدادات الشركة من قاعدة البيانات
            from company_settings import get_company_settings
            company_settings = get_company_settings(self.db)
            
            doc_title = "عرض سعر" if self.is_quote else "فاتورة ضريبية"
            if self.design_choice == 2:
                pdf = ClassicInvoicePDF(title=doc_title, is_quote=self.is_quote)
                pdf.add_invoice_data(invoice_data, customer_data)
            else:
                pdf = CustomInvoicePDF(company_settings, is_quote=self.is_quote)
                pdf.add_page()
                pdf.add_invoice_data(invoice_data, customer_data)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if action == 'save':
                doc_type_name = "عرض سعر" if self.is_quote else "فاتورة ضريبه"
                default_name = f"{doc_type_name} {invoice_number}.pdf"
                filepath = choose_pdf_save_path(default_name, title='تنزيل الفاتورة كـ PDF')
                if not filepath:
                    return
            else:
                import tempfile
                temp_dir = tempfile.gettempdir()
                filename = f"preview_invoice_{invoice_number}_{timestamp}.pdf"
                filepath = os.path.join(temp_dir, filename)
            
            if not save_pdf_document(pdf, filepath):
                return
            
            if action == 'save':
                self.status_callback(f"✅ تم تنزيل الفاتورة بنجاح: {filepath}")
                messagebox.showinfo("نجاح", f"✅ تم تنزيل الفاتورة بنجاح على جهازك\n📂 في: {filepath}")
            elif action == 'print':
                if print_pdf_document(filepath):
                    self.status_callback(f"🖨️ جاري فتح نافذة الطباعة للفاتورة {invoice_number}")
                else:
                    messagebox.showwarning("تنبيه", "⚠️ لم يتم إرسال الملف إلى الطابعة")
            elif action == 'preview':
                if not open_pdf_document(filepath):
                    messagebox.showwarning("تنبيه", f"⚠️ تعذر فتح ملف PDF")
            
            if close_window:
                self.window.destroy()
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تصدير الفاتورة: {str(e)}")

# الوحدة الرئيسية للفواتير
class InvoiceModule:
    def __init__(self, parent, status_callback):
        self.parent = parent
        self.status_callback = status_callback
        self.db = Database()
        self.frame = ttk.Frame(parent)
        self.company_settings = self.load_company_settings()
        
        # إنشاء ScrollArea للتبويب
        self.create_scrollable_content()
        
        self.setup_ui()
        self.load_invoices()
        self.load_quotes()
    
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
    
    def load_company_settings(self):
        # تحميل إعدادات الشركة من قاعدة البيانات
        try:
            from company_settings import get_company_settings
            return get_company_settings(self.db)
        except:
            # القيم الافتراضية في حالة فشل التحميل
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
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.content_frame, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # إنشاء تبويبات
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True, pady=(0, 10))
        
        # تبويب الفواتير
        self.invoice_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.invoice_tab, text='📄 الفواتير')
        self.setup_invoice_tab()
        
        # تبويب عروض الأسعار
        self.quote_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.quote_tab, text='📋 عروض الأسعار')
        self.setup_quote_tab()
    
    def create_action_button(self, parent, text, command, bg, fg='white', width=None):
        """إنشاء زر إجراء بنفس الشكل المستخدم في نافذة الفاتورة الرئيسية"""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            font=('Segoe UI', 10, 'bold'),
            relief=tk.FLAT,
            padx=14,
            pady=8,
            cursor='hand2'
        )
        if width:
            btn.config(width=width)
        return btn

    def setup_invoice_tab(self):
        """إعداد تبويب الفواتير"""
        # أزرار سريعة - حجم مناسب
        quick_actions = ttk.Frame(self.invoice_tab)
        quick_actions.pack(fill='x', pady=(0, 15))
        
        action_buttons = [
            ("➕ فاتورة جديدة", self.create_new_invoice),
            ("📊 إحصائيات سريعة", self.show_quick_stats),
            ("📦 فاتورة مجمعة", self.create_combined_invoice),
            ("📤 تصدير البيانات", self.export_data)
        ]
        
        for text, command in action_buttons:
            btn = ttk.Button(quick_actions, text=text, command=command)
            btn.pack(side='left', padx=6, ipady=6)
        
        # شريط البحث - حجم مناسب
        search_frame = ttk.Frame(self.invoice_tab)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="بحث:", font=('Segoe UI', 10)).pack(side='left', padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30, font=('Segoe UI', 10))
        self.search_entry.pack(side='left', padx=5, ipady=4)
        self.search_entry.bind('<KeyRelease>', self.search_invoices)
        
        ttk.Button(search_frame, text="بحث", command=self.search_invoices).pack(side='left', padx=5, ipady=4)
        ttk.Button(search_frame, text="عرض الكل", command=self.load_invoices).pack(side='left', padx=5, ipady=4)
        
        # جدول الفواتير
        tree_frame = ttk.LabelFrame(self.invoice_tab, text="سجل الفواتير")
        tree_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # إطار Checkbox
        checkbox_frame = tk.Frame(tree_frame, bg='white')
        checkbox_frame.pack(fill='x', padx=5, pady=5)
        
        tk.Label(checkbox_frame, text="اختيار الكل:", font=('Segoe UI', 9),
                bg='white').pack(side='right', padx=5)
        
        self.select_all_var = tk.BooleanVar()
        select_all_check = tk.Checkbutton(checkbox_frame, variable=self.select_all_var,
                                          bg='white', command=self.toggle_select_all)
        select_all_check.pack(side='right', padx=5)
        
        # إنشاء جدول الفواتير
        self.create_invoice_tree(tree_frame)
        
        # أزرار التحكم
        control_frame = ttk.Frame(self.invoice_tab)
        control_frame.pack(fill='x', pady=(10, 0))
        
        self.create_action_button(control_frame, "👁️ عرض", self.view_invoice, '#F39C12').pack(side='right', padx=5)
        self.create_action_button(control_frame, "✏️ تعديل", self.edit_invoice, '#8E44AD').pack(side='right', padx=5)
        self.create_action_button(control_frame, "📥 تنزيل", self.download_invoice, '#3498DB').pack(side='right', padx=5)
        self.create_action_button(control_frame, "🖨️ طباعة", self.direct_print_invoice, '#1A5276').pack(side='right', padx=5)
        self.create_action_button(control_frame, "🗑️ حذف", self.delete_invoice, '#E74C3C').pack(side='right', padx=5)

    
    def setup_quote_tab(self):
        """إعداد تبويب عروض الأسعار"""
        # أزرار سريعة
        quick_actions = ttk.Frame(self.quote_tab)
        quick_actions.pack(fill='x', pady=(0, 15))
        
        ttk.Button(quick_actions, text="📋 عرض سعر جديد", command=self.create_price_quote).pack(side='left', padx=6, ipady=6)
        ttk.Button(quick_actions, text="📊 إحصائيات عروض الأسعار", command=self.show_quote_stats).pack(side='left', padx=6, ipady=6)
        
        # شريط البحث
        search_frame = ttk.Frame(self.quote_tab)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="بحث:", font=('Segoe UI', 10)).pack(side='left', padx=5)
        self.quote_search_entry = ttk.Entry(search_frame, width=30, font=('Segoe UI', 10))
        self.quote_search_entry.pack(side='left', padx=5, ipady=4)
        self.quote_search_entry.bind('<KeyRelease>', self.search_quotes)
        
        ttk.Button(search_frame, text="بحث", command=self.search_quotes).pack(side='left', padx=5, ipady=4)
        ttk.Button(search_frame, text="عرض الكل", command=self.load_quotes).pack(side='left', padx=5, ipady=4)
        
        # جدول عروض الأسعار
        tree_frame = ttk.LabelFrame(self.quote_tab, text="سجل عروض الأسعار")
        tree_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # إنشاء جدول عروض الأسعار
        self.create_quote_tree(tree_frame)
        
        # أزرار التحكم
        control_frame = ttk.Frame(self.quote_tab)
        control_frame.pack(fill='x', pady=(10, 0))
        
        self.create_action_button(control_frame, "👁️ عرض", self.view_quote, '#F39C12').pack(side='right', padx=5)
        self.create_action_button(control_frame, "📥 تنزيل", self.download_quote, '#3498DB').pack(side='right', padx=5)
        self.create_action_button(control_frame, "✏️ تعديل", self.edit_quote, '#8E44AD').pack(side='right', padx=5)
        self.create_action_button(control_frame, "🖨️ طباعة", self.print_quote, '#1A5276').pack(side='right', padx=5)
        self.create_action_button(control_frame, "🗑️ حذف", self.delete_quote, '#E74C3C').pack(side='right', padx=5)
    
    def create_invoice_tree(self, tree_frame):
        """إنشاء جدول الفواتير"""
        # إنشاء Treeview مع أعمدة - مع Checkbox
        columns = ('select', 'id', 'number', 'customer', 'date', 'total', 'tax', 'grand_total')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # تعريف الأعمدة
        self.tree.heading('select', text='✓')
        self.tree.heading('id', text='ID')
        self.tree.heading('number', text='رقم الفاتورة')
        self.tree.heading('customer', text='اسم العميل')
        self.tree.heading('date', text='التاريخ')
        self.tree.heading('total', text='الإجمالي')
        self.tree.heading('tax', text='الضريبة')
        self.tree.heading('grand_total', text='الإجمالي النهائي')
        
        # تعريفات عرض الأعمدة
        self.tree.column('select', width=45, anchor='center')
        self.tree.column('id', width=40)
        self.tree.column('number', width=100)
        self.tree.column('customer', width=150)
        self.tree.column('date', width=100)
        self.tree.column('total', width=80)
        self.tree.column('tax', width=80)
        self.tree.column('grand_total', width=100)
        
        self.tree.pack(side='left', fill='both', expand=True)
        
        # ربط أحداث النقر وزر المسافة للتبديل الفوري للـ Checkbox
        self.tree.bind('<Button-1>', self.on_invoice_tree_click, add='+')
        self.tree.bind('<space>', self.on_invoice_tree_space)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # متغيرات Checkbox للفواتير
        self.invoice_checkboxes = {}
    
    def create_quote_tree(self, tree_frame):
        """إنشاء جدول عروض الأسعار"""
        # إنشاء Treeview مع أعمدة
        columns = ('id', 'number', 'customer', 'date', 'valid_until', 'total')
        self.quote_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # تعريف الأعمدة
        self.quote_tree.heading('id', text='ID')
        self.quote_tree.heading('number', text='رقم العرض')
        self.quote_tree.heading('customer', text='اسم العميل')
        self.quote_tree.heading('date', text='التاريخ')
        self.quote_tree.heading('valid_until', text='صالح حتى')
        self.quote_tree.heading('total', text='الإجمالي')
        
        # تعريفات عرض الأعمدة
        self.quote_tree.column('id', width=40)
        self.quote_tree.column('number', width=100)
        self.quote_tree.column('customer', width=150)
        self.quote_tree.column('date', width=100)
        self.quote_tree.column('valid_until', width=100)
        self.quote_tree.column('total', width=100)
        
        self.quote_tree.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.quote_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.quote_tree.configure(yscrollcommand=scrollbar.set)
    
    def load_quotes(self):
        """تحميل عروض الأسعار"""
        try:
            quotes = self.db.execute_query("""
                SELECT pq.*, c.name as customer_name
                FROM price_quotes pq
                LEFT JOIN customers c ON pq.customer_id = c.id
                ORDER BY pq.date DESC
            """)
            
            # مسح الجدول
            for item in list(getattr(self, '_quote_all_items', [])) + list(self.quote_tree.get_children()):
                if self.quote_tree.exists(item):
                    self.quote_tree.delete(item)
            self._quote_all_items = []
            
            # إضافة البيانات
            for quote in quotes:
                self.quote_tree.insert('', 'end', values=(
                    quote[0],  # id
                    quote[2],  # quote_number
                    quote[13] or '---',  # customer_name (الحقل الصحيح)
                    quote[3],  # date
                    quote[4],  # valid_until
                    f"{quote[9]:.2f}"  # grand_total
                ))
                
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تحميل عروض الأسعار: {str(e)}")
    
    def get_selected_invoice_ids(self):
        """إرجاع قائمة الفواتير المختارة من الـ Checkbox أو التحديد الحالي"""
        selected_invoices = []
        for inv_id, var in self.invoice_checkboxes.items():
            if var.get():
                selected_invoices.append(inv_id)

        if not selected_invoices:
            selected = self.tree.selection()
            if selected:
                for item in selected:
                    values = self.tree.item(item, 'values')
                    if len(values) > 1:
                        try:
                            selected_invoices.append(int(values[1]))
                        except (ValueError, IndexError):
                            continue

        return selected_invoices

    def get_selected_quote_ids(self):
        """إرجاع قائمة عروض الأسعار المختارة"""
        selected_quotes = []
        selected = self.quote_tree.selection()
        if selected:
            for item in selected:
                values = self.quote_tree.item(item, 'values')
                if len(values) > 0:
                    try:
                        selected_quotes.append(int(values[0]))
                    except (ValueError, IndexError):
                        continue
        return selected_quotes

    def search_quotes(self, event=None):
        """البحث في عروض الأسعار (إخفاء/إظهار الصفوف عبر detach/move لأن Treeview لا يدعم hide)"""
        search_term = self.quote_search_entry.get().lower().strip()
        tree = self.quote_tree
        all_items = [i for i in getattr(self, '_quote_all_items', []) if tree.exists(i)]
        known = set(all_items)
        for i in tree.get_children():
            if i not in known:
                all_items.append(i)
        self._quote_all_items = all_items
        pos = 0
        for item in all_items:
            values = tree.item(item, 'values')
            if not search_term or any(search_term in str(v).lower() for v in values):
                tree.move(item, '', pos)
                pos += 1
            else:
                tree.detach(item)

    def show_quote_stats(self):
        """إظهار إحصائيات عروض الأسعار"""
        try:
            total_quotes = len(self.db.execute_query("SELECT id FROM price_quotes"))
            result = self.db.execute_query("SELECT SUM(grand_total) FROM price_quotes")
            total_amount = result[0][0] if result and result[0][0] else 0
            
            messagebox.showinfo("إحصائيات عروض الأسعار", 
                              f"📊 إحصائيات عروض الأسعار:\n\n"
                              f"• إجمالي عروض الأسعار: {total_quotes}\n"
                              f"• إجمالي القيم: {total_amount:,.2f} ريال")
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في عرض الإحصائيات: {str(e)}")
    
    def edit_quote(self):
        """تعديل عرض سعر"""
        selected = self.quote_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عرض سعر لتعديله")
            return
        
        quote_id = self.quote_tree.item(selected[0], 'values')[0]
        PriceQuoteDialog(self.parent, self.db, self.status_callback, self.load_quotes, quote_id)
    
    def delete_quote(self):
        """حذف عرض سعر"""
        selected = self.quote_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عرض سعر لحذفه")
            return
        
        if messagebox.askyesno("تأكيد", "⚠️ هل أنت متأكد من حذف عرض السعر؟"):
            quote_id = self.quote_tree.item(selected[0], 'values')[0]
            self.db.execute_query("DELETE FROM price_quotes WHERE id = ?", (quote_id,))
            self.status_callback("✅ تم حذف عرض السعر")
            self.load_quotes()
    
    def view_quote(self):
        """عرض عرض السعر مباشرة"""
        selected_quotes = self.get_selected_quote_ids()
        if not selected_quotes:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عرض سعر لعرضه")
            return

        self.export_quote_pdf(selected_quotes[0], action='preview')

    def download_quote(self):
        """حفظ عرض السعر في مكان محدد"""
        selected_quotes = self.get_selected_quote_ids()
        if not selected_quotes:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عرض سعر لحفظه")
            return

        self.export_quote_pdf(selected_quotes[0], action='save')

    def print_quote(self):
        """طباعة عرض السعر مباشرة دون سؤال عن مكان الحفظ"""
        selected_quotes = self.get_selected_quote_ids()
        if not selected_quotes:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عرض سعر لطباعته")
            return

        self.export_quote_pdf(selected_quotes[0], action='print')

    def export_quote_pdf(self, quote_id, action='print'):
        """تصدير عرض السعر إلى PDF مع دعم الطباعة أو الحفظ أو المعاينة"""
        try:
            self.status_callback("🔄 جاري تحضير عرض السعر")
            quote = self.db.execute_query("""
                SELECT pq.*, c.name as customer_name
                FROM price_quotes pq
                LEFT JOIN customers c ON pq.customer_id = c.id
                WHERE pq.id = ?
            """, (quote_id,))

            if not quote:
                messagebox.showerror("خطأ", "❌ لم يتم العثور على عرض السعر")
                return

            quote = quote[0]
            customer = self.db.execute_query("SELECT * FROM customers WHERE id = ?", (quote[1],))
            if not customer:
                messagebox.showerror("خطأ", "❌ لم يتم العثور على العميل")
                return

            customer_data = customer[0]
            from company_settings import get_company_settings
            company_settings = get_company_settings(self.db)

            items_json = quote[10].replace("'", '"') if quote[10] else '[]'
            invoice_data = (
                quote[0],          # [0] id
                quote[2],          # [1] quote_number (e.g. "001")
                quote[1],          # [2] customer_id
                quote[3],          # [3] date
                items_json,        # [4] items JSON
                quote[6] or 0.0,   # [5] subtotal
                quote[8] or 0.0,   # [6] tax
                quote[7] or 0.0,   # [7] discount
                quote[9] or 0.0    # [8] grand_total
            )

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_name = f"عرض سعر {quote[2]}.pdf"

            if action == 'save':
                filepath = choose_pdf_save_path(default_name, title='حفظ عرض السعر كـ')
                if not filepath:
                    return
            else:
                temp_dir = tempfile.gettempdir()
                filename = default_name if action == 'print' else f"preview_quote_{quote[2]}_{timestamp}.pdf"
                filepath = os.path.join(temp_dir, filename)

            choice_dialog = DesignChoiceDialog(self.parent.winfo_toplevel())
            self.parent.winfo_toplevel().wait_window(choice_dialog)
            design_choice = choice_dialog.choice

            if not design_choice:
                return

            if design_choice == 2:
                pdf = ClassicInvoicePDF(title="عرض سعر", is_quote=True)
                pdf.add_invoice_data(invoice_data, customer_data)
            else:
                pdf = CustomInvoicePDF(company_settings, is_quote=True)
                pdf.add_page()
                pdf.add_invoice_data(invoice_data, customer_data)

            if not save_pdf_document(pdf, filepath):
                return

            if action == 'save':
                self.status_callback(f"✅ تم حفظ عرض السعر: {filepath}")
                messagebox.showinfo("نجاح", f"✅ تم حفظ عرض السعر بنجاح\n📂 في: {filepath}")
            elif action == 'print':
                if print_pdf_document(filepath):
                    self.status_callback(f"✅ تم طباعة عرض السعر بنجاح")
                    messagebox.showinfo("نجاح", f"✅ تم طباعة عرض السعر بنجاح\n📂 تم حفظه مؤقتاً في: {filepath}")
                else:
                    self.status_callback("⚠️ لم يتم إرسال عرض السعر للطباعة")
                    messagebox.showwarning("تنبيه", "⚠️ لم يتم إرسال الملف إلى الطابعة")
            elif action == 'preview':
                open_pdf_document(filepath)

        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في معالجة عرض السعر: {str(e)}")
            self.status_callback("❌ فشل في معالجة عرض السعر")
    
    def _add_quote_data(self, pdf, invoice_data, customer_data):
        """دالة مساعدة لإضافة بيانات عرض السعر مع تعديل العنوان"""
        pdf.is_quote = True
        pdf.add_invoice_data(invoice_data, customer_data)
    
    def create_new_invoice(self):
        InvoiceDialog(self.parent, self.db, self.status_callback, self.load_invoices)
    
    def create_price_quote(self):
        PriceQuoteDialog(self.parent, self.db, self.status_callback, self.load_quotes)
    
    def show_quick_stats(self):
        total_invoices = len(self.db.execute_query("SELECT id FROM invoices"))
        total_amount = self.db.execute_query("SELECT SUM(grand_total) FROM invoices")[0][0] or 0
        today_invoices = len(self.db.execute_query("SELECT id FROM invoices WHERE date = ?", 
                                                 (datetime.now().strftime('%Y-%m-%d'),)))
        
        messagebox.showinfo("إحصائيات سريعة", 
                          f"📊 إحصائيات الفواتير:\n\n"
                          f"• إجمالي الفواتير: {total_invoices}\n"
                          f"• إجمالي المبالغ: {total_amount:,.2f} ريال\n"
                          f"• فواتير اليوم: {today_invoices}")
    
    def batch_print(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار فواتير للطباعة")
            return
        
        for item in selected:
            invoice_id = self.tree.item(item, 'values')[0]
            self.print_single_invoice(invoice_id)
        
        self.status_callback(f"✅ تم طباعة {len(selected)} فاتورة")
    
    def export_data(self):
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="حفظ كملف Excel"
            )
            
            if filename:
                invoices = self.db.execute_query('''
                    SELECT i.invoice_number, c.name, i.date, i.total, i.tax, i.discount, i.grand_total 
                    FROM invoices i 
                    LEFT JOIN customers c ON i.customer_id = c.id
                ''')
                
                df = pd.DataFrame(invoices, columns=[
                    'رقم الفاتورة', 'اسم العميل', 'التاريخ', 
                    'المجموع', 'الضريبة', 'الخصم', 'الإجمالي النهائي'
                ])
                
                df.to_excel(filename, index=False, engine='openpyxl')
                
                self.status_callback(f"✅ تم تصدير البيانات إلى: {filename}")
                messagebox.showinfo("نجاح", f"✅ تم تصدير البيانات إلى: {filename}")
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تصدير البيانات: {str(e)}")
    
    def search_invoices(self, event=None):
        search_term = self.search_entry.get()
        if not search_term:
            self.load_invoices()
            return
        
        query = '''
        SELECT i.id, i.invoice_number, c.name, i.date, i.total, i.tax, i.grand_total
        FROM invoices i 
        LEFT JOIN customers c ON i.customer_id = c.id
        WHERE i.invoice_number LIKE ? OR c.name LIKE ? OR i.date LIKE ?
        ORDER BY i.date DESC
        '''
        
        search_pattern = f'%{search_term}%'
        invoices = self.db.execute_query(query, (search_pattern, search_pattern, search_pattern))
        self.display_invoices(invoices)
    
    def load_invoices(self):
        query = '''
        SELECT i.id, i.invoice_number, c.name, i.date, i.total, i.tax, i.grand_total
        FROM invoices i 
        LEFT JOIN customers c ON i.customer_id = c.id
        ORDER BY i.date DESC
        '''
        invoices = self.db.execute_query(query)
        self.display_invoices(invoices)
    
    def display_invoices(self, invoices):
        self.tree.delete(*self.tree.get_children())
        self.invoice_checkboxes = {}
        for invoice in invoices:
            invoice_id = invoice[0]
            var = tk.BooleanVar(value=False)
            self.invoice_checkboxes[invoice_id] = var
            
            # إدراج الصف مع Checkbox
            self.tree.insert('', 'end', values=(
                '☐', invoice_id, invoice[1], invoice[2], invoice[3],
                f"{invoice[4]:.2f}", f"{invoice[5]:.2f}", f"{invoice[6]:.2f}"
            ))

    def on_invoice_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region not in ('cell', 'tree'):
            return
        col = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        if not item:
            return
        # النقر على عمود الـ Checkbox الأول
        if col == '#1':
            self.toggle_invoice_item(item)
            return 'break'

    def on_invoice_tree_space(self, event):
        selected = self.tree.selection()
        if selected:
            for item in selected:
                self.toggle_invoice_item(item)
            return 'break'

    def toggle_invoice_item(self, item):
        values = list(self.tree.item(item, 'values'))
        if not values or len(values) < 2:
            return
        try:
            inv_id = int(values[1])
        except (ValueError, TypeError):
            return
            
        var = self.invoice_checkboxes.get(inv_id)
        if not var:
            var = tk.BooleanVar(value=False)
            self.invoice_checkboxes[inv_id] = var
            
        new_state = not var.get()
        var.set(new_state)
        self.tree.set(item, 'select', '☑' if new_state else '☐')
        
        # مزامنة خانة اختيار الكل
        if self.invoice_checkboxes:
            all_checked = all(v.get() for v in self.invoice_checkboxes.values())
            self.select_all_var.set(all_checked)
    
    def toggle_select_all(self):
        """تحديد/إلغاء تحديد جميع الفواتير"""
        state = self.select_all_var.get()
        for inv_id, var in self.invoice_checkboxes.items():
            var.set(state)
        for item in self.tree.get_children():
            self.tree.set(item, 'select', '☑' if state else '☐')
    
    def load_customers(self):
        self.customers = self.db.execute_query("SELECT id, name FROM customers")
    
    def load_projects(self):
        self.projects = self.db.execute_query("SELECT id, name FROM projects")
    
    def view_invoice(self):
        selected_invoices = self.get_selected_invoice_ids()
        if not selected_invoices:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار فاتورة لعرضها")
            return

        self.show_invoice_details(selected_invoices[0])

    def save_invoice(self):
        selected_invoices = self.get_selected_invoice_ids()
        if not selected_invoices:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار فاتورة لحفظها")
            return

        self.print_single_invoice(selected_invoices[0], action='save')

    def edit_invoice(self):
        selected_invoices = self.get_selected_invoice_ids()
        if not selected_invoices:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار فاتورة لتعديلها")
            return

        InvoiceDialog(self.parent, self.db, self.status_callback, self.load_invoices, selected_invoices[0])

    def delete_invoice(self):
        selected_invoices = self.get_selected_invoice_ids()
        if not selected_invoices:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار فاتورة لحذفها")
            return

        invoice_id = selected_invoices[0]
        invoice = self.db.execute_query("SELECT invoice_number FROM invoices WHERE id = ?", (invoice_id,))
        invoice_number = invoice[0][0] if invoice else "غير معروف"

        if messagebox.askyesno("تأكيد", f"⚠️ هل أنت متأكد من حذف الفاتورة رقم {invoice_number}؟"):
            try:
                self.db.execute_query("DELETE FROM invoices WHERE id = ?", (invoice_id,))
                self.db.execute_query("DELETE FROM transactions WHERE description = ?", (f"فاتورة #{invoice_number}",))
                self.status_callback(f"✅ تم حذف الفاتورة رقم {invoice_number}")
                self.load_invoices()
            except Exception as e:
                messagebox.showerror("خطأ", f"❌ فشل في حذف الفاتورة: {str(e)}")

    def direct_print_invoice(self):
        """طباعة الفاتورة مباشرة: يولد PDF مؤقت ثم يفتح نافذة الطباعة"""
        selected_invoices = self.get_selected_invoice_ids()
        if not selected_invoices:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار فاتورة واحدة على الأقل لطباعتها")
            return

        if len(selected_invoices) > 1:
            if messagebox.askyesno("تأكيد", "لقد قمت بتحديد عدة فواتير. هل تريد إنشاء 'فاتورة مجمعة' لهم؟\n(إذا اخترت 'لا' سيتم طباعة كل فاتورة على حدة)"):
                self.print_combined_invoice(selected_invoices, action='print')
                return
            for inv_id in selected_invoices:
                self.print_single_invoice(inv_id, action='print')
        else:
            self.print_single_invoice(selected_invoices[0], action='print')

    def download_invoice(self):
        """تنزيل الفاتورة المحددة كملف PDF باختيار مكان الحفظ والاسم"""
        selected_invoices = self.get_selected_invoice_ids()
        if not selected_invoices:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار فاتورة واحدة على الأقل لتنزيلها")
            return

        if len(selected_invoices) > 1:
            if messagebox.askyesno("تأكيد", "لقد قمت بتحديد عدة فواتير. هل تريد إنشاء 'فاتورة مجمعة' لهم؟\n(إذا اخترت 'لا' سيتم حفظ كل فاتورة على حدة)"):
                self.print_combined_invoice(selected_invoices, action='save')
                return

        for inv_id in selected_invoices:
            self.print_single_invoice(inv_id, action='save')

    def print_invoice(self):
        """طباعة الفواتير المحددة مباشرة بدون سؤال عن مكان الحفظ"""
        selected_invoices = self.get_selected_invoice_ids()
        if not selected_invoices:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار فاتورة واحدة على الأقل لطباعتها")
            return

        if len(selected_invoices) > 1:
            if messagebox.askyesno("تأكيد", "لقد قمت بتحديد عدة فواتير. هل تريد إنشاء 'فاتورة مجمعة' لهم؟\n(إذا اخترت 'لا' سيتم طباعة كل فاتورة على حدة)"):
                self.print_combined_invoice(selected_invoices, action='print')
                return
            for inv_id in selected_invoices:
                self.print_single_invoice(inv_id, action='print')
        else:
            self.print_single_invoice(selected_invoices[0], action='print')

    def print_combined_invoice(self, invoice_ids, action='print'):
        """إنشاء فاتورة مجمعة لمجموعة من الفواتير لنفس العميل"""
        try:
            self.status_callback("جاري تحضير الفاتورة المجمعة...")
            
            invoices = []
            for inv_id in invoice_ids:
                invoice = self.db.execute_query("SELECT * FROM invoices WHERE id = ?", (inv_id,))
                if invoice:
                    invoices.append(invoice[0])
                    
            if not invoices:
                return
                
            customer_id = invoices[0][2]
            for inv in invoices:
                if inv[2] != customer_id:
                    messagebox.showerror("خطأ", "❌ يجب أن تكون جميع الفواتير المحددة لنفس العميل لإنشاء فاتورة مجمعة")
                    return
                    
            customer = self.db.execute_query("SELECT * FROM customers WHERE id = ?", (customer_id,))
            if not customer:
                messagebox.showerror("خطأ", "❌ لم يتم العثور على العميل")
                return
            customer_data = customer[0]
            
            combined_items = []
            combined_total = 0.0
            combined_tax = 0.0
            combined_discount = 0.0
            combined_grand_total = 0.0
            combined_numbers = []
            
            import json
            for inv in invoices:
                combined_numbers.append(str(inv[1]))
                try:
                    items = json.loads(inv[4])
                    for item in items:
                        item['desc'] = f"{item.get('desc', '')} (فاتورة #{inv[1]})"
                    combined_items.extend(items)
                except:
                    pass
                combined_total += float(inv[5] or 0)
                combined_tax += float(inv[6] or 0)
                combined_discount += float(inv[7] or 0)
                combined_grand_total += float(inv[8] or 0)
                
            combined_number = f"مجمعة ({','.join(combined_numbers)})"
            if len(combined_number) > 40:
                combined_number = f"مجمعة لـ {len(invoices)} فواتير"
                
            current_date = datetime.now().strftime('%Y-%m-%d')
            combined_invoice = (0, combined_number, customer_id, current_date, json.dumps(combined_items), 
                               combined_total, combined_tax, combined_discount, combined_grand_total, "معلق", "")
                               
            from company_settings import get_company_settings
            company_settings = get_company_settings(self.db)

            choice_dialog = DesignChoiceDialog(self.window.winfo_toplevel())
            self.window.winfo_toplevel().wait_window(choice_dialog)
            design_choice = choice_dialog.choice
            if not design_choice:
                return
            
            if design_choice == 2:
                pdf = ClassicInvoicePDF(title="فاتورة ضريبية مجمعة")
                pdf.add_invoice_data(combined_invoice, customer_data)
            else:
                pdf = CustomInvoicePDF(company_settings)
                pdf.add_page()
                pdf.add_invoice_data(combined_invoice, customer_data)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_name = f"فاتورة_مجمعة_{customer_data[1]}_{timestamp}.pdf"

            if action == 'save':
                filepath = choose_pdf_save_path(default_name, title='حفظ الفاتورة المجمعة بصيغة PDF')
                if not filepath:
                    return
            else:
                temp_dir = tempfile.gettempdir()
                filename = default_name if action == 'print' else f"preview_combined_{timestamp}.pdf"
                filepath = os.path.join(temp_dir, filename)

            if not save_pdf_document(pdf, filepath):
                return

            if action == 'save':
                self.status_callback(f"✅ تم حفظ الفاتورة المجمعة: {filepath}")
                messagebox.showinfo("نجاح", f"✅ تم حفظ الفاتورة المجمعة بنجاح\n📁 في: {filepath}")
            elif action == 'print':
                if print_pdf_document(filepath):
                    self.status_callback(f"🖨️ جاري طباعة الفاتورة المجمعة")
                else:
                    self.status_callback("⚠️ فشلت عملية الطباعة")
                    messagebox.showwarning("تنبيه", "⚠️ لم يتم العثور على طابعة على النظام")
            elif action == 'preview':
                open_pdf_document(filepath)

        except Exception as e:
            messagebox.showerror("خطأ", f"❌ حدث خطأ في معالجة الفاتورة المجمعة: {str(e)}")
            self.status_callback("❌ حدث خطأ في معالجة الفاتورة المجمعة")

    def print_single_invoice(self, invoice_id, action='print'):
        try:
            self.status_callback("🔄 جاري تحضير الفاتورة")

            invoice = self.db.execute_query("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
            if not invoice:
                messagebox.showerror("خطأ", "❌ لم يتم العثور على الفاتورة")
                return

            invoice = invoice[0]
            customer = self.db.execute_query("SELECT * FROM customers WHERE id = ?", (invoice[2],))
            if not customer:
                messagebox.showerror("خطأ", "❌ لم يتم العثور على العميل")
                return

            customer_data = customer[0]

            from company_settings import get_company_settings
            company_settings = get_company_settings(self.db)

            choice_dialog = DesignChoiceDialog(self.parent.winfo_toplevel())
            self.parent.winfo_toplevel().wait_window(choice_dialog)
            design_choice = choice_dialog.choice
            if not design_choice:
                return
            
            if design_choice == 2:
                pdf = ClassicInvoicePDF(title="فاتورة ضريبية")
                pdf.add_invoice_data(invoice, customer_data)
            else:
                pdf = CustomInvoicePDF(company_settings)
                pdf.add_page()
                pdf.add_invoice_data(invoice, customer_data)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            default_name = f"فاتورة ضريبه {invoice[1]}.pdf"

            if action == 'save':
                filepath = choose_pdf_save_path(default_name, title='تنزيل الفاتورة كـ PDF')
                if not filepath:
                    return
            else:
                temp_dir = tempfile.gettempdir()
                filename = default_name if action == 'print' else f"preview_invoice_{invoice[1]}_{timestamp}.pdf"
                filepath = os.path.join(temp_dir, filename)

            if not save_pdf_document(pdf, filepath):
                return

            if action == 'save':
                self.status_callback(f"✅ تم حفظ الفاتورة: {filepath}")
                messagebox.showinfo("نجاح", f"✅ تم حفظ الفاتورة بنجاح\n📂 في: {filepath}")
            elif action == 'print':
                if print_pdf_document(filepath):
                    self.status_callback(f"🖨️ جاري فتح نافذة الطباعة للفاتورة {invoice[1]}")
                else:
                    self.status_callback("⚠️ لم يتم إرسال الفاتورة للطباعة")
                    messagebox.showwarning("تنبيه", "⚠️ لم يتم إرسال الملف إلى الطابعة")
            elif action == 'preview':
                open_pdf_document(filepath)

        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في معالجة الفاتورة: {str(e)}")
            self.status_callback("❌ فشل في معالجة الفاتورة")
    
    def duplicate_invoice(self):
        # البحث عن فاتورة محددة (من Checkbox أو selection)
        invoice_id = None
        
        # البحث في Checkboxes
        for inv_id, var in self.invoice_checkboxes.items():
            if var.get():
                invoice_id = inv_id
                break
        
        # إذا لم يتم العثور، جرب selection
        if not invoice_id:
            selected = self.tree.selection()
            if selected:
                values = self.tree.item(selected[0], 'values')
                if len(values) > 1:
                    invoice_id = values[1]
        
        if not invoice_id:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار فاتورة للنسخ")
            return
        invoice = self.db.execute_query("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
        
        if invoice:
            invoice = invoice[0]
            # إنشاء فاتورة جديدة بنفس البيانات
            invoice_dialog = InvoiceDialog(self.parent, self.db, self.status_callback, self.load_invoices)
            
            # تحميل بيانات الفاتورة القديمة
            invoice_dialog.invoice_id = None  # فاتورة جديدة
            invoice_dialog.invoice_number.delete(0, tk.END)
            invoice_dialog.invoice_number.insert(0, f"{invoice[1]}_COPY")
            invoice_dialog.date_entry.delete(0, tk.END)
            invoice_dialog.date_entry.insert(0, invoice[3])
            
            # تحميل العميل
            customer = self.db.execute_query("SELECT * FROM customers WHERE id = ?", (invoice[2],))
            if customer:
                customer = customer[0]
                invoice_dialog.customer_var.set(f"{customer[0]} - {customer[1]}")
            
            # تحميل العناصر
            items = json.loads(invoice[4])
            invoice_dialog.items = items.copy()
            invoice_dialog.update_items_tree()
            
            # تحديث المبالغ
            invoice_dialog.discount_entry.delete(0, tk.END)
            invoice_dialog.discount_entry.insert(0, str(invoice[6] or 0))
    
    def create_combined_invoice(self):
        """إنشاء فاتورة مجمعة من عدة فواتير"""
        # البحث عن فواتير محددة (من Checkbox)
        selected_invoices = []
        for inv_id, var in self.invoice_checkboxes.items():
            if var.get():
                selected_invoices.append(inv_id)
        
        # إذا لم يتم العثور، جرب selection
        if not selected_invoices:
            selected = self.tree.selection()
            if selected:
                for item in selected:
                    values = self.tree.item(item, 'values')
                    if len(values) > 1:
                        selected_invoices.append(values[1])
        
        if len(selected_invoices) < 2:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار فاتورتين أو أكثر لإنشاء فاتورة مجمعة")
            return
        
        # جمع بيانات الفواتير المختارة
        all_items = []
        total_amount = 0
        tax_amount = 0
        discount_amount = 0
        customer_id = None
        invoice_numbers = []
        
        for invoice_id in selected_invoices:
            invoice = self.db.execute_query("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
            if invoice:
                invoice = invoice[0]
                invoice_numbers.append(invoice[1])
                
                if customer_id is None:
                    customer_id = invoice[2]
                elif customer_id != invoice[2]:
                    messagebox.showerror("خطأ", "❌ جميع الفواتير يجب أن تكون لنفس العميل")
                    return
                
                # جمع العناصر
                items = json.loads(invoice[4])
                all_items.extend(items)
                
                total_amount += invoice[5] or 0
                tax_amount += invoice[6] or 0
                discount_amount += invoice[7] or 0
        
        if not customer_id:
            messagebox.showerror("خطأ", "❌ لم يتم العثور على بيانات العميل")
            return
        
        # إنشاء فاتورة جديدة مجمعة
        invoice_dialog = InvoiceDialog(self.parent, self.db, self.status_callback, self.load_invoices)
        
        # تعيين بيانات الفاتورة المجمعة
        invoice_dialog.invoice_number.delete(0, tk.END)
        invoice_dialog.invoice_number.insert(0, f"COMBINED_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        invoice_dialog.date_entry.delete(0, tk.END)
        invoice_dialog.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        
        # تحميل العميل
        customer = self.db.execute_query("SELECT * FROM customers WHERE id = ?", (customer_id,))
        if customer:
            customer = customer[0]
            invoice_dialog.customer_var.set(f"{customer[0]} - {customer[1]}")
        
        # تحميل العناصر المجمعة
        invoice_dialog.items = all_items
        invoice_dialog.update_items_tree()
        
        # تعيين الخصم
        invoice_dialog.discount_entry.delete(0, tk.END)
        invoice_dialog.discount_entry.insert(0, str(discount_amount))
        
        messagebox.showinfo("نجاح", f"✅ تم إنشاء فاتورة مجمعة من {len(selected_invoices)} فاتورة\n📋 الأرقام: {', '.join(invoice_numbers)}")
    
    def show_invoice_details(self, invoice_id):
        """عرض تفاصيل الفاتورة بنفس الشكل الحقيقي المستخدم في الطباعة والحفظ."""
        try:
            invoice = self.db.execute_query("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
            if not invoice:
                messagebox.showerror("خطأ", "لم يتم العثور على الفاتورة")
                return
            self.print_single_invoice(invoice_id, action='preview')
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ تعذر فتح عرض الفاتورة: {str(e)}")
            self.status_callback("❌ فشل في عرض الفاتورة")
    
    def get_company_settings(self):
        """الحصول على إعدادات الشركة"""
        return {
            'company_name_ar': 'محمد بن منير بن محمد سعيد دغستاني',
            'company_name_en': 'Mohammed bin Munir bin Mohammed Saeed Daghestani',
            'owner_name': 'محمد بن منير دغستاني',
            'owner_name_en': 'Mohammed bin Munir Daghestani',
            'commercial_register': '4030330926',
            'tax_number': '300262161400003',
            'address': 'جدة - أبحر الشمالية - شارع أبي محمد العطار',
            'phone1': '0582224122',
            'phone2': '0538833640',
            'po_box': '117332',
            'postal_code': '21391',
            'email': 'seapearl.est@gmail.com'
        }
    
    def create_professional_invoice_gui(self, parent, invoice, customer_data, company_settings):
        """إنشاء واجهة الفاتورة الاحترافية - نفس التصميم بالضبط من PDF v39"""
        # Main container - نفس ألوان PDF - يأخذ الصفحة كاملة
        main_frame = tk.Frame(parent, bg='#FEFEFA')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        try:
            # Header Section - نفس تصميم PDF بالضبط
            self.create_header_exact_pdf(main_frame, invoice, company_settings)
            
            # Customer Details Section - نفس تصميم PDF بالضبط
            self.create_customer_details_exact_pdf(main_frame, invoice, customer_data)
            
            # Items Table Section - نفس تصميم PDF بالضبط
            self.create_items_table_exact_pdf(main_frame, invoice)
            
            # Totals Section - نفس تصميم PDF بالضبط
            self.create_totals_section_exact_pdf(main_frame, invoice)
            
            # Footer Section - نفس تصميم PDF بالضبط
            self.create_footer_exact_pdf(main_frame, invoice, company_settings)
            
            # Close button - محسن
            close_btn = tk.Button(main_frame, text="❌ إغلاق", bg='#95A5A6', fg='white',
                                 font=('Arial', 11, 'bold'), relief=tk.FLAT, padx=30, pady=10,
                                 cursor='hand2', command=parent.winfo_toplevel().destroy)
            close_btn.pack(pady=15)
            
            # تحديث الوالد للتأكد من ظهور المحتوى
            parent.update_idletasks()
        except Exception as e:
            import traceback
            error_label = tk.Label(main_frame, text=f"خطأ في عرض الفاتورة: {str(e)}", 
                                  bg='#FEFEFA', fg='red', font=('Arial', 12))
            error_label.pack(pady=20)
            traceback.print_exc()
    
    def create_header_exact_pdf(self, parent, invoice, company_settings):
        """رأس الفاتورة - نفس تصميم PDF v39 بالضبط"""
        # صندوق أزرق في الأعلى - نفس PDF v39
        header_box = tk.Frame(parent, bg='#4C75A3', height=60)
        header_box.pack(fill=tk.X, pady=(0, 10))
        header_box.pack_propagate(False)
        
        header_content = tk.Frame(header_box, bg='#4C75A3')
        header_content.pack(fill=tk.BOTH, expand=True, padx=15, pady=8)
        
        # الجانب الأيسر - معلومات الشركة بالإنجليزية (v39)
        left_frame = tk.Frame(header_content, bg='#4C75A3')
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        company_name_en = company_settings.get('company_name_en', 'Sea Pearl Contracting')
        owner_name_en = company_settings.get('owner_name_en', 'Mohammed bin Munir Daghestani')
        cr_no = company_settings.get('commercial_register', '4030330926')
        vat_no = company_settings.get('tax_number', '300262161400003')
        
        tk.Label(left_frame, text=company_name_en, 
                font=('Arial', 16, 'bold'), bg='#4C75A3', fg='white').pack(anchor='w')
        tk.Label(left_frame, text=owner_name_en, 
                font=('Arial', 9), bg='#4C75A3', fg='white').pack(anchor='w')
        tk.Label(left_frame, text=f"CR: {cr_no}", 
                font=('Arial', 9), bg='#4C75A3', fg='white').pack(anchor='w')
        tk.Label(left_frame, text=f"VAT: {vat_no}", 
                font=('Arial', 9), bg='#4C75A3', fg='white').pack(anchor='w')
        
        # الوسط - العنوان (v39)
        center_frame = tk.Frame(header_content, bg='#4C75A3')
        center_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        tk.Label(center_frame, text=ar("فاتورة ضريبية"), 
                font=('Amiri', 13, 'bold'), bg='#4C75A3', fg='white').pack(pady=(5, 0))
        tk.Label(center_frame, text="TAX INVOICE", 
                font=('Arial', 11, 'bold'), bg='#4C75A3', fg='white').pack()
        
        # الجانب الأيمن - معلومات الشركة بالعربية (v39)
        right_frame = tk.Frame(header_content, bg='#4C75A3')
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        
        company_name_ar = company_settings.get('company_name_ar', 'مؤسسه لؤلؤه البحر للمقاولات')
        owner_name_ar = company_settings.get('owner_name', 'محمد بن منير دغستاني')
        
        tk.Label(right_frame, text=ar(company_name_ar), 
                font=('Amiri', 16, 'bold'), bg='#4C75A3', fg='white').pack(anchor='e')
        tk.Label(right_frame, text=ar(owner_name_ar), 
                font=('Amiri', 9, 'bold'), bg='#4C75A3', fg='white').pack(anchor='e')
        tk.Label(right_frame, text=ar(f"س.ت: {cr_no}"), 
                font=('Amiri', 9, 'bold'), bg='#4C75A3', fg='white').pack(anchor='e')
        tk.Label(right_frame, text=ar(f"الرقم الضريبي: {vat_no}"), 
                font=('Amiri', 9, 'bold'), bg='#4C75A3', fg='white').pack(anchor='e')
    
    def create_customer_details_exact_pdf(self, parent, invoice, customer_data):
        """بيانات العميل - نفس تصميم PDF v39 بالضبط"""
        main_rgb = '#011B40'
        label_rgb = '#2E5090'
        
        customer_frame = tk.Frame(parent, bg='#FEFEFA')
        customer_frame.pack(fill=tk.X, pady=(0, 15))
        
        cust_name = customer_data[1] if len(customer_data) > 1 else '---'
        cust_vat = customer_data[2] if len(customer_data) > 2 and customer_data[2] else '---'
        cust_address = customer_data[3] if len(customer_data) > 3 and customer_data[3] else '---'
        
        # بيانات الفاتورة - صف أول
        inv_fields = [
            ("Invoice No.", "رقم الفاتورة", invoice[1]),
            ("Cust. VAT", "الرقم الضريبي", cust_vat),
            ("Date", "التاريخ", invoice[3]),
            ("Time", "الوقت", datetime.now().strftime('%H:%M:%S'))
        ]
        
        inv_row = tk.Frame(customer_frame, bg='#FEFEFA')
        inv_row.pack(fill=tk.X, pady=5)
        
        for label_en, label_ar, value in inv_fields:
            box_frame = tk.Frame(inv_row, bg='white', relief=tk.RAISED, bd=1)
            box_frame.pack(side=tk.LEFT, padx=2, fill=tk.BOTH, expand=True)
            
            tk.Label(box_frame, text=f"{label_en} / {ar(label_ar)}", 
                    font=('Amiri', 9, 'bold'), bg='white', fg=label_rgb).pack(pady=2)
            tk.Label(box_frame, text=ar(str(value)), 
                    font=('Amiri', 11, 'bold'), bg='white', fg=main_rgb).pack()
        
        # بيانات العميل - اسم العميل
        cust_name_row = tk.Frame(customer_frame, bg='#FEFEFA')
        cust_name_row.pack(fill=tk.X, pady=5)
        
        name_box = tk.Frame(cust_name_row, bg='white', relief=tk.RAISED, bd=1)
        name_box.pack(fill=tk.BOTH, expand=True, padx=2)
        
        name_inner = tk.Frame(name_box, bg='white')
        name_inner.pack(side=tk.RIGHT, padx=10, pady=5)
        tk.Label(name_inner, text=f" : Customer Name / {ar('اسم العميل')}", font=('Amiri', 9, 'bold'), bg='white', fg=label_rgb).pack(side=tk.RIGHT)
        tk.Label(name_inner, text=ar(str(cust_name)), font=('Amiri', 12, 'bold'), bg='white', fg=main_rgb).pack(side=tk.RIGHT)
        
        # بيانات العميل - العنوان
        cust_address_row = tk.Frame(customer_frame, bg='#FEFEFA')
        cust_address_row.pack(fill=tk.X, pady=5)
        
        addr_box = tk.Frame(cust_address_row, bg='white', relief=tk.RAISED, bd=1)
        addr_box.pack(fill=tk.BOTH, expand=True, padx=2)
        
        addr_inner = tk.Frame(addr_box, bg='white')
        addr_inner.pack(side=tk.RIGHT, padx=10, pady=5)
        tk.Label(addr_inner, text=f" : Address / {ar('العنوان')}", font=('Amiri', 9, 'bold'), bg='white', fg=label_rgb).pack(side=tk.RIGHT)
        tk.Label(addr_inner, text=ar(str(cust_address)), font=('Amiri', 12, 'bold'), bg='white', fg=main_rgb).pack(side=tk.RIGHT)
    
    def create_items_table_exact_pdf(self, parent, invoice):
        """جدول العناصر - نفس تصميم PDF v39 بالضبط"""
        main_rgb = '#011B40'
        label_rgb = '#2E5090'
        
        table_frame = tk.Frame(parent, bg='#FEFEFA')
        table_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # رأس الجدول (v39: خط عريض)
        headers = [ar('م'), ar('البيان'), ar('الوحدة'), ar('الكمية'), ar('سعر الوحدة'), ar('الإجمالي')]
        col_widths = [10, 101, 15, 15, 20, 24]
        
        header_row = tk.Frame(table_frame, bg='#FEFEFA')
        header_row.pack(fill=tk.X, pady=5)
        
        for i, header in enumerate(headers):
            header_box = tk.Frame(header_row, bg='#F5F5F5', relief=tk.RAISED, bd=1)
            header_box.pack(side=tk.LEFT, padx=1, fill=tk.BOTH, expand=True)
            
            tk.Label(header_box, text=header, font=('Amiri', 13, 'bold'), 
                    bg='#F5F5F5', fg=label_rgb).pack(pady=3)
        
        # العناصر (v39: خط عريض)
        items = json.loads(invoice[4])
        for idx, item in enumerate(items, 1):
            item_row = tk.Frame(table_frame, bg='#FEFEFA')
            item_row.pack(fill=tk.X, pady=2)
            
            qty, price, total = float(item['quantity']), float(item['price']), item['total']
            row_data = [
                str(idx),
                ar(item['description']),
                ar(item.get('unit', 'Pcs')),
                f"{qty:.3f}",
                f"{price:.3f}",
                f"{total:.2f}"
            ]
            
            for i, data in enumerate(row_data):
                item_box = tk.Frame(item_row, bg='white', relief=tk.RAISED, bd=1)
                item_box.pack(side=tk.LEFT, padx=1, fill=tk.BOTH, expand=True)
                
                tk.Label(item_box, text=str(data), font=('Amiri', 12, 'bold'), 
                        bg='white', fg=main_rgb).pack(pady=3)
    
    def create_totals_section_exact_pdf(self, parent, invoice):
        """قسم الإجماليات - نفس تصميم PDF بالضبط (مربعات بيضاوية على اليمين)"""
        main_rgb = '#011B40'
        label_rgb = '#2E5090'
        
        totals_frame = tk.Frame(parent, bg='#FEFEFA')
        totals_frame.pack(fill=tk.X, pady=(0, 15))
        
        # الإجماليات على اليمين
        totals_right = tk.Frame(totals_frame, bg='#FEFEFA')
        totals_right.pack(side=tk.RIGHT, padx=10)
        
        totals_data = [
            ("Total", "الإجمالي", f"{invoice[5]:.2f}"),
            ("Discount Amount", "قيمة الخصم", f"{invoice[7] or 0:.2f}"),
            ("VAT Amount 15%", ar("% الضريبة 15"), f"{invoice[6]:.2f}"),
            ("Grand Total", "الإجمالي النهائي", f"{invoice[8]:.2f}")
        ]
        
        # Create a grid frame inside totals_right
        grid_frame = tk.Frame(totals_right, bg='#FEFEFA')
        grid_frame.pack(fill=tk.BOTH, expand=True)
        
        for i, (label_en, label_ar, value) in enumerate(totals_data):
            row = i // 2
            col = i % 2
            box_frame = tk.Frame(grid_frame, bg='white', relief=tk.RAISED, bd=1, width=150)
            box_frame.grid(row=row, column=col, padx=2, pady=2, sticky='nsew')
            
            height = 12 if i == 3 else 10
            box_frame.config(height=height)
            box_frame.pack_propagate(False)
            
            tk.Label(box_frame, text=f"{label_en} / {label_ar if 'VAT' in label_en else ar(label_ar)}", 
                    font=('Amiri', 8, 'bold'), bg='white', fg=label_rgb).pack(pady=1)
            tk.Label(box_frame, text=value, 
                    font=('Amiri', 11 if i < 3 else 12, 'bold'), bg='white', fg=main_rgb).pack()
        
        # المبلغ بالحروف
        amount_in_words = number_to_arabic_text(invoice[8])
        words_frame = tk.Frame(totals_frame, bg='#FEFEFA')
        words_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(words_frame, text=ar(f"المبلغ بالحروف: {amount_in_words}"), 
                font=('Amiri', 12, 'bold'), bg='#FEFEFA', fg=main_rgb).pack(anchor='e', padx=10)
    
    def create_footer_exact_pdf(self, parent, invoice, company_settings):
        """تذييل الفاتورة - نفس تصميم PDF بالضبط"""
        main_rgb = '#011B40'
        footer_bg = '#4C75A3'
        
        footer_frame = tk.Frame(parent, bg='#FEFEFA')
        footer_frame.pack(fill=tk.X, pady=(0, 15))
        
        # QR Code والتوقيعات
        top_footer = tk.Frame(footer_frame, bg='#FEFEFA')
        top_footer.pack(fill=tk.X, pady=10)
        
        # QR Code
        qr_frame = tk.Frame(top_footer, bg='#FEFEFA')
        qr_frame.pack(side=tk.LEFT, padx=10)
        
        try:
            if QR_AVAILABLE:
                qr = qrcode.QRCode(version=1, box_size=3, border=1)
                qr.add_data(f"Inv:{invoice[1]}, Tot:{invoice[8]}")
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white")
                from PIL import ImageTk
                qr_photo = ImageTk.PhotoImage(qr_img)
                qr_label = tk.Label(qr_frame, image=qr_photo, bg='#FEFEFA')
                qr_label.image = qr_photo
                qr_label.pack()
            else:
                tk.Label(qr_frame, text="QR\nCode", font=('Arial', 8), 
                        bg='white', relief=tk.RIDGE, width=8, height=4).pack()
        except:
            tk.Label(qr_frame, text="QR\nCode", font=('Arial', 8), 
                    bg='white', relief=tk.RIDGE, width=8, height=4).pack()
        
        # التوقيعات
        sig_frame = tk.Frame(top_footer, bg='#FEFEFA')
        sig_frame.pack(side=tk.LEFT, expand=True, padx=20)
        
        sig_labels = tk.Frame(sig_frame, bg='#FEFEFA')
        sig_labels.pack(fill=tk.X)
        
        tk.Label(sig_labels, text="Salesman / " + ar("البائع"), 
                font=('Amiri', 10, 'bold'), bg='#FEFEFA', fg=main_rgb).pack(side=tk.LEFT, padx=(0, 50))
        tk.Label(sig_labels, text="Received By / " + ar("المستلم"), 
                font=('Amiri', 10, 'bold'), bg='#FEFEFA', fg=main_rgb).pack(side=tk.LEFT)
        
        sig_lines = tk.Frame(sig_frame, bg='#FEFEFA')
        sig_lines.pack(fill=tk.X, pady=10)
        
        tk.Frame(sig_lines, height=1, bg='black', width=100).pack(side=tk.LEFT, padx=(0, 50))
        tk.Frame(sig_lines, height=1, bg='black', width=100).pack(side=tk.LEFT)
        
        # صندوق التذييل الأزرق
        footer_box = tk.Frame(footer_frame, bg=footer_bg, height=20)
        footer_box.pack(fill=tk.X, pady=10)
        footer_box.pack_propagate(False)
        
        footer_content = tk.Frame(footer_box, bg=footer_bg)
        footer_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=3)
        
        addr_ar = company_settings.get('address', 'جدة - أبحر الشمالية - شارع أبي محمد العطار')
        addr_en = company_settings.get('address_en', 'Jeddah - Obhur Al Shamaliah - Abi Mohammed Al Attar St.')
        mob1 = company_settings.get('phone1', '0582224122')
        mob2 = company_settings.get('phone2', '0538833640')
        email = company_settings.get('email', 'seapearl.est@gmail.com')
        
        # v39: خط أكبر في التذييل
        tk.Label(footer_content, text=f"{ar(addr_ar)}  |  {addr_en}", 
                font=('Amiri', 9, 'bold'), bg=footer_bg, fg='white').pack()
        tk.Label(footer_content, text=f"Mobile: {mob1} - {mob2}  |  Email: {email}", 
                font=('Amiri', 11, 'bold'), bg=footer_bg, fg='white').pack()


class DesignChoiceDialog(tk.Toplevel):
    def __init__(self, parent, title="اختيار تصميم الطباعة"):
        super().__init__(parent)
        self.title(title)
        self.geometry("450x200")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        # Center the window
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 200) // 2
        self.geometry(f"+{x}+{y}")
        
        self.choice = None
        
        lbl = tk.Label(self, text="الرجاء اختيار تصميم الطباعة:", font=('Segoe UI', 12, 'bold'))
        lbl.pack(pady=20)
        
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill='both', expand=True, padx=20)
        
        btn1 = tk.Button(btn_frame, text="التصميم الأساسي (1)", font=('Segoe UI', 10), bg='#1e3a8a', fg='white', 
                         command=lambda: self.select(1))
        btn1.pack(side='right', padx=10, fill='x', expand=True)
        
        btn2 = tk.Button(btn_frame, text="التصميم الكلاسيكي (2)", font=('Segoe UI', 10), bg='#eab308', fg='white',
                         command=lambda: self.select(2))
        btn2.pack(side='left', padx=10, fill='x', expand=True)
        
    def select(self, choice):
        self.choice = choice
        self.destroy()


# =========================================================================
# كلاس نافذة عروض الأسعار
# =========================================================================
class PriceQuoteDialog(InvoiceDialog):
    """نافذة إنشاء وتعديل عروض الأسعار باحترافية"""
    def __init__(self, parent, db, status_callback, refresh_callback, quote_id=None, view_only=False):
        super().__init__(parent, db, status_callback, refresh_callback, invoice_id=quote_id, view_only=view_only, is_quote=True)
