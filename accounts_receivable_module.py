import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
from database import Database
import pandas as pd

# استيراد ModernButton من main
class ModernButton(tk.Button):
    """زر عصري محسن مع تأثيرات بصرية"""
    def __init__(self, master=None, **kwargs):
        # إزالة style من kwargs إذا كان موجوداً
        kwargs.pop('style', None)
        super().__init__(master, **kwargs)
        self.configure(
            relief=tk.FLAT,
            cursor='hand2',
            font=('Segoe UI', 11, 'bold'),
            padx=20,
            pady=10
        )

class AccountsReceivableDialog(tk.Toplevel):
    """نافذة إدارة الحسابات المدينة (العملاء)"""
    def __init__(self, parent, db, status_callback, refresh_callback, account_id=None):
        super().__init__(parent)
        self.db = db
        self.status_callback = status_callback
        self.refresh_callback = refresh_callback
        self.account_id = account_id
        
        self.setup_dialog()
        self.load_data()
        self.create_widgets()
        
        if account_id:
            self.load_account_data()
    
    def setup_dialog(self):
        self.title("📋 حساب مدين جديد" if not self.account_id else "✏️ تعديل حساب مدين")
        self.geometry("900x750")
        self.resizable(True, True)
        self.transient(self.master)
        self.grab_set()
        
        # توسيط النافذة على الشاشة
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def load_data(self):
        self.customers = self.db.execute_query("SELECT id, name FROM customers")
        self.invoices = self.db.execute_query("SELECT id, invoice_number FROM invoices")
        self.projects = self.db.execute_query("SELECT id, name FROM projects")
    
    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(main_frame, text="بيانات الحساب المدين", font=('Segoe UI', 14, 'bold')).pack(pady=15)
        
        field_frame = ttk.Frame(main_frame)
        field_frame.pack(fill='x', pady=8)
        
        # العميل
        ttk.Label(field_frame, text="العميل:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, padx=8, pady=8, sticky='e')
        self.customer_combo = ttk.Combobox(field_frame, state='readonly', width=30, font=('Segoe UI', 10))
        self.customer_combo['values'] = [f"{c[0]} - {c[1]}" for c in self.customers]
        self.customer_combo.grid(row=0, column=1, padx=8, pady=8, sticky='w', ipady=4)
        
        # الفاتورة
        ttk.Label(field_frame, text="الفاتورة:", font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, padx=8, pady=8, sticky='e')
        self.invoice_combo = ttk.Combobox(field_frame, state='readonly', width=30, font=('Segoe UI', 10))
        self.invoice_combo['values'] = [f"{i[0]} - {i[1]}" for i in self.invoices]
        self.invoice_combo.grid(row=1, column=1, padx=8, pady=8, sticky='w', ipady=4)
        
        # المشروع
        ttk.Label(field_frame, text="المشروع:", font=('Segoe UI', 10, 'bold')).grid(row=2, column=0, padx=8, pady=8, sticky='e')
        self.project_combo = ttk.Combobox(field_frame, state='readonly', width=30, font=('Segoe UI', 10))
        self.project_combo['values'] = [f"{p[0]} - {p[1]}" for p in self.projects]
        self.project_combo.grid(row=2, column=1, padx=8, pady=8, sticky='w', ipady=4)
        
        # المبلغ الإجمالي
        ttk.Label(field_frame, text="المبلغ الإجمالي:", font=('Segoe UI', 10, 'bold')).grid(row=3, column=0, padx=8, pady=8, sticky='e')
        self.amount_entry = ttk.Entry(field_frame, width=32, font=('Segoe UI', 10))
        self.amount_entry.grid(row=3, column=1, padx=8, pady=8, sticky='w', ipady=4)
        
        # المبلغ المدفوع
        ttk.Label(field_frame, text="المبلغ المدفوع:", font=('Segoe UI', 10, 'bold')).grid(row=4, column=0, padx=8, pady=8, sticky='e')
        self.paid_entry = ttk.Entry(field_frame, width=32, font=('Segoe UI', 10))
        self.paid_entry.insert(0, "0")
        self.paid_entry.grid(row=4, column=1, padx=8, pady=8, sticky='w', ipady=4)
        self.paid_entry.bind('<KeyRelease>', self.calculate_remaining)
        
        # المبلغ المتبقي
        ttk.Label(field_frame, text="المبلغ المتبقي:", font=('Segoe UI', 10, 'bold')).grid(row=5, column=0, padx=8, pady=8, sticky='e')
        self.remaining_label = ttk.Label(field_frame, text="0.00", font=('Segoe UI', 10, 'bold'))
        self.remaining_label.grid(row=5, column=1, padx=8, pady=8, sticky='w')
        
        # تاريخ الاستحقاق
        ttk.Label(field_frame, text="تاريخ الاستحقاق:", font=('Segoe UI', 10, 'bold')).grid(row=6, column=0, padx=8, pady=8, sticky='e')
        self.due_date_entry = ttk.Entry(field_frame, width=32, font=('Segoe UI', 10))
        due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        self.due_date_entry.insert(0, due_date)
        self.due_date_entry.grid(row=6, column=1, padx=8, pady=8, sticky='w', ipady=4)
        
        # الحالة
        ttk.Label(field_frame, text="الحالة:", font=('Segoe UI', 10, 'bold')).grid(row=7, column=0, padx=8, pady=8, sticky='e')
        self.status_combo = ttk.Combobox(field_frame, values=['معلق', 'مدفوع جزئياً', 'مدفوع بالكامل', 'متأخر'], state='readonly', width=28, font=('Segoe UI', 10))
        self.status_combo.current(0)
        self.status_combo.grid(row=7, column=1, padx=8, pady=8, sticky='w', ipady=4)
        
        # ملاحظات
        ttk.Label(field_frame, text="ملاحظات:", font=('Segoe UI', 10, 'bold')).grid(row=8, column=0, padx=8, pady=8, sticky='e')
        self.notes_text = tk.Text(field_frame, width=30, height=3, font=('Segoe UI', 10))
        self.notes_text.grid(row=8, column=1, padx=8, pady=8, sticky='w')
        
        # أزرار الحفظ
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side='bottom', fill='x', pady=(10, 0))
        
        save_btn = ttk.Button(btn_frame, text="💾 حفظ", command=self.save_account, width=20)
        save_btn.pack(side='right', padx=10, pady=10, ipady=15)
        cancel_btn = ttk.Button(btn_frame, text="❌ إلغاء", command=self.destroy, width=20)
        cancel_btn.pack(side='left', padx=10, pady=10, ipady=15)
    
    def calculate_remaining(self, event=None):
        try:
            amount = float(self.amount_entry.get() or 0)
            paid = float(self.paid_entry.get() or 0)
            remaining = amount - paid
            self.remaining_label.config(text=f"{remaining:.2f}")
            
            # تحديث الحالة تلقائياً
            if remaining <= 0:
                self.status_combo.set('مدفوع بالكامل')
            elif paid > 0:
                self.status_combo.set('مدفوع جزئياً')
            else:
                self.status_combo.set('معلق')
        except ValueError:
            self.remaining_label.config(text="0.00")
    
    def load_account_data(self):
        if not self.account_id:
            return
        
        account = self.db.execute_query("SELECT * FROM accounts_receivable WHERE id = ?", (self.account_id,))
        if account:
            account = account[0]
            
            # تحديد العميل
            for i, cust in enumerate(self.customers):
                if cust[0] == account[1]:
                    self.customer_combo.current(i)
                    break
            
            # تحديد المشروع
            for i, proj in enumerate(self.projects):
                if proj[0] == account[3]:
                    self.project_combo.current(i)
                    break
            
            # تحديد الفاتورة
            for i, inv in enumerate(self.invoices):
                if inv[0] == account[2]:
                    self.invoice_combo.current(i)
                    break
            
            self.amount_entry.insert(0, str(account[4]))
            self.paid_entry.insert(0, str(account[5]))
            self.calculate_remaining()
            self.due_date_entry.delete(0, tk.END)
            self.due_date_entry.insert(0, account[7])
            self.status_combo.set(account[8])
            self.notes_text.insert('1.0', account[11] or "")
    
    def save_account(self):
        try:
            customer_id = int(self.customer_combo.get().split(' - ')[0])
            invoice_id = int(self.invoice_combo.get().split(' - ')[0]) if self.invoice_combo.get() else None
            project_id = int(self.project_combo.get().split(' - ')[0]) if self.project_combo.get() else None
            amount = float(self.amount_entry.get())
            paid_amount = float(self.paid_entry.get())
            remaining_amount = amount - paid_amount
            due_date = self.due_date_entry.get()
            status = self.status_combo.get()
            notes = self.notes_text.get('1.0', tk.END).strip()
            created_date = datetime.now().strftime('%Y-%m-%d')
            
            if self.account_id:
                self.db.execute_query(
                    """UPDATE accounts_receivable 
                       SET customer_id=?, invoice_id=?, project_id=?, amount=?, paid_amount=?, 
                           remaining_amount=?, due_date=?, status=?, notes=? 
                       WHERE id=?""",
                    (customer_id, invoice_id, project_id, amount, paid_amount, remaining_amount, 
                     due_date, status, notes, self.account_id)
                )
                self.status_callback(f"✅ تم تحديث الحساب المدين")
            else:
                self.db.execute_query(
                    """INSERT INTO accounts_receivable 
                       (customer_id, invoice_id, project_id, amount, paid_amount, remaining_amount, 
                        due_date, status, created_date, notes) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (customer_id, invoice_id, project_id, amount, paid_amount, remaining_amount, 
                     due_date, status, created_date, notes)
                )
                self.status_callback(f"✅ تم إضافة حساب مدين جديد")
            
            self.refresh_callback()
            self.destroy()
            
        except ValueError as e:
            messagebox.showerror("خطأ", f"❌ خطأ في البيانات: {str(e)}")
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حفظ الحساب: {str(e)}")

class PaymentDialog(tk.Toplevel):
    """نافذة تسجيل الدفعات"""
    def __init__(self, parent, db, status_callback, refresh_callback, account_type, account_id, current_remaining):
        super().__init__(parent)
        self.db = db
        self.status_callback = status_callback
        self.refresh_callback = refresh_callback
        self.account_type = account_type
        self.account_id = account_id
        self.current_remaining = current_remaining
        
        self.setup_dialog()
        self.create_widgets()
    
    def setup_dialog(self):
        title = "💵 تسجيل دفعة - حساب مدين" if self.account_type == 'receivable' else "💵 تسجيل دفعة - حساب دائن"
        self.title(title)
        self.geometry("600x500")
        self.resizable(True, True)
        self.transient(self.master)
        self.grab_set()
        
        # توسيط النافذة على الشاشة
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(main_frame, text="تسجيل دفعة جديدة", font=('Segoe UI', 14, 'bold')).pack(pady=15)
        
        field_frame = ttk.Frame(main_frame)
        field_frame.pack(fill='x', pady=8)
        
        # المبلغ المتبقي الحالي
        ttk.Label(field_frame, text="المبلغ المتبقي:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, padx=8, pady=8, sticky='e')
        ttk.Label(field_frame, text=f"{self.current_remaining:.2f} ريال", font=('Segoe UI', 10, 'bold')).grid(row=0, column=1, padx=8, pady=8, sticky='w')
        
        # مبلغ الدفعة
        ttk.Label(field_frame, text="مبلغ الدفعة:", font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, padx=8, pady=8, sticky='e')
        self.payment_entry = ttk.Entry(field_frame, width=25, font=('Segoe UI', 10))
        self.payment_entry.grid(row=1, column=1, padx=8, pady=8, sticky='w', ipady=4)
        
        # طريقة الدفع
        ttk.Label(field_frame, text="طريقة الدفع:", font=('Segoe UI', 10, 'bold')).grid(row=2, column=0, padx=8, pady=8, sticky='e')
        self.method_combo = ttk.Combobox(field_frame, values=['نقدي', 'تحويل بنكي', 'شيك', 'أخرى'], state='readonly', width=23, font=('Segoe UI', 10))
        self.method_combo.current(0)
        self.method_combo.grid(row=2, column=1, padx=8, pady=8, sticky='w', ipady=4)
        
        # رقم المرجع
        ttk.Label(field_frame, text="رقم المرجع:", font=('Segoe UI', 10, 'bold')).grid(row=3, column=0, padx=8, pady=8, sticky='e')
        self.reference_entry = ttk.Entry(field_frame, width=25, font=('Segoe UI', 10))
        self.reference_entry.grid(row=3, column=1, padx=8, pady=8, sticky='w', ipady=4)
        
        # التاريخ
        ttk.Label(field_frame, text="التاريخ:", font=('Segoe UI', 10, 'bold')).grid(row=4, column=0, padx=8, pady=8, sticky='e')
        self.date_entry = ttk.Entry(field_frame, width=25, font=('Segoe UI', 10))
        self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.date_entry.grid(row=4, column=1, padx=8, pady=8, sticky='w', ipady=4)
        
        # ملاحظات
        ttk.Label(field_frame, text="ملاحظات:", font=('Segoe UI', 10, 'bold')).grid(row=5, column=0, padx=8, pady=8, sticky='e')
        self.notes_text = tk.Text(field_frame, width=25, height=3, font=('Segoe UI', 10))
        self.notes_text.grid(row=5, column=1, padx=8, pady=8, sticky='w')
        
        # أزرار الحفظ
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill='x', pady=25)
        
        save_btn = ttk.Button(btn_frame, text="💾 حفظ الدفعة", command=self.save_payment, width=20)
        save_btn.pack(side='right', padx=10, pady=10, ipady=15)
        cancel_btn = ttk.Button(btn_frame, text="❌ إلغاء", command=self.destroy, width=20)
        cancel_btn.pack(side='left', padx=10, pady=10, ipady=15)
    
    def save_payment(self):
        try:
            payment_amount = float(self.payment_entry.get())
            payment_method = self.method_combo.get()
            reference_number = self.reference_entry.get()
            payment_date = self.date_entry.get()
            notes = self.notes_text.get('1.0', tk.END).strip()
            
            if payment_amount <= 0:
                messagebox.showerror("خطأ", "❌ مبلغ الدفعة يجب أن يكون أكبر من صفر")
                return
            
            if payment_amount > self.current_remaining:
                messagebox.showerror("خطأ", f"❌ مبلغ الدفعة يتجاوز المبلغ المتبقي ({self.current_remaining:.2f})")
                return
            
            # تحديث الحساب
            if self.account_type == 'receivable':
                self.db.execute_query(
                    """UPDATE accounts_receivable 
                       SET paid_amount = paid_amount + ?, 
                           remaining_amount = remaining_amount - ?,
                           last_payment_date = ?,
                           status = CASE 
                               WHEN remaining_amount - ? = 0 THEN 'مدفوع بالكامل'
                               WHEN remaining_amount - ? > 0 THEN 'مدفوع جزئياً'
                               ELSE status 
                           END
                       WHERE id = ?""",
                    (payment_amount, payment_amount, payment_date, payment_amount, payment_amount, self.account_id)
                )
            else:
                self.db.execute_query(
                    """UPDATE accounts_payable 
                       SET paid_amount = paid_amount + ?, 
                           remaining_amount = remaining_amount - ?,
                           last_payment_date = ?,
                           status = CASE 
                               WHEN remaining_amount - ? = 0 THEN 'مدفوع بالكامل'
                               WHEN remaining_amount - ? > 0 THEN 'مدفوع جزئياً'
                               ELSE status 
                           END
                       WHERE id = ?""",
                    (payment_amount, payment_amount, payment_date, payment_amount, payment_amount, self.account_id)
                )
            
            # تسجيل الدفعة
            self.db.execute_query(
                """INSERT INTO payment_records 
                   (account_type, account_id, amount, payment_date, payment_method, reference_number, notes) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (self.account_type, self.account_id, payment_amount, payment_date, payment_method, reference_number, notes)
            )
            
            self.status_callback(f"✅ تم تسجيل دفعة بقيمة {payment_amount:.2f} ريال")
            self.refresh_callback()
            self.destroy()
            
        except ValueError:
            messagebox.showerror("خطأ", "❌ المبلغ يجب أن يكون رقمًا")
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تسجيل الدفعة: {str(e)}")

