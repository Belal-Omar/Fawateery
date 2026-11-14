import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
from database import Database
import pandas as pd

class CustomerDialog(tk.Toplevel):
    def __init__(self, parent, db, status_callback, refresh_callback, customer_id=None):
        super().__init__(parent)
        self.db = db
        self.status_callback = status_callback
        self.refresh_callback = refresh_callback
        self.customer_id = customer_id
        
        self.setup_dialog()
        self.create_widgets()
        
        if customer_id:
            self.load_customer_data()
    
    def setup_dialog(self):
        self.title("👥 عميل جديد" if not self.customer_id else "✏️ تعديل العميل")
        w, h = 580, 520
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(0, (screen_w - w) // 2)
        y = max(0, (screen_h - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(500, 460)
        self.resizable(True, True)
        
        self.transient(self.master)
        self.grab_set()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=25, pady=15)
        
        # الأزرار في الأسفل أولاً لضمان عدم اختفائها أو قصها نهائياً
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side='bottom', fill='x', pady=(15, 5))
        
        ttk.Button(button_frame, text="💾 حفظ", command=self.save_customer).pack(side='left', padx=5, ipady=6, ipadx=10)
        ttk.Button(button_frame, text="❌ إلغاء", command=self.destroy).pack(side='right', padx=5, ipady=6, ipadx=10)
        
        # العنوان في الأعلى
        ttk.Label(main_frame, text="بيانات العميل", font=('Segoe UI', 16, 'bold')).pack(side='top', pady=(5, 12))
        
        # الحقول في الوسط
        field_frame = ttk.Frame(main_frame)
        field_frame.pack(side='top', fill='both', expand=True, pady=5)
        
        fields = [
            ("اسم العميل:", "name"),
            ("الرقم الضريبي:", "tax_number"),
            ("العنوان:", "address"),
            ("الهاتف:", "phone"),
            ("البريد الإلكتروني:", "email")
        ]
        
        self.entries = {}
        for i, (label, field) in enumerate(fields):
            ttk.Label(field_frame, text=label, font=('Segoe UI', 11, 'bold')).grid(row=i, column=0, padx=8, pady=7, sticky='e')
            entry = ttk.Entry(field_frame, width=32, font=('Segoe UI', 11), justify='right')
            entry.grid(row=i, column=1, padx=8, pady=7, sticky='w', ipady=5)
            self.entries[field] = entry
    
    def save_customer(self):
        try:
            name = self.entries['name'].get().strip()
            tax_number = self.entries['tax_number'].get().strip()
            address = self.entries['address'].get().strip()
            phone = self.entries['phone'].get().strip()
            email = self.entries['email'].get().strip()
            
            if not name:
                messagebox.showerror("خطأ", "❌ يرجى إدخال اسم العميل")
                return

            # التحقق من تكرار اسم العميل والتنبيه
            chk_query = "SELECT id FROM customers WHERE name = ?" + (" AND id != ?" if self.customer_id else "")
            chk_params = (name, self.customer_id) if self.customer_id else (name,)
            existing = self.db.execute_query(chk_query, chk_params)
            if existing:
                msg = f"⚠️ تنبيه تكرار الاسم:\nاسم العميل '{name}' مسجل مسبقاً في النظام!\n\nهل تريد بالتأكيد المتابعة وتسجيله مرة أخرى؟"
                if not messagebox.askyesno("تنبيه تكرار الاسم", msg, parent=self):
                    self.entries['name'].focus()
                    return
            
            if self.customer_id:
                # تعديل عميل موجود
                self.db.execute_query('''
                    UPDATE customers SET name=?, tax_number=?, address=?, phone=?, email=?
                    WHERE id=?
                ''', (name, tax_number, address, phone, email, self.customer_id))
                self.status_callback(f"✅ تم تحديث العميل: {name}")
            else:
                # إضافة عميل جديد
                self.db.execute_query('''
                    INSERT INTO customers (name, tax_number, address, phone, email)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, tax_number, address, phone, email))
                self.status_callback(f"✅ تم إضافة العميل: {name}")
            
            self.refresh_callback()
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حفظ العميل: {str(e)}")
    
    def load_customer_data(self):
        try:
            customer = self.db.execute_query("SELECT * FROM customers WHERE id = ?", (self.customer_id,))
            if customer:
                cust = customer[0]
                self.entries['name'].insert(0, cust[1])
                self.entries['tax_number'].insert(0, cust[2] or '')
                self.entries['address'].insert(0, cust[3] or '')
                self.entries['phone'].insert(0, cust[4] or '')
                self.entries['email'].insert(0, cust[5] or '')
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تحميل بيانات العميل: {str(e)}")

class ProjectDialog(tk.Toplevel):
    def __init__(self, parent, db, status_callback, refresh_callback, project_id=None):
        super().__init__(parent)
        self.db = db
        self.status_callback = status_callback
        self.refresh_callback = refresh_callback
        self.project_id = project_id
        
        self.setup_dialog()
        self.create_widgets()
        
        if project_id:
            self.load_project_data()
    
    def setup_dialog(self):
        self.title("🏗️ مشروع جديد" if not self.project_id else "✏️ تعديل المشروع")
        w, h = 640, 580
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(0, (screen_w - w) // 2)
        y = max(0, (screen_h - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(560, 500)
        self.resizable(True, True)
        
        self.transient(self.master)
        self.grab_set()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=25, pady=15)
        
        # أزرار الحفظ في الأسفل أولاً لضمان عدم اختفائها
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side='bottom', fill='x', pady=(15, 5))
        
        save_btn = ttk.Button(btn_frame, text="💾 حفظ", command=self.save_project, 
                  style='Modern.TButton')
        save_btn.pack(side='right', padx=8, ipadx=15, ipady=6)
        cancel_btn = ttk.Button(btn_frame, text="❌ إلغاء", command=self.destroy)
        cancel_btn.pack(side='left', padx=8, ipadx=15, ipady=6)
        
        # العنوان في الأعلى
        ttk.Label(main_frame, text="بيانات المشروع", font=('Segoe UI', 16, 'bold')).pack(side='top', pady=(5, 12))
        
        # الحقول
        field_frame = ttk.Frame(main_frame)
        field_frame.pack(side='top', fill='both', expand=True, pady=5)
        
        fields = [
            ("اسم المشروع:", "name"),
            ("تاريخ البدء:", "start_date"),
            ("اسم العميل:", "client_name")
        ]
        
        self.entries = {}
        for i, (label, field) in enumerate(fields):
            ttk.Label(field_frame, text=label, font=('Segoe UI', 11, 'bold'), width=16).grid(row=i, column=0, padx=8, pady=7, sticky='e')
            entry = ttk.Entry(field_frame, width=32, font=('Segoe UI', 11), justify='right')
            entry.grid(row=i, column=1, padx=8, pady=7, sticky='w', ipady=5)
            self.entries[field] = entry
            
            if field == 'start_date':
                entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        
        # حالة المشروع - حجم مناسب
        ttk.Label(field_frame, text="حالة المشروع:", font=('Segoe UI', 11, 'bold')).grid(row=5, column=0, padx=8, pady=7, sticky='e')
        self.status_combo = ttk.Combobox(field_frame, values=['قيد التنفيذ', 'مكتمل', 'متوقف', 'ملغى'], 
                                       state='readonly', width=30, font=('Segoe UI', 11))
        self.status_combo.current(0)
        self.status_combo.grid(row=5, column=1, padx=8, pady=7, sticky='w', ipady=4)
        
        # وصف المشروع - حجم مناسب
        ttk.Label(field_frame, text="وصف المشروع:", font=('Segoe UI', 11, 'bold')).grid(row=6, column=0, padx=8, pady=7, sticky='ne')
        self.description_text = tk.Text(field_frame, width=32, height=4, font=('Segoe UI', 11))
        self.description_text.grid(row=6, column=1, padx=8, pady=7, sticky='w')
    
    def load_project_data(self):
        if not self.project_id:
            return
        
        project = self.db.execute_query("SELECT * FROM projects WHERE id = ?", (self.project_id,))
        if project:
            project = project[0]
            self.entries['name'].insert(0, project[1])
            self.entries['start_date'].delete(0, tk.END)
            self.entries['start_date'].insert(0, project[2])
            # التحقق من وجود end_date
            if len(project) > 3 and project[3] and 'end_date' in self.entries:
                self.entries['end_date'].insert(0, project[3])
            # التحقق من وجود budget
            if len(project) > 4 and project[4] and 'budget' in self.entries:
                self.entries['budget'].insert(0, str(project[4]))
            
            # التحقق من وجود status
            if len(project) > 5 and project[5]:
                status_index = ['قيد التنفيذ', 'مكتمل', 'متوقف', 'ملغى'].index(project[5]) if project[5] in ['قيد التنفيذ', 'مكتمل', 'متوقف', 'ملغى'] else 0
                self.status_combo.current(status_index)
            
            # التحقق من وجود client_name
            if len(project) > 6 and project[6]:
                self.entries['client_name'].insert(0, project[6])
            
            # التحقق من وجود description
            if len(project) > 7 and project[7]:
                self.description_text.insert("1.0", project[7])
    
    def save_project(self):
        try:
            name = self.entries['name'].get()
            start_date = self.entries['start_date'].get()
            # التحقق من وجود end_date في entries
            end_date = None
            if 'end_date' in self.entries and self.entries['end_date'].get():
                end_date = self.entries['end_date'].get()
            
            # التحقق من وجود budget في entries
            budget = 0.0
            if 'budget' in self.entries and self.entries['budget'].get():
                budget = float(self.entries['budget'].get())
            
            status = self.status_combo.get()
            client_name = self.entries['client_name'].get()
            description = self.description_text.get("1.0", tk.END).strip()
            
            if not name or not start_date:
                messagebox.showerror("خطأ", "❌ اسم المشروع وتاريخ البدء مطلوبان")
                return

            # التحقق من تكرار اسم المشروع والتنبيه
            chk_query = "SELECT id FROM projects WHERE name = ?" + (" AND id != ?" if self.project_id else "")
            chk_params = (name, self.project_id) if self.project_id else (name,)
            existing = self.db.execute_query(chk_query, chk_params)
            if existing:
                msg = f"⚠️ تنبيه تكرار الاسم:\nاسم المشروع '{name}' مسجل مسبقاً في النظام!\n\nهل تريد بالتأكيد المتابعة وتسجيله مرة أخرى؟"
                if not messagebox.askyesno("تنبيه تكرار الاسم", msg, parent=self):
                    self.entries['name'].focus()
                    return
            
            if self.project_id:
                self.db.execute_query(
                    "UPDATE projects SET name=?, start_date=?, end_date=?, budget=?, status=?, client_name=?, description=? WHERE id=?",
                    (name, start_date, end_date, budget, status, client_name, description, self.project_id)
                )
                self.status_callback(f"✅ تم تحديث المشروع: {name}")
            else:
                self.db.execute_query(
                    "INSERT INTO projects (name, start_date, end_date, budget, status, client_name, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (name, start_date, end_date, budget, status, client_name, description)
                )
                
                # إنشاء حساب دائن تلقائي للمشروع (إذا كان هناك ميزانية)
                if budget > 0:
                    project_id = self.db.execute_query("SELECT last_insert_rowid()")[0][0]
                    due_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=30)).strftime('%Y-%m-%d')
                    self.db.execute_query('''
                        INSERT INTO accounts_payable 
                        (supplier_name, project_id, amount, paid_amount, remaining_amount, due_date, status, category, created_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (f'مشروع {name}', project_id, budget, 0, budget, due_date, 'معلق', 'معدات', 
                         datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                
                self.status_callback(f"✅ تم إضافة المشروع: {name}" + (f" وحساب دائن تلقائي" if budget > 0 else ""))
            
            self.refresh_callback()
            self.destroy()
            
        except ValueError:
            messagebox.showerror("خطأ", "❌ الميزانية يجب أن تكون رقمًا")
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حفظ المشروع: {str(e)}")
            print(f"تفصيل الخطأ: {e}")  # للتصحيح

class ProjectsModule:
    def __init__(self, notebook, status_callback):
        self.db = Database()
        self.status_callback = status_callback
        self.frame = ttk.Frame(notebook)
        
        # إنشاء ScrollArea للتبويب
        self.create_scrollable_content()
        
        self.create_widgets()
        self.load_projects()
    
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
        
        # إنشاء تبويبات
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill='both', expand=True)
        
        # تبويب المشاريع فقط
        self.create_projects_tab()
    
    def create_projects_tab(self):
        """إنشاء تبويب المشاريع"""
        projects_frame = ttk.Frame(self.notebook)
        self.notebook.add(projects_frame, text="🏗️ المشاريع")
        
        title_frame = ttk.Frame(projects_frame)
        title_frame.pack(fill='x', pady=(0, 20))
        
        ttk.Label(title_frame, text="🏗️ إدارة المشاريع", 
                 font=('Segoe UI', 16, 'bold')).pack(pady=10)
        
        quick_actions = ttk.Frame(projects_frame)
        quick_actions.pack(fill='x', pady=(0, 15))
        
        btn1 = ttk.Button(quick_actions, text="➕ مشروع جديد", command=self.add_project,
                  width=15)
        btn1.pack(side='left', padx=5, ipady=6)
        btn2 = ttk.Button(quick_actions, text="📊 تقارير المشاريع", command=self.show_project_reports,
                  width=15)
        btn2.pack(side='left', padx=5, ipady=6)
        
        search_frame = ttk.Frame(projects_frame)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="بحث:", font=('Segoe UI', 10)).pack(side='left', padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30, font=('Segoe UI', 10))
        self.search_entry.pack(side='left', padx=5, ipady=4)
        self.search_entry.bind('<KeyRelease>', self.search_projects)
        
        ttk.Button(search_frame, text="بحث", command=self.search_projects).pack(side='left', padx=5, ipady=4)
        ttk.Button(search_frame, text="عرض الكل", command=self.load_projects).pack(side='left', padx=5, ipady=4)
        
        tree_frame = ttk.LabelFrame(projects_frame, text="قائمة المشاريع")
        tree_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        self.tree = ttk.Treeview(tree_frame, columns=('id', 'name', 'start_date', 'end_date', 'budget', 'status', 'client'), show='headings', height=15)
        
        columns = [
            ('id', 'ID', 50),
            ('name', 'اسم المشروع', 150),
            ('start_date', 'تاريخ البدء', 100),
            ('end_date', 'تاريخ الانتهاء', 100),
            ('budget', 'الميزانية', 100),
            ('status', 'الحالة', 100),
            ('client', 'اسم العميل', 150)
        ]
        
        for col, heading, width in columns:
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width)
        
        self.tree.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        control_frame = ttk.Frame(projects_frame)
        control_frame.pack(fill='x')
        
        control_buttons = [
            ("👁️ عرض", self.view_project),
            ("✏️ تعديل", self.edit_project),
            ("💰 مالية", self.show_financials),
            ("🗑️ حذف", self.delete_project),
            ("📋 تقرير", self.generate_project_report)
        ]
        
        for text, command in control_buttons:
            btn = ttk.Button(control_frame, text=text, command=command)
            btn.pack(side='left', padx=5, ipady=6)
        
        self.tree.bind('<Double-1>', lambda e: self.view_project())
    
    def create_customers_tab(self):
        """إنشاء تبويب العملاء"""
        customers_frame = ttk.Frame(self.notebook)
        self.notebook.add(customers_frame, text="👥 العملاء")
        
        title_frame = ttk.Frame(customers_frame)
        title_frame.pack(fill='x', pady=(0, 20))
        
        ttk.Label(title_frame, text="👥 إدارة العملاء", 
                 font=('Segoe UI', 16, 'bold')).pack(pady=10)
        
        quick_actions = ttk.Frame(customers_frame)
        quick_actions.pack(fill='x', pady=(0, 15))
        
        btn1 = ttk.Button(quick_actions, text="➕ عميل جديد", command=self.add_customer,
                  width=15)
        btn1.pack(side='left', padx=5, ipady=6)
        
        search_frame = ttk.Frame(customers_frame)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="بحث:", font=('Segoe UI', 10)).pack(side='left', padx=5)
        self.customer_search_entry = ttk.Entry(search_frame, width=30, font=('Segoe UI', 10))
        self.customer_search_entry.pack(side='left', padx=5, ipady=4)
        self.customer_search_entry.bind('<KeyRelease>', self.search_customers)
        
        ttk.Button(search_frame, text="بحث", command=self.search_customers).pack(side='left', padx=5, ipady=4)
        ttk.Button(search_frame, text="عرض الكل", command=self.load_customers).pack(side='left', padx=5, ipady=4)
        
        tree_frame = ttk.LabelFrame(customers_frame, text="قائمة العملاء")
        tree_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        self.customer_tree = ttk.Treeview(tree_frame, columns=('id', 'name', 'tax_number', 'phone', 'email'), show='headings', height=15)
        
        columns = [
            ('id', 'ID', 50),
            ('name', 'اسم العميل', 200),
            ('tax_number', 'الرقم الضريبي', 120),
            ('phone', 'الهاتف', 120),
            ('email', 'البريد الإلكتروني', 200)
        ]
        
        for col, heading, width in columns:
            self.customer_tree.heading(col, text=heading)
            self.customer_tree.column(col, width=width)
        
        self.customer_tree.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.customer_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.customer_tree.configure(yscrollcommand=scrollbar.set)
        
        control_frame = ttk.Frame(customers_frame)
        control_frame.pack(fill='x')
        
        control_buttons = [
            ("👁️ عرض", self.view_customer),
            ("✏️ تعديل", self.edit_customer),
            ("🗑️ حذف", self.delete_customer)
        ]
        
        for text, command in control_buttons:
            btn = ttk.Button(control_frame, text=text, command=command)
            btn.pack(side='left', padx=5, ipady=6)
        
        self.customer_tree.bind('<Double-1>', lambda e: self.view_customer())
        
        # تحميل العملاء
        self.load_customers()
    
    def add_project(self):
        ProjectDialog(self.frame, self.db, self.status_callback, self.load_projects)
    
    def edit_project(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار مشروع لتعديله")
            return
        
        project_id = self.tree.item(selected[0], 'values')[0]
        ProjectDialog(self.frame, self.db, self.status_callback, self.load_projects, project_id)
    
    def view_project(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار مشروع لعرضه")
            return
        
        project_id = self.tree.item(selected[0], 'values')[0]
        project = self.db.execute_query("SELECT * FROM projects WHERE id = ?", (project_id,))
        
        if project:
            project = project[0]
            
            # حساب الإحصائيات المالية
            income = self.db.execute_query(
                "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'income' AND project_id = ?",
                (project_id,)
            )[0][0]
            
            expenses = self.db.execute_query(
                "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'expense' AND project_id = ?",
                (project_id,)
            )[0][0]
            
            profit = income - expenses
            budget_usage = (expenses / project[4] * 100) if project[4] > 0 else 0
            
            details = f"""
            📋 بيانات المشروع:
            
            الاسم: {project[1]}
            الحالة: {project[5]}
            تاريخ البدء: {project[2]}
            تاريخ الانتهاء: {project[3] or 'غير محدد'}
            الميزانية: {project[4]:.2f} ريال
            العميل: {project[6] or 'غير محدد'}
            
            📊 الإحصائيات المالية:
            
            الإيرادات: {income:.2f} ريال
            المصروفات: {expenses:.2f} ريال
            صافي الربح: {profit:.2f} ريال
            استهلاك الميزانية: {budget_usage:.1f}%
            """
            
            if project[7]:
                details += f"\n📝 الوصف:\n{project[7]}"
            
            messagebox.showinfo("تفاصيل المشروع", details)
    
    def show_financials(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار مشروع")
            return
        
        project_id = self.tree.item(selected[0], 'values')[0]
        project_name = self.tree.item(selected[0], 'values')[1]
        
        # الحصول على جميع المعاملات المرتبطة بالمشروع
        transactions = self.db.execute_query('''
            SELECT type, amount, description, date, category 
            FROM transactions 
            WHERE project_id = ? 
            ORDER BY date DESC
        ''', (project_id,))
        
        if transactions:
            financials = f"المعاملات المالية - {project_name}\n\n"
            total_income = 0
            total_expenses = 0
            
            for trans in transactions:
                type_text = "إيراد" if trans[0] == 'income' else "مصروف"
                financials += f"• {trans[3]} - {type_text} - {trans[2]} - {trans[1]:.2f} ريال\n"
                
                if trans[0] == 'income':
                    total_income += trans[1]
                else:
                    total_expenses += trans[1]
            
            financials += f"\nالإجمالي:\n"
            financials += f"إجمالي الإيرادات: {total_income:.2f} ريال\n"
            financials += f"إجمالي المصروفات: {total_expenses:.2f} ريال\n"
            financials += f"صافي الربح: {total_income - total_expenses:.2f} ريال"
            
            messagebox.showinfo("المعاملات المالية", financials)
        else:
            messagebox.showinfo("المعاملات المالية", f"لا توجد معاملات مالية للمشروع {project_name}")
    
    def delete_project(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار مشروع لحذفه")
            return
        
        project_id = self.tree.item(selected[0], 'values')[0]
        project_name = self.tree.item(selected[0], 'values')[1]
        
        # التحقق من وجود معاملات مرتبطة
        transactions = self.db.execute_query(
            "SELECT COUNT(*) FROM transactions WHERE project_id = ?", (project_id,)
        )
        if transactions and transactions[0][0] > 0:
            messagebox.showerror("خطأ", "❌ لا يمكن حذف المشروع لأنه مرتبط بمعاملات مالية")
            return
        
        # التحقق من وجود موظفين مرتبطين
        employees = self.db.execute_query(
            "SELECT COUNT(*) FROM employees WHERE project_id = ?", (project_id,)
        )
        if employees and employees[0][0] > 0:
            messagebox.showerror("خطأ", "❌ لا يمكن حذف المشروع لأنه مرتبط بموظفين")
            return
        
        if messagebox.askyesno("تأكيد", f"⚠️ هل أنت متأكد من حذف المشروع '{project_name}'؟"):
            try:
                self.db.execute_query("DELETE FROM projects WHERE id = ?", (project_id,))
                self.status_callback(f"✅ تم حذف المشروع: {project_name}")
                self.load_projects()
            except Exception as e:
                messagebox.showerror("خطأ", f"❌ فشل في حذف المشروع: {str(e)}")
    
    def generate_project_report(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار مشروع")
            return
        
        project_id = self.tree.item(selected[0], 'values')[0]
        project_name = self.tree.item(selected[0], 'values')[1]
        
        # جمع بيانات التقرير
        project = self.db.execute_query("SELECT * FROM projects WHERE id = ?", (project_id,))[0]
        employees = self.db.execute_query(
            "SELECT name, position, salary FROM employees WHERE project_id = ?", (project_id,)
        )
        transactions = self.db.execute_query(
            "SELECT type, amount, description, date FROM transactions WHERE project_id = ? ORDER BY date DESC",
            (project_id,)
        )
        
        report = f"📊 تقرير مفصل - {project_name}\n\n"
        report += f"معلومات المشروع:\n"
        report += f"• الحالة: {project[5]}\n"
        report += f"• تاريخ البدء: {project[2]}\n"
        report += f"• تاريخ الانتهاء: {project[3] or 'غير محدد'}\n"
        report += f"• الميزانية: {project[4]:.2f} ريال\n"
        report += f"• العميل: {project[6] or 'غير محدد'}\n\n"
        
        report += f"الموظفين ({len(employees)}):\n"
        total_salaries = 0
        for emp in employees:
            report += f"• {emp[0]} - {emp[1]} - {emp[2]:.2f} ريال\n"
            total_salaries += emp[2]
        
        report += f"\nإجمالي الرواتب: {total_salaries:.2f} ريال\n\n"
        
        report += f"المعاملات المالية ({len(transactions)}):\n"
        total_income = 0
        total_expenses = 0
        for trans in transactions:
            type_text = "إيراد" if trans[0] == 'income' else "مصروف"
            report += f"• {trans[3]} - {type_text} - {trans[2]} - {trans[1]:.2f} ريال\n"
            
            if trans[0] == 'income':
                total_income += trans[1]
            else:
                total_expenses += trans[1]
        
        report += f"\nالإحصائيات المالية:\n"
        report += f"• إجمالي الإيرادات: {total_income:.2f} ريال\n"
        report += f"• إجمالي المصروفات: {total_expenses:.2f} ريال\n"
        report += f"• صافي الربح: {total_income - total_expenses:.2f} ريال\n"
        report += f"• نسبة الربحية: {((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0:.1f}%"
        
        messagebox.showinfo(f"تقرير {project_name}", report)
    
    def show_project_reports(self):
        total_projects = len(self.db.execute_query("SELECT id FROM projects"))
        active_projects = len(self.db.execute_query("SELECT id FROM projects WHERE status = 'قيد التنفيذ'"))
        completed_projects = len(self.db.execute_query("SELECT id FROM projects WHERE status = 'مكتمل'"))
        total_budget = self.db.execute_query("SELECT SUM(budget) FROM projects")[0][0] or 0
        
        messagebox.showinfo("تقارير المشاريع", 
                          f"📊 إحصائيات المشاريع:\n\n"
                          f"• إجمالي المشاريع: {total_projects}\n"
                          f"• المشاريع النشطة: {active_projects}\n"
                          f"• المشاريع المكتملة: {completed_projects}\n"
                          f"• إجمالي الميزانيات: {total_budget:.2f} ريال")
    
    def search_projects(self, event=None):
        search_term = self.search_entry.get()
        if not search_term:
            self.load_projects()
            return
        
        projects = self.db.execute_query(
            "SELECT id, name, start_date, end_date, budget, status, client_name FROM projects WHERE name LIKE ? OR client_name LIKE ? OR status LIKE ?",
            (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%')
        )
        self.display_projects(projects)
    
    def load_projects(self):
        projects = self.db.execute_query("SELECT id, name, start_date, end_date, budget, status, client_name FROM projects ORDER BY start_date DESC")
        self.display_projects(projects)
    
    def display_projects(self, projects):
        self.tree.delete(*self.tree.get_children())
        for proj in projects:
            self.tree.insert('', 'end', values=(
                proj[0], proj[1], proj[2], proj[3] or '', 
                f"{proj[4]:.2f}", proj[5], proj[6] or ''
            ))
    
    def search_customers(self, event=None):
        search_term = self.customer_search_entry.get()
        if not search_term:
            self.load_customers()
            return
        
        customers = self.db.execute_query(
            "SELECT id, name, tax_number, phone, email FROM customers WHERE name LIKE ? OR tax_number LIKE ? OR phone LIKE ? OR email LIKE ?",
            (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', f'%{search_term}%')
        )
        self.display_customers(customers)
    
    def load_customers(self):
        customers = self.db.execute_query("SELECT id, name, tax_number, phone, email FROM customers ORDER BY name")
        self.display_customers(customers)
    
    def display_customers(self, customers):
        self.customer_tree.delete(*self.customer_tree.get_children())
        for cust in customers:
            self.customer_tree.insert('', 'end', values=(
                cust[0], cust[1], cust[2] or '', cust[3] or '', cust[4] or ''
            ))
    
    # دوال العملاء
    def add_customer(self):
        CustomerDialog(self.frame, self.db, self.status_callback, self.load_customers)
    
    def edit_customer(self):
        selected = self.customer_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عميل لتعديله")
            return
        
        customer_id = self.customer_tree.item(selected[0], 'values')[0]
        CustomerDialog(self.frame, self.db, self.status_callback, self.load_customers, customer_id)
    
    def view_customer(self):
        selected = self.customer_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عميل لعرضه")
            return
        
        customer_id = self.customer_tree.item(selected[0], 'values')[0]
        customer = self.db.execute_query("SELECT * FROM customers WHERE id = ?", (customer_id,))
        
        if customer:
            cust = customer[0]
            
            # حساب إحصائيات العميل
            invoices_count = len(self.db.execute_query("SELECT id FROM invoices WHERE customer_id = ?", (customer_id,)))
            total_invoices = self.db.execute_query("SELECT COALESCE(SUM(grand_total), 0) FROM invoices WHERE customer_id = ?", (customer_id,))
            total_amount = total_invoices[0][0] if total_invoices else 0
            
            details = f"""
            📋 بيانات العميل:
            
            الاسم: {cust[1]}
            الرقم الضريبي: {cust[2] or 'غير محدد'}
            العنوان: {cust[3] or 'غير محدد'}
            الهاتف: {cust[4] or 'غير محدد'}
            البريد الإلكتروني: {cust[5] or 'غير محدد'}
            
            📊 إحصائيات العميل:
            
            عدد الفواتير: {invoices_count}
            إجمالي الفواتير: {total_amount:.2f} ريال
            """
            
            messagebox.showinfo("تفاصيل العميل", details)
    
    def delete_customer(self):
        selected = self.customer_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عميل لحذفه")
            return
        
        customer_id = self.customer_tree.item(selected[0], 'values')[0]
        customer_name = self.customer_tree.item(selected[0], 'values')[1]
        
        # التحقق من وجود فواتير مرتبطة
        invoices = self.db.execute_query(
            "SELECT COUNT(*) FROM invoices WHERE customer_id = ?", (customer_id,)
        )
        if invoices and invoices[0][0] > 0:
            messagebox.showerror("خطأ", "❌ لا يمكن حذف العميل لأنه مرتبط بفواتير")
            return
        
        if messagebox.askyesno("تأكيد", f"⚠️ هل أنت متأكد من حذف العميل '{customer_name}'؟"):
            try:
                self.db.execute_query("DELETE FROM customers WHERE id = ?", (customer_id,))
                self.status_callback(f"✅ تم حذف العميل: {customer_name}")
                self.load_customers()
            except Exception as e:
                messagebox.showerror("خطأ", f"❌ فشل في حذف العميل: {str(e)}")