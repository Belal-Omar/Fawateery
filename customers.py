import tkinter as tk
from tkinter import ttk, messagebox
from database import Database

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

class CustomerDialog(tk.Toplevel):
    def __init__(self, parent, db, status_callback, refresh_callback, customer_id=None):
        super().__init__(parent)
        self.db = db
        self.status_callback = status_callback
        self.refresh_callback = refresh_callback
        self.customer_id = customer_id
        
        # ألوان
        self.colors = {
            'bg': '#F5F6FA',
            'card': '#FFFFFF',
            'primary': '#3498DB',
            'success': '#27AE60',
            'text': '#2C3E50',
            'text_light': '#7F8C8D'
        }
        
        self.setup_dialog()
        self.create_widgets()
        
        if customer_id:
            self.load_customer_data()
    
    def setup_dialog(self):
        self.title("👥 إضافة عميل جديد" if not self.customer_id else "✏️ تعديل بيانات العميل")
        self.geometry("520x550")
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
        
        title_label = tk.Label(title_card, text="بيانات العميل",
                              font=('Segoe UI', 14, 'bold'),
                              bg=self.colors['card'], fg=self.colors['text'])
        title_label.pack(pady=15)
        
        # بطاقة الحقول
        fields_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        fields_card.pack(fill='both', expand=True, pady=(0, 10))
        
        fields_frame = tk.Frame(fields_card, bg=self.colors['card'])
        fields_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # الحقول
        fields = [
            ("اسم العميل:", "name", True),
            ("الرقم الضريبي:", "tax", False),
            ("العنوان:", "address", False),
            ("الهاتف:", "phone", False),
            ("البريد الإلكتروني:", "email", False)
        ]
        
        self.entries = {}
        for i, (label, field, required) in enumerate(fields):
            row_frame = tk.Frame(fields_frame, bg=self.colors['card'])
            row_frame.pack(fill='x', pady=10)
            
            label_text = label + (" *" if required else "")
            label_color = self.colors['text'] if required else self.colors['text_light']
            
            tk.Label(row_frame, text=label_text, font=('Segoe UI', 10, 'bold' if required else 'normal'),
                    bg=self.colors['card'], fg=label_color).pack(side='right', padx=(0, 10))
            
            entry = ttk.Entry(row_frame, width=35, font=('Segoe UI', 10), justify='right')
            entry.pack(side='right', fill='x', expand=True, ipady=5)
            # تفعيل الضغط على Enter لحفظ العميل
            entry.bind('<Return>', lambda e: self.save_customer())
            self.entries[field] = entry
        
        # أزرار الحفظ - واضحة ومنظمة بشكل أفضل
        btn_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        btn_card.pack(fill='x', pady=(0, 0))
        
        btn_frame = tk.Frame(btn_card, bg=self.colors['card'])
        btn_frame.pack(fill='x', padx=20, pady=15)
        
        save_text = "💾 حفظ" if self.customer_id else "➕ إضافة"
        save_btn = ModernButton(btn_frame, text=save_text, bg=self.colors['success'],
                              fg='white', command=self.save_customer)
        save_btn.pack(side='right', padx=10, ipadx=25, ipady=12)
        
        cancel_btn = ModernButton(btn_frame, text="❌ إلغاء", bg='#95A5A6',
                                  fg='white', command=self.destroy)
        cancel_btn.pack(side='right', padx=10, ipadx=25, ipady=12)
    
    def load_customer_data(self):
        if not self.customer_id:
            return
        
        customer = self.db.execute_query("SELECT * FROM customers WHERE id = ?", (self.customer_id,))
        if customer:
            customer = customer[0]
            self.entries['name'].insert(0, customer[1])
            self.entries['tax'].insert(0, customer[2] if customer[2] else "")
            self.entries['address'].insert(0, customer[3] if customer[3] else "")
            self.entries['phone'].insert(0, customer[4] if customer[4] else "")
            self.entries['email'].insert(0, customer[5] if customer[5] else "")
    
    def save_customer(self):
        try:
            name = self.entries['name'].get().strip()
            tax_number = self.entries['tax'].get().strip()
            address = self.entries['address'].get().strip()
            phone = self.entries['phone'].get().strip()
            email = self.entries['email'].get().strip()
            
            if not name:
                messagebox.showerror("خطأ", "❌ اسم العميل مطلوب")
                self.entries['name'].focus()
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
                self.db.execute_query(
                    "UPDATE customers SET name = ?, tax_number = ?, address = ?, phone = ?, email = ? WHERE id = ?",
                    (name, tax_number, address, phone, email, self.customer_id)
                )
                self.status_callback(f"✅ تم تحديث بيانات العميل: {name}")
            else:
                self.db.execute_query(
                    "INSERT INTO customers (name, tax_number, address, phone, email) VALUES (?, ?, ?, ?, ?)",
                    (name, tax_number, address, phone, email)
                )
                self.status_callback(f"✅ تم إضافة العميل: {name}")
            
            self.refresh_callback()
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حفظ بيانات العميل: {str(e)}")

