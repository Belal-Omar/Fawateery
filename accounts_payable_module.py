import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from database import Database
import pandas as pd

class AccountsPayableDialog(tk.Toplevel):
    """نافذة إدارة حسابات الموردين (الدائنون)"""
    def __init__(self, parent, db, status_callback, refresh_callback, account_id=None):
        super().__init__(parent)
        self.parent = parent
        self.db = db
        self.status_callback = status_callback
        self.refresh_callback = refresh_callback
        self.account_id = account_id
        
        self.setup_dialog()
        self.load_data()
        self.create_widgets()
        
        if account_id:
            self.load_account_data()
    
    def load_data(self):
        self.projects = self.db.execute_query("SELECT id, name FROM projects")
    
    def setup_dialog(self):
        self.title("💰 إدارة حساب المورد" if not self.account_id else "✏️ تعديل حساب المورد")
        self.geometry("600x500")
        self.resizable(True, True)
        self.transient(self.parent)
        self.grab_set()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # العنوان
        title_label = ttk.Label(main_frame, text="💰 حساب المورد", font=('Segoe UI', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # معلومات الحساب
        info_frame = ttk.LabelFrame(main_frame, text="معلومات الحساب", padding="10")
        info_frame.pack(fill='x', pady=(0, 15))
        
        # اسم المورد
        ttk.Label(info_frame, text="اسم المورد:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.supplier_entry = ttk.Entry(info_frame, width=30, font=('Segoe UI', 10))
        self.supplier_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        # المبلغ الإجمالي
        ttk.Label(info_frame, text="المبلغ الإجمالي:", font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.amount_entry = ttk.Entry(info_frame, width=30, font=('Segoe UI', 10))
        self.amount_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        self.amount_entry.bind('<KeyRelease>', self.calculate_remaining)
        
        # المبلغ المدفوع
        ttk.Label(info_frame, text="المبلغ المدفوع:", font=('Segoe UI', 10, 'bold')).grid(row=2, column=0, padx=5, pady=5, sticky='e')
        self.paid_entry = ttk.Entry(info_frame, width=30, font=('Segoe UI', 10))
        self.paid_entry.insert(0, "0")
        self.paid_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        self.paid_entry.bind('<KeyRelease>', self.calculate_remaining)
        
        # المبلغ المتبقي
        ttk.Label(info_frame, text="المبلغ المتبقي:", font=('Segoe UI', 10, 'bold')).grid(row=3, column=0, padx=5, pady=5, sticky='e')
        self.remaining_label = ttk.Label(info_frame, text="0.00 ريال", font=('Segoe UI', 10, 'bold'))
        self.remaining_label.grid(row=3, column=1, padx=5, pady=5, sticky='w')
        
        # تاريخ الاستحقاق
        ttk.Label(info_frame, text="تاريخ الاستحقاق:", font=('Segoe UI', 10, 'bold')).grid(row=4, column=0, padx=5, pady=5, sticky='e')
        self.due_date_entry = ttk.Entry(info_frame, width=30, font=('Segoe UI', 10))
        self.due_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.due_date_entry.grid(row=4, column=1, padx=5, pady=5, sticky='w')
        
        # الحالة
        ttk.Label(info_frame, text="الحالة:", font=('Segoe UI', 10, 'bold')).grid(row=5, column=0, padx=5, pady=5, sticky='e')
        self.status_combo = ttk.Combobox(info_frame, values=['معلق', 'مدفوع جزئياً', 'مدفوع بالكامل', 'متأخر'], 
                                        state='readonly', width=28, font=('Segoe UI', 10))
        self.status_combo.set('معلق')
        self.status_combo.grid(row=5, column=1, padx=5, pady=5, sticky='w')
        
        # الفئة
        ttk.Label(info_frame, text="الفئة:", font=('Segoe UI', 10, 'bold')).grid(row=6, column=0, padx=5, pady=5, sticky='e')
        self.category_combo = ttk.Combobox(info_frame, values=['مواد خام', 'معدات', 'خدمات', 'إيجار', 'كهرباء', 'مياه', 'أخرى'], 
                                           state='readonly', width=28, font=('Segoe UI', 10))
        self.category_combo.set('مواد خام')
        self.category_combo.grid(row=6, column=1, padx=5, pady=5, sticky='w')
        
        # المشروع
        ttk.Label(info_frame, text="المشروع:", font=('Segoe UI', 10, 'bold')).grid(row=7, column=0, padx=5, pady=5, sticky='e')
        self.project_combo = ttk.Combobox(info_frame, state='readonly', width=28, font=('Segoe UI', 10))
        self.project_combo['values'] = [f"{p[0]} - {p[1]}" for p in self.projects]
        self.project_combo.grid(row=7, column=1, padx=5, pady=5, sticky='w')
        
        # ملاحظات
        notes_frame = ttk.LabelFrame(main_frame, text="ملاحظات", padding="10")
        notes_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        self.notes_text = tk.Text(notes_frame, height=6, font=('Segoe UI', 10))
        self.notes_text.pack(fill='both', expand=True)
        
        # أزرار الحفظ
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill='x')
        
        ttk.Button(buttons_frame, text="💾 حفظ", command=self.save_account).pack(side='right', padx=5)
        ttk.Button(buttons_frame, text="❌ إلغاء", command=self.destroy).pack(side='right', padx=5)
    
    def calculate_remaining(self, event=None):
        try:
            amount = float(self.amount_entry.get() or 0)
            paid = float(self.paid_entry.get() or 0)
            remaining = amount - paid
            self.remaining_label.config(text=f"{remaining:.2f} ريال")
            
            # تحديث الحالة تلقائياً
            if remaining <= 0:
                self.status_combo.set('مدفوع بالكامل')
            elif paid > 0:
                self.status_combo.set('مدفوع جزئياً')
            else:
                self.status_combo.set('معلق')
        except ValueError:
            self.remaining_label.config(text="0.00 ريال")
    
    def load_account_data(self):
        if not self.account_id:
            return
        
        account = self.db.execute_query("SELECT * FROM accounts_payable WHERE id = ?", (self.account_id,))
        if account:
            account = account[0]
            self.supplier_entry.insert(0, account[1] or '')
            self.amount_entry.insert(0, str(account[2] or 0))
            self.paid_entry.insert(0, str(account[3] or 0))
            self.due_date_entry.insert(0, account[5] or '')
            self.status_combo.set(account[6] or 'معلق')
            self.category_combo.set(account[10] or 'مواد خام')
            self.notes_text.insert('1.0', account[11] or '')
            self.calculate_remaining()
    
    def save_account(self):
        try:
            supplier_name = self.supplier_entry.get()
            amount = float(self.amount_entry.get() or 0)
            paid_amount = float(self.paid_entry.get() or 0)
            remaining_amount = amount - paid_amount
            due_date = self.due_date_entry.get()
            status = self.status_combo.get()
            category = self.category_combo.get()
            project_id = int(self.project_combo.get().split(' - ')[0]) if self.project_combo.get() else None
            notes = self.notes_text.get('1.0', tk.END).strip()
            
            if not supplier_name or amount <= 0:
                messagebox.showerror("خطأ", "❌ اسم المورد والمبلغ الإجمالي مطلوبان")
                return
            
            created_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if self.account_id:
                # تحديث حساب موجود
                self.db.execute_query(
                    """UPDATE accounts_payable 
                       SET supplier_name=?, amount=?, paid_amount=?, remaining_amount=?, 
                           due_date=?, status=?, last_payment_date=?, category=?, project_id=?, notes=?
                       WHERE id=?""",
                    (supplier_name, amount, paid_amount, remaining_amount, due_date, status,
                     datetime.now().strftime('%Y-%m-%d') if paid_amount > 0 else None,
                     category, project_id, notes, self.account_id)
                )
                self.status_callback(f"✅ تم تحديث حساب المورد: {supplier_name}")
            else:
                # إنشاء حساب جديد
                self.db.execute_query(
                    """INSERT INTO accounts_payable 
                       (supplier_name, amount, paid_amount, remaining_amount, due_date, 
                        status, created_date, last_payment_date, category, project_id, notes) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (supplier_name, amount, paid_amount, remaining_amount, due_date, status,
                     created_date, datetime.now().strftime('%Y-%m-%d') if paid_amount > 0 else None,
                     category, project_id, notes)
                )
                self.status_callback(f"✅ تم إنشاء حساب المورد: {supplier_name}")
            
            self.refresh_callback()
            self.destroy()
            
        except ValueError as e:
            messagebox.showerror("خطأ", f"❌ خطأ في البيانات: {str(e)}")
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حفظ حساب المورد: {str(e)}")

class PaymentDialog:
    """نافذة تسجيل دفعة"""
    def __init__(self, parent, db, status_callback, refresh_callback, account_id, account_type):
        self.parent = parent
        self.db = db
        self.status_callback = status_callback
        self.refresh_callback = refresh_callback
        self.account_id = account_id
        self.account_type = account_type
        
        self.setup_dialog()
        self.create_widgets()
    
    def setup_dialog(self):
        self.title("💳 تسجيل دفعة جديدة")
        self.geometry("400x300")
        self.resizable(False, False)
        self.transient(self.parent)
        self.grab_set()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # العنوان
        title_label = ttk.Label(main_frame, text="💳 تسجيل دفعة جديدة", font=('Segoe UI', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # معلومات الدفعة
        info_frame = ttk.LabelFrame(main_frame, text="معلومات الدفعة", padding="10")
        info_frame.pack(fill='x', pady=(0, 15))
        
        # المبلغ
        ttk.Label(info_frame, text="المبلغ:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.amount_entry = ttk.Entry(info_frame, width=20, font=('Segoe UI', 10))
        self.amount_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        
        # طريقة الدفع
        ttk.Label(info_frame, text="طريقة الدفع:", font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.method_combo = ttk.Combobox(info_frame, values=['نقدي', 'شيك', 'تحويل بنكي', 'بطاقة ائتمان'], 
                                        state='readonly', width=18, font=('Segoe UI', 10))
        self.method_combo.set('نقدي')
        self.method_combo.grid(row=1, column=1, padx=5, pady=5, sticky='w')
        
        # الرقم المرجعي
        ttk.Label(info_frame, text="الرقم المرجعي:", font=('Segoe UI', 10, 'bold')).grid(row=2, column=0, padx=5, pady=5, sticky='e')
        self.reference_entry = ttk.Entry(info_frame, width=20, font=('Segoe UI', 10))
        self.reference_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')
        
        # التاريخ
        ttk.Label(info_frame, text="التاريخ:", font=('Segoe UI', 10, 'bold')).grid(row=3, column=0, padx=5, pady=5, sticky='e')
        self.date_entry = ttk.Entry(info_frame, width=20, font=('Segoe UI', 10))
        self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.date_entry.grid(row=3, column=1, padx=5, pady=5, sticky='w')
        
        # ملاحظات
        notes_frame = ttk.LabelFrame(main_frame, text="ملاحظات", padding="10")
        notes_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        self.notes_text = tk.Text(notes_frame, height=4, font=('Segoe UI', 10))
        self.notes_text.pack(fill='both', expand=True)
        
        # أزرار الحفظ
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill='x')
        
        ttk.Button(buttons_frame, text="💾 تسجيل الدفعة", command=self.save_payment).pack(side='right', padx=5)
        ttk.Button(buttons_frame, text="❌ إلغاء", command=self.destroy).pack(side='right', padx=5)
    
    def save_payment(self):
        try:
            amount = float(self.amount_entry.get() or 0)
            if amount <= 0:
                messagebox.showerror("خطأ", "❌ المبلغ يجب أن يكون أكبر من صفر")
                return
            
            payment_method = self.method_combo.get()
            reference_number = self.reference_entry.get()
            payment_date = self.date_entry.get()
            notes = self.notes_text.get('1.0', tk.END).strip()
            
            # تسجيل الدفعة
            self.db.execute_query(
                """INSERT INTO payment_records 
                   (account_type, account_id, amount, payment_date, payment_method, 
                    reference_number, notes) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (self.account_type, self.account_id, amount, payment_date, payment_method,
                 reference_number, notes)
            )
            
            # تحديث الحساب
            if self.account_type == 'receivable':
                table = 'accounts_receivable'
            else:
                table = 'accounts_payable'
            
            # الحصول على المبلغ المدفوع الحالي
            current = self.db.execute_query(f"SELECT paid_amount, amount FROM {table} WHERE id = ?", (self.account_id,))
            if current:
                current_paid = current[0][0]
                total_amount = current[0][1]
                new_paid = current_paid + amount
                remaining = total_amount - new_paid
                
                # تحديث الحالة
                if remaining <= 0:
                    status = 'مدفوع بالكامل'
                elif new_paid > 0:
                    status = 'مدفوع جزئياً'
                else:
                    status = 'معلق'
                
                self.db.execute_query(
                    f"""UPDATE {table} 
                       SET paid_amount=?, remaining_amount=?, status=?, last_payment_date=?
                       WHERE id=?""",
                    (new_paid, remaining, status, payment_date, self.account_id)
                )
            
            self.status_callback(f"✅ تم تسجيل دفعة بقيمة {amount:.2f} ريال")
            self.refresh_callback()
            self.destroy()
            
        except ValueError as e:
            messagebox.showerror("خطأ", f"❌ خطأ في البيانات: {str(e)}")
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تسجيل الدفعة: {str(e)}")

class AccountsPayableModule:
    """وحدة إدارة حسابات الموردين (الدائنون)"""
    def __init__(self, parent, status_callback):
        self.parent = parent
        self.status_callback = status_callback
        self.db = Database()
        self.frame = ttk.Frame(parent)
        
        # إنشاء ScrollArea للتبويب
        self.create_scrollable_content()
        
        self.setup_ui()
        self.load_accounts()
    
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
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.content_frame, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # أزرار سريعة
        quick_actions = ttk.Frame(main_frame)
        quick_actions.pack(fill='x', pady=(0, 15))
        
        ttk.Button(quick_actions, text="➕ حساب جديد", command=self.add_account, width=15).pack(side='right', padx=5, ipady=6)
        ttk.Button(quick_actions, text="📊 إحصائيات", command=self.show_stats, width=15).pack(side='right', padx=5, ipady=6)
        ttk.Button(quick_actions, text="📤 تصدير", command=self.export_data, width=15).pack(side='right', padx=5, ipady=6)
        
        # شريط البحث والفلترة
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="بحث:", font=('Segoe UI', 10)).pack(side='right', padx=5)
        self.search_entry = ttk.Entry(search_frame, width=25, font=('Segoe UI', 10))
        self.search_entry.pack(side='right', padx=5)
        self.search_entry.bind('<KeyRelease>', self.search_accounts)
        
        ttk.Label(search_frame, text="الحالة:", font=('Segoe UI', 10)).pack(side='right', padx=5)
        self.status_filter = ttk.Combobox(search_frame, values=['الكل', 'معلق', 'مدفوع جزئياً', 'مدفوع بالكامل', 'متأخر'], 
                                        state='readonly', width=15, font=('Segoe UI', 10))
        self.status_filter.set('الكل')
        self.status_filter.pack(side='right', padx=5)
        self.status_filter.bind('<<ComboboxSelected>>', self.filter_accounts)
        
        ttk.Button(search_frame, text="عرض الكل", command=self.load_accounts).pack(side='left', padx=5)
        
        # جدول الحسابات
        tree_frame = ttk.LabelFrame(main_frame, text="سجل حسابات الموردين")
        tree_frame.pack(fill='both', expand=True)
        
        columns = ('id', 'supplier', 'amount', 'paid', 'remaining', 'due_date', 'status', 'category', 'project')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        self.tree.heading('id', text='الرقم')
        self.tree.heading('supplier', text='اسم المورد')
        self.tree.heading('amount', text='المبلغ الإجمالي')
        self.tree.heading('paid', text='المدفوع')
        self.tree.heading('remaining', text='المتبقي')
        self.tree.heading('due_date', text='تاريخ الاستحقاق')
        self.tree.heading('status', text='الحالة')
        self.tree.heading('category', text='الفئة')
        self.tree.heading('project', text='المشروع')
        
        self.tree.column('id', width=50)
        self.tree.column('supplier', width=150)
        self.tree.column('amount', width=100)
        self.tree.column('paid', width=100)
        self.tree.column('remaining', width=100)
        self.tree.column('due_date', width=100)
        self.tree.column('status', width=100)
        self.tree.column('category', width=100)
        self.tree.column('project', width=120)
        
        self.tree.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # قائمة منسدلة
        self.tree.bind('<Button-3>', self.show_context_menu)
        
        # أزرار التحكم
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(control_frame, text="✏️ تعديل", command=self.edit_account).pack(side='right', padx=5)
        ttk.Button(control_frame, text="💳 دفعة", command=self.add_payment).pack(side='right', padx=5)
        ttk.Button(control_frame, text="🗑️ حذف", command=self.delete_account).pack(side='right', padx=5)
    
    def load_accounts(self):
        # مسح الجدول (بما فيها الصفوف المخفية بالفلتر)
        for item in list(getattr(self, '_ap_all_items', [])) + list(self.tree.get_children()):
            if self.tree.exists(item):
                self.tree.delete(item)
        self._ap_all_items = []
        
        # جلب البيانات مع ربط المشاريع
        accounts = self.db.execute_query(
            """SELECT ap.*, p.name as project_name
               FROM accounts_payable ap 
               LEFT JOIN projects p ON ap.project_id = p.id 
               ORDER BY ap.created_date DESC"""
        )
        
        for account in accounts:
            self.tree.insert('', 'end', values=(
                account[0],  # id
                account[1],  # supplier_name
                f"{account[2]:.2f}",  # amount
                f"{account[3]:.2f}",  # paid_amount
                f"{account[4]:.2f}",  # remaining_amount
                account[5],  # due_date
                account[6],  # status
                account[10], # category
                account[11] or 'غير محدد'  # project_name
            ))
    
    def _apply_row_filter(self, predicate):
        """إخفاء/إظهار الصفوف (Treeview لا يدعم الخيار hide) عبر detach/move مع حفظ الترتيب الأصلي"""
        all_items = [i for i in getattr(self, '_ap_all_items', []) if self.tree.exists(i)]
        known = set(all_items)
        for i in self.tree.get_children():
            if i not in known:
                all_items.append(i)
        self._ap_all_items = all_items
        pos = 0
        for item in all_items:
            values = self.tree.item(item, 'values')
            if predicate(values):
                self.tree.move(item, '', pos)
                pos += 1
            else:
                self.tree.detach(item)

    def _current_row_predicate(self):
        term = self.search_entry.get().lower().strip()
        try:
            status_filter = self.status_filter.get()
        except Exception:
            status_filter = 'الكل'

        def pred(values):
            if term and not any(term in str(v).lower() for v in values):
                return False
            if status_filter and status_filter != 'الكل':
                status = values[6] if len(values) > 6 else ''
                if status != status_filter:
                    return False
            return True
        return pred

    def search_accounts(self, event=None):
        self._apply_row_filter(self._current_row_predicate())

    def filter_accounts(self, event=None):
        self._apply_row_filter(self._current_row_predicate())

    def add_account(self):
        AccountsPayableDialog(self.parent, self.db, self.status_callback, self.load_accounts)
    
    def edit_account(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار حساب لتعديله")
            return
        
        account_id = self.tree.item(selected[0], 'values')[0]
        AccountsPayableDialog(self.parent, self.db, self.status_callback, self.load_accounts, account_id)
    
    def delete_account(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار حساب لحذفه")
            return
        
        if messagebox.askyesno("تأكيد", "⚠️ هل أنت متأكد من حذف هذا الحساب؟"):
            account_id = self.tree.item(selected[0], 'values')[0]
            self.db.execute_query("DELETE FROM accounts_payable WHERE id = ?", (account_id,))
            self.status_callback("✅ تم حذف الحساب")
            self.load_accounts()
    
    def add_payment(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار حساب لتسجيل دفعة عليه")
            return
        
        account_id = self.tree.item(selected[0], 'values')[0]
        PaymentDialog(self.parent, self.db, self.status_callback, self.load_accounts, account_id, 'payable')
    
    def load_data(self):
        self.projects = self.db.execute_query("SELECT id, name FROM projects")

    def show_stats(self):
        total_accounts = len(self.db.execute_query("SELECT id FROM accounts_payable"))
        total_amount = self.db.execute_query("SELECT SUM(amount) FROM accounts_payable")[0][0] or 0
        total_paid = self.db.execute_query("SELECT SUM(paid_amount) FROM accounts_payable")[0][0] or 0
        total_remaining = total_amount - total_paid
        
        messagebox.showinfo("إحصائيات الحسابات الدائنة", 
                          f"📊 إحصائيات حسابات الموردين:\n\n"
                          f"• إجمالي الحسابات: {total_accounts}\n"
                          f"• إجمالي المبالغ: {total_amount:,.2f} ريال\n"
                          f"• إجمالي المدفوع: {total_paid:,.2f} ريال\n"
                          f"• إجمالي المتبقي: {total_remaining:,.2f} ريال")
    
    def export_data(self):
        try:
            accounts = self.db.execute_query(
                """SELECT ap.supplier_name, ap.amount, ap.paid_amount, ap.remaining_amount, 
                          ap.due_date, ap.status, ap.category, p.name as project_name, ap.created_date 
                   FROM accounts_payable ap 
                   LEFT JOIN projects p ON ap.project_id = p.id 
                   ORDER BY ap.created_date DESC"""
            )
            
            df = pd.DataFrame(accounts, columns=[
                'اسم المورد', 'المبلغ الإجمالي', 'المدفوع', 'المتبقي',
                'تاريخ الاستحقاق', 'الحالة', 'الفئة', 'المشروع', 'تاريخ الإنشاء'
            ])
            
            filename = f"حسابات_الموردين_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df.to_excel(filename, index=False)
            
            self.status_callback(f"✅ تم تصدير البيانات إلى {filename}")
            messagebox.showinfo("نجاح", f"✅ تم تصدير البيانات بنجاح\n\nالملف: {filename}")
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تصدير البيانات: {str(e)}")
    
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            
            context_menu = tk.Menu(self.parent, tearoff=0)
            context_menu.add_command(label="✏️ تعديل", command=self.edit_account)
            context_menu.add_command(label="💳 تسجيل دفعة", command=self.add_payment)
            context_menu.add_separator()
            context_menu.add_command(label="🗑️ حذف", command=self.delete_account)
            
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
    
    def load_customers(self):
        """load customers for dropdown"""
        customers = self.db.execute_query("SELECT id, name FROM customers ORDER BY name")
        return customers
    
    def load_projects(self):
        """load projects for dropdown"""
        projects = self.db.execute_query("SELECT id, name FROM projects ORDER BY name")
        return projects
    
    def load_account_items(self):
        """load account items for dropdown"""
        items = self.db.execute_query("SELECT id, number, name FROM account_items ORDER BY number")
        return items
