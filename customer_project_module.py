"""
وحدة إدارة العملاء والمشاريع
Customer & Project Management Module
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from central_refresh import emit_customer_change, emit_project_change

# استيراد دالة ar و CustomStatementPDF من invoices_fixed
try:
    from invoices_fixed import ar, CustomStatementPDF
except ImportError:
    # دالة معالجة النصوص العربية البديلة
    try:
        from arabic_reshaper import reshape
        from bidi.algorithm import get_display
        def ar(text):
            if not text:
                return ""
            try:
                reshaped_text = reshape(str(text))
                return get_display(reshaped_text)
            except:
                return str(text)
    except ImportError:
        def ar(text):
            return str(text) if text else ""
    
    from fpdf import FPDF
    class CustomStatementPDF(FPDF):
        """PDF class مخصص لكشف الحساب بدون header تلقائي"""
        def __init__(self):
            super().__init__()
            self.set_auto_page_break(auto=True, margin=15)
            self.font_name = 'Amiri'
            try:
                self.add_font('Amiri', '', 'Amiri-Regular.ttf', uni=True)
                self.add_font('Amiri', 'B', 'Amiri-Bold.ttf', uni=True)
            except:
                print("Warning: Amiri font not found, using default fonts")
                self.font_name = 'Arial'
            self.set_right_margin(10)
            self.set_left_margin(10)
        
        def header(self):
            # header فارغ - لا شيء يكتب تلقائياً
            pass

class CustomerProjectModule:
    """وحدة إدارة العملاء والمشاريع"""
    
    def __init__(self, notebook, status_callback, db):
        self.notebook = notebook
        self.status_callback = status_callback
        self.db = db
        
        self.frame = ttk.Frame(notebook)
        
        # إنشاء ScrollArea للتبويب
        self.create_scrollable_content()
        
        # إنشاء الواجهة
        self.create_widgets()
        
        # تحميل البيانات
        self.load_data()
    
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
        """إنشاء عناصر الواجهة"""
        # إطار رئيسي
        main_container = ttk.Frame(self.content_frame)
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # عنوان
        title_label = tk.Label(main_container, text="👥 العملاء والمشاريع", 
                              font=('Segoe UI', 16, 'bold'))
        title_label.pack(pady=10)
        
        # إنشاء دفتر ملاحظات للتبويبات الفرعية
        self.sub_notebook = ttk.Notebook(main_container)
        self.sub_notebook.pack(fill='both', expand=True)
        
        # تبويب العملاء
        self.create_customers_tab(self.sub_notebook)
        
        # تبويب المشاريع
        self.create_projects_tab(self.sub_notebook)
        
        # تبويب كشوف الحسابات
        self.create_statements_tab(self.sub_notebook)
    
    def create_customers_tab(self, notebook):
        """إنشاء تبويب إدارة العملاء"""
        customers_frame = ttk.Frame(notebook)
        notebook.add(customers_frame, text="👥 العملاء")
        
        # إطار إضافة عميل جديد
        add_frame = ttk.LabelFrame(customers_frame, text="➕ إضافة عميل جديد")
        add_frame.pack(fill='x', padx=10, pady=10)
        
        # حقول الإدخال
        input_frame = ttk.Frame(add_frame)
        input_frame.pack(fill='x', padx=10, pady=10)
        
        # العمود الأول
        col1 = ttk.Frame(input_frame)
        col1.pack(side='right', padx=10, fill='y')
        
        ttk.Label(col1, text="اسم العميل:", font=('Segoe UI', 10, 'bold')).pack(pady=2)
        self.customer_name_entry = ttk.Entry(col1, width=30, justify='right')
        self.customer_name_entry.pack(pady=2)
        
        ttk.Label(col1, text="الرقم الضريبي:", font=('Segoe UI', 10, 'bold')).pack(pady=2)
        self.customer_vat_entry = ttk.Entry(col1, width=30, justify='center')
        self.customer_vat_entry.pack(pady=2)
        
        # العمود الثاني
        col2 = ttk.Frame(input_frame)
        col2.pack(side='right', padx=10, fill='y')
        
        ttk.Label(col2, text="العنوان:", font=('Segoe UI', 10, 'bold')).pack(pady=2)
        self.customer_address_entry = ttk.Entry(col2, width=30, justify='right')
        self.customer_address_entry.pack(pady=2)
        
        ttk.Label(col2, text="رقم الهاتف:", font=('Segoe UI', 10, 'bold')).pack(pady=2)
        self.customer_phone_entry = ttk.Entry(col2, width=30, justify='center')
        self.customer_phone_entry.pack(pady=2)
        
        # أزرار
        btn_frame = ttk.Frame(add_frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="💾 حفظ العميل", 
                  command=self.save_customer).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="🔄 مسح", 
                  command=self.clear_customer_form).pack(side='right', padx=5)
        
        # إطار البحث عن العميل
        search_frame = ttk.LabelFrame(customers_frame, text="🔍 البحث عن عميل")
        search_frame.pack(fill='x', padx=10, pady=(5, 5))
        
        search_inner = ttk.Frame(search_frame)
        search_inner.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(search_inner, text="🔍 بحث (الاسم / الرقم الضريبي / الهاتف / العنوان):", font=('Segoe UI', 9, 'bold')).pack(side='right', padx=(0, 5))
        
        self.customer_search_entry = ttk.Entry(search_inner, width=35, font=('Segoe UI', 10))
        self.customer_search_entry.pack(side='right', padx=5, fill='x', expand=True)
        self.customer_search_entry.bind('<KeyRelease>', self.search_customers)
        
        ttk.Button(search_inner, text="🔍 بحث", command=self.search_customers).pack(side='right', padx=3)
        ttk.Button(search_inner, text="🔄 عرض الكل", command=self.clear_customer_search).pack(side='right', padx=3)
        
        # جدول العملاء
        list_frame = ttk.LabelFrame(customers_frame, text="📋 قائمة العملاء")
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        columns = ('id', 'name', 'vat', 'address', 'phone', 'projects_count')
        self.customers_tree = ttk.Treeview(list_frame, columns=columns, 
                                           show='headings', height=10)
        
        self.customers_tree.heading('id', text='الرقم')
        self.customers_tree.heading('name', text='اسم العميل')
        self.customers_tree.heading('vat', text='الرقم الضريبي')
        self.customers_tree.heading('address', text='العنوان')
        self.customers_tree.heading('phone', text='الهاتف')
        self.customers_tree.heading('projects_count', text='عدد المشاريع')
        
        self.customers_tree.column('id', width=50)
        self.customers_tree.column('name', width=150)
        self.customers_tree.column('vat', width=100)
        self.customers_tree.column('address', width=150)
        self.customers_tree.column('phone', width=100)
        self.customers_tree.column('projects_count', width=80, anchor='center')
        
        self.customers_tree.pack(side='left', fill='both', expand=True)
        
        # شريط تمرير
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", 
                                  command=self.customers_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.customers_tree.configure(yscrollcommand=scrollbar.set)
        
        # أزرار التحكم
        control_frame = ttk.Frame(customers_frame)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(control_frame, text="✏️ تعديل", 
                  command=self.edit_customer).pack(side='right', padx=5)
        ttk.Button(control_frame, text="🗑️ حذف", 
                  command=self.delete_customer).pack(side='right', padx=5)
        ttk.Button(control_frame, text="📄 كشف حساب", 
                  command=self.show_customer_statement).pack(side='right', padx=5)
        ttk.Button(control_frame, text="🔄 تحديث", 
                  command=self.clear_customer_search).pack(side='right', padx=5)
    
    def create_projects_tab(self, notebook):
        """إنشاء تبويب إدارة المشاريع"""
        projects_frame = ttk.Frame(notebook)
        notebook.add(projects_frame, text="📁 المشاريع")
        
        # إطار إضافة مشروع جديد
        add_frame = ttk.LabelFrame(projects_frame, text="➕ إضافة مشروع جديد")
        add_frame.pack(fill='x', padx=10, pady=5)
        
        # حقول الإدخال في صف واحد أفقي
        input_frame = ttk.Frame(add_frame)
        input_frame.pack(fill='x', padx=5, pady=5)
        
        # صف 1: اسم المشروع والعميل
        row1 = ttk.Frame(input_frame)
        row1.pack(fill='x', pady=2)
        
        ttk.Label(row1, text="اسم المشروع:", font=('Segoe UI', 9, 'bold')).pack(side='right', padx=5)
        self.project_name_entry = ttk.Entry(row1, width=25, justify='right')
        self.project_name_entry.pack(side='right', padx=5)
        
        ttk.Label(row1, text="العميل:", font=('Segoe UI', 9, 'bold')).pack(side='right', padx=5)
        self.project_customer_combo = ttk.Combobox(row1, width=20, state='readonly')
        self.project_customer_combo.pack(side='right', padx=5)
        
        ttk.Label(row1, text="تاريخ البدء:", font=('Segoe UI', 9, 'bold')).pack(side='right', padx=5)
        self.project_start_entry = ttk.Entry(row1, width=12)
        self.project_start_entry.pack(side='right', padx=5)
        self.project_start_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        
        # صف 2: الميزانية والحالة والوصف
        row2 = ttk.Frame(input_frame)
        row2.pack(fill='x', pady=2)
        
        ttk.Label(row2, text="الميزانية:", font=('Segoe UI', 9, 'bold')).pack(side='right', padx=5)
        self.project_budget_entry = ttk.Entry(row2, width=15)
        self.project_budget_entry.pack(side='right', padx=5)
        self.project_budget_entry.insert(0, "0")
        
        ttk.Label(row2, text="الحالة:", font=('Segoe UI', 9, 'bold')).pack(side='right', padx=5)
        self.project_status_combo = ttk.Combobox(row2, width=10, state='readonly')
        self.project_status_combo['values'] = ('نشط', 'معلق', 'منتهي', 'ملغي')
        self.project_status_combo.set('نشط')
        self.project_status_combo.pack(side='right', padx=5)
        
        ttk.Label(row2, text="الوصف:", font=('Segoe UI', 9, 'bold')).pack(side='right', padx=5)
        self.project_desc_entry = ttk.Entry(row2, width=30, justify='right')
        self.project_desc_entry.pack(side='right', padx=5, fill='x', expand=True)
        
        # أزرار في نفس الإطار
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(side='left', padx=10)
        
        ttk.Button(btn_frame, text="💾 حفظ", 
                  command=self.save_project, width=10).pack(side='right', padx=3)
        ttk.Button(btn_frame, text="🔄 مسح", 
                  command=self.clear_project_form, width=10).pack(side='right', padx=3)
        
        # جدول المشاريع
        list_frame = ttk.LabelFrame(projects_frame, text="📋 قائمة المشاريع")
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('id', 'name', 'customer', 'budget', 'spent', 'received', 'balance', 'status')
        self.projects_tree = ttk.Treeview(list_frame, columns=columns, 
                                         show='headings', height=10)
        
        self.projects_tree.heading('id', text='الرقم')
        self.projects_tree.heading('name', text='اسم المشروع')
        self.projects_tree.heading('customer', text='العميل')
        self.projects_tree.heading('budget', text='الميزانية')
        self.projects_tree.heading('spent', text='المصروف')
        self.projects_tree.heading('received', text='المستلم')
        self.projects_tree.heading('balance', text='الرصيد')
        self.projects_tree.heading('status', text='الحالة')
        
        self.projects_tree.column('id', width=50)
        self.projects_tree.column('name', width=150)
        self.projects_tree.column('customer', width=120)
        self.projects_tree.column('budget', width=80)
        self.projects_tree.column('spent', width=80)
        self.projects_tree.column('received', width=80)
        self.projects_tree.column('balance', width=80)
        self.projects_tree.column('status', width=80)
        
        self.projects_tree.pack(side='left', fill='both', expand=True)
        
        # شريط تمرير
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", 
                                 command=self.projects_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.projects_tree.configure(yscrollcommand=scrollbar.set)
        
        # أزرار التحكم
        control_frame = ttk.Frame(projects_frame)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(control_frame, text="👁️ عرض التفاصيل", 
                  command=self.show_project_details).pack(side='right', padx=5)
        ttk.Button(control_frame, text="✏️ تعديل", 
                  command=self.edit_project).pack(side='right', padx=5)
        ttk.Button(control_frame, text="🗑️ حذف", 
                  command=self.delete_project).pack(side='right', padx=5)
        ttk.Button(control_frame, text="📄 كشف حساب", 
                  command=self.show_project_statement).pack(side='right', padx=5)
        ttk.Button(control_frame, text="🔄 تحديث", 
                  command=self.load_projects).pack(side='right', padx=5)
    
    def create_statements_tab(self, notebook):
        """إنشاء تبويب كشوف الحسابات"""
        self.statements_tab = ttk.Frame(notebook)
        statements_frame = self.statements_tab
        notebook.add(statements_frame, text="📊 كشوف الحسابات")
        
        # إطار البحث
        search_frame = ttk.LabelFrame(statements_frame, text="البحث")
        search_frame.pack(fill='x', padx=10, pady=10)
        
        search_content = ttk.Frame(search_frame)
        search_content.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(search_content, text="اختر العميل:", 
                 font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        
        self.statement_customer_combo = ttk.Combobox(search_content, width=30, state='readonly')
        self.statement_customer_combo.pack(side='right', padx=5)
        
        ttk.Label(search_content, text="أو المشروع:", 
                 font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        
        self.statement_project_combo = ttk.Combobox(search_content, width=30, state='readonly')
        self.statement_project_combo.pack(side='right', padx=5)
        
        ttk.Button(search_content, text="📄 عرض كشف الحساب", 
                  command=self.generate_statement).pack(side='right', padx=10)
        
        # جدول المعاملات
        list_frame = ttk.LabelFrame(statements_frame, text="📋 حركات الحساب")
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('date', 'type', 'description', 'debit', 'credit', 'balance')
        self.statement_tree = ttk.Treeview(list_frame, columns=columns, 
                                          show='headings', height=15)
        
        self.statement_tree.heading('date', text='التاريخ')
        self.statement_tree.heading('type', text='النوع')
        self.statement_tree.heading('description', text='البيان')
        self.statement_tree.heading('debit', text='مدين (صرف)')
        self.statement_tree.heading('credit', text='دائن (استلام)')
        self.statement_tree.heading('balance', text='الرصيد')
        
        self.statement_tree.column('date', width=100)
        self.statement_tree.column('type', width=100)
        self.statement_tree.column('description', width=250)
        self.statement_tree.column('debit', width=100)
        self.statement_tree.column('credit', width=100)
        self.statement_tree.column('balance', width=100)
        
        self.statement_tree.pack(side='left', fill='both', expand=True)
        
        # شريط تمرير
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", 
                                 command=self.statement_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.statement_tree.configure(yscrollcommand=scrollbar.set)
        
        # ملخص
        summary_frame = ttk.LabelFrame(statements_frame, text="📊 الملخص")
        summary_frame.pack(fill='x', padx=10, pady=10)
        
        summary_content = ttk.Frame(summary_frame)
        summary_content.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(summary_content, text="إجمالي المصروفات:", 
                 font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        self.total_debit_label = tk.Label(summary_content, text="0.00 ريال", 
                                         font=('Segoe UI', 12, 'bold'), fg='red')
        self.total_debit_label.pack(side='right', padx=10)
        
        ttk.Label(summary_content, text="إجمالي المقبوضات:", 
                 font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        self.total_credit_label = tk.Label(summary_content, text="0.00 ريال", 
                                          font=('Segoe UI', 12, 'bold'), fg='green')
        self.total_credit_label.pack(side='right', padx=10)
        
        ttk.Label(summary_content, text="الرصيد النهائي:", 
                 font=('Segoe UI', 10, 'bold')).pack(side='right', padx=5)
        self.final_balance_label = tk.Label(summary_content, text="0.00 ريال", 
                                           font=('Segoe UI', 14, 'bold'), fg='blue')
        self.final_balance_label.pack(side='right', padx=10)
        
        # أزرار
        btn_frame = ttk.Frame(statements_frame)
        btn_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(btn_frame, text="🖨️ طباعة", 
                  command=self.print_statement).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="💾 تصدير Excel", 
                  command=self.export_statement).pack(side='right', padx=5)
    
    def load_data(self):
        """تحميل جميع البيانات"""
        self.load_customers()
        self.load_projects()
        self.update_combos()
    
    def update_combos(self):
        """تحديث قوائم الاختيار"""
        # تحديث قائمة العملاء في مشروع جديد
        customers = self.db.execute_query("SELECT id, name FROM customers ORDER BY name")
        customer_list = [f"{c[0]} - {c[1]}" for c in customers] if customers else []
        self.project_customer_combo['values'] = ["-- اختر العميل --"] + customer_list
        if self.project_customer_combo['values']:
            self.project_customer_combo.current(0)
        
        # تحديث قوائم كشف الحساب
        self.statement_customer_combo['values'] = ["-- اختر العميل --"] + customer_list
        
        projects = self.db.execute_query("SELECT id, name FROM projects ORDER BY name")
        project_list = [f"{p[0]} - {p[1]}" for p in projects] if projects else []
        self.statement_project_combo['values'] = ["-- اختر المشروع --"] + project_list
    
    def load_customers(self):
        """تحميل قائمة العملاء"""
        try:
            # مسح الجدول
            for item in self.customers_tree.get_children():
                self.customers_tree.delete(item)
            
            # تحميل العملاء
            customers = self.db.execute_query("""
                SELECT c.id, c.name, c.tax_number, c.address, c.phone,
                       COUNT(p.id) as projects_count
                FROM customers c
                LEFT JOIN projects p ON c.id = p.customer_id
                GROUP BY c.id
                ORDER BY c.name
            """)
            
            for customer in customers:
                self.customers_tree.insert('', 'end', values=customer)
                
        except Exception as e:
            print(f"خطأ في تحميل العملاء: {e}")

    def search_customers(self, event=None):
        """البحث التفاعلي عن العملاء"""
        if not hasattr(self, 'customer_search_entry'):
            return
            
        search_term = self.customer_search_entry.get().strip()
        if not search_term:
            self.load_customers()
            return
            
        try:
            for item in self.customers_tree.get_children():
                self.customers_tree.delete(item)
                
            customers = self.db.execute_query("""
                SELECT c.id, c.name, c.tax_number, c.address, c.phone,
                       COUNT(p.id) as projects_count
                FROM customers c
                LEFT JOIN projects p ON c.id = p.customer_id
                WHERE c.name LIKE ? OR c.tax_number LIKE ? OR c.address LIKE ? OR c.phone LIKE ?
                GROUP BY c.id
                ORDER BY c.name
            """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
            
            for customer in customers:
                self.customers_tree.insert('', 'end', values=customer)
        except Exception as e:
            print(f"خطأ في البحث عن العملاء: {e}")

    def clear_customer_search(self):
        """إلغاء البحث وإعادة عرض كل العملاء"""
        if hasattr(self, 'customer_search_entry'):
            self.customer_search_entry.delete(0, tk.END)
        self.load_customers()
    
    def load_projects(self):
        """تحميل قائمة المشاريع مع حساب المصروفات والمقبوضات"""
        try:
            # مسح الجدول
            for item in self.projects_tree.get_children():
                self.projects_tree.delete(item)
            
            # تحميل المشاريع مع بيانات العملاء
            projects = self.db.execute_query("""
                SELECT p.id, p.name, c.name as customer_name, p.budget, p.status
                FROM projects p
                LEFT JOIN customers c ON p.customer_id = c.id
                ORDER BY p.name
            """)
            
            for project in projects:
                project_id = project[0]
                
                # حساب المصروفات (سندات الصرف)
                spent = self.db.execute_query("""
                    SELECT COALESCE(SUM(amount), 0)
                    FROM treasury_transactions
                    WHERE project_id = ? AND type = 'expense'
                """, (project_id,))
                spent_amount = spent[0][0] if spent else 0
                
                # حساب المقبوضات (سندات اليومية الدائنة)
                received = self.db.execute_query("""
                    SELECT COALESCE(SUM(amount), 0)
                    FROM treasury_transactions
                    WHERE project_id = ? AND type = 'income'
                """, (project_id,))
                received_amount = received[0][0] if received else 0
                
                # حساب الرصيد
                balance = received_amount - spent_amount
                
                self.projects_tree.insert('', 'end', values=(
                    project_id, project[1], project[2] or "غير محدد", 
                    f"{project[3]:.2f}", f"{spent_amount:.2f}", 
                    f"{received_amount:.2f}", f"{balance:.2f}", project[4]
                ))
                
        except Exception as e:
            print(f"خطأ في تحميل المشاريع: {e}")
    
    def save_customer(self):
        """حفظ عميل جديد"""
        try:
            name = self.customer_name_entry.get().strip()
            vat = self.customer_vat_entry.get().strip()
            address = self.customer_address_entry.get().strip()
            phone = self.customer_phone_entry.get().strip()
            
            if not name:
                messagebox.showerror("خطأ", "❌ يرجى إدخال اسم العميل")
                return

            # فحص تكرار اسم العميل والتنبيه
            existing_cust = self.db.execute_query("SELECT id FROM customers WHERE name = ?", (name,))
            if existing_cust:
                msg = f"⚠️ تنبيه تكرار الاسم:\nاسم العميل '{name}' مسجل مسبقاً في النظام!\n\nهل تريد بالتأكيد المتابعة وتسجيله مرة أخرى؟"
                if not messagebox.askyesno("تنبيه تكرار الاسم", msg):
                    self.customer_name_entry.focus_set()
                    return
            
            self.db.execute_query("""
                INSERT INTO customers (name, tax_number, address, phone)
                VALUES (?, ?, ?, ?)
            """, (name, vat, address, phone))
            
            self.status_callback(f"✅ تم إضافة العميل: {name}")
            self.clear_customer_form()
            self.load_customers()
            self.update_combos()
            
            # Send refresh signals
            emit_customer_change()
            
            messagebox.showinfo("نجاح", f"✅ تم إضافة العميل بنجاح!")
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حفظ العميل: {str(e)}")
    
    def save_project(self):
        """حفظ مشروع جديد"""
        try:
            name = self.project_name_entry.get().strip()
            customer_text = self.project_customer_combo.get()
            start_date = self.project_start_entry.get().strip()
            budget = self.project_budget_entry.get().strip()
            status = self.project_status_combo.get()
            description = self.project_desc_entry.get().strip()
            
            if not name:
                messagebox.showerror("خطأ", "❌ يرجى إدخال اسم المشروع")
                return

            # فحص تكرار اسم المشروع والتنبيه
            existing_proj = self.db.execute_query("SELECT id FROM projects WHERE name = ?", (name,))
            if existing_proj:
                msg = f"⚠️ تنبيه تكرار الاسم:\nاسم المشروع '{name}' مسجل مسبقاً في النظام!\n\nهل تريد بالتأكيد المتابعة وتسجيله مرة أخرى؟"
                if not messagebox.askyesno("تنبيه تكرار الاسم", msg):
                    self.project_name_entry.focus_set()
                    return
            
            # استخراج معرف العميل
            customer_id = None
            if customer_text and " - " in customer_text:
                try:
                    customer_id = int(customer_text.split(" - ")[0])
                except:
                    pass
            
            try:
                budget_val = float(budget) if budget else 0
            except:
                budget_val = 0
            
            self.db.execute_query("""
                INSERT INTO projects (name, customer_id, start_date, budget, status, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, customer_id, start_date, budget_val, status, description))
            
            self.status_callback(f"✅ تم إضافة المشروع: {name}")
            self.clear_project_form()
            self.load_projects()
            self.update_combos()
            
            # Send refresh signals
            emit_project_change()
            
            messagebox.showinfo("نجاح", f"✅ تم إضافة المشروع بنجاح!")
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حفظ المشروع: {str(e)}")
    
    def clear_customer_form(self):
        """مسح نموذج العميل"""
        self.customer_name_entry.delete(0, tk.END)
        self.customer_vat_entry.delete(0, tk.END)
        self.customer_address_entry.delete(0, tk.END)
        self.customer_phone_entry.delete(0, tk.END)
    
    def clear_project_form(self):
        """مسح نموذج المشروع"""
        self.project_name_entry.delete(0, tk.END)
        self.project_customer_combo.set("-- اختر العميل --")
        self.project_start_entry.delete(0, tk.END)
        self.project_start_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.project_budget_entry.delete(0, tk.END)
        self.project_budget_entry.insert(0, "0")
        self.project_status_combo.set('نشط')
        self.project_desc_entry.delete(0, tk.END)
    
    def delete_customer(self):
        """حذف عميل"""
        try:
            selected = self.customers_tree.selection()
            if not selected:
                messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عميل للحذف")
                return
            
            item = self.customers_tree.item(selected[0], 'values')
            customer_id = item[0]
            customer_name = item[1]
            
            # التحقق من وجود مشاريع مرتبطة
            projects = self.db.execute_query(
                "SELECT COUNT(*) FROM projects WHERE customer_id = ?", 
                (customer_id,)
            )
            if projects and projects[0][0] > 0:
                messagebox.showerror("خطأ", 
                    f"❌ لا يمكن حذف العميل '{customer_name}' لأنه مرتبط بـ {projects[0][0]} مشروع")
                return
            
            if messagebox.askyesno("تأكيد", f"هل أنت متأكد من حذف العميل '{customer_name}'؟"):
                self.db.execute_query("DELETE FROM customers WHERE id = ?", (customer_id,))
                self.status_callback(f"✅ تم حذف العميل: {customer_name}")
                self.load_customers()
                self.update_combos()
                
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حذف العميل: {str(e)}")
    
    def delete_project(self):
        """حذف مشروع"""
        try:
            selected = self.projects_tree.selection()
            if not selected:
                messagebox.showwarning("تحذير", "⚠️ يرجى اختيار مشروع للحذف")
                return
            
            item = self.projects_tree.item(selected[0], 'values')
            project_id = item[0]
            project_name = item[1]
            
            # التحقق من وجود معاملات مرتبطة
            transactions = self.db.execute_query(
                "SELECT COUNT(*) FROM treasury_transactions WHERE project_id = ?", 
                (project_id,)
            )
            if transactions and transactions[0][0] > 0:
                messagebox.showerror("خطأ", 
                    f"❌ لا يمكن حذف المشروع '{project_name}' لأنه يحتوي على معاملات مالية")
                return
            
            if messagebox.askyesno("تأكيد", f"هل أنت متأكد من حذف المشروع '{project_name}'؟"):
                self.db.execute_query("DELETE FROM projects WHERE id = ?", (project_id,))
                self.status_callback(f"✅ تم حذف المشروع: {project_name}")
                self.load_projects()
                self.update_combos()
                
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حذف المشروع: {str(e)}")
    
    def edit_customer(self):
        """تعديل بيانات العميل"""
        try:
            selected = self.customers_tree.selection()
            if not selected:
                messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عميل للتعديل")
                return
            
            item = self.customers_tree.item(selected[0], 'values')
            customer_id = item[0]
            
            # فتح نافذة التعديل
            edit_window = tk.Toplevel(self.frame)
            edit_window.title(f"✏️ تعديل العميل: {item[1]}")
            edit_window.geometry("400x300")
            edit_window.transient(self.frame)
            
            # حقول التعديل
            ttk.Label(edit_window, text="اسم العميل:", font=('Segoe UI', 10, 'bold')).pack(pady=5)
            name_entry = ttk.Entry(edit_window, width=30, justify='right')
            name_entry.pack(pady=2)
            name_entry.insert(0, item[1])
            
            ttk.Label(edit_window, text="الرقم الضريبي:", font=('Segoe UI', 10, 'bold')).pack(pady=5)
            vat_entry = ttk.Entry(edit_window, width=30, justify='center')
            vat_entry.pack(pady=2)
            vat_entry.insert(0, item[2] if item[2] else "")
            
            ttk.Label(edit_window, text="العنوان:", font=('Segoe UI', 10, 'bold')).pack(pady=5)
            address_entry = ttk.Entry(edit_window, width=30, justify='right')
            address_entry.pack(pady=2)
            address_entry.insert(0, item[3] if item[3] else "")
            
            ttk.Label(edit_window, text="رقم الهاتف:", font=('Segoe UI', 10, 'bold')).pack(pady=5)
            phone_entry = ttk.Entry(edit_window, width=30, justify='center')
            phone_entry.pack(pady=2)
            phone_entry.insert(0, item[4] if item[4] else "")
            
            def save_changes():
                try:
                    c_name = name_entry.get().strip()
                    if not c_name:
                        messagebox.showerror("خطأ", "❌ يرجى إدخال اسم العميل", parent=edit_window)
                        return
                    # فحص تكرار الاسم
                    chk = self.db.execute_query("SELECT id FROM customers WHERE name = ? AND id != ?", (c_name, customer_id))
                    if chk:
                        msg = f"⚠️ تنبيه تكرار الاسم:\nاسم العميل '{c_name}' مسجل مسبقاً في النظام!\n\nهل تريد بالتأكيد المتابعة وتحديث البيانات؟"
                        if not messagebox.askyesno("تنبيه تكرار الاسم", msg, parent=edit_window):
                            name_entry.focus_set()
                            return
                    self.db.execute_query("""
                        UPDATE customers 
                        SET name = ?, tax_number = ?, address = ?, phone = ?
                        WHERE id = ?
                    """, (c_name, vat_entry.get().strip(),
                          address_entry.get().strip(), phone_entry.get().strip(), customer_id))
                    
                    self.status_callback(f"✅ تم تحديث بيانات العميل: {name_entry.get()}")
                    self.load_customers()
                    self.update_combos()
                    edit_window.destroy()
                    messagebox.showinfo("نجاح", "✅ تم تحديث بيانات العميل بنجاح!")
                    
                except Exception as e:
                    messagebox.showerror("خطأ", f"❌ فشل في تحديث البيانات: {str(e)}")
            
            ttk.Button(edit_window, text="💾 حفظ التعديلات", command=save_changes).pack(pady=20)
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في فتح نافذة التعديل: {str(e)}")
    
    def edit_project(self):
        """تعديل مشروع"""
        try:
            item = self.projects_tree.selection()
            if not item:
                messagebox.showwarning("تحذير", "⚠️ يرجى اختيار المشروع للتعديل")
                return
            
            item = item[0]
            values = self.projects_tree.item(item)['values']
            project_id = values[0]
            project_name = values[1]
            budget = values[3]
            status = values[4]
            
            # نافذة التعديل
            edit_window = tk.Toplevel(self.frame)
            edit_window.title("تعديل المشروع")
            edit_window.geometry("600x450")
            edit_window.transient(self.frame)
            
            # إطار رئيسي
            main_frame = ttk.Frame(edit_window, padding=20)
            main_frame.pack(fill='both', expand=True)
            
            # اسم المشروع
            ttk.Label(main_frame, text="اسم المشروع:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=2, sticky='e', pady=5)
            name_entry = ttk.Entry(main_frame, font=('Segoe UI', 10), width=40, justify='right')
            name_entry.grid(row=0, column=0, columnspan=2, sticky='w', pady=5)
            name_entry.insert(0, project_name)
            
            # العميل
            ttk.Label(main_frame, text="العميل:", font=('Segoe UI', 10, 'bold')).grid(row=1, column=2, sticky='e', pady=5)
            customer_combo = ttk.Combobox(main_frame, font=('Segoe UI', 10), width=37)
            customer_combo.grid(row=1, column=0, columnspan=2, sticky='w', pady=5)
            
            # ملء قائمة العملاء
            customers = self.db.execute_query("SELECT id, name FROM customers ORDER BY name")
            customer_combo['values'] = ["-- اختر العميل --"] + [f"{c[0]} - {c[1]}" for c in customers]
            customer_combo.current(0)
            
            # تحديد العميل الحالي للمشروع
            current_customer = self.db.execute_query(
                "SELECT customer_id FROM projects WHERE id = ?", (project_id,)
            )
            if current_customer and current_customer[0][0]:
                for i, value in enumerate(customer_combo['values']):
                    if value and " - " in value:
                        first_part = value.split(" - ")[0].strip()
                        if first_part.isdigit() and int(first_part) == current_customer[0][0]:
                            customer_combo.current(i)
                            break
            
            # الميزانية
            ttk.Label(main_frame, text="الميزانية:", font=('Segoe UI', 10, 'bold')).grid(row=2, column=2, sticky='e', pady=5)
            budget_entry = ttk.Entry(main_frame, font=('Segoe UI', 10), width=40)
            budget_entry.grid(row=2, column=0, columnspan=2, sticky='w', pady=5)
            budget_entry.insert(0, str(budget))
            
            # الحالة
            ttk.Label(main_frame, text="الحالة:", font=('Segoe UI', 10, 'bold')).grid(row=3, column=2, sticky='e', pady=5)
            status_combo = ttk.Combobox(main_frame, font=('Segoe UI', 10), width=37)
            status_combo.grid(row=3, column=0, columnspan=2, sticky='w', pady=5)
            status_combo['values'] = ['قيد التنفيذ', 'مكتمل', 'معلق', 'ملغي']
            status_combo.set(status)
            
            # الوصف
            ttk.Label(main_frame, text="الوصف:", font=('Segoe UI', 10, 'bold')).grid(row=4, column=2, sticky='e', pady=5)
            desc_text = tk.Text(main_frame, font=('Segoe UI', 10), width=40, height=5)
            desc_text.grid(row=4, column=0, columnspan=2, sticky='w', pady=5)
            
            # جلب الوصف الحالي
            current_desc = self.db.execute_query(
                "SELECT description FROM projects WHERE id = ?", (project_id,)
            )
            if current_desc and current_desc[0][0]:
                desc_text.insert('1.0', current_desc[0][0])
            
            def save_changes():
                try:
                    new_name = name_entry.get().strip()
                    customer_text = customer_combo.get()
                    new_budget = budget_entry.get().strip()
                    new_status = status_combo.get()
                    new_description = desc_text.get('1.0', 'end').strip()
                    
                    if not new_name:
                        messagebox.showerror("خطأ", "⚠️ يرجى إدخال اسم المشروع")
                        return
                    
                    customer_id = None
                    if customer_text and customer_text != "-- اختر العميل --":
                        if " - " in customer_text:
                            first_part = customer_text.split(" - ")[0].strip()
                            if first_part.isdigit():
                                customer_id = int(first_part)
                    
                    if not customer_id:
                        messagebox.showerror("خطأ", "⚠️ يرجى اختيار العميل")
                        return
                    
                    # التحقق من عدم تكرار الاسم
                    check_name = self.db.execute_query(
                        "SELECT id FROM projects WHERE name = ? AND id != ?", 
                        (new_name, project_id)
                    )
                    if check_name:
                        messagebox.showerror("خطأ", "⚠️ اسم المشروع موجود بالفعل")
                        return
                    
                    # تحديث المشروع
                    self.db.execute_query('''
                        UPDATE projects 
                        SET name = ?, budget = ?, status = ?, customer_id = ?, description = ?
                        WHERE id = ?
                    ''', (new_name, float(new_budget) if new_budget else 0, new_status, customer_id, new_description, project_id))
                    
                    self.load_projects()
                    self.update_combos()
                    edit_window.destroy()
                    messagebox.showinfo("نجاح", "✅ تم تعديل المشروع بنجاح")
                    
                except ValueError as e:
                    messagebox.showerror("خطأ", f"⚠️ خطأ في البيانات: {str(e)}")
                except Exception as e:
                    messagebox.showerror("خطأ", f"❌ فشل في تعديل المشروع: {str(e)}")
            
            # الأزرار
            btn_frame = ttk.Frame(main_frame)
            btn_frame.grid(row=5, column=0, columnspan=3, pady=20)
            
            ttk.Button(btn_frame, text="💾 حفظ التعديلات", 
                      command=save_changes).pack(side='right', padx=5)
            ttk.Button(btn_frame, text="❌ إلغاء", 
                      command=edit_window.destroy).pack(side='left', padx=5)
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تعديل المشروع: {str(e)}")
    
    def generate_statement(self):
        """إنشاء كشف الحساب"""
        try:
            # منع التكرار
            if hasattr(self, '_statement_processing') and self._statement_processing:
                print("Debug: Statement already processing, skipping...")
                return
            
            self._statement_processing = True
            print("Debug: Starting statement processing...")
            # مسح الجدول
            for item in self.statement_tree.get_children():
                self.statement_tree.delete(item)
            
            customer_text = self.statement_customer_combo.get()
            project_text = self.statement_project_combo.get()
            
            print(f"Debug: Customer combo value: '{customer_text}'")
            print(f"Debug: Project combo value: '{project_text}'")
            
            customer_id = None
            project_id = None
            
            # التحقق من اختيار العميل
            if customer_text and customer_text != "-- اختر العميل --":
                if " - " in customer_text:
                    first_part = customer_text.split(" - ")[0].strip()
                    if first_part.isdigit():
                        customer_id = int(first_part)
            
            # التحقق من اختيار المشروع
            if project_text and project_text != "-- اختر المشروع --":
                if " - " in project_text:
                    first_part = project_text.split(" - ")[0].strip()
                    if first_part.isdigit():
                        project_id = int(first_part)
            
            print(f"Debug: Extracted IDs - Customer: {customer_id}, Project: {project_id}")
            
            if not customer_id and not project_id:
                messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عميل أو مشروع من القوائم")
                return
            
            transactions = []
            
            # تهيئة المتغيرات في البداية
            total_debit = 0
            total_credit = 0
            running_balance = 0
            row_count = 0
            
            if project_id:
                # كشف حساب مشروع محدد
                transactions = self.db.execute_query("""
                    SELECT t.date, t.type, t.description, t.amount,
                           CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END as debit,
                           CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END as credit,
                           c.name as customer_name
                    FROM treasury_transactions t
                    LEFT JOIN customers c ON t.customer_id = c.id
                    WHERE t.project_id = ?
                    ORDER BY t.date
                """, (project_id,))
                
                print(f"Debug: Statements tab - Found {len(transactions)} transactions for project {project_id}")
                
                for trans in transactions:
                    date, trans_type, desc, amount, debit, credit, cust_name = trans
                    print(f"Debug: Statements tab - Processing project: {date}, {trans_type}, {desc}, {debit}, {credit}, {cust_name}")
                    
                    # منطق الحسابات للمشروع
                    if trans_type == 'expense':
                        trans_type_display = "🔴 صرف (سند يومية)"
                        tag = 'expense'
                        customer_debit = float(debit) if debit else 0
                        customer_credit = 0
                    else:
                        trans_type_display = "🟢 استلام (سند صرف)"
                        tag = 'income'
                        customer_credit = float(credit) if credit else 0
                        customer_debit = 0
                    
                    # حساب الإجماليات
                    total_debit += customer_debit
                    total_credit += customer_credit
                    running_balance += customer_credit - customer_debit
                    row_count += 1
                    
                    # إضافة للجدول
                    item_id = self.statement_tree.insert('', 'end', values=(
                        date,
                        trans_type_display,
                        desc,
                        f"{customer_debit:,.2f} ريال" if customer_debit > 0 else "-",
                        f"{customer_credit:,.2f} ريال" if customer_credit > 0 else "-",
                        f"{running_balance:,.2f} ريال"
                    ), tags=(tag,))
                    
                    # تحديث فوري
                    self.statement_tree.update()
                    self.statement_tree.see(item_id)
                    print(f"Debug: Added row {item_id}")
                    
            elif customer_id:
                # كشف حساب العميل (جميع مشاريعه) - معاملات مرتبطة مباشرة أو عبر المشاريع
                transactions = self.db.execute_query("""
                    SELECT t.date, t.type, t.description, t.amount,
                           CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END as debit,
                           CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END as credit,
                           p.name as project_name
                    FROM treasury_transactions t
                    LEFT JOIN projects p ON t.project_id = p.id
                    WHERE t.customer_id = ? OR (t.project_id IS NOT NULL AND t.project_id IN 
                           (SELECT id FROM projects WHERE customer_id = ?))
                    ORDER BY t.date
                """, (customer_id, customer_id))
                
                print(f"Debug: Statements tab - Found {len(transactions)} transactions for customer {customer_id}")
                
                for trans in transactions:
                    date, trans_type, desc, amount, debit, credit, proj_name = trans
                    print(f"Debug: Statements tab - Processing: {date}, {trans_type}, {desc}, {debit}, {credit}, {proj_name}")
                    
                    # تصحيح منطق الحسابات للعميل
                    if trans_type == 'expense':
                        # سند اليومية (expense) يعتبر صرف من العميل
                        trans_type_display = "🔴 صرف (سند يومية)"
                        tag = 'expense'
                        customer_debit = float(debit) if debit else 0
                        customer_credit = 0
                    else:
                        # سند الصرف (income) يعتبر استلام للعميل
                        trans_type_display = "🟢 استلام (سند صرف)"
                        tag = 'income'
                        customer_credit = float(credit) if credit else 0
                        customer_debit = 0
                    
                    # حساب الإجماليات
                    total_debit += customer_debit
                    total_credit += customer_credit
                    running_balance += customer_credit - customer_debit
                    row_count += 1
                    
                    # إضافة للجدول المباشر
                    item_id = self.statement_tree.insert('', 'end', values=(
                        date,
                        trans_type_display,
                        desc,
                        f"{customer_debit:,.2f} ريال" if customer_debit > 0 else "-",
                        f"{customer_credit:,.2f} ريال" if customer_credit > 0 else "-",
                        f"{running_balance:,.2f} ريال"
                    ), tags=(tag,))
                    
                    print(f"Debug: Inserted row with ID: {item_id}")
                    
                    # عرض فوري بدون أي انتظار
                    self.statement_tree.see(item_id)
                    self.statement_tree.focus(item_id)
                    
                    # تحديث بسيط فقط
                    self.statement_tree.update()
                    
                    print(f"Debug: Row {item_id} should be visible now")
            
            # تحديث الملخص
            if customer_id:
                # استخدام الإجماليات من الحلقة الجديدة
                self.total_debit_label.config(text=f"{total_debit:.2f} ريال")
                self.total_credit_label.config(text=f"{total_credit:.2f} ريال")
                final_balance = total_credit - total_debit
                self.final_balance_label.config(text=f"{final_balance:.2f} ريال")
            else:
                # للمعاملات القديمة (المشاريع)
                self.total_debit_label.config(text=f"{total_debit:.2f} ريال")
                self.total_credit_label.config(text=f"{total_credit:.2f} ريال")
                final_balance = total_credit - total_debit
                self.final_balance_label.config(text=f"{final_balance:.2f} ريال")
            
            # تحديد لون الرصيد
            if final_balance >= 0:
                self.final_balance_label.config(fg='green')
            else:
                self.final_balance_label.config(fg='red')
            
            # تحديث شامل للواجهة بأكملها
            import time
            time.sleep(0.2)  # انتظار أطول للتحديث
            self.statement_tree.update()
            self.statement_tree.update_idletasks()
            self.statement_tree.master.update()
            self.statement_tree.master.update_idletasks()
            
            # إعادة رسم الجدول بالكامل
            self.statement_tree.event_generate('<<TreeviewSelect>>')
            self.statement_tree.event_generate('<<TreeviewOpen>>')
            
            # التحقق النهائي من عدد الصفوف
            final_children_count = len(self.statement_tree.get_children())
            print(f"Debug: Final tree children count: {final_children_count}")
            
            # فرض تحديث مرئي نهائي
            if final_children_count > 0:
                for i, child_id in enumerate(self.statement_tree.get_children()):
                    self.statement_tree.see(child_id)
                    print(f"Debug: Made visible row {i+1}: {child_id}")
            
            print("Debug: Complete interface refresh done")
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في إنشاء كشف الحساب: {str(e)}")
        finally:
            # إعادة تعيين متغير التكرار
            self._statement_processing = False
            print("Debug: Statement processing completed")
    
    def show_project_details(self):
        """عرض تفاصيل المشروع"""
        try:
            selected = self.projects_tree.selection()
            if not selected:
                messagebox.showwarning("تحذير", "⚠️ يرجى اختيار مشروع")
                return
            
            item = self.projects_tree.item(selected[0], 'values')
            project_id = item[0]
            project_name = item[1]
            
            # إنشاء نافذة التفاصيل
            details_window = tk.Toplevel(self.frame)
            details_window.title(f"📋 تفاصيل المشروع: {project_name}")
            details_window.geometry("800x600")
            details_window.transient(self.frame)
            
            # جلب تفاصيل المشروع
            project = self.db.execute_query(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            )
            customer_name = "غير محدد"
            if project and project[0][7]:  # customer_id
                customer = self.db.execute_query(
                    "SELECT name FROM customers WHERE id = ?", (project[0][7],)
                )
                if customer:
                    customer_name = customer[0][0]
            
            # معلومات المشروع
            info_frame = ttk.LabelFrame(details_window, text="📊 معلومات المشروع")
            info_frame.pack(fill='x', padx=10, pady=10)
            
            info_text = f"""
            اسم المشروع: {project_name}
            العميل: {customer_name}
            تاريخ البدء: {project[0][3] if project else 'غير محدد'}
            الميزانية: {float(project[0][4] if project and project[0][4] else 0):.2f} ريال
            الحالة: {project[0][5] if project else 'غير محدد'}
            الوصف: {project[0][8] if project else 'غير محدد'}
            """
            
            ttk.Label(info_frame, text=info_text, font=('Segoe UI', 10), 
                     justify='right').pack(padx=10, pady=10)
            
            # جدول المعاملات
            trans_frame = ttk.LabelFrame(details_window, text="💰 حركات المشروع المالية")
            trans_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            columns = ('date', 'type', 'description', 'amount', 'voucher_type')
            trans_tree = ttk.Treeview(trans_frame, columns=columns, 
                                     show='headings', height=12)
            
            trans_tree.heading('date', text='التاريخ')
            trans_tree.heading('type', text='النوع')
            trans_tree.heading('description', text='البيان')
            trans_tree.heading('amount', text='المبلغ')
            trans_tree.heading('voucher_type', text='نوع السند')
            
            trans_tree.column('date', width=100)
            trans_tree.column('type', width=80)
            trans_tree.column('description', width=300)
            trans_tree.column('amount', width=100)
            trans_tree.column('voucher_type', width=100)
            
            trans_tree.pack(side='left', fill='both', expand=True)
            
            scrollbar = ttk.Scrollbar(trans_frame, orient="vertical", 
                                    command=trans_tree.yview)
            scrollbar.pack(side='right', fill='y')
            trans_tree.configure(yscrollcommand=scrollbar.set)
            
            # تحميل المعاملات
            transactions = self.db.execute_query("""
                SELECT date, type, description, amount,
                       CASE 
                           WHEN description LIKE 'سند صرف%' THEN 'سند صرف'
                           WHEN description LIKE 'سند يومية%' THEN 'سند يومية'
                           ELSE 'أخرى'
                       END as voucher_type
                FROM treasury_transactions
                WHERE project_id = ?
                ORDER BY date DESC
            """, (project_id,))
            
            total_spent = 0
            total_received = 0
            
            for trans in transactions:
                date, trans_type, desc, amount, voucher_type = trans
                amount_val = float(amount) if amount else 0
                
                if trans_type == 'expense':
                    total_spent += amount_val
                    trans_tree.insert('', 'end', values=(
                        date, 'مصروف', desc, f"{amount_val:.2f}", voucher_type
                    ), tags=('expense',))
                else:
                    total_received += amount_val
                    trans_tree.insert('', 'end', values=(
                        date, 'إيراد', desc, f"{amount_val:.2f}", voucher_type
                    ), tags=('income',))
            
            trans_tree.tag_configure('expense', foreground='red')
            trans_tree.tag_configure('income', foreground='green')
            
            # ملخص المشروع
            summary_frame = ttk.LabelFrame(details_window, text="📊 ملخص المشروع")
            summary_frame.pack(fill='x', padx=10, pady=10)
            
            balance = total_received - total_spent
            
            summary_text = f"""
            إجمالي المصروفات (سندات الصرف): {total_spent:.2f} ريال
            إجمالي المقبوضات (سندات اليومية): {total_received:.2f} ريال
            صافي الرصيد: {balance:.2f} ريال
            """
            
            balance_color = 'green' if balance >= 0 else 'red'
            summary_label = ttk.Label(summary_frame, text=summary_text, 
                                    font=('Segoe UI', 11, 'bold'), 
                                    foreground=balance_color, justify='right')
            summary_label.pack(padx=10, pady=10)
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في عرض التفاصيل: {str(e)}")
    
    def show_customer_statement(self):
        """عرض كشف حساب العميل في نافذة منفصلة"""
        try:
            selected = self.customers_tree.selection()
            if not selected:
                messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عميل")
                return
            
            item = self.customers_tree.item(selected[0], 'values')
            customer_id = item[0]
            customer_name = item[1]
            
            # إنشاء نافذة كشف الحساب المنفصلة
            self.create_statement_window(customer_id=customer_id, customer_name=customer_name)
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في عرض كشف الحساب: {str(e)}")
    
    def show_project_statement(self):
        """عرض كشف حساب المشروع في نافذة منفصلة"""
        try:
            selected = self.projects_tree.selection()
            if not selected:
                messagebox.showwarning("تحذير", "⚠️ يرجى اختيار مشروع")
                return
            
            item = self.projects_tree.item(selected[0], 'values')
            project_id = item[0]
            project_name = item[1]
            
            # إنشاء نافذة كشف الحساب المنفصلة
            self.create_statement_window(project_id=project_id, project_name=project_name)
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في عرض كشف الحساب: {str(e)}")
    
    def create_statement_window(self, customer_id=None, customer_name=None, project_id=None, project_name=None):
        """إنشاء نافذة كشف حساب احترافية - تصميم 2025"""
        from datetime import datetime
        import tkinter.font as tkfont
        
        # إنشاء النافذة بحجم متوسط مع أزرار شريط العنوان
        stmt_window = tk.Toplevel(self.frame)
        stmt_window.title(f"كشف حساب - {customer_name or project_name}")
        stmt_window.geometry("1200x800")
        stmt_window.configure(bg='#FFFFFF')
        
        # إضافة أزرار شريط العنوان (تصغير، تكبير، إغلاق)
        stmt_window.resizable(True, True)
        
        # إطار رئيسي بدون تمرير
        main_container = tk.Frame(stmt_window, bg='#F8F9FA')
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # ===== رأس الكشف =====
        header_frame = tk.Frame(main_container, bg='#1E3A5F', padx=30, pady=20)
        header_frame.pack(fill='x')
        
        # شعار النظام
        tk.Label(header_frame, text="FAWATEERY", 
                font=('Segoe UI', 12, 'bold'), bg='#1E3A5F', fg='#5DADE2').pack(anchor='w')
        
        # عنوان الكشف
        title = "كشف حساب العميل" if customer_name else "كشف حساب المشروع"
        subtitle = customer_name or project_name
        
        tk.Label(header_frame, text=title, 
                font=('Segoe UI', 18, 'bold'), bg='#1E3A5F', fg='#FFFFFF').pack(pady=(10, 0))
        tk.Label(header_frame, text=subtitle, 
                font=('Segoe UI', 14), bg='#1E3A5F', fg='#85C1E9').pack()
        
        # التاريخ
        current_date = datetime.now().strftime('%Y-%m-%d')
        tk.Label(header_frame, text=f"التاريخ: {current_date}", 
                font=('Segoe UI', 10), bg='#1E3A5F', fg='#AED6F1').pack(anchor='e', pady=(10, 0))
        
        # ===== عنوان الجدول =====
        table_title = tk.Frame(main_container, bg='#2980B9', padx=20, pady=10)
        table_title.pack(fill='x', pady=(20, 0))
        tk.Label(table_title, text="سجل الحركات المالية", 
                font=('Segoe UI', 12, 'bold'), bg='#2980B9', fg='white').pack()
        
        # ===== الجدول =====
        table_frame = tk.Frame(main_container, bg='#FFFFFF', bd=1, relief='solid')
        table_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        columns = ('date', 'type', 'account', 'description', 'debit', 'credit', 'balance')
        tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=12)
        
        # تنسيق الأعمدة - أحجام مناسبة للنص
        tree.heading('date', text='التاريخ')
        tree.heading('type', text='النوع')
        tree.heading('account', text='الحساب')
        tree.heading('description', text='البيان')
        tree.heading('debit', text='مدين (صرف)')
        tree.heading('credit', text='دائن (استلام)')
        tree.heading('balance', text='الرصيد')
        
        # أحجام الأعمدة المعدلة
        tree.column('date', width=100, anchor='center')
        tree.column('type', width=140, anchor='center')
        tree.column('account', width=180, anchor='w')
        tree.column('description', width=350, anchor='w')
        tree.column('debit', width=100, anchor='e')
        tree.column('credit', width=100, anchor='e')
        tree.column('balance', width=100, anchor='e')
        
        tree.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        vsb.pack(side='right', fill='y', padx=(0, 10), pady=10)
        tree.configure(yscrollcommand=vsb.set)
        
        # ألوان الصفوف
        tree.tag_configure('expense', background='#FDEDEC', foreground='#C0392B')
        tree.tag_configure('income', background='#EAFAF1', foreground='#27AE60')
        tree.tag_configure('total', background='#EBF5FB', foreground='#154360')
        
        # ===== جلب البيانات وملء الجدول =====
        transactions = []
        if project_id:
            print(f"Debug: Querying for project_id = {project_id}")
            transactions = self.db.execute_query("""
                SELECT t.date, t.type, t.account_name, t.description, t.amount,
                       CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END as debit,
                       CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END as credit,
                       c.name as customer_name
                FROM treasury_transactions t
                LEFT JOIN customers c ON t.customer_id = c.id
                WHERE t.project_id = ?
                ORDER BY t.date
            """, (project_id,))
        elif customer_id:
            print(f"Debug: Querying for customer_id = {customer_id}")
            transactions = self.db.execute_query("""
                SELECT t.date, t.type, t.account_name, t.description, t.amount,
                       CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END as debit,
                       CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END as credit,
                       p.name as project_name
                FROM treasury_transactions t
                LEFT JOIN projects p ON t.project_id = p.id
                WHERE t.customer_id = ? OR (t.project_id IS NOT NULL AND t.project_id IN 
                       (SELECT id FROM projects WHERE customer_id = ?))
                ORDER BY t.date
            """, (customer_id, customer_id))
        
        print(f"Debug: Total transactions found: {len(transactions)}")
        for i, trans in enumerate(transactions):
            print(f"Debug: Transaction {i+1}: {trans}")
        
        # تصحيح: إذا كانت المعاملات فارغة، أضف رسالة توضيحية
        if not transactions:
            messagebox.showinfo("معلومات", "ℹ️ لا توجد معاملات لهذا الحساب")
            return
        
        # ملء الجدول
        total_debit = 0
        total_credit = 0
        running_balance = 0
        row_count = 0
        
        print(f"Debug: Starting to fill table with {len(transactions)} transactions")
        
        for trans in transactions:
            print(f"Debug: Processing transaction: {trans}")
            if project_id:
                date, trans_type, account_name, desc, amount, debit, credit, cust_name = trans
                print(f"Debug: Project transaction - Date: {date}, Type: {trans_type}, Account: {account_name}, Desc: {desc}, Cust: {cust_name}")
                account_display = account_name if account_name else "-"
                desc = f"👤 [{cust_name}] {desc}" if cust_name else desc
            else:
                date, trans_type, account_name, desc, amount, debit, credit, proj_name = trans
                print(f"Debug: Customer transaction - Date: {date}, Type: {trans_type}, Account: {account_name}, Desc: {desc}, Proj: {proj_name}")
                account_display = account_name if account_name else "-"
                desc = f"🏗️ [{proj_name}] {desc}"
            
            debit_val = float(debit) if debit else 0
            credit_val = float(credit) if credit else 0
            
            # تصحيح منطق الحسابات للعميل والمشروع
            if customer_id:
                # حسابات العميل: المنطق الصحيح
                if trans_type == 'expense':
                    # سند اليومية (expense) يعتبر صرف من العميل
                    trans_type_display = "صرف (سند يومية)"
                    tag = 'expense'  # استخدم لون الأحمر
                    customer_debit = debit_val  # الصرف من العميل
                    customer_credit = 0
                else:
                    # سند الصرف (income) يعتبر استلام للعميل
                    trans_type_display = "استلام (سند صرف)"
                    tag = 'income'  # استخدم لون الأخضر
                    customer_credit = credit_val  # الاستلام للعميل
                    customer_debit = 0
            else:
                # حسابات المشروع: المنطق الصحيح
                # سند الصرف (income) = فلوس دخلت المشروع = credit
                # سند اليومية (expense) = فلوس المشروع دفعها = debit
                if trans_type == 'expense':
                    # سند اليومية (expense) يعتبر صرف من المشروع
                    trans_type_display = "🔴 صرف (سند يومية)"
                    tag = 'expense'  # استخدم لون الأحمر
                    customer_debit = debit_val  # الصرف من المشروع
                    customer_credit = 0
                else:
                    # سند الصرف (income) يعتبر استلام للمشروع
                    trans_type_display = "🟢 استلام (سند صرف)"
                    tag = 'income'  # استخدم لون الأخضر
                    customer_credit = credit_val  # الاستلام للمشروع
                    customer_debit = 0
            
            # حساب الإجماليات للعرض
            total_debit += customer_debit
            total_credit += customer_credit
            running_balance += customer_credit - customer_debit
            row_count += 1
            
            print(f"Debug: Adding row {row_count}: {date}, {trans_type_display}, {customer_debit}, {customer_credit}")
            
            tree.insert('', 'end', values=(
                date,
                trans_type_display,
                account_display,
                desc,
                f"{customer_debit:,.2f} ريال" if customer_debit > 0 else "-",
                f"{customer_credit:,.2f} ريال" if customer_credit > 0 else "-",
                f"{running_balance:,.2f} ريال"
            ), tags=(tag,))
            
            # تحديث فوري للجدول بعد كل إضافة
            tree.update()
            tree.update_idletasks()
            stmt_window.update()
            stmt_window.update_idletasks()
        
        # تحديث الجدول لعرض البيانات
        tree.update()
        tree.update_idletasks()
        
        # فرض تحديث كامل للنافذة
        stmt_window.update()
        stmt_window.update_idletasks()
        
        # إضافة صف إجمالي احترافي
        if row_count > 0:
            print(f"Debug: Adding summary with total_debit={total_debit}, total_credit={total_credit}")
            tree.insert('', 'end', values=(
                "", "═══════════════════════════════════════════════════════",
                "══════════════════════════════════════════════════════════════════",
                "══════════════════════════════════════════════════════════════════",
                "══════════════════════════════════════════════════════════════════",
                "══════════════════════════════════════════════════════════════════"
            ), tags=('header_row',))
            tree.insert('', 'end', values=(
                "", f"الإجمالي النهائي ({row_count} حركة)",
                f"المجموع: {total_debit + total_credit:,.2f} ريال",
                f"{total_debit:,.2f} ريال",
                f"{total_credit:,.2f} ريال",
                f"{total_credit - total_debit:,.2f} ريال"
            ), tags=('header_row',))
        
        # ===== بطاقات الملخص =====
        summary_frame = tk.Frame(main_container, bg='#F8F9FA', pady=15)
        summary_frame.pack(fill='x')
        
        final_balance = total_credit - total_debit
        balance_color = '#27AE60' if final_balance >= 0 else '#E74C3C'
        
        # بطاقة المصروفات
        debit_card = tk.Frame(summary_frame, bg='#E74C3C', padx=25, pady=12)
        debit_card.pack(side='right', padx=10)
        tk.Label(debit_card, text="المصروفات", font=('Segoe UI', 10, 'bold'), 
                bg='#E74C3C', fg='white').pack()
        tk.Label(debit_card, text=f"{total_debit:,.2f} ريال", font=('Segoe UI', 14, 'bold'), 
                bg='#E74C3C', fg='white').pack()
        
        # بطاقة المقبوضات
        credit_card = tk.Frame(summary_frame, bg='#27AE60', padx=25, pady=12)
        credit_card.pack(side='right', padx=10)
        tk.Label(credit_card, text="المقبوضات", font=('Segoe UI', 10, 'bold'), 
                bg='#27AE60', fg='white').pack()
        tk.Label(credit_card, text=f"{total_credit:,.2f} ريال", font=('Segoe UI', 14, 'bold'), 
                bg='#27AE60', fg='white').pack()
        
        # بطاقة الرصيد
        balance_card = tk.Frame(summary_frame, bg=balance_color, padx=30, pady=15)
        balance_card.pack(side='right', padx=10)
        tk.Label(balance_card, text="الرصيد النهائي", font=('Segoe UI', 11, 'bold'), 
                bg=balance_color, fg='white').pack()
        tk.Label(balance_card, text=f"{final_balance:,.2f} ريال", font=('Segoe UI', 16, 'bold'), 
                bg=balance_color, fg='white').pack()
        
        # ===== الأزرار =====
        btn_frame = tk.Frame(main_container, bg='#F8F9FA', pady=10)
        btn_frame.pack(fill='x')
        
        # تخزين البيانات
        stmt_window.transactions_data = transactions
        stmt_window.summary_data = {
            'total_debit': total_debit,
            'total_credit': total_credit,
            'final_balance': final_balance,
            'row_count': row_count,
            'title': f"كشف حساب - {customer_name or project_name}",
            'customer_name': customer_name,
            'project_name': project_name,
            'date': current_date
        }
        
        # زر PDF
        tk.Button(btn_frame, text="طباعة PDF", font=('Segoe UI', 11, 'bold'),
                 bg='#3498DB', fg='white', padx=25, pady=8,
                 command=lambda: self.print_statement_window(stmt_window)).pack(side='right', padx=5)
        
        # زر Excel
        tk.Button(btn_frame, text="تصدير Excel", font=('Segoe UI', 11, 'bold'),
                 bg='#27AE60', fg='white', padx=25, pady=8,
                 command=lambda: self.export_statement_excel(stmt_window)).pack(side='right', padx=5)
        
        # زر إغلاق
        tk.Button(btn_frame, text="إغلاق", font=('Segoe UI', 11, 'bold'),
                 bg='#95A5A6', fg='white', padx=25, pady=8,
                 command=stmt_window.destroy).pack(side='right', padx=5)
    
    def print_statement_window(self, window):
        """طباعة كشف الحساب من النافذة"""
        try:
            from datetime import datetime
            import os
            
            # التأكد من وجود البيانات
            summary_data = getattr(window, 'summary_data', {})
            transactions_data = getattr(window, 'transactions_data', [])
            
            # معالجة البيانات إذا كانت None
            if not summary_data:
                summary_data = {}
            if not transactions_data:
                transactions_data = []
            
            # حفظ الملف على الديسك توب
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            customer_name = summary_data.get('customer_name', 'عميل')
            filename = f"كشف_حساب_{customer_name}_{timestamp}.pdf"
            desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
            filepath = os.path.join(desktop_path, filename)
            
            self.generate_statement_pdf(filepath, summary_data, transactions_data)
            
            # فتح الملف تلقائياً
            try:
                if os.name == 'nt':
                    os.startfile(filepath)
                elif os.name == 'posix':
                    os.system(f'xdg-open {filepath}')
            except:
                print("⚠️ لا يمكن فتح الملف تلقائياً")
            
            messagebox.showinfo("نجاح", f"✅ تم حفظ كشف الحساب بنجاح!\n📂 تم حفظها في: {filepath}")
                
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في طباعة كشف الحساب: {str(e)}")
    
    def export_statement_excel(self, window):
        """تصدير كشف الحساب كـ Excel"""
        try:
            import pandas as pd
            from tkinter import filedialog
            
            # استخراج البيانات من النافذة
            summary_data = getattr(window, 'summary_data', {})
            transactions = getattr(window, 'transactions_data', [])
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="حفظ كشف الحساب"
            )
            
            if filename:
                # تحويل البيانات لجدول
                data = []
                for trans in transactions:
                    if len(trans) >= 6:
                        date, trans_type, desc, amount, debit, credit = trans[:6]
                    elif len(trans) >= 7:
                        date, trans_type, desc, amount, debit, credit, proj_name = trans
                        desc = f"[{proj_name}] {desc}"
                    else:
                        continue
                    
                    debit_val = float(debit) if debit else 0
                    credit_val = float(credit) if credit else 0
                    trans_type_display = "صرف" if trans_type == 'expense' else "استلام"
                    
                    data.append({
                        'التاريخ': date,
                        'نوع الحركة': trans_type_display,
                        'البيان': desc,
                        'المدين (ريال)': debit_val if debit_val > 0 else 0,
                        'الدائن (ريال)': credit_val if credit_val > 0 else 0
                    })
                
                # إنشاء DataFrame
                df = pd.DataFrame(data)
                
                # إضافة صف الإجماليات
                summary_row = {
                    'التاريخ': '',
                    'نوع الحركة': 'الإجمالي',
                    'البيان': f"عدد الحركات: {len(data)}",
                    'المدين (ريال)': summary_data.get('total_debit', 0),
                    'الدائن (ريال)': summary_data.get('total_credit', 0)
                }
                df = pd.concat([df, pd.DataFrame([summary_row])], ignore_index=True)
                
                # حفظ الملف
                df.to_excel(filename, index=False, engine='openpyxl')
                messagebox.showinfo("نجاح", f"✅ تم تصدير كشف الحساب بنجاح!\n{filename}")
                
        except ImportError:
            messagebox.showerror("خطأ", "❌ يجب تثبيت مكتبة pandas و openpyxl")
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تصدير Excel: {str(e)}")
    
    def export_statement_pdf(self, window):
        """تصدير كشف الحساب كـ PDF"""
        self.print_statement_window(window)
    
    def print_statement(self):
        """طباعة كشف الحساب (من التبويب القديم)"""
        messagebox.showinfo("معلومة", "🖨️ استخدم زر كشف الحساب من قائمة العملاء أو المشاريع")
    
    def export_statement(self):
        """تصدير كشف الحساب (من التبويب القديم)"""
        messagebox.showinfo("معلومة", "💾 استخدم زر كشف الحساب من قائمة العملاء أو المشاريع")
    
    def generate_statement_pdf(self, filename, summary, transactions):
        """إنشاء ملف PDF لكشف الحساب بنفس تصميم الفاتورة"""
        try:
            # معالجة شاملة للبيانات
            if summary is None:
                summary = {}
            if transactions is None:
                transactions = []
            
            # التأكد من أن summary هو dict
            if not isinstance(summary, dict):
                summary = {}
            
            # التأكد من أن transactions هو list
            if not isinstance(transactions, list):
                transactions = []
            
            from datetime import datetime
            import os
            
            # استخراج البيانات مع معالجة الأخطاء
            try:
                title = summary.get('title', 'كشف حساب')
                customer_name = summary.get('customer_name', 'غير محدد')
                project_name = summary.get('project_name')
                total_debit = summary.get('total_debit', 0)
                total_credit = summary.get('total_credit', 0)
                final_balance = summary.get('final_balance', 0)
                row_count = summary.get('row_count', 0)
            except Exception as e:
                print(f"⚠️ خطأ في استخراج بيانات الملخص: {e}")
                title = 'كشف حساب'
                customer_name = 'غير محدد'
                project_name = None
                total_debit = 0
                total_credit = 0
                final_balance = 0
                row_count = 0
            
            # إنشاء PDF باستخدام fpdf2 (يدعم العربية بشكل أفضل)
            try:
                from fpdf import FPDF
                pdf = FPDF(orientation='P', unit='mm', format='A4')
                pdf.add_page()
                pdf.set_auto_page_break(auto=True, margin=15)
                
                # تحميل خط Amiri باستخدام fpdf2
                import os
                current_dir = os.path.dirname(os.path.abspath(__file__))
                amiri_regular = os.path.join(current_dir, 'Amiri', 'Amiri-Regular.ttf')
                amiri_bold = os.path.join(current_dir, 'Amiri', 'Amiri-Bold.ttf')
                
                font_name = 'Amiri'
                try:
                    pdf.add_font('Amiri', '', amiri_regular)
                    pdf.add_font('Amiri', 'B', amiri_bold)
                except Exception as font_error:
                    print(f"Warning: Could not load Amiri font: {font_error}")
                    font_name = 'Arial'
            
                # التأكد من أن جميع القيم موجودة
                try:
                    total_debit = float(total_debit) if total_debit else 0
                    total_credit = float(total_credit) if total_credit else 0
                    final_balance = float(final_balance) if final_balance else 0
                    row_count = int(row_count) if row_count else 0
                except (ValueError, TypeError):
                    total_debit = 0
                    total_credit = 0
                    final_balance = 0
                    row_count = 0
                
                # ألوان الفاتورة
                header_color = (76, 117, 163)  # #4C75A3
                dark_blue = (1, 27, 64)  # #011B40
                label_blue = (46, 80, 144)  # #2E5090
            
                # ===== ألوان احترافية =====
                primary_color = (41, 65, 114)      # أزرق داكن #294172
                secondary_color = (52, 73, 94)     # رمادي أزرق #34495E
                accent_color = (52, 152, 219)      # أزرق فاتح #3498DB
                light_bg = (248, 249, 250)         # خلفية فاتحة #F8F9FA
                white = (255, 255, 255)
                
                # ===== رأس الصفحة الاحترافي =====
                start_y = 10
                
                # خلفية رأس الصفحة
                pdf.set_fill_color(*primary_color)
                pdf.rect(10, start_y, 190, 40, 'F')
                
                # خط علوي مميز
                pdf.set_fill_color(*accent_color)
                pdf.rect(10, start_y, 190, 4, 'F')
                
                # شعار النظام
                pdf.set_text_color(*white)
                pdf.set_font(font_name, 'B', 20)
                pdf.set_xy(10, start_y + 10)
                pdf.cell(190, 10, ar('FAWATEERY'), 0, 1, 'C')
                
                pdf.set_font(font_name, '', 12)
                pdf.cell(190, 6, ar('نظام الفواتير والمحاسبة الذكي'), 0, 1, 'C')
                
                # ===== عنوان الكشف في بطاقة منفصلة =====
                y_pos = start_y + 48
                
                # إطار البطاقة
                pdf.set_draw_color(200, 200, 200)
                pdf.set_fill_color(*white)
                pdf.rect(10, y_pos, 190, 22, 'DF')
                
                # خط جانبي ملون
                pdf.set_fill_color(*accent_color)
                pdf.rect(10, y_pos, 5, 22, 'F')
                
                # عنوان الكشف
                pdf.set_text_color(*primary_color)
                pdf.set_font(font_name, 'B', 14)
                pdf.set_xy(20, y_pos + 4)
                display_name = customer_name or project_name or ar('غير محدد')
                pdf.cell(180, 8, ar(f'كشف حساب: {display_name}'), 0, 1, 'R')
                
                # التاريخ
                pdf.set_text_color(120, 120, 120)
                pdf.set_font(font_name, '', 10)
                pdf.set_xy(20, y_pos + 14)
                pdf.cell(180, 6, ar(f'تاريخ إنشاء الكشف: {datetime.now().strftime("%Y-%m-%d")}'), 0, 1, 'R')
                
                pdf.ln(8)
                
                # ===== جدول المعاملات الاحترافي =====
                y_pos = pdf.get_y()
                
                # عنوان الجدول
                pdf.set_fill_color(*secondary_color)
                pdf.set_text_color(*white)
                pdf.set_font(font_name, 'B', 11)
                pdf.set_xy(10, y_pos)
                pdf.cell(190, 9, ar('تفاصيل الحركات المالية'), 0, 1, 'C', True)
                
                y_pos += 9
                
                # رأس الجدول
                pdf.set_fill_color(236, 240, 241)  # رمادي فاتح #ECF0F1
                pdf.set_text_color(*secondary_color)
                pdf.set_font(font_name, 'B', 10)
                pdf.set_xy(10, y_pos)
                pdf.cell(25, 9, ar('التاريخ'), 1, 0, 'C', True)
                pdf.cell(25, 9, ar('النوع'), 1, 0, 'C', True)
                pdf.cell(40, 9, ar('الحساب'), 1, 0, 'C', True)
                pdf.cell(60, 9, ar('البيان'), 1, 0, 'C', True)
                pdf.cell(20, 9, ar('صرف'), 1, 0, 'C', True)
                pdf.cell(20, 9, ar('استلام'), 1, 1, 'C', True)
                
                # بيانات الجدول
                pdf.set_font(font_name, '', 9)
                running_balance = 0
                row_count = 0
            
                # معالجة المعاملات
                if not transactions:
                    transactions = []
                
                for trans in transactions:
                    try:
                        # التأكد من أن trans هو tuple أو list
                        if not isinstance(trans, (tuple, list)):
                            print(f"⚠️ المعاملة ليست tuple أو list: {trans}")
                            continue
                        
                        # معالجة الحالات المختلفة
                        if len(trans) >= 7:
                            date, trans_type, account_name, desc, amount, debit, credit = trans[:7]
                        elif len(trans) >= 6:
                            date, trans_type, desc, amount, debit, credit = trans[:6]
                            account_name = "-"
                        elif len(trans) >= 5:
                            date, trans_type, desc, amount, debit = trans[:5]
                            credit = 0
                            account_name = "-"
                        elif len(trans) >= 4:
                            date, trans_type, desc, amount = trans[:4]
                            debit = 0
                            credit = 0
                            account_name = "-"
                        else:
                            print(f"⚠️ المعاملة قصيرة جداً: {trans}")
                            continue
                    except (ValueError, IndexError, TypeError) as e:
                        print(f"⚠️ خطأ في معالجة المعاملة: {e}, trans: {trans}")
                        continue
                
                    debit_val = float(debit) if debit else 0
                    credit_val = float(credit) if credit else 0
                    running_balance += credit_val - debit_val
                    row_count += 1
                    
                    # نوع الحركة - تحديد بناءً على debit/credit
                    row_num = row_count % 2  # تناوب الألوان
                    if debit_val > 0:
                        trans_display = ar('صرف')
                        bg_color = (254, 242, 242) if row_num == 0 else (253, 237, 236)  # أحمر فاتح
                        text_color = (192, 57, 43)
                    elif credit_val > 0:
                        trans_display = ar('استلام')
                        bg_color = (232, 245, 233) if row_num == 0 else (232, 246, 237)  # أخضر فاتح
                        text_color = (39, 174, 96)
                    else:
                        trans_display = ar('-')
                        bg_color = (250, 250, 250) if row_num == 0 else (245, 247, 250)
                        text_color = (100, 100, 100)
                    
                    pdf.set_fill_color(*bg_color)
                    pdf.set_text_color(*text_color)
                    
                    pdf.cell(25, 8, str(date)[:10], 1, 0, 'C', True)
                    pdf.cell(25, 8, trans_display, 1, 0, 'C', True)
                    
                    # اسم الحساب
                    account_text = ar(str(account_name)[:20]) if account_name else '-'
                    pdf.cell(40, 8, account_text, 1, 0, 'R', True)
                    
                    # البيان
                    desc_text = ar(str(desc)[:30]) if desc else ''
                    pdf.cell(60, 8, desc_text, 1, 0, 'R', True)
                    
                    # المبالغ
                    debit_str = f'{debit_val:,.0f}' if debit_val > 0 else '-'
                    credit_str = f'{credit_val:,.0f}' if credit_val > 0 else '-'
                    
                    pdf.cell(20, 8, debit_str, 1, 0, 'C', True)
                    pdf.cell(20, 8, credit_str, 1, 1, 'C', True)
                
                pdf.ln(10)
                
                # ===== فاصل =====
                pdf.ln(5)
                
                # ===== قسم الملخص الاحترافي =====
                y_pos = pdf.get_y()
                
                # عنوان الملخص
                pdf.set_fill_color(*secondary_color)
                pdf.set_text_color(*white)
                pdf.set_font(font_name, 'B', 11)
                pdf.set_xy(10, y_pos)
                pdf.cell(190, 9, ar('ملخص الحساب'), 0, 1, 'C', True)
                
                y_pos += 9
                
                # خلفية الملخص
                pdf.set_fill_color(245, 247, 250)  # رمادي فاتح جداً
                pdf.rect(10, y_pos, 190, 35, 'F')
                
                # بطاقة المصروفات
                pdf.set_fill_color(*white)
                pdf.set_draw_color(220, 220, 220)
                pdf.rect(130, y_pos + 5, 65, 25, 'DF')
                pdf.set_fill_color(231, 76, 60)
                pdf.rect(130, y_pos + 5, 65, 5, 'F')  # خط علوي أحمر
                pdf.set_xy(130, y_pos + 12)
                pdf.set_text_color(100, 100, 100)
                pdf.set_font(font_name, 'B', 10)
                pdf.cell(65, 6, ar('المصروفات'), 0, 0, 'C')
                pdf.set_xy(130, y_pos + 20)
                pdf.set_text_color(231, 76, 60)
                pdf.set_font(font_name, 'B', 13)
                pdf.cell(65, 8, ar(f'{int(total_debit):,} ريال'), 0, 0, 'C')
                
                # بطاقة المقبوضات
                pdf.set_fill_color(*white)
                pdf.rect(70, y_pos + 5, 55, 25, 'DF')
                pdf.set_fill_color(39, 174, 96)
                pdf.rect(70, y_pos + 5, 55, 5, 'F')  # خط علوي أخضر
                pdf.set_xy(70, y_pos + 12)
                pdf.set_text_color(100, 100, 100)
                pdf.set_font(font_name, 'B', 10)
                pdf.cell(55, 6, ar('المقبوضات'), 0, 0, 'C')
                pdf.set_xy(70, y_pos + 20)
                pdf.set_text_color(39, 174, 96)
                pdf.set_font(font_name, 'B', 13)
                pdf.cell(55, 8, ar(f'{int(total_credit):,} ريال'), 0, 0, 'C')
                
                # بطاقة الرصيد (أكبر)
                balance_color_top = (41, 128, 185) if final_balance >= 0 else (231, 76, 60)
                balance_color_text = (41, 128, 185) if final_balance >= 0 else (231, 76, 60)
                pdf.set_fill_color(*white)
                pdf.rect(15, y_pos + 2, 50, 31, 'DF')
                pdf.set_fill_color(*balance_color_top)
                pdf.rect(15, y_pos + 2, 50, 5, 'F')  # خط علوي
                pdf.set_xy(15, y_pos + 10)
                pdf.set_text_color(100, 100, 100)
                pdf.set_font(font_name, 'B', 10)
                pdf.cell(50, 6, ar('الرصيد'), 0, 0, 'C')
                pdf.set_xy(15, y_pos + 18)
                pdf.set_text_color(*balance_color_text)
                pdf.set_font(font_name, 'B', 15)
                pdf.cell(50, 10, ar(f'{int(final_balance):,} ريال'), 0, 0, 'C')
                
                # ===== تذييل الصفحة الاحترافي =====
                pdf.set_y(-20)
                pdf.set_fill_color(*secondary_color)
                pdf.rect(10, pdf.get_y(), 190, 15, 'F')
                pdf.set_text_color(*white)
                pdf.set_font(font_name, '', 9)
                pdf.cell(0, 6, ar('تم إنشاء هذا الكشف بواسطة نظام Fawateery'), 0, 1, 'C')
                pdf.set_text_color(180, 180, 180)
                pdf.set_font(font_name, '', 8)
                pdf.cell(0, 5, ar(f'{datetime.now().strftime("%Y-%m-%d")}'), 0, 0, 'C')
                
                pdf.output(filename)
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                print(f"❌ خطأ في إنشاء PDF: {e}")
                print(f"تفاصيل الخطأ:\n{error_details}")
                messagebox.showerror("خطأ", f"❌ فشل في إنشاء ملف PDF: {str(e)}\n\nقد يكون السبب مشكلة في الخط العربي.\nجاري استخدام خط افتراضي...")
                return
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ خطأ في معالجة البيانات: {e}")
            print(f"تفاصيل الخطأ:\n{error_details}")
            messagebox.showerror("خطأ", f"❌ فشل في معالجة البيانات: {str(e)}")
            return
