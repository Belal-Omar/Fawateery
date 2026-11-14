import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from database import Database
import calendar
import pandas as pd
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

from employees_new import EmployeeDialog

class SalaryDialog(tk.Toplevel):
    def __init__(self, parent, db, status_callback, employee_data):
        super().__init__(parent)
        self.db = db
        self.status_callback = status_callback
        self.employee_data = employee_data
        
        # ألوان
        self.colors = {
            'bg': '#F5F6FA',
            'card': '#FFFFFF',
            'success': '#27AE60',
            'text': '#2C3E50',
            'text_light': '#7F8C8D'
        }
        
        self.setup_dialog()
        self.create_widgets()
    
    def setup_dialog(self):
        self.title(f"💰 دفع راتب للموظف: {self.employee_data[1]}")
        self.geometry("600x550")
        self.resizable(False, False)
        self.configure(bg=self.colors['bg'])
        self.transient(self.master)
        self.grab_set()
    
    def create_widgets(self):
        # إطار رئيسي
        main_frame = tk.Frame(self, bg=self.colors['bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # بطاقة العنوان
        title_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        title_card.pack(fill='x', pady=(0, 20))
        
        title_label = tk.Label(title_card, text=f"💰 دفع راتب - {self.employee_data[1]}",
                               font=('Segoe UI', 14, 'bold'),
                               bg=self.colors['card'], fg=self.colors['text'])
        title_label.pack(pady=15)
        
        # بطاقة الحقول
        fields_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        fields_card.pack(fill='both', expand=True, pady=(0, 20))
        
        fields_frame = tk.Frame(fields_card, bg=self.colors['card'])
        fields_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # الشهر والسنة
        row_frame = tk.Frame(fields_frame, bg=self.colors['card'])
        row_frame.pack(fill='x', pady=10)
        
        tk.Label(row_frame, text="الشهر والسنة:", font=('Segoe UI', 10, 'bold'),
                bg=self.colors['card'], fg=self.colors['text']).pack(side='right', padx=(0, 10))
        
        self.month_year = ttk.Entry(row_frame, width=25, font=('Segoe UI', 10))
        self.month_year.insert(0, datetime.now().strftime("%Y-%m"))
        self.month_year.pack(side='right', fill='x', expand=True, ipady=5)
        
        # الراتب الأساسي
        row_frame = tk.Frame(fields_frame, bg=self.colors['card'])
        row_frame.pack(fill='x', pady=10)
        
        tk.Label(row_frame, text="الراتب الأساسي:", font=('Segoe UI', 10, 'bold'),
                bg=self.colors['card'], fg=self.colors['text']).pack(side='right', padx=(0, 10))
        
        self.basic_salary = tk.Label(row_frame, text=f"{float(self.employee_data[3]):.2f} ريال",
                                    font=('Segoe UI', 11),
                                    bg=self.colors['card'], fg=self.colors['text'])
        self.basic_salary.pack(side='right')
        
        # المكافآت
        row_frame = tk.Frame(fields_frame, bg=self.colors['card'])
        row_frame.pack(fill='x', pady=10)
        
        tk.Label(row_frame, text="المكافآت:", font=('Segoe UI', 10, 'bold'),
                bg=self.colors['card'], fg=self.colors['text']).pack(side='right', padx=(0, 10))
        
        self.bonuses = ttk.Entry(row_frame, width=25, font=('Segoe UI', 10))
        self.bonuses.insert(0, "0")
        self.bonuses.pack(side='right', fill='x', expand=True, ipady=5)
        
        # الخصومات
        row_frame = tk.Frame(fields_frame, bg=self.colors['card'])
        row_frame.pack(fill='x', pady=10)
        
        tk.Label(row_frame, text="الخصومات:", font=('Segoe UI', 10, 'bold'),
                bg=self.colors['card'], fg=self.colors['text']).pack(side='right', padx=(0, 10))
        
        self.deductions = ttk.Entry(row_frame, width=25, font=('Segoe UI', 10))
        self.deductions.insert(0, "0")
        self.deductions.pack(side='right', fill='x', expand=True, ipady=5)
        
        # صافي الراتب
        row_frame = tk.Frame(fields_frame, bg=self.colors['card'])
        row_frame.pack(fill='x', pady=10)
        
        tk.Label(row_frame, text="صافي الراتب:", font=('Segoe UI', 11, 'bold'),
                bg=self.colors['card'], fg=self.colors['text']).pack(side='right', padx=(0, 10))
        
        self.net_salary = tk.Label(row_frame, text=f"{float(self.employee_data[3]):.2f} ريال",
                                   font=('Segoe UI', 12, 'bold'),
                                   bg=self.colors['card'], fg=self.colors['success'])
        self.net_salary.pack(side='right')
        
        # تاريخ الدفع
        row_frame = tk.Frame(fields_frame, bg=self.colors['card'])
        row_frame.pack(fill='x', pady=10)
        
        tk.Label(row_frame, text="تاريخ الدفع:", font=('Segoe UI', 10, 'bold'),
                bg=self.colors['card'], fg=self.colors['text']).pack(side='right', padx=(0, 10))
        
        self.payment_date = ttk.Entry(row_frame, width=25, font=('Segoe UI', 10))
        self.payment_date.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.payment_date.pack(side='right', fill='x', expand=True, ipady=5)
        
        # ربط الأحداث لحساب صافي الراتب
        self.bonuses.bind('<KeyRelease>', self.calculate_net_salary)
        self.deductions.bind('<KeyRelease>', self.calculate_net_salary)
        
        # أزرار الحفظ - واضحة
        btn_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        btn_frame.pack(fill='x')
        
        save_btn = ModernButton(btn_frame, text="💾 حفظ",
                               bg=self.colors['success'], fg='white',
                               command=self.save_salary)
        save_btn.pack(side='right', padx=5)
        
        cancel_btn = ModernButton(btn_frame, text="❌ إلغاء",
                                  bg='#95A5A6', fg='white',
                                  command=self.destroy)
        cancel_btn.pack(side='right', padx=5)
    
    def calculate_net_salary(self, event=None):
        try:
            basic = float(self.employee_data[3])
            bonuses = float(self.bonuses.get() or 0)
            deductions = float(self.deductions.get() or 0)
            net = basic + bonuses - deductions
            self.net_salary.config(text=f"{net:.2f} ريال")
        except ValueError:
            pass
    
    def save_salary(self):
        try:
            month_year = self.month_year.get()
            basic_salary = float(self.employee_data[3])
            bonuses = float(self.bonuses.get() or 0)
            deductions = float(self.deductions.get() or 0)
            net_salary_text = self.net_salary.cget("text").replace(" ريال", "").strip()
            net_salary = float(net_salary_text)
            payment_date = self.payment_date.get()
            
            # التحقق من عدم دفع الراتب لنفس الشهر مرتين
            existing = self.db.execute_query(
                "SELECT id FROM salaries WHERE employee_id = ? AND month_year = ?",
                (self.employee_data[0], month_year)
            )
            
            if existing:
                messagebox.showerror("خطأ", "❌ تم دفع راتب هذا الموظف لهذا الشهر بالفعل")
                return
            
            # حفظ الراتب
            self.db.execute_query(
                "INSERT INTO salaries (employee_id, month_year, basic_salary, bonuses, deductions, net_salary, payment_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (self.employee_data[0], month_year, basic_salary, bonuses, deductions, net_salary, payment_date)
            )
            
            # تسجيل المعاملة كمصروف
            self.db.execute_query(
                "INSERT INTO transactions (type, amount, description, date, category) VALUES (?, ?, ?, ?, ?)",
                ('expense', net_salary, f"راتب {self.employee_data[1]} لشهر {month_year}", payment_date, 'salaries')
            )
            
            self.status_callback(f"✅ تم دفع راتب {self.employee_data[1]} لشهر {month_year} بمبلغ {net_salary:.2f}")
            self.destroy()
            
            # إرسال إشارة التحديث الفوري
            emit_employee_change(self.employee_data[0])
            
        except ValueError:
            messagebox.showerror("خطأ", "❌ يجب إدخال قيم رقمية للمكافآت والخصومات")
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حفظ بيانات الراتب: {str(e)}")

class EmployeesModule:
    def __init__(self, notebook, status_callback):
        self.db = Database()
        self.status_callback = status_callback
        self.frame = ttk.Frame(notebook)
        
        # إنشاء ScrollArea للتبويب
        self.create_scrollable_content()
        
        self.create_widgets()
        self.load_employees()
    
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
        main_frame = ttk.Frame(self.content_frame)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill='x', pady=(0, 20))
        
        ttk.Label(title_frame, text="👨‍💼 إدارة الموظفين والرواتب", 
                 font=('Segoe UI', 16, 'bold')).pack(pady=10)
        
        quick_actions = ttk.Frame(main_frame)
        quick_actions.pack(fill='x', pady=(0, 15))
        
        btn1 = ttk.Button(quick_actions, text="➕ موظف جديد", command=self.add_employee,
                  width=15)
        btn1.pack(side='left', padx=5, ipady=6)
        btn2 = ttk.Button(quick_actions, text="💰 دفع رواتب", command=self.pay_salaries_batch,
                  width=15)
        btn2.pack(side='left', padx=5, ipady=6)
        btn3 = ttk.Button(quick_actions, text="📊 تقارير الرواتب", command=self.show_salary_reports,
                  width=15)
        btn3.pack(side='left', padx=5, ipady=6)
        
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="بحث:", font=('Segoe UI', 10)).pack(side='left', padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30, font=('Segoe UI', 10))
        self.search_entry.pack(side='left', padx=5, ipady=4)
        self.search_entry.bind('<KeyRelease>', self.search_employees)
        
        ttk.Button(search_frame, text="بحث", command=self.search_employees).pack(side='left', padx=5, ipady=4)
        ttk.Button(search_frame, text="عرض الكل", command=self.load_employees).pack(side='left', padx=5, ipady=4)
        
        tree_frame = ttk.LabelFrame(main_frame, text="قائمة الموظفين")
        tree_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        self.tree = ttk.Treeview(tree_frame, columns=('id', 'name', 'position', 'salary', 'hire_date', 'project'), show='headings', height=15)
        
        columns = [
            ('id', 'ID', 50),
            ('name', 'الاسم', 150),
            ('position', 'الوظيفة', 120),
            ('salary', 'الراتب', 100),
            ('hire_date', 'تاريخ التعيين', 100),
            ('project', 'المشروع', 150)
        ]
        
        for col, heading, width in columns:
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width)
        
        self.tree.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill='x')
        
        control_buttons = [
            ("👁️ عرض", self.view_employee),
            ("✏️ تعديل", self.edit_employee),
            ("💰 راتب", self.pay_salary),
            ("🗑️ حذف", self.delete_employee),
            ("📋 سجل الرواتب", self.view_salary_history)
        ]
        
        for text, command in control_buttons:
            btn = ttk.Button(control_frame, text=text, command=command)
            btn.pack(side='left', padx=5, ipady=6)
        
        self.tree.bind('<Double-1>', lambda e: self.view_employee())
    
    def add_employee(self):
        EmployeeDialog(self.frame, self.db, self.status_callback, self.load_employees)
    
    def edit_employee(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار موظف لتعديله")
            return
        
        employee_id = self.tree.item(selected[0], 'values')[0]
        EmployeeDialog(self.frame, self.db, self.status_callback, self.load_employees, employee_id)
    
    def view_employee(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار موظف لعرضه")
            return
        
        employee_id = self.tree.item(selected[0], 'values')[0]
        employee = self.db.execute_query("SELECT * FROM employees WHERE id = ?", (employee_id,))
        
        if employee:
            employee = employee[0]
            project_name = "لا يوجد"
            if employee[7]:
                project = self.db.execute_query("SELECT name FROM projects WHERE id = ?", (employee[7],))
                if project:
                    project_name = project[0][0]
            
            # ألوان
            colors = {
                'bg': '#F5F6FA',
                'card': '#FFFFFF',
                'primary': '#3498DB',
                'warning': '#F39C12',
                'text': '#2C3E50',
                'text_light': '#7F8C8D'
            }
            
            # نافذة عرض أكبر وأوضح
            view_window = tk.Toplevel(self.frame)
            view_window.title(f"👁️ عرض بيانات الموظف - {employee[1]}")
            view_window.geometry("600x500")
            view_window.configure(bg=colors['bg'])
            view_window.transient(self.frame)
            view_window.grab_set()
            
            # إطار رئيسي
            main_frame = tk.Frame(view_window, bg=colors['bg'])
            main_frame.pack(fill='both', expand=True, padx=30, pady=30)
            
            # بطاقة العنوان
            title_card = tk.Frame(main_frame, bg=colors['card'], relief=tk.RAISED, bd=1)
            title_card.pack(fill='x', pady=(0, 20))
            
            title_label = tk.Label(title_card, text=f"👁️ بيانات الموظف: {employee[1]}",
                                   font=('Segoe UI', 16, 'bold'),
                                   bg=colors['card'], fg=colors['text'])
            title_label.pack(pady=20)
            
            # بطاقة البيانات
            data_card = tk.Frame(main_frame, bg=colors['card'], relief=tk.RAISED, bd=1)
            data_card.pack(fill='both', expand=True, pady=(0, 20))
            
            data_frame = tk.Frame(data_card, bg=colors['card'])
            data_frame.pack(fill='both', expand=True, padx=25, pady=25)
            
            # البيانات
            fields = [
                ("الاسم:", employee[1]),
                ("الوظيفة:", employee[2]),
                ("الراتب:", f"{employee[3]:.2f} ريال"),
                ("تاريخ التعيين:", employee[4]),
                ("الهاتف:", employee[5] or 'غير متوفر'),
                ("العنوان:", employee[6] or 'غير متوفر'),
                ("المشروع:", project_name)
            ]
            
            for label, value in fields:
                row_frame = tk.Frame(data_frame, bg=colors['card'])
                row_frame.pack(fill='x', pady=12)
                
                tk.Label(row_frame, text=label, font=('Segoe UI', 11, 'bold'),
                        bg=colors['card'], fg=colors['text_light']).pack(side='right', padx=(0, 15))
                
                tk.Label(row_frame, text=str(value), font=('Segoe UI', 12),
                        bg=colors['card'], fg=colors['text']).pack(side='right')
            
            # أزرار
            btn_frame = tk.Frame(main_frame, bg=colors['bg'])
            btn_frame.pack(fill='x')
            
            edit_btn = tk.Button(btn_frame, text="✏️ تعديل",
                                bg=colors['warning'], fg='white',
                                font=('Segoe UI', 10, 'bold'),
                                relief=tk.FLAT, padx=15, pady=8,
                                cursor='hand2',
                                command=lambda: [view_window.destroy(), self.edit_employee()])
            edit_btn.pack(side='right', padx=5)
            
            close_btn = tk.Button(btn_frame, text="❌ إغلاق",
                                bg='#95A5A6', fg='white',
                                font=('Segoe UI', 10, 'bold'),
                                relief=tk.FLAT, padx=15, pady=8,
                                cursor='hand2',
                                command=view_window.destroy)
            close_btn.pack(side='right', padx=5)
    
    def pay_salary(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار موظف لدفع راتبه")
            return
        
        employee_data = self.tree.item(selected[0], 'values')
        SalaryDialog(self.frame, self.db, self.status_callback, employee_data)
    
    def pay_salaries_batch(self):
        employees = self.db.execute_query("SELECT id, name, position, salary FROM employees")
        if not employees:
            messagebox.showinfo("دفع الرواتب", "❌ لا توجد موظفين في النظام")
            return
        
        total_salaries = sum(emp[3] for emp in employees)
        if messagebox.askyesno("دفع الرواتب", 
                             f"هل تريد دفع رواتب جميع الموظفين؟\n\nإجمالي المبلغ: {total_salaries:.2f} ريال\nعدد الموظفين: {len(employees)}"):
            current_month = datetime.now().strftime("%Y-%m")
            for emp in employees:
                # التحقق من عدم دفع الراتب مسبقاً
                existing = self.db.execute_query(
                    "SELECT id FROM salaries WHERE employee_id = ? AND month_year = ?",
                    (emp[0], current_month)
                )
                
                if not existing:
                    self.db.execute_query(
                        "INSERT INTO salaries (employee_id, month_year, basic_salary, bonuses, deductions, net_salary, payment_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (emp[0], current_month, emp[3], 0, 0, emp[3], datetime.now().strftime('%Y-%m-%d'))
                    )
            
            self.status_callback(f"✅ تم دفع رواتب {len(employees)} موظف")
            messagebox.showinfo("نجاح", f"✅ تم دفع رواتب جميع الموظفين بنجاح")
    
    def view_salary_history(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار موظف")
            return
        
        employee_id = self.tree.item(selected[0], 'values')[0]
        employee_name = self.tree.item(selected[0], 'values')[1]
        
        salaries = self.db.execute_query(
            "SELECT month_year, basic_salary, bonuses, deductions, net_salary, payment_date FROM salaries WHERE employee_id = ? ORDER BY month_year DESC",
            (employee_id,)
        )
        
        # ألوان
        colors = {
            'bg': '#F5F6FA',
            'card': '#FFFFFF',
            'primary': '#3498DB',
            'text': '#2C3E50',
            'text_light': '#7F8C8D'
        }
        
        # نافذة سجل الرواتب - أكبر وأوضح
        history_window = tk.Toplevel(self.frame)
        history_window.title(f"📋 سجل رواتب الموظف - {employee_name}")
        history_window.geometry("700x550")
        history_window.configure(bg=colors['bg'])
        history_window.transient(self.frame)
        history_window.grab_set()
        
        # إطار رئيسي
        main_frame = tk.Frame(history_window, bg=colors['bg'])
        main_frame.pack(fill='both', expand=True, padx=25, pady=25)
        
        # بطاقة العنوان
        title_card = tk.Frame(main_frame, bg=colors['card'], relief=tk.RAISED, bd=1)
        title_card.pack(fill='x', pady=(0, 20))
        
        title_label = tk.Label(title_card, text=f"📋 سجل رواتب الموظف: {employee_name}",
                              font=('Segoe UI', 16, 'bold'),
                              bg=colors['card'], fg=colors['text'])
        title_label.pack(pady=15)
        
        if salaries:
            # بطاقة الجدول
            table_card = tk.Frame(main_frame, bg=colors['card'], relief=tk.RAISED, bd=1)
            table_card.pack(fill='both', expand=True, pady=(0, 20))
            
            table_frame = tk.Frame(table_card, bg=colors['card'])
            table_frame.pack(fill='both', expand=True, padx=15, pady=15)
            
            # جدول الرواتب
            columns = ('month_year', 'basic_salary', 'bonuses', 'deductions', 'net_salary', 'payment_date')
            tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)
            
            tree.heading('month_year', text='الشهر')
            tree.heading('basic_salary', text='الراتب الأساسي')
            tree.heading('bonuses', text='المكافآت')
            tree.heading('deductions', text='الخصومات')
            tree.heading('net_salary', text='صافي الراتب')
            tree.heading('payment_date', text='تاريخ الدفع')
            
            tree.column('month_year', width=120)
            tree.column('basic_salary', width=120)
            tree.column('bonuses', width=100)
            tree.column('deductions', width=100)
            tree.column('net_salary', width=120)
            tree.column('payment_date', width=120)
            
            total_net = 0
            for salary in salaries:
                tree.insert('', 'end', values=(
                    salary[0],
                    f"{salary[1]:.2f}",
                    f"{salary[2]:.2f}",
                    f"{salary[3]:.2f}",
                    f"{salary[4]:.2f}",
                    salary[5]
                ))
                total_net += salary[4]
            
            tree.pack(side='left', fill='both', expand=True)
            
            scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
            scrollbar.pack(side='right', fill='y')
            tree.configure(yscrollcommand=scrollbar.set)
            
            # بطاقة الإجمالي
            total_card = tk.Frame(main_frame, bg=colors['primary'], relief=tk.RAISED, bd=1)
            total_card.pack(fill='x', pady=(0, 20))
            
            total_frame = tk.Frame(total_card, bg=colors['primary'])
            total_frame.pack(padx=20, pady=15)
            
            tk.Label(total_frame, text=f"💰 إجمالي المدفوع: {total_net:,.2f} ريال",
                    font=('Segoe UI', 14, 'bold'),
                    bg=colors['primary'], fg='white').pack()
            
            tk.Label(total_frame, text=f"📊 عدد الرواتب: {len(salaries)}",
                    font=('Segoe UI', 12),
                    bg=colors['primary'], fg='white').pack(pady=(5, 0))
        else:
            # لا توجد رواتب
            no_data_card = tk.Frame(main_frame, bg=colors['card'], relief=tk.RAISED, bd=1)
            no_data_card.pack(fill='both', expand=True)
            
            no_data_frame = tk.Frame(no_data_card, bg=colors['card'])
            no_data_frame.pack(expand=True)
            
            tk.Label(no_data_frame, text="📭 لا توجد رواتب مسجلة",
                    font=('Segoe UI', 16, 'bold'),
                    bg=colors['card'], fg=colors['text_light']).pack(pady=50)
        
        # زر الإغلاق
        btn_frame = tk.Frame(main_frame, bg=colors['bg'])
        btn_frame.pack(fill='x')
        
        close_btn = tk.Button(btn_frame, text="❌ إغلاق",
                             bg='#95A5A6', fg='white',
                             font=('Segoe UI', 10, 'bold'),
                             relief=tk.FLAT, padx=15, pady=8,
                             cursor='hand2',
                             command=history_window.destroy)
        close_btn.pack(side='right', padx=5)
    
    def delete_employee(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار موظف لحذفه")
            return
        
        employee_id = self.tree.item(selected[0], 'values')[0]
        employee_name = self.tree.item(selected[0], 'values')[1]
        
        # التحقق من وجود رواتب مرتبطة
        salaries = self.db.execute_query("SELECT COUNT(*) FROM salaries WHERE employee_id = ?", (employee_id,))
        if salaries and salaries[0][0] > 0:
            messagebox.showerror("خطأ", "❌ لا يمكن حذف الموظف لأنه مرتبط برواتب مسجلة")
            return
        
        if messagebox.askyesno("تأكيد", f"⚠️ هل أنت متأكد من حذف الموظف {employee_name}؟"):
            try:
                self.db.execute_query("DELETE FROM employees WHERE id = ?", (employee_id,))
                self.status_callback(f"✅ تم حذف الموظف: {employee_name}")
                self.load_employees()
            except Exception as e:
                messagebox.showerror("خطأ", f"❌ فشل في حذف الموظف: {str(e)}")
    
    def show_salary_reports(self):
        total_employees = len(self.db.execute_query("SELECT id FROM employees"))
        total_salaries = self.db.execute_query("SELECT SUM(salary) FROM employees")[0][0] or 0
        current_month = datetime.now().strftime("%Y-%m")
        paid_this_month = len(self.db.execute_query(
            "SELECT id FROM salaries WHERE month_year = ?", (current_month,)
        ))
        
        # ألوان
        colors = {
            'bg': '#F5F6FA',
            'card': '#FFFFFF',
            'primary': '#3498DB',
            'success': '#27AE60',
            'warning': '#F39C12',
            'text': '#2C3E50',
            'text_light': '#7F8C8D'
        }
        
        # نافذة التقارير - أكبر وأوضح
        reports_window = tk.Toplevel(self.frame)
        reports_window.title("📊 تقارير الرواتب")
        reports_window.geometry("650x500")
        reports_window.configure(bg=colors['bg'])
        reports_window.transient(self.frame)
        reports_window.grab_set()
        
        # إطار رئيسي
        main_frame = tk.Frame(reports_window, bg=colors['bg'])
        main_frame.pack(fill='both', expand=True, padx=30, pady=30)
        
        # بطاقة العنوان
        title_card = tk.Frame(main_frame, bg=colors['card'], relief=tk.RAISED, bd=1)
        title_card.pack(fill='x', pady=(0, 20))
        
        title_label = tk.Label(title_card, text="📊 تقارير وإحصائيات الرواتب",
                              font=('Segoe UI', 16, 'bold'),
                              bg=colors['card'], fg=colors['text'])
        title_label.pack(pady=20)
        
        # بطاقة الإحصائيات
        stats_card = tk.Frame(main_frame, bg=colors['card'], relief=tk.RAISED, bd=1)
        stats_card.pack(fill='both', expand=True, pady=(0, 20))
        
        stats_frame = tk.Frame(stats_card, bg=colors['card'])
        stats_frame.pack(fill='both', expand=True, padx=25, pady=25)
        
        stats = [
            ("إجمالي الموظفين", total_employees, colors['primary']),
            ("إجمالي الرواتب الشهرية", f"{total_salaries:,.2f} ريال", colors['success']),
            ("تم دفع رواتب هذا الشهر", paid_this_month, colors['success']),
            ("باقي الدفع", total_employees - paid_this_month, colors['warning'])
        ]
        
        for label, value, color in stats:
            stat_row = tk.Frame(stats_frame, bg=colors['card'], relief=tk.RAISED, bd=1)
            stat_row.pack(fill='x', pady=12, padx=5)
            
            inner_frame = tk.Frame(stat_row, bg=color)
            inner_frame.pack(fill='x', padx=2, pady=2)
            
            content_frame = tk.Frame(inner_frame, bg=color)
            content_frame.pack(fill='x', padx=15, pady=12)
            
            tk.Label(content_frame, text=label + ":", font=('Segoe UI', 12, 'bold'),
                    bg=color, fg='white').pack(side='right', padx=10)
            
            tk.Label(content_frame, text=str(value), font=('Segoe UI', 14, 'bold'),
                    bg=color, fg='white').pack(side='right', padx=10)
        
        # زر الإغلاق
        btn_frame = tk.Frame(main_frame, bg=colors['bg'])
        btn_frame.pack(fill='x')
        
        close_btn = tk.Button(btn_frame, text="❌ إغلاق",
                             bg='#95A5A6', fg='white',
                             font=('Segoe UI', 10, 'bold'),
                             relief=tk.FLAT, padx=15, pady=8,
                             cursor='hand2',
                             command=reports_window.destroy)
        close_btn.pack(side='right', padx=5)
    
    def search_employees(self, event=None):
        search_term = self.search_entry.get()
        if not search_term:
            self.load_employees()
            return
        
        query = '''
        SELECT e.id, e.name, e.position, e.salary, e.hire_date, p.name 
        FROM employees e 
        LEFT JOIN projects p ON e.project_id = p.id
        WHERE e.name LIKE ?
        ORDER BY e.name
        '''
        
        search_pattern = f'%{search_term}%'
        employees = self.db.execute_query(query, (search_pattern,))
        self.display_employees(employees)
    
    def load_employees(self):
        query = '''
        SELECT e.id, e.name, e.position, e.salary, e.hire_date, p.name 
        FROM employees e 
        LEFT JOIN projects p ON e.project_id = p.id
        ORDER BY e.name
        '''
        employees = self.db.execute_query(query)
        self.display_employees(employees)
    
    def display_employees(self, employees):
        self.tree.delete(*self.tree.get_children())
        for emp in employees:
            self.tree.insert('', 'end', values=(
                emp[0], emp[1], emp[2], f"{emp[3]:.2f}", emp[4], emp[5] or "لا يوجد"
            ))