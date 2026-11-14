import tkinter as tk
import arabic_entry_fix
from tkinter import ttk, messagebox
from datetime import datetime
from database import Database
from central_refresh import emit_employee_change

class ModernButton(tk.Button):
    """زر عصري محسن"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(relief=tk.FLAT, cursor='hand2', font=('Segoe UI', 10, 'bold'), padx=12, pady=6)
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
    
    def on_enter(self, e):
        self.configure(relief=tk.RAISED)
    
    def on_leave(self, e):
        self.configure(relief=tk.FLAT)

class EmployeeDialog(tk.Toplevel):
    """نافذة إضافة موظف جديدة بالكامل"""
    def __init__(self, parent, db, status_callback, refresh_callback, employee_id=None):
        super().__init__(parent)
        arabic_entry_fix.apply_arabic_entry_fix(self)
        self.db = db
        self.status_callback = status_callback
        self.refresh_callback = refresh_callback
        self.employee_id = employee_id
        
        # ألوان عصرية
        self.colors = {
            'bg': '#F8F9FA',
            'card': '#FFFFFF',
            'primary': '#4A90E2',
            'success': '#27AE60',
            'danger': '#E74C3C',
            'warning': '#F39C12',
            'text': '#2C3E50',
            'text_light': '#7F8C8D',
            'border': '#E1E8ED'
        }
        
        self.setup_dialog()
        self.create_widgets()
        
        if employee_id:
            self.load_employee_data()
    
    def setup_dialog(self):
        """إعداد النافذة"""
        self.title("👨‍💼 إضافة موظف جديد" if not self.employee_id else "✏️ تعديل بيانات الموظف")
        self.geometry("1200x1000")  # أعرض وأطول إلى الحد الأقصى
        self.resizable(True, True)
        self.configure(bg=self.colors['bg'])
        self.transient(self.master)
        self.grab_set()
        
        # توسيط النافذة
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """إنشاء جميع العناصر"""
        # إطار رئيسي أفقي
        main_container = tk.Frame(self, bg=self.colors['bg'])
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # إطار علوي للعنوان والأزرار
        top_frame = tk.Frame(main_container, bg=self.colors['bg'])
        top_frame.pack(fill='x', pady=(0, 20))
        
        # بطاقة العنوان
        self.create_title_card(top_frame)
        
        # بطاقة الأزرار
        self.create_button_card(top_frame)
        
        # إطار سفقي للبيانات (أفقي)
        data_frame = tk.Frame(main_container, bg=self.colors['bg'])
        data_frame.pack(fill='both', expand=True)
        
        # عمود يسار للبيانات الأساسية
        left_column = tk.Frame(data_frame, bg=self.colors['bg'])
        left_column.pack(side='right', fill='both', expand=True, padx=(0, 10))
        
        # عمود يمين للبيانات الإضافية والمشروع
        right_column = tk.Frame(data_frame, bg=self.colors['bg'])
        right_column.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        # بطاقة البيانات الأساسية (يسار)
        self.create_basic_info_card(left_column)
        
        # مسافة بين البطاقات
        tk.Frame(left_column, bg=self.colors['bg'], height=25).pack(fill='x')
        
        # بطاقة البيانات الإضافية (يمين)
        self.create_additional_info_card(right_column)
        
        # مسافة بين البطاقات
        tk.Frame(right_column, bg=self.colors['bg'], height=25).pack(fill='x')
        
        # بطاقة المشروع (يمين)
        self.create_project_card(right_column)
    
    def create_title_card(self, parent):
        """إنشاء بطاقة العنوان"""
        title_card = tk.Frame(parent, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        title_card.pack(fill='x', pady=(0, 15))
        
        # أيقونة وعنوان (أفقي)
        title_frame = tk.Frame(title_card, bg=self.colors['card'])
        title_frame.pack(fill='x', padx=20, pady=12)
        
        icon_label = tk.Label(title_frame, text="👨‍💼", 
                           font=('Segoe UI', 24), bg=self.colors['card'], fg=self.colors['primary'])
        icon_label.pack(side='right', padx=(0, 10))
        
        title_text = "إضافة موظف جديد" if not self.employee_id else "تعديل بيانات الموظف"
        title_label = tk.Label(title_frame, text=title_text,
                             font=('Segoe UI', 16, 'bold'), bg=self.colors['card'], fg=self.colors['text'])
        title_label.pack(side='right')
        
        # خط فاصل
        separator = tk.Frame(title_card, bg=self.colors['primary'], height=2)
        separator.pack(fill='x', side='bottom')
    
    def create_basic_info_card(self, parent):
        """إنشاء بطاقة البيانات الأساسية"""
        card = tk.Frame(parent, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        card.pack(fill='both', expand=True, pady=(0, 15))
        
        # عنوان البطاقة
        card_header = tk.Frame(card, bg=self.colors['primary'])
        card_header.pack(fill='x')
        
        tk.Label(card_header, text="📋 البيانات الأساسية", 
                font=('Segoe UI', 12, 'bold'), bg=self.colors['primary'], fg='white').pack(pady=8)
        
        # محتوى البطاقة
        card_content = tk.Frame(card, bg=self.colors['card'])
        card_content.pack(fill='both', expand=True, padx=15, pady=15)
        
        # الحقول الأساسية
        self.entries = {}
        
        # الاسم الكامل
        self.create_field(card_content, "الاسم الكامل *", "name", True, 0)
        
        # الوظيفة
        self.create_field(card_content, "الوظيفة *", "position", True, 1)
        
        # الهاتف
        self.create_field(card_content, "رقم الهاتف", "phone", False, 2)
        
        # البريد الإلكتروني
        self.create_field(card_content, "البريد الإلكتروني", "email", False, 3)
        
        # العنوان
        self.create_field(card_content, "العنوان", "address", False, 4)
    
    def create_additional_info_card(self, parent):
        """إنشاء بطاقة البيانات الإضافية"""
        card = tk.Frame(parent, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        card.pack(fill='x', pady=(0, 15))
        
        # عنوان البطاقة
        card_header = tk.Frame(card, bg=self.colors['warning'])
        card_header.pack(fill='x')
        
        tk.Label(card_header, text="📝 بيانات إضافية", 
                font=('Segoe UI', 12, 'bold'), bg=self.colors['warning'], fg='white').pack(pady=8)
        
        # محتوى البطاقة
        card_content = tk.Frame(card, bg=self.colors['card'])
        card_content.pack(fill='x', padx=15, pady=15)
        
        # القسم
        self.create_field(card_content, "القسم", "department", False, 0)
        
        # الراتب الأساسي
        self.create_field(card_content, "الراتب الأساسي", "salary", False, 1)
        
        # تاريخ التعيين (تلقائي)
        date_frame = tk.Frame(card_content, bg=self.colors['card'])
        date_frame.pack(fill='x', pady=20)  # زيادة من 15 إلى 20
        
        tk.Label(date_frame, text="تاريخ التعيين:", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['card'], fg=self.colors['text']).pack(side='right', padx=(0, 10))
        
        self.hire_date_label = tk.Label(date_frame, text=datetime.now().strftime('%Y-%m-%d'),
                                       font=('Segoe UI', 11), bg=self.colors['card'], fg=self.colors['success'])
        self.hire_date_label.pack(side='right')
        
        # رقم الهوية
        self.create_field(card_content, "رقم الهوية", "national_id", False, 2)
    
    def create_project_card(self, parent):
        """إنشاء بطاقة المشروع"""
        card = tk.Frame(parent, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        card.pack(fill='x', pady=(0, 15))
        
        # عنوان البطاقة
        card_header = tk.Frame(card, bg=self.colors['success'])
        card_header.pack(fill='x')
        
        tk.Label(card_header, text="🏢 المشروع", 
                font=('Segoe UI', 12, 'bold'), bg=self.colors['success'], fg='white').pack(pady=8)
        
        # محتوى البطاقة
        card_content = tk.Frame(card, bg=self.colors['card'])
        card_content.pack(fill='x', padx=15, pady=15)
        
        # تحميل المشاريع
        projects = self.db.execute_query("SELECT id, name FROM projects ORDER BY name")
        project_list = ["لا يوجد"] + [f"{p[0]} - {p[1]}" for p in projects]
        
        # حقل المشروع
        project_frame = tk.Frame(card_content, bg=self.colors['card'])
        project_frame.pack(fill='x', pady=25)  # زيادة من 20 إلى 25
        
        tk.Label(project_frame, text="المشروع:", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['card'], fg=self.colors['text']).pack(side='right', padx=(0, 10))
        
        self.project_combo = ttk.Combobox(project_frame, values=project_list, state='readonly',
                                         font=('Segoe UI', 11), width=35)
        self.project_combo.current(0)
        self.project_combo.pack(side='right', fill='x', expand=True, ipady=12)  # زيادة من 10 إلى 12
    
    def create_button_card(self, parent):
        """إنشاء بطاقة الأزرار"""
        card = tk.Frame(parent, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        card.pack(fill='x', pady=(15, 0))
        
        # محتوى البطاقة
        card_content = tk.Frame(card, bg=self.colors['card'])
        card_content.pack(fill='x', padx=20, pady=25)  # زيادة من 20 إلى 25
        
        # أزرار
        button_frame = tk.Frame(card_content, bg=self.colors['card'])
        button_frame.pack(fill='x')
        
        # زر الحفظ
        save_text = "💾 حفظ" if self.employee_id else "➕ إضافة موظف"
        save_btn = ModernButton(button_frame, text=save_text,
                             bg=self.colors['success'], fg='white',
                             command=self.save_employee)
        save_btn.pack(side='right', padx=(10, 0))
        
        # زر إلغاء
        cancel_btn = ModernButton(button_frame, text="❌ إلغاء",
                                bg=self.colors['danger'], fg='white',
                                command=self.destroy)
        cancel_btn.pack(side='right')
        
        # زر مسح (فقط في حالة التعديل)
        if self.employee_id:
            clear_btn = ModernButton(button_frame, text="🧹 مسح الحقول",
                                  bg=self.colors['warning'], fg='white',
                                  command=self.clear_fields)
            clear_btn.pack(side='left')
    
    def create_field(self, parent, label_text, field_name, required, row):
        """إنشاء حقل إدخال"""
        # إطار الحقل
        field_frame = tk.Frame(parent, bg=self.colors['card'])
        field_frame.pack(fill='x', pady=15)  # زيادة من 12 إلى 15
        
        # التسمية
        label = tk.Label(field_frame, text=label_text,
                        font=('Segoe UI', 11, 'bold'), bg=self.colors['card'], 
                        fg=self.colors['text'] if required else self.colors['text_light'])
        label.pack(side='right', padx=(0, 10))
        
        # حقل الإدخال
        justify_val = 'right' if field_name not in ['salary', 'national_id', 'phone'] else 'center'
        entry = ttk.Entry(field_frame, font=('Segoe UI', 11), width=40, justify=justify_val)
        entry.pack(side='right', fill='x', expand=True, ipady=12)  # زيادة من 10 إلى 12
        self.entries[field_name] = entry
        
        # قيمة افتراضية للراتب
        if field_name == 'salary':
            entry.insert(0, "0")
    
    def load_employee_data(self):
        """تحميل بيانات الموظف للتعديل"""
        try:
            employee = self.db.execute_query("SELECT * FROM employees WHERE id = ?", (self.employee_id,))
            if employee:
                emp = employee[0]
                self.entries['name'].insert(0, emp[1] or "")
                self.entries['position'].insert(0, emp[2] or "")
                self.entries['salary'].insert(0, str(emp[3]) if emp[3] else "0")
                self.entries['phone'].insert(0, emp[5] or "")
                self.entries['email'].insert(0, emp[6] or "")
                self.entries['address'].insert(0, emp[4] or "")
                
                # تحديث تاريخ التعيين
                if emp[4]:
                    self.hire_date_label.config(text=emp[4])
                
                # تحديد المشروع
                if emp[7]:
                    for i, proj in enumerate(self.project_combo['values']):
                        if str(emp[7]) in proj:
                            self.project_combo.current(i)
                            break
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تحميل بيانات الموظف: {str(e)}")
    
    def clear_fields(self):
        """مسح جميع الحقول"""
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.project_combo.current(0)
    
    def save_employee(self):
        """حفظ بيانات الموظف"""
        try:
            # التحقق من الحقول المطلوبة
            name = self.entries['name'].get().strip()
            position = self.entries['position'].get().strip()
            
            if not name:
                messagebox.showerror("خطأ", "❌ يرجى إدخال الاسم الكامل")
                self.entries['name'].focus()
                return
            
            if not position:
                messagebox.showerror("خطأ", "❌ يرجى إدخال الوظيفة")
                self.entries['position'].focus()
                return

            # التحقق من تكرار اسم الموظف والتنبيه
            chk_query = "SELECT id FROM employees WHERE name = ?" + (" AND id != ?" if self.employee_id else "")
            chk_params = (name, self.employee_id) if self.employee_id else (name,)
            existing_emp = self.db.execute_query(chk_query, chk_params)
            if existing_emp:
                msg = f"⚠️ تنبيه تكرار الاسم:\nاسم الموظف '{name}' مسجل مسبقاً في النظام!\n\nهل تريد بالتأكيد المتابعة وتسجيله مرة أخرى؟"
                if not messagebox.askyesno("تنبيه تكرار الاسم", msg, parent=self):
                    self.entries['name'].focus()
                    return
            
            # جمع البيانات
            phone = self.entries['phone'].get().strip()
            email = self.entries['email'].get().strip()
            address = self.entries['address'].get().strip()
            department = self.entries['department'].get().strip()
            salary_str = self.entries['salary'].get().strip()
            national_id = self.entries['national_id'].get().strip()
            
            # تحويل الراتب لرقم
            salary = 0.0
            if salary_str:
                try:
                    salary = float(salary_str)
                except ValueError:
                    messagebox.showerror("خطأ", "❌ الراتب يجب أن يكون رقمًا")
                    self.entries['salary'].focus()
                    return
            
            # تاريخ التعيين التلقائي
            hire_date = datetime.now().strftime('%Y-%m-%d')
            
            # المشروع
            project_id = None
            if self.project_combo.current() > 0:
                project_text = self.project_combo.get()
                if " - " in project_text:
                    project_id = int(project_text.split(' - ')[0].strip())
            
            # حفظ في قاعدة البيانات
            if self.employee_id:
                # تعديل موظف موجود
                self.db.execute_query("""
                    UPDATE employees SET name=?, position=?, salary=?, hire_date=?, 
                    phone=?, email=?, address=?, department=?, national_id=?, project_id=?
                    WHERE id=?
                """, (name, position, salary, hire_date, phone, email, address, department, 
                      national_id, project_id, self.employee_id))
                self.status_callback(f"✅ تم تحديث بيانات الموظف: {name}")
            else:
                # إضافة موظف جديد
                self.db.execute_query("""
                    INSERT INTO employees (name, position, salary, hire_date, phone, address, 
                    email, department, national_id, project_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, position, salary, hire_date, phone, address, email, department, 
                      national_id, project_id))
                self.status_callback(f"✅ تم إضافة الموظف: {name}")
            
            self.refresh_callback()
            self.destroy()
            
            # Send refresh signals
            emit_employee_change(self.employee_id)
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حفظ بيانات الموظف: {str(e)}")
            print(f"تفصيل الخطأ: {e}")

# مثال للاستخدام
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # إخفاء النافذة الرئيسية
    
    db = Database()
    
    def status_callback(msg):
        print(msg)
    
    def refresh_callback():
        print("تم تحديث القائمة")
    
    dialog = EmployeeDialog(root, db, status_callback, refresh_callback)
    root.mainloop()
