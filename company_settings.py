import tkinter as tk
from tkinter import ttk, messagebox
from database import Database
import json

class ModernButton(tk.Button):
    """زر عصري مع تصميم جميل"""
    def __init__(self, parent, text, bg='#4CAF50', fg='white', font=('Segoe UI', 10, 'bold'),
                 command=None, **kwargs):
        super().__init__(parent, text=text, bg=bg, fg=fg, font=font, command=command,
                        relief='flat', cursor='hand2', **kwargs)
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
    
    def on_enter(self, event):
        self.config(bg=self['bg'].replace('50', '60'))
    
    def on_leave(self, event):
        self.config(bg=self['bg'].replace('60', '50'))

class CompanySettingsDialog(tk.Toplevel):
    def __init__(self, parent, db, status_callback):
        super().__init__(parent)
        self.db = db
        self.status_callback = status_callback
        
        self.setup_dialog()
        self.load_settings()
        self.create_widgets()
    
    def setup_dialog(self):
        self.title("⚙️ إعدادات الشركة والفاتورة")
        self.geometry("1000x900")
        self.resizable(True, True)
        
        # ألوان احترافية
        self.colors = {
            'primary': '#2196F3',
            'secondary': '#FF9800',
            'success': '#4CAF50',
            'danger': '#f44336',
            'warning': '#FFC107',
            'info': '#00BCD4',
            'bg': '#F5F5F5',
            'card': '#FFFFFF',
            'text': '#333333',
            'text_light': '#666666',
            'border': '#E0E0E0'
        }
        
        self.configure(bg=self.colors['bg'])
        self.transient(self.master)
        self.grab_set()
    
    def load_settings(self):
        # تحميل الإعدادات المحفوظة أو استخدام قيم افتراضية
        # التحقق من وجود الجدول القديم وترحيل البيانات إذا لزم الأمر
        self.migrate_old_table_if_needed()
        
        settings = self.db.execute_query("""
            SELECT company_name_ar, company_name_en, owner_name, tax_number, commercial_register,
                   address, address_en, phone1, phone2, po_box, postal_code, email, website 
            FROM company_settings WHERE id = 1
        """)
        if settings and settings[0]:
            s = settings[0]
            self.settings = {
                'company_name_ar': s[0] if s[0] else 'مؤسسة لؤلؤة البحر للمقاولات',
                'company_name_en': s[1] if s[1] else  'Sea Pearl Contracting EST. ',
                'owner_name': s[2] if s[2] else 'محمد بن منير دغستاني',
                'tax_number': s[3] if s[3] else '300262161400003',
                'commercial_register': s[4] if s[4] else '4030330926',
                'address': s[5] if s[5] else 'جدة - أبحر الشمالية - شارع أبي محمد العطار',
                'address_en': s[6] if s[6] else 'Jeddah - Obhur Al Shamaliah - Abi Mohammed Al Attar St.',
                'phone1': s[7] if s[7] else '0582224122',
                'phone2': s[8] if s[8] else '0538833640',
                'po_box': s[9] if s[9] else '117332',
                'postal_code': s[10] if s[10] else '21391',
                'email': s[11] if s[11] else 'seapearl.est@gmail.com',
                'website': s[12] if s[12] else ''
            }
        else:
            self.settings = {
                'company_name_ar': 'مؤسسة لؤلؤة البحر للمقاولات',
                'company_name_en': 'Sea Pearl Contracting EST. ',
                'owner_name': 'محمد بن منير دغستاني',
                'tax_number': '300262161400003',
                'commercial_register': '4030330926',
                'address': 'جدة - أبحر الشمالية - شارع أبي محمد العطار',
                'address_en': 'Jeddah - Obhur Al Shamaliah - Abi Mohammed Al Attar St.',
                'phone1': '0582224122',
                'phone2': '0538833640',
                'po_box': '117332',
                'postal_code': '21391',
                'email': 'seapearl.est@gmail.com',
                'website': ''
            }
    
    def migrate_old_table_if_needed(self):
        """ترحيل البيانات من الجدول القديم إلى الجديد إذا وجد"""
        try:
            # التحقق من وجود الأعمدة القديمة
            old_data = self.db.execute_query("SELECT company_name_ar, tax_number, address, phone1, email FROM company_settings WHERE id = 1")
            if old_data and old_data[0]:
                # البيانات موجودة بالفعل بالأعمدة الجديدة
                pass
        except:
            pass
    
    def create_widgets(self):
        # إطار رئيسي
        main_container = tk.Frame(self, bg=self.colors['bg'])
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # إطار العنوان
        header_frame = tk.Frame(main_container, bg=self.colors['primary'], height=70)
        header_frame.pack(fill='x', pady=(0, 20))
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="⚙️ إعدادات الشركة والفاتورة",
                font=('Segoe UI', 18, 'bold'),
                bg=self.colors['primary'], fg='white').pack(expand=True)
        
        # إطار المحتوى
        content_frame = tk.Frame(main_container, bg=self.colors['card'], relief='flat', bd=0)
        content_frame.pack(fill='both', expand=False, padx=10, pady=(10, 0))
        
        # إنشاء دفتر ملاحظات للتنظيم
        notebook = ttk.Notebook(content_frame)
        notebook.pack(fill='both', expand=True, padx=10, pady=(10, 10))
        
        # تبويب المعلومات الأساسية
        basic_frame = tk.Frame(notebook, bg=self.colors['card'])
        notebook.add(basic_frame, text="🏢 المعلومات الأساسية")
        
        tk.Label(basic_frame, text="معلومات الشركة الأساسية",
                font=('Segoe UI', 14, 'bold'),
                bg=self.colors['card'], fg=self.colors['text']).pack(pady=15)
        
        fields_basic = [
            ("اسم الشركة بالعربية:", "company_name_ar"),
            ("اسم الشركة بالإنجليزية:", "company_name_en"),
            ("اسم صاحب المؤسسة:", "owner_name"),
            ("الرقم الضريبي:", "tax_number"),
            ("السجل التجاري:", "commercial_register"),
        ]
        
        self.entries = {}
        for i, (label, field) in enumerate(fields_basic):
            frame = tk.Frame(basic_frame, bg=self.colors['card'])
            frame.pack(fill='x', padx=30, pady=8)
            
            tk.Label(frame, text=label, font=('Segoe UI', 11, 'bold'),
                    bg=self.colors['card'], fg=self.colors['text']).pack(side='right', padx=(0, 10))
            entry = ttk.Entry(frame, width=45, font=('Segoe UI', 10))
            entry.pack(side='right', fill='x', expand=True)
            self.entries[field] = entry
        
        # تبويب معلومات الاتصال
        contact_frame = tk.Frame(notebook, bg=self.colors['card'])
        notebook.add(contact_frame, text="📞 معلومات الاتصال")
        
        tk.Label(contact_frame, text="معلومات الاتصال",
                font=('Segoe UI', 14, 'bold'),
                bg=self.colors['card'], fg=self.colors['text']).pack(pady=15)
        
        fields_contact = [
            ("العنوان بالعربية:", "address"),
            ("العنوان بالإنجليزية:", "address_en"),
            ("الجوال الأول:", "phone1"),
            ("الجوال الثاني:", "phone2"),
            ("صندوق البريد:", "po_box"),
            ("الرمز البريدي:", "postal_code"),
            ("البريد الإلكتروني:", "email"),
            ("الموقع الإلكتروني:", "website")
        ]
        
        for label, field in fields_contact:
            frame = tk.Frame(contact_frame, bg=self.colors['card'])
            frame.pack(fill='x', padx=30, pady=8)
            
            tk.Label(frame, text=label, font=('Segoe UI', 11, 'bold'),
                    bg=self.colors['card'], fg=self.colors['text']).pack(side='right', padx=(0, 10))
            entry = ttk.Entry(frame, width=45, font=('Segoe UI', 10))
            entry.pack(side='right', fill='x', expand=True)
            self.entries[field] = entry
        
        # تعبئة الحقول بالإعدادات الحالية
        for field, entry in self.entries.items():
            if field in self.settings:
                entry.insert(0, self.settings[field])
        
        # إطار الأزرار - وضعه في main_container خارج content_frame
        btn_frame = tk.Frame(main_container, bg=self.colors['bg'])
        btn_frame.pack(fill='x', pady=15)
        
        save_btn = ModernButton(btn_frame, text="💾 حفظ الإعدادات",
                              bg=self.colors['success'], fg='white',
                              command=self.save_settings)
        save_btn.pack(side='right', padx=5, ipadx=20, ipady=10)
        
        reset_btn = ModernButton(btn_frame, text="🔄 استعادة الافتراضي",
                               bg=self.colors['warning'], fg='white',
                               command=self.reset_defaults)
        reset_btn.pack(side='right', padx=5, ipadx=20, ipady=10)
        
        cancel_btn = ModernButton(btn_frame, text="❌ إلغاء",
                                 bg=self.colors['danger'], fg='white',
                                 command=self.destroy)
        cancel_btn.pack(side='right', padx=5, ipadx=20, ipady=10)
    
    def save_settings(self):
        try:
            # جمع البيانات من الحقول
            for field, entry in self.entries.items():
                self.settings[field] = entry.get()
            
            # حفظ في قاعدة البيانات - جميع الأعمدة الجديدة
            existing = self.db.execute_query("SELECT id FROM company_settings WHERE id = 1")
            if existing:
                self.db.execute_query(
                    """UPDATE company_settings SET 
                        company_name_ar=?, company_name_en=?, owner_name=?, tax_number=?, 
                        commercial_register=?, address=?, address_en=?, phone1=?, phone2=?, 
                        po_box=?, postal_code=?, email=?, website=?
                    WHERE id = 1""",
                    (self.settings.get('company_name_ar', ''),
                     self.settings.get('company_name_en', ''),
                     self.settings.get('owner_name', ''),
                     self.settings.get('tax_number', ''),
                     self.settings.get('commercial_register', ''),
                     self.settings.get('address', ''),
                     self.settings.get('address_en', ''),
                     self.settings.get('phone1', ''),
                     self.settings.get('phone2', ''),
                     self.settings.get('po_box', ''),
                     self.settings.get('postal_code', ''),
                     self.settings.get('email', ''),
                     self.settings.get('website', ''))
                )
            else:
                self.db.execute_query(
                    """INSERT INTO company_settings 
                        (id, company_name_ar, company_name_en, owner_name, tax_number, commercial_register,
                         address, address_en, phone1, phone2, po_box, postal_code, email, website) 
                    VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (self.settings.get('company_name_ar', ''),
                     self.settings.get('company_name_en', ''),
                     self.settings.get('owner_name', ''),
                     self.settings.get('tax_number', ''),
                     self.settings.get('commercial_register', ''),
                     self.settings.get('address', ''),
                     self.settings.get('address_en', ''),
                     self.settings.get('phone1', ''),
                     self.settings.get('phone2', ''),
                     self.settings.get('po_box', ''),
                     self.settings.get('postal_code', ''),
                     self.settings.get('email', ''),
                     self.settings.get('website', ''))
                )
            
            self.status_callback("✅ تم حفظ إعدادات الشركة بنجاح")
            messagebox.showinfo("نجاح", "✅ تم حفظ إعدادات الشركة بنجاح")
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حفظ الإعدادات: {str(e)}")
    
    def reset_defaults(self):
        if messagebox.askyesno("تأكيد", "⚠️ هل أنت متأكد من استعادة الإعدادات الافتراضية؟"):
            # حذف الحقول الحالية
            for entry in self.entries.values():
                entry.delete(0, tk.END)
            
            # إعادة تعيين الإعدادات
            self.settings = {
                'company_name_ar': 'محمد بن منير بن محمد سعيد دغستاني',
                'company_name_en': 'Mohammed bin Munir bin Mohammed Saeed Daghestani',
                'owner_name': 'محمد بن منير دغستاني',
                'tax_number': '300262161400003',
                'commercial_register': '4030330926',
                'address': 'جدة - أبحر الشمالية - شارع أبي محمد العطار',
                'address_en': 'Jeddah - Obhur Al Shamaliah - Abi Mohammed Al Attar St.',
                'phone1': '0582224122',
                'phone2': '0538833640',
                'po_box': '117332',
                'postal_code': '21391',
                'email': 'seapearl.est@gmail.com',
                'website': ''
            }
            
            # تعبئة الحقول بالإعدادات الافتراضية
            for field, entry in self.entries.items():
                if field in self.settings:
                    entry.insert(0, self.settings[field])

def get_company_settings(db):
    """دالة للحصول على إعدادات الشركة الحالية"""
    settings = db.execute_query("""
        SELECT company_name_ar, company_name_en, owner_name, tax_number, commercial_register,
               address, address_en, phone1, phone2, po_box, postal_code, email, website 
        FROM company_settings WHERE id = 1
    """)
    if settings and settings[0]:
        s = settings[0]
        return {
            'company_name_ar': s[0] if s[0] else 'محمد بن منير بن محمد سعيد دغستاني',
            'company_name_en': s[1] if s[1] else 'Mohammed bin Munir bin Mohammed Saeed Daghestani',
            'owner_name': s[2] if s[2] else 'محمد بن منير دغستاني',
            'tax_number': s[3] if s[3] else '300262161400003',
            'commercial_register': s[4] if s[4] else '4030330926',
            'address': s[5] if s[5] else 'جدة - أبحر الشمالية - شارع أبي محمد العطار',
            'address_en': s[6] if s[6] else 'Jeddah - Obhur Al Shamaliah - Abi Mohammed Al Attar St.',
            'phone1': s[7] if s[7] else '0582224122',
            'phone2': s[8] if s[8] else '0538833640',
            'po_box': s[9] if s[9] else '117332',
            'postal_code': s[10] if s[10] else '21391',
            'email': s[11] if s[11] else 'seapearl.est@gmail.com',
            'website': s[12] if s[12] else ''
        }
    else:
        # إعدادات افتراضية
        return {
            'company_name_ar': 'محمد بن منير بن محمد سعيد دغستاني',
            'company_name_en': 'Mohammed bin Munir bin Mohammed Saeed Daghestani',
            'owner_name': 'محمد بن منير دغستاني',
            'tax_number': '300262161400003',
            'commercial_register': '4030330926',
            'address': 'جدة - أبحر الشمالية - شارع أبي محمد العطار',
            'address_en': 'Jeddah - Obhur Al Shamaliah - Abi Mohammed Al Attar St.',
            'phone1': '0582224122',
            'phone2': '0538833640',
            'po_box': '117332',
            'postal_code': '21391',
            'email': 'seapearl.est@gmail.com',
            'website': ''
        }