class AccountsReceivableModule:
    """وحدة إدارة الحسابات المدينة"""
    def __init__(self, notebook, status_callback):
        self.db = Database()
        self.status_callback = status_callback
        self.frame = ttk.Frame(notebook)
        
        # إنشاء ScrollArea للتبويب
        self.create_scrollable_content()
        
        self.create_widgets()
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
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.content_frame)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill='x', pady=(0, 20))
        
        ttk.Label(title_frame, text="📋 الحسابات المدينة (العملاء)", 
                 font=('Segoe UI', 16, 'bold')).pack(pady=10)
        
        quick_actions = ttk.Frame(main_frame)
        quick_actions.pack(fill='x', pady=(0, 15))
        
        btn1 = ttk.Button(quick_actions, text="➕ حساب مدين جديد", command=self.add_account, width=30)
        btn1.pack(side='right', padx=8, ipady=15)
        btn2 = ttk.Button(quick_actions, text="📊 تقرير الحسابات", command=self.show_report, width=30)
        btn2.pack(side='right', padx=8, ipady=15)
        
        # فلاتر البحث
        filter_frame = ttk.LabelFrame(main_frame, text="فلاتر البحث")
        filter_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(filter_frame, text="العميل:", font=('Segoe UI', 10)).grid(row=0, column=0, padx=5, pady=5)
        self.filter_customer = ttk.Entry(filter_frame, width=20, font=('Segoe UI', 10))
        self.filter_customer.grid(row=0, column=1, padx=5, pady=5, ipady=3)
        
        ttk.Label(filter_frame, text="الحالة:", font=('Segoe UI', 10)).grid(row=0, column=2, padx=5, pady=5)
        self.filter_status = ttk.Combobox(filter_frame, values=['الكل', 'معلق', 'مدفوع جزئياً', 'مدفوع بالكامل', 'متأخر'], state='readonly', width=15, font=('Segoe UI', 10))
        self.filter_status.current(0)
        self.filter_status.grid(row=0, column=3, padx=5, pady=5, ipady=3)
        
        ttk.Button(filter_frame, text="بحث", command=self.apply_filters).grid(row=0, column=4, padx=5, pady=5, ipady=4)
        ttk.Button(filter_frame, text="عرض الكل", command=self.load_accounts).grid(row=0, column=5, padx=5, pady=5, ipady=4)
        
        tree_frame = ttk.LabelFrame(main_frame, text="قائمة الحسابات المدينة")
        tree_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        self.tree = ttk.Treeview(tree_frame, columns=('id', 'customer', 'amount', 'paid', 'remaining', 'due_date', 'status', 'project'), show='headings', height=18)
        
        columns = [
            ('id', 'الرقم', 70),
            ('customer', 'العميل', 160),
            ('amount', 'الإجمالي', 110),
            ('paid', 'المدفوع', 110),
            ('remaining', 'المتبقي', 110),
            ('due_date', 'تاريخ الاستحقاق', 130),
            ('status', 'الحالة', 110),
            ('project', 'المشروع', 130)
        ]
        
        for col, heading, width in columns:
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width)
        
        self.tree.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill='x', pady=15)
        
        control_buttons = [
            ("💵 تسجيل دفعة", self.record_payment),
            ("✏️ تعديل", self.edit_account),
            ("🗑️ حذف", self.delete_account),
            ("👁️ تفاصيل", self.view_details)
        ]
        
        for text, command in control_buttons:
            btn = ttk.Button(control_frame, text=text, command=command, width=25)
            btn.pack(side='right', padx=8, ipady=15)
    
    def add_account(self):
        AccountsReceivableDialog(self.frame, self.db, self.status_callback, self.load_accounts)
    
    def edit_account(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار حساب لتعديله")
            return
        
        account_id = self.tree.item(selected[0], 'values')[0]
        AccountsReceivableDialog(self.frame, self.db, self.status_callback, self.load_accounts, account_id)
    
    def record_payment(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار حساب لتسجيل دفعة")
            return
        
        account_id = self.tree.item(selected[0], 'values')[0]
        remaining = float(self.tree.item(selected[0], 'values')[4].replace(',', ''))
        
        PaymentDialog(self.frame, self.db, self.status_callback, self.load_accounts, 'receivable', account_id, remaining)
    
    def delete_account(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار حساب لحذفه")
            return
        
        account_id = self.tree.item(selected[0], 'values')[0]
        customer_name = self.tree.item(selected[0], 'values')[1]
        
        if messagebox.askyesno("تأكيد", f"⚠️ هل أنت متأكد من حذف حساب العميل '{customer_name}'؟"):
            try:
                self.db.execute_query("DELETE FROM accounts_receivable WHERE id = ?", (account_id,))
                self.status_callback(f"✅ تم حذف حساب العميل: {customer_name}")
                self.load_accounts()
            except Exception as e:
                messagebox.showerror("خطأ", f"❌ فشل في حذف الحساب: {str(e)}")
    
    def view_details(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار حساب لعرض تفاصيله")
            return
        
        account_id = self.tree.item(selected[0], 'values')[0]
        account = self.db.execute_query("""
            SELECT ar.*, c.name as customer_name, i.invoice_number, p.name as project_name
            FROM accounts_receivable ar 
            LEFT JOIN customers c ON ar.customer_id = c.id 
            LEFT JOIN invoices i ON ar.invoice_id = i.id 
            LEFT JOIN projects p ON ar.project_id = p.id
            WHERE ar.id = ?
        """, (account_id,))
        
        if account:
            account = account[0]
            details = f"""
            📋 تفاصيل الحساب المدين:
            
            العميل: {account[11]}
            الفاتورة: {account[12] or 'غير محدد'}
            المشروع: {account[13] or 'غير محدد'}
            المبلغ الإجمالي: {account[4]:.2f} ريال
            المبلغ المدفوع: {account[5]:.2f} ريال
            المبلغ المتبقي: {account[6]:.2f} ريال
            تاريخ الاستحقاق: {account[7]}
            الحالة: {account[8]}
            تاريخ الإنشاء: {account[9]}
            آخر دفعة: {account[10] or 'لا يوجد'}
            ملاحظات: {account[12] or 'لا يوجد'}
            """
            
            messagebox.showinfo("تفاصيل الحساب", details)
    
    def apply_filters(self):
        query = """
            SELECT ar.id, c.name, ar.amount, ar.paid_amount, ar.remaining_amount, 
                   ar.due_date, ar.status, p.name as project_name
            FROM accounts_receivable ar 
            LEFT JOIN customers c ON ar.customer_id = c.id 
            LEFT JOIN projects p ON ar.project_id = p.id 
            WHERE 1=1
        """
        params = []
        
        # فلترة العميل
        if self.filter_customer.get():
            query += " AND c.name LIKE ?"
            params.append(f'%{self.filter_customer.get()}%')
        
        # فلترة الحالة
        if self.filter_status.get() != 'الكل':
            query += " AND ar.status = ?"
            params.append(self.filter_status.get())
        
        query += " ORDER BY ar.due_date ASC"
        
        accounts = self.db.execute_query(query, params)
        self.display_accounts(accounts)
    
    def show_report(self):
        total_receivable = self.db.execute_query("SELECT COALESCE(SUM(remaining_amount), 0) FROM accounts_receivable")[0][0]
        overdue_accounts = self.db.execute_query("""
            SELECT COUNT(*) FROM accounts_receivable 
            WHERE status = 'متأخر' AND remaining_amount > 0
        """)[0][0]
        
        paid_accounts = self.db.execute_query("""
            SELECT COUNT(*) FROM accounts_receivable 
            WHERE status = 'مدفوع بالكامل'
        """)[0][0]
        report_msg = (
            f"📊 تقرير الحسابات المدينة:\n\n"
            f"• إجمالي المبالغ المستحقة: {total_receivable:,.2f} ريال\n"
            f"• عدد الحسابات المتأخرة: {overdue_accounts}\n"
            f"• عدد الحسابات المسددة بالكامل: {paid_accounts}"
        )
        messagebox.showinfo("تقرير الحسابات", report_msg)
        self.load_accounts()
    
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
    
    def load_accounts(self):
        """load all accounts"""
        accounts = self.db.execute_query('''
            SELECT ar.id, c.name, ar.amount, ar.paid_amount, 
                   ar.remaining_amount,
                   ar.due_date, ar.status, p.name as project_name
            FROM accounts_receivable ar
            LEFT JOIN customers c ON ar.customer_id = c.id
            LEFT JOIN projects p ON ar.project_id = p.id
            ORDER BY ar.due_date DESC
        ''')
        self.display_accounts(accounts)
    
    def display_accounts(self, accounts):
        """display accounts in tree"""
        self.tree.delete(*self.tree.get_children())
        for account in accounts:
            status_arabic = {
                'mualq': 'mualq',
                'madfoj_juzian': 'madfoj_juzian',
                'madfoj_bilkamil': 'madfoj_bilkamil',
                'mutakhir': 'mutakhir'
            }.get(account[6], account[6])
            
            self.tree.insert('', 'end', values=(
                account[0], account[1], f"{account[2]:,.2f}", 
                f"{account[3]:,.2f}", f"{account[4]:,.2f}", 
                account[5], status_arabic, account[7] or 'not specified'
            ))