class CustomersModule:
    def __init__(self, notebook, status_callback):
        self.db = Database()
        self.status_callback = status_callback
        self.frame = tk.Frame(notebook, bg='#F5F6FA')
        
        # ألوان
        self.colors = {
            'bg': '#F5F6FA',
            'card': '#FFFFFF',
            'primary': '#3498DB',
            'success': '#27AE60',
            'danger': '#E74C3C',
            'warning': '#F39C12',
            'text': '#2C3E50',
            'text_light': '#7F8C8D'
        }
        
        # إنشاء ScrollArea للتبويب
        self.create_scrollable_content()
        
        self.create_widgets()
        self.load_customers()
    
    def create_scrollable_content(self):
        """إنشاء محتوى قابل للتمرير"""
        # إنشاء إطار رئيسي للتمرير
        self.scroll_frame = tk.Frame(self.frame, bg=self.colors['bg'])
        self.scroll_frame.pack(fill='both', expand=True)
        
        # إنشاء Canvas للتمرير
        self.canvas = tk.Canvas(self.scroll_frame, bg=self.colors['bg'])
        self.canvas.pack(side='left', fill='both', expand=True)
        
        # إنشاء شريط تمرير عمودي
        scrollbar = ttk.Scrollbar(self.scroll_frame, orient='vertical', command=self.canvas.yview)
        scrollbar.pack(side='right', fill='y')
        
        # ربط Canvas مع شريط التمرير
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # إنشاء إطار المحتوى الفعلي
        self.content_frame = tk.Frame(self.canvas, bg=self.colors['bg'])
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
        # إطار رئيسي
        main_frame = tk.Frame(self.content_frame, bg=self.colors['bg'])
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # بطاقة العنوان والأزرار
        header_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        header_card.pack(fill='x', pady=(0, 15))
        
        header_content = tk.Frame(header_card, bg=self.colors['card'])
        header_content.pack(fill='x', padx=20, pady=15)
        
        # العنوان
        title_label = tk.Label(header_content, text="👥 إدارة العملاء",
                              font=('Segoe UI', 16, 'bold'),
                              bg=self.colors['card'], fg=self.colors['text'])
        title_label.pack(side='right')
        
        # أزرار سريعة
        actions_frame = tk.Frame(header_content, bg=self.colors['card'])
        actions_frame.pack(side='left')
        
        btn1 = ModernButton(actions_frame, text="➕ عميل جديد",
                           bg=self.colors['success'], fg='white',
                           command=self.add_customer)
        btn1.pack(side='left', padx=5)
        
        btn2 = ModernButton(actions_frame, text="📊 تقارير",
                           bg=self.colors['primary'], fg='white',
                           command=self.show_reports)
        btn2.pack(side='left', padx=5)
        
        # بطاقة البحث
        search_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        search_card.pack(fill='x', pady=(0, 15))
        
        search_frame = tk.Frame(search_card, bg=self.colors['card'])
        search_frame.pack(fill='x', padx=15, pady=12)
        
        tk.Label(search_frame, text="🔍 بحث:", font=('Segoe UI', 10, 'bold'),
                bg=self.colors['card'], fg=self.colors['text']).pack(side='right', padx=(0, 10))
        
        self.search_entry = ttk.Entry(search_frame, width=40, font=('Segoe UI', 10))
        self.search_entry.pack(side='right', fill='x', expand=True, padx=5, ipady=5)
        self.search_entry.bind('<KeyRelease>', self.search_customers)
        
        btn_search = ModernButton(search_frame, text="بحث",
                                 bg=self.colors['primary'], fg='white',
                                 command=self.search_customers)
        btn_search.pack(side='right', padx=5)
        
        btn_clear = ModernButton(search_frame, text="عرض الكل",
                                bg='#95A5A6', fg='white',
                                command=self.load_customers)
        btn_clear.pack(side='right', padx=5)
        
        # بطاقة الجدول
        table_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        table_card.pack(fill='both', expand=True, pady=(0, 15))
        
        table_frame = tk.Frame(table_card, bg=self.colors['card'])
        table_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # جدول العملاء
        columns = ('id', 'name', 'tax_number', 'phone', 'email')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=18)
        
        self.tree.heading('id', text='ID')
        self.tree.heading('name', text='اسم العميل')
        self.tree.heading('tax_number', text='الرقم الضريبي')
        self.tree.heading('phone', text='الهاتف')
        self.tree.heading('email', text='البريد الإلكتروني')
        
        self.tree.column('id', width=50, anchor='center')
        self.tree.column('name', width=250)
        self.tree.column('tax_number', width=150)
        self.tree.column('phone', width=120)
        self.tree.column('email', width=200)
        
        self.tree.pack(side='left', fill='both', expand=True)
        
        # شريط التمرير
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # ربط حدث النقر المزدوج
        self.tree.bind('<Double-1>', lambda e: self.view_customer())
        
        # بطاقة الأزرار
        actions_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        actions_card.pack(fill='x')
        
        actions_frame = tk.Frame(actions_card, bg=self.colors['card'])
        actions_frame.pack(padx=15, pady=12)
        
        buttons = [
            ("👁️ عرض", self.view_customer, self.colors['primary']),
            ("✏️ تعديل", self.edit_customer, self.colors['warning']),
            ("🗑️ حذف", self.delete_customer, self.colors['danger']),
            ("📋 فواتير", self.show_customer_invoices, self.colors['success'])
        ]
        
        for text, command, color in buttons:
            btn = ModernButton(actions_frame, text=text, bg=color, fg='white',
                             command=command)
            btn.pack(side='right', padx=5)
    
    def add_customer(self):
        CustomerDialog(self.frame, self.db, self.status_callback, self.load_customers)
    
    def edit_customer(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عميل لتعديله")
            return
        
        customer_id = self.tree.item(selected[0], 'values')[0]
        CustomerDialog(self.frame, self.db, self.status_callback, self.load_customers, customer_id)
    
    def view_customer(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عميل لعرضه")
            return
        
        customer_id = self.tree.item(selected[0], 'values')[0]
        customer = self.db.execute_query("SELECT * FROM customers WHERE id = ?", (customer_id,))
        
        if customer:
            customer = customer[0]
            
            # نافذة عرض أكبر وأوضح
            view_window = tk.Toplevel(self.frame)
            view_window.title(f"👁️ عرض بيانات العميل - {customer[1]}")
            view_window.geometry("600x500")
            view_window.configure(bg=self.colors['bg'])
            view_window.transient(self.frame)
            view_window.grab_set()
            
            # إطار رئيسي
            main_frame = tk.Frame(view_window, bg=self.colors['bg'])
            main_frame.pack(fill='both', expand=True, padx=30, pady=30)
            
            # بطاقة العنوان
            title_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
            title_card.pack(fill='x', pady=(0, 20))
            
            title_label = tk.Label(title_card, text=f"👁️ بيانات العميل: {customer[1]}",
                                   font=('Segoe UI', 16, 'bold'),
                                   bg=self.colors['card'], fg=self.colors['text'])
            title_label.pack(pady=20)
            
            # بطاقة البيانات
            data_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
            data_card.pack(fill='both', expand=True, pady=(0, 20))
            
            data_frame = tk.Frame(data_card, bg=self.colors['card'])
            data_frame.pack(fill='both', expand=True, padx=25, pady=25)
            
            # البيانات
            fields = [
                ("الاسم:", customer[1]),
                ("الرقم الضريبي:", customer[2] or 'غير متوفر'),
                ("العنوان:", customer[3] or 'غير متوفر'),
                ("الهاتف:", customer[4] or 'غير متوفر'),
                ("البريد الإلكتروني:", customer[5] or 'غير متوفر')
            ]
            
            for label, value in fields:
                row_frame = tk.Frame(data_frame, bg=self.colors['card'])
                row_frame.pack(fill='x', pady=12)
                
                tk.Label(row_frame, text=label, font=('Segoe UI', 11, 'bold'),
                        bg=self.colors['card'], fg=self.colors['text_light']).pack(side='right', padx=(0, 15))
                
                tk.Label(row_frame, text=str(value), font=('Segoe UI', 12),
                        bg=self.colors['card'], fg=self.colors['text']).pack(side='right')
            
            # أزرار - واضحة ومنظمة بشكل أفضل
            btn_frame = tk.Frame(main_frame, bg=self.colors['bg'])
            btn_frame.pack(fill='x', pady=(20, 0))
            
            # إطار داخلي للأزرار
            buttons_inner = tk.Frame(btn_frame, bg=self.colors['bg'])
            buttons_inner.pack(expand=True)
            
            edit_btn = ModernButton(buttons_inner, text="✏️ تعديل",
                                   bg=self.colors['warning'], fg='white',
                                   command=lambda: [view_window.destroy(), self.edit_customer()])
            edit_btn.pack(side='right', padx=10, ipadx=25, ipady=12)
            
            close_btn = ModernButton(buttons_inner, text="❌ إغلاق",
                                    bg='#95A5A6', fg='white',
                                    command=view_window.destroy)
            close_btn.pack(side='right', padx=10, ipadx=25, ipady=12)
    
    def delete_customer(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عميل لحذفه")
            return
        
        customer_id = self.tree.item(selected[0], 'values')[0]
        customer_name = self.tree.item(selected[0], 'values')[1]
        
        # التحقق من وجود فواتير مرتبطة
        invoices = self.db.execute_query("SELECT COUNT(*) FROM invoices WHERE customer_id = ?", (customer_id,))
        if invoices and invoices[0][0] > 0:
            messagebox.showerror("خطأ", "❌ لا يمكن حذف العميل لأنه مرتبط بفواتير")
            return
        
        if messagebox.askyesno("تأكيد", f"⚠️ هل أنت متأكد من حذف العميل {customer_name}؟"):
            try:
                self.db.execute_query("DELETE FROM customers WHERE id = ?", (customer_id,))
                self.status_callback(f"✅ تم حذف العميل: {customer_name}")
                self.load_customers()
            except Exception as e:
                messagebox.showerror("خطأ", f"❌ فشل في حذف العميل: {str(e)}")
    
    def show_customer_invoices(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار عميل")
            return
        
        customer_id = self.tree.item(selected[0], 'values')[0]
        customer_name = self.tree.item(selected[0], 'values')[1]
        
        invoices = self.db.execute_query('''
            SELECT invoice_number, date, grand_total 
            FROM invoices 
            WHERE customer_id = ? 
            ORDER BY date DESC
        ''', (customer_id,))
        
        # نافذة عرض الفواتير - أكبر وأوضح
        invoices_window = tk.Toplevel(self.frame)
        invoices_window.title(f"📋 فواتير العميل - {customer_name}")
        invoices_window.geometry("700x600")
        invoices_window.configure(bg=self.colors['bg'])
        invoices_window.transient(self.frame)
        invoices_window.grab_set()
        
        # إطار رئيسي
        main_frame = tk.Frame(invoices_window, bg=self.colors['bg'])
        main_frame.pack(fill='both', expand=True, padx=25, pady=25)
        
        # بطاقة العنوان
        title_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        title_card.pack(fill='x', pady=(0, 20))
        
        title_label = tk.Label(title_card, text=f"📋 فواتير العميل: {customer_name}",
                              font=('Segoe UI', 16, 'bold'),
                              bg=self.colors['card'], fg=self.colors['text'])
        title_label.pack(pady=15)
        
        if invoices:
            # بطاقة الجدول
            table_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
            table_card.pack(fill='both', expand=True, pady=(0, 20))
            
            table_frame = tk.Frame(table_card, bg=self.colors['card'])
            table_frame.pack(fill='both', expand=True, padx=15, pady=15)
            
            # جدول الفواتير
            columns = ('invoice_number', 'date', 'grand_total')
            tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
            
            tree.heading('invoice_number', text='رقم الفاتورة')
            tree.heading('date', text='التاريخ')
            tree.heading('grand_total', text='المبلغ')
            
            tree.column('invoice_number', width=200)
            tree.column('date', width=150)
            tree.column('grand_total', width=150)
            
            total_amount = 0
            for inv in invoices:
                tree.insert('', 'end', values=(inv[0], inv[1], f"{inv[2]:.2f} ر.س"))
                total_amount += inv[2]
            
            tree.pack(side='left', fill='both', expand=True)
            
            scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
            scrollbar.pack(side='right', fill='y')
            tree.configure(yscrollcommand=scrollbar.set)
            
            # بطاقة الإجمالي
            total_card = tk.Frame(main_frame, bg=self.colors['success'], relief=tk.RAISED, bd=1)
            total_card.pack(fill='x', pady=(0, 20))
            
            total_frame = tk.Frame(total_card, bg=self.colors['success'])
            total_frame.pack(padx=20, pady=15)
            
            tk.Label(total_frame, text=f"💰 إجمالي المبالغ: {total_amount:,.2f} ريال",
                    font=('Segoe UI', 14, 'bold'),
                    bg=self.colors['success'], fg='white').pack()
            
            tk.Label(total_frame, text=f"📊 عدد الفواتير: {len(invoices)}",
                    font=('Segoe UI', 12),
                    bg=self.colors['success'], fg='white').pack(pady=(5, 0))
        else:
            # لا توجد فواتير
            no_data_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
            no_data_card.pack(fill='both', expand=True)
            
            no_data_frame = tk.Frame(no_data_card, bg=self.colors['card'])
            no_data_frame.pack(expand=True)
            
            tk.Label(no_data_frame, text="📭 لا توجد فواتير",
                    font=('Segoe UI', 16, 'bold'),
                    bg=self.colors['card'], fg=self.colors['text_light']).pack(pady=50)
        
        # زر الإغلاق
        btn_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        btn_frame.pack(fill='x')
        
        close_btn = ModernButton(btn_frame, text="❌ إغلاق",
                                bg='#95A5A6', fg='white',
                                command=invoices_window.destroy)
        close_btn.pack(side='right', padx=5)
    
    def show_reports(self):
        total_customers = len(self.db.execute_query("SELECT id FROM customers"))
        customers_with_tax = len(self.db.execute_query("SELECT id FROM customers WHERE tax_number IS NOT NULL AND tax_number != ''"))
        
        # نافذة التقارير - أكبر وأوضح
        reports_window = tk.Toplevel(self.frame)
        reports_window.title("📊 تقارير العملاء")
        reports_window.geometry("600x450")
        reports_window.configure(bg=self.colors['bg'])
        reports_window.transient(self.frame)
        reports_window.grab_set()
        
        # إطار رئيسي
        main_frame = tk.Frame(reports_window, bg=self.colors['bg'])
        main_frame.pack(fill='both', expand=True, padx=30, pady=30)
        
        # بطاقة العنوان
        title_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        title_card.pack(fill='x', pady=(0, 20))
        
        title_label = tk.Label(title_card, text="📊 تقارير وإحصائيات العملاء",
                              font=('Segoe UI', 16, 'bold'),
                              bg=self.colors['card'], fg=self.colors['text'])
        title_label.pack(pady=20)
        
        # بطاقة الإحصائيات
        stats_card = tk.Frame(main_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
        stats_card.pack(fill='both', expand=True, pady=(0, 20))
        
        stats_frame = tk.Frame(stats_card, bg=self.colors['card'])
        stats_frame.pack(fill='both', expand=True, padx=25, pady=25)
        
        stats = [
            ("إجمالي العملاء", total_customers, self.colors['primary']),
            ("عملاء برقم ضريبي", customers_with_tax, self.colors['success']),
            ("عملاء بدون رقم ضريبي", total_customers - customers_with_tax, self.colors['warning'])
        ]
        
        for label, value, color in stats:
            stat_row = tk.Frame(stats_frame, bg=self.colors['card'], relief=tk.RAISED, bd=1)
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
        btn_frame = tk.Frame(main_frame, bg=self.colors['bg'])
        btn_frame.pack(fill='x')
        
        close_btn = ModernButton(btn_frame, text="❌ إغلاق",
                                bg='#95A5A6', fg='white',
                                command=reports_window.destroy)
        close_btn.pack(side='right', padx=5)
    
    def search_customers(self, event=None):
        search_term = self.search_entry.get().strip()
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
        self.tree.delete(*self.tree.get_children())
        for customer in customers:
            self.tree.insert('', 'end', values=customer)
