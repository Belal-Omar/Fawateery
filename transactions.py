import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
from database import Database
import pandas as pd
from central_refresh import emit_customer_change, emit_transaction_change, emit_project_change

try:
    from tkcalendar import DateEntry
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False

class AccountsReceivableDialog(tk.Toplevel):
    """نافذة إدارة الحسابات المدينة (العملاء)"""
    def __init__(self, parent, db, status_callback, refresh_callback, account_id=None):
        super().__init__(parent)
        self.db = db
        self.status_callback = status_callback
        self.refresh_callback = refresh_callback
        self.account_id = account_id
        self.transaction_id = account_id
        
        # إنشاء ScrollArea للنافذة
        self.create_scrollable_content()
        
        self.setup_dialog()
        self.load_data()
        self.create_widgets()
        
        if account_id:
            self.load_transaction_data()
    
    def create_scrollable_content(self):
        """إنشاء محتوى قابل للتمرير"""
        # إنشاء إطار رئيسي للتمرير
        self.scroll_frame = ttk.Frame(self)
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
        self.bind('<MouseWheel>', self.on_mousewheel)
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
    
    def setup_dialog(self):
        self.title("💳 معاملة جديدة" if not self.account_id else "✏️ تعديل المعاملة")
        self.geometry("650x550")
        self.resizable(False, False)
        
        self.transient(self.master)
        self.grab_set()
    
    def load_data(self):
        self.projects = self.db.execute_query("SELECT id, name FROM projects")
        self.customers = self.db.execute_query("SELECT id, name FROM customers")
    
    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(main_frame, text="بيانات المعاملة", font=('Segoe UI', 18, 'bold')).pack(pady=20)
        
        field_frame = ttk.Frame(main_frame)
        field_frame.pack(fill='x', pady=8)
        
        # نوع المعاملة - حجم مناسب
        ttk.Label(field_frame, text="نوع المعاملة:", font=('Segoe UI', 12, 'bold')).grid(row=0, column=0, padx=8, pady=10, sticky='e')
        self.type_combo = ttk.Combobox(field_frame, values=['وارد', 'منصرف'], state='readonly', width=28, font=('Segoe UI', 12))
        self.type_combo.current(0)
        self.type_combo.grid(row=0, column=1, padx=8, pady=10, sticky='w', ipady=6)
        self.type_combo.bind('<<ComboboxSelected>>', self.update_category_options)
        
        # المبلغ
        ttk.Label(field_frame, text="المبلغ:", font=('Segoe UI', 12, 'bold')).grid(row=1, column=0, padx=8, pady=10, sticky='e')
        self.amount_entry = ttk.Entry(field_frame, width=30, font=('Segoe UI', 12))
        self.amount_entry.grid(row=1, column=1, padx=8, pady=10, sticky='w', ipady=6)
        
        # الوصف
        ttk.Label(field_frame, text="الوصف:", font=('Segoe UI', 12, 'bold')).grid(row=2, column=0, padx=8, pady=10, sticky='e')
        self.desc_entry = ttk.Entry(field_frame, width=30, font=('Segoe UI', 12))
        self.desc_entry.grid(row=2, column=1, padx=8, pady=10, sticky='w', ipady=6)
        
        # التاريخ
        ttk.Label(field_frame, text="التاريخ:", font=('Segoe UI', 12, 'bold')).grid(row=3, column=0, padx=8, pady=10, sticky='e')
        if HAS_TKCALENDAR:
            self.date_entry = DateEntry(field_frame, width=28, font=('Segoe UI', 12), background='darkblue',
                                       foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
            self.date_entry.set_date(datetime.now())
        else:
            self.date_entry = ttk.Entry(field_frame, width=30, font=('Segoe UI', 12))
            self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.date_entry.grid(row=3, column=1, padx=8, pady=10, sticky='w', ipady=6)
        
        # الفئة
        ttk.Label(field_frame, text="الفئة:", font=('Segoe UI', 12, 'bold')).grid(row=4, column=0, padx=8, pady=10, sticky='e')
        self.category_combo = ttk.Combobox(field_frame, width=28, font=('Segoe UI', 12))
        self.category_combo.grid(row=4, column=1, padx=8, pady=10, sticky='w', ipady=6)
        
        # المشروع
        ttk.Label(field_frame, text="المشروع:", font=('Segoe UI', 12, 'bold')).grid(row=5, column=0, padx=8, pady=10, sticky='e')
        self.project_combo = ttk.Combobox(field_frame, state='readonly', width=28, font=('Segoe UI', 12))
        self.project_combo['values'] = ["عام"] + [f"{p[0]} - {p[1]}" for p in self.projects]
        self.project_combo.current(0)
        self.project_combo.grid(row=5, column=1, padx=8, pady=10, sticky='w', ipady=6)
        
        # تحديث خيارات الفئة
        self.update_category_options()
        
        # أزرار الحفظ - حجم مناسب
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill='x', pady=20)
        
        save_btn = ttk.Button(btn_frame, text="💾 حفظ", command=self.save_transaction, 
                  style='Modern.TButton')
        save_btn.pack(side='right', padx=8, ipadx=15, ipady=8)
        cancel_btn = ttk.Button(btn_frame, text="❌ إلغاء", command=self.destroy)
        cancel_btn.pack(side='left', padx=8, ipadx=15, ipady=8)
    
    def update_category_options(self, event=None):
        if self.type_combo.get() == 'وارد' or self.type_combo.get() == 'income':
            self.category_combo['values'] = ['مبيعات', 'خدمات', 'إيرادات أخرى']
        else:
            self.category_combo['values'] = ['رواتب', 'إيجار', 'مرافق', 'مستلزمات', 'مصروفات أخرى']
        self.category_combo.current(0)
    
    def load_transaction_data(self):
        if not self.transaction_id:
            return
        
        transaction = self.db.execute_query("SELECT * FROM transactions WHERE id = ?", (self.transaction_id,))
        if transaction:
            transaction = transaction[0]
            type_text = 'وارد' if transaction[1] == 'income' else 'منصرف'
            self.type_combo.set(type_text)
            self.amount_entry.insert(0, str(transaction[2]))
            self.desc_entry.insert(0, transaction[3])
            
            if HAS_TKCALENDAR:
                try:
                    dt = datetime.strptime(transaction[4], '%Y-%m-%d')
                    self.date_entry.set_date(dt)
                except:
                    pass
            else:
                self.date_entry.delete(0, tk.END)
                self.date_entry.insert(0, transaction[4])
                
            self.category_combo.set(transaction[5])
            
            if transaction[6]:
                for i, proj in enumerate(self.projects):
                    if proj[0] == transaction[6]:
                        self.project_combo.current(i + 1)
                        break
            
            self.update_category_options()
    
    def save_transaction(self):
        try:
            trans_type_text = self.type_combo.get()
            trans_type = 'income' if trans_type_text == 'وارد' else 'expense'
            amount = float(self.amount_entry.get())
            description = self.desc_entry.get()
            trans_date = self.date_entry.get()
            category = self.category_combo.get()
            
            if not amount or not description:
                messagebox.showerror("خطأ", "❌ المبلغ والوصف مطلوبان")
                return
            
            project_id = None
            if self.project_combo.current() > 0:
                project_text = self.project_combo.get()
                if " - " in project_text:
                    first_part = project_text.split(' - ')[0].strip()
                    if first_part.isdigit():
                        project_id = int(first_part)
            
            if self.transaction_id:
                self.db.execute_query(
                    "UPDATE transactions SET type=?, amount=?, description=?, date=?, category=?, project_id=? WHERE id=?",
                    (trans_type, amount, description, trans_date, category, project_id, self.transaction_id)
                )
                self.status_callback(f"✅ تم تحديث المعاملة: {description}")
            else:
                self.db.execute_query(
                    "INSERT INTO transactions (type, amount, description, date, category, project_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (trans_type, amount, description, trans_date, category, project_id)
                )
                self.status_callback(f"✅ تم إضافة المعاملة: {description}")
            
            self.refresh_callback()
            self.destroy()
            
            # Send refresh signals
            emit_transaction_change(self.transaction_id)
            if project_id:
                emit_project_change(project_id)
            
        except ValueError:
            messagebox.showerror("خطأ", "❌ المبلغ يجب أن يكون رقمًا")
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حفظ المعاملة: {str(e)}")

class TransactionsModule:
    def __init__(self, notebook, status_callback):
        self.db = Database()
        self.status_callback = status_callback
        self.frame = ttk.Frame(notebook)
        
        # إنشاء ScrollArea للتبويب
        self.create_scrollable_content()
        
        self.create_widgets()
        self.load_transactions()
    
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
        main_frame = self.content_frame
        
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill='x', pady=(0, 15))
        
        ttk.Label(title_frame, text="💳 المعاملات المالية", 
                 font=('Segoe UI', 14, 'bold')).pack(pady=5)
        
        # زر الإجراءات الرئيسية - في إطار منفصل
        main_actions = ttk.LabelFrame(main_frame, text="الإجراءات الرئيسية")
        main_actions.pack(fill='x', pady=(0, 10))
        
        actions_frame = ttk.Frame(main_actions)
        actions_frame.pack(fill='x', padx=10, pady=10)
        
        # زر معاملة جديدة - أكبر وأوضح
        btn1 = ttk.Button(actions_frame, text="➕ معاملة جديدة", command=self.add_transaction,
                  width=20)
        btn1.pack(side='left', padx=3, ipady=8, ipadx=5)
        
        # زر التقارير
        btn2 = ttk.Button(actions_frame, text="📊 تقارير مالية", command=self.show_financial_reports,
                  width=20)
        btn2.pack(side='left', padx=3, ipady=8, ipadx=5)
        
        # زر التصدير
        btn3 = ttk.Button(actions_frame, text="📤 تصدير البيانات", command=self.export_data,
                  width=20)
        btn3.pack(side='left', padx=3, ipady=8, ipadx=5)
        
        # فلاتر البحث - تحسين العرض
        filter_frame = ttk.LabelFrame(main_frame, text="فلاتر البحث")
        filter_frame.pack(fill='x', pady=(0, 10))
        
        filter_content = ttk.Frame(filter_frame)
        filter_content.pack(fill='x', padx=10, pady=8)
        
        # الصف الأول من الفلاتر
        filter_row1 = ttk.Frame(filter_content)
        filter_row1.pack(fill='x', pady=(0, 5))
        
        # نوع المعاملة
        ttk.Label(filter_row1, text="النوع:", font=('Segoe UI', 9)).pack(side='right', padx=5)
        self.filter_type = ttk.Combobox(filter_row1, values=['الكل', 'وارد', 'منصرف'], state='readonly', width=12, font=('Segoe UI', 9))
        self.filter_type.current(0)
        self.filter_type.pack(side='right', padx=5, ipady=2)
        
        # من تاريخ
        ttk.Label(filter_row1, text="من:", font=('Segoe UI', 9)).pack(side='right', padx=5)
        if HAS_TKCALENDAR:
            self.filter_from_date = DateEntry(filter_row1, width=10, font=('Segoe UI', 9), background='darkblue',
                                             foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
            self.filter_from_date.delete(0, 'end') # Start empty
        else:
            self.filter_from_date = ttk.Entry(filter_row1, width=12, font=('Segoe UI', 9))
        self.filter_from_date.pack(side='right', padx=5, ipady=2)
        
        # إلى تاريخ
        ttk.Label(filter_row1, text="إلى:", font=('Segoe UI', 9)).pack(side='right', padx=5)
        if HAS_TKCALENDAR:
            self.filter_to_date = DateEntry(filter_row1, width=10, font=('Segoe UI', 9), background='darkblue',
                                           foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
            self.filter_to_date.delete(0, 'end') # Start empty
        else:
            self.filter_to_date = ttk.Entry(filter_row1, width=12, font=('Segoe UI', 9))
        self.filter_to_date.pack(side='right', padx=5, ipady=2)
        
        # الصف الثاني من الفلاتر
        filter_row2 = ttk.Frame(filter_content)
        filter_row2.pack(fill='x')
        
        # بحث نصي
        ttk.Label(filter_row2, text="بحث:", font=('Segoe UI', 9)).pack(side='right', padx=5)
        self.search_entry = ttk.Entry(filter_row2, width=25, font=('Segoe UI', 9))
        self.search_entry.pack(side='right', padx=5, ipady=2)
        
        # أزرار الفلترة - أكبر وأوضح
        filter_buttons = ttk.Frame(filter_row2)
        filter_buttons.pack(side='right', padx=10)
        
        ttk.Button(filter_buttons, text="🔍 بحث", command=self.apply_filters).pack(side='left', padx=2, ipady=4, ipadx=3)
        ttk.Button(filter_buttons, text="🔄 عرض الكل", command=self.load_transactions).pack(side='left', padx=2, ipady=4, ipadx=3)
        
        tree_frame = ttk.LabelFrame(main_frame, text="سجل المعاملات")
        tree_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        self.tree = ttk.Treeview(tree_frame, columns=('id', 'type', 'amount', 'desc', 'date', 'category', 'project'), show='headings', height=15)
        
        columns = [
            ('id', 'ID', 50),
            ('type', 'النوع', 80),
            ('amount', 'المبلغ', 100),
            ('desc', 'الوصف', 200),
            ('date', 'التاريخ', 100),
            ('category', 'الفئة', 120),
            ('project', 'المشروع', 150)
        ]
        
        for col, heading, width in columns:
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width)
        
        self.tree.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        control_frame = ttk.LabelFrame(main_frame, text="إجراءات التحكم")
        control_frame.pack(fill='x', pady=(0, 5))
        
        control_buttons_frame = ttk.Frame(control_frame)
        control_buttons_frame.pack(fill='x', padx=10, pady=8)
        
        control_buttons = [
            ("👁️ عرض", self.view_transaction),
            ("✏️ تعديل", self.edit_transaction),
            ("🗑️ حذف", self.delete_transaction),
            ("📋 نسخ", self.duplicate_transaction)
        ]
        
        for text, command in control_buttons:
            btn = ttk.Button(control_buttons_frame, text=text, command=command, width=15)
            btn.pack(side='left', padx=3, ipady=8, ipadx=3)
        
        self.tree.bind('<Double-1>', lambda e: self.view_transaction())
    
    def add_transaction(self):
        AccountsReceivableDialog(self.frame, self.db, self.status_callback, self.load_transactions)
    
    def edit_transaction(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار معاملة لتعديلها")
            return
        
        transaction_id = self.tree.item(selected[0], 'values')[0]
        AccountsReceivableDialog(self.frame, self.db, self.status_callback, self.load_transactions, transaction_id)
    
    def view_transaction(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار معاملة لعرضها")
            return
        
        transaction_id = self.tree.item(selected[0], 'values')[0]
        transaction = self.db.execute_query("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
        
        if transaction:
            transaction = transaction[0]
            project_name = "عام"
            if transaction[6]:
                project = self.db.execute_query("SELECT name FROM projects WHERE id = ?", (transaction[6],))
                if project:
                    project_name = project[0][0]
            
            type_text = "وارد" if transaction[1] == 'income' else "منصرف"
            
            details = f"""
            📋 بيانات المعاملة:
            
            النوع: {type_text}
            المبلغ: {transaction[2]:.2f} ريال
            الوصف: {transaction[3]}
            التاريخ: {transaction[4]}
            الفئة: {transaction[5]}
            المشروع: {project_name}
            """
            
            messagebox.showinfo("تفاصيل المعاملة", details)
    
    def delete_transaction(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار معاملة لحذفها")
            return
        
        transaction_id = self.tree.item(selected[0], 'values')[0]
        transaction_desc = self.tree.item(selected[0], 'values')[3]
        
        if messagebox.askyesno("تأكيد", f"⚠️ هل أنت متأكد من حذف المعاملة '{transaction_desc}'؟"):
            try:
                self.db.execute_query("DELETE FROM transactions WHERE id = ?", (transaction_id,))
                self.status_callback(f"✅ تم حذف المعاملة: {transaction_desc}")
                self.load_transactions()
            except Exception as e:
                messagebox.showerror("خطأ", f"❌ فشل في حذف المعاملة: {str(e)}")
    
    def duplicate_transaction(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار معاملة لنسخها")
            return
        
        transaction_id = self.tree.item(selected[0], 'values')[0]
        transaction = self.db.execute_query("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
        
        if transaction:
            # نافذة معاملة جديدة معبأة ببيانات المعاملة الأصلية (نسخ وليس تعديل)
            dlg = AccountsReceivableDialog(self.frame, self.db, self.status_callback, self.load_transactions)
            dlg.transaction_id = transaction_id
            dlg.load_transaction_data()
            dlg.transaction_id = None
            dlg.title("📋 نسخ معاملة")
    
    def apply_filters(self):
        query = "SELECT t.id, t.type, t.amount, t.description, t.date, t.category, p.name FROM transactions t LEFT JOIN projects p ON t.project_id = p.id WHERE 1=1"
        params = []
        
        # فلترة النوع
        if self.filter_type.get() == 'وارد':
            query += " AND t.type = 'income'"
        elif self.filter_type.get() == 'منصرف':
            query += " AND t.type = 'expense'"
        
        # فلترة التاريخ
        from_date = self.filter_from_date.get().strip()
        if from_date:
            try:
                # محاولة توحيد الصيغة إذا أدخلها المستخدم بشكل مختلف
                if '/' in from_date:
                    from_date = datetime.strptime(from_date, '%d/%m/%Y').strftime('%Y-%m-%d')
            except ValueError:
                pass
            query += " AND t.date >= ?"
            params.append(from_date)
            
        to_date = self.filter_to_date.get().strip()
        if to_date:
            try:
                if '/' in to_date:
                    to_date = datetime.strptime(to_date, '%d/%m/%Y').strftime('%Y-%m-%d')
            except ValueError:
                pass
            query += " AND t.date <= ?"
            params.append(to_date)
        
        # بحث نصي
        if self.search_entry.get():
            query += " AND (t.description LIKE ? OR t.category LIKE ?)"
            search_pattern = f'%{self.search_entry.get()}%'
            params.extend([search_pattern, search_pattern])
        
        query += " ORDER BY t.date DESC"
        
        transactions = self.db.execute_query(query, params)
        self.display_transactions(transactions)
    
    def show_financial_reports(self):
        total_income = self.db.execute_query("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'income'")[0][0]
        total_expenses = self.db.execute_query("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'expense'")[0][0]
        net_profit = total_income - total_expenses
        
        # المعاملات لهذا الشهر
        current_month = datetime.now().strftime("%Y-%m")
        monthly_income = self.db.execute_query(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'income' AND strftime('%Y-%m', date) = ?",
            (current_month,)
        )[0][0]
        
        monthly_expenses = self.db.execute_query(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'expense' AND strftime('%Y-%m', date) = ?",
            (current_month,)
        )[0][0]
        
        messagebox.showinfo("التقارير المالية", 
                          f"📊 التقرير المالي الشامل:\n\n"
                          f"الإجمالي العام:\n"
                          f"• إجمالي الإيرادات: {total_income:.2f} ريال\n"
                          f"• إجمالي المصروفات: {total_expenses:.2f} ريال\n"
                          f"• صافي الربح: {net_profit:.2f} ريال\n\n"
                          f"لهذا الشهر ({current_month}):\n"
                          f"• الإيرادات: {monthly_income:.2f} ريال\n"
                          f"• المصروفات: {monthly_expenses:.2f} ريال\n"
                          f"• صافي الربح: {monthly_income - monthly_expenses:.2f} ريال")
    
    def export_data(self):
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
                title="حفظ كملف Excel"
            )
            
            if filename:
                transactions = self.db.execute_query('''
                    SELECT 
                        t.id,
                        CASE WHEN t.type = 'income' THEN 'وارد' ELSE 'منصرف' END as type,
                        t.amount,
                        t.description,
                        t.date,
                        t.category,
                        COALESCE(p.name, 'عام') as project
                    FROM transactions t 
                    LEFT JOIN projects p ON t.project_id = p.id
                    ORDER BY t.date DESC
                ''')
                
                df = pd.DataFrame(transactions, columns=[
                    'ID', 'النوع', 'المبلغ', 'الوصف', 'التاريخ', 'الفئة', 'المشروع'
                ])
                
                df.to_excel(filename, index=False, engine='openpyxl')
                
                self.status_callback(f"✅ تم تصدير البيانات إلى: {filename}")
                messagebox.showinfo("نجاح", f"✅ تم تصدير البيانات إلى: {filename}")
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تصدير البيانات: {str(e)}")
    
    def load_projects(self):
        query = "SELECT id, name FROM projects ORDER BY name"
        projects = self.db.execute_query(query)
        return projects
    
    def load_customers(self):
        """load customers for dropdown"""
        customers = self.db.execute_query("SELECT id, name FROM customers ORDER BY name")
        return customers
    
    def load_account_items(self):
        """load account items for dropdown"""
        items = self.db.execute_query("SELECT id, number, name FROM account_items ORDER BY number")
        return items
    
    def load_transactions(self):
        query = '''
        SELECT t.id, t.type, t.amount, t.description, t.date, t.category, p.name 
        FROM transactions t 
        LEFT JOIN projects p ON t.project_id = p.id
        ORDER BY t.date DESC
        '''
        transactions = self.db.execute_query(query)
        self.display_transactions(transactions)
    
    def display_transactions(self, transactions):
        self.tree.delete(*self.tree.get_children())
        for trans in transactions:
            trans_type = "وارد" if trans[1] == 'income' else "منصرف"
            self.tree.insert('', 'end', values=(
                trans[0], trans_type, f"{trans[2]:.2f}", 
                trans[3], trans[4], trans[5], 
                trans[6] if trans[6] else "عام"
            ))