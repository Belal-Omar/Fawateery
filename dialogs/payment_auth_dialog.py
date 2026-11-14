#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نموذج حوار إذن الصرف
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

class PaymentAuthorizationDialog:
    def __init__(self, parent, db, status_callback, refresh_callback, auth_id=None):
        self.parent = parent
        self.db = db
        self.status_callback = status_callback
        self.refresh_callback = refresh_callback
        self.auth_id = auth_id
        
        # إنشاء نافذة
        self.window = tk.Toplevel(parent)
        self.window.title("إذن صرف جديد" if not auth_id else f"تعديل إذن الصرف #{auth_id}")
        self.window.geometry("950x750")
        self.window.resizable(True, True)
        self.window.transient(parent)
        self.window.grab_set()
        
        # إنشاء ScrollArea للنافذة
        self.create_scrollable_content()
        
        # توسيط النافذة على الشاشة
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
        
        self.setup_ui()
        
        if auth_id:
            self.load_auth_data()
    
    def create_scrollable_content(self):
        """إنشاء محتوى قابل للتمرير"""
        # إنشاء إطار رئيسي للتمرير
        self.scroll_frame = ttk.Frame(self.window)
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
        """إعداد واجهة المستخدم"""
        main_frame = ttk.Frame(self.content_frame, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # معلومات الإذن
        info_frame = ttk.LabelFrame(main_frame, text="معلومات الإذن", padding="10")
        info_frame.pack(fill='x', pady=(0, 10))
        
        # رقم الإذن
        ttk.Label(info_frame, text="رقم الإذن:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.auth_number_var = tk.StringVar()
        ttk.Entry(info_frame, textvariable=self.auth_number_var, width=30).grid(row=0, column=1, padx=5, pady=5)
        
        # التاريخ
        ttk.Label(info_frame, text="التاريخ:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        ttk.Entry(info_frame, textvariable=self.date_var, width=30).grid(row=1, column=1, padx=5, pady=5)
        
        # العميل
        ttk.Label(info_frame, text="العميل:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.customer_var = tk.StringVar()
        self.customer_combo = ttk.Combobox(info_frame, textvariable=self.customer_var, width=28)
        self.customer_combo.grid(row=2, column=1, padx=5, pady=5)
        self.load_customers()
        
        # المشروع
        ttk.Label(info_frame, text="المشروع:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.project_var = tk.StringVar()
        self.project_combo = ttk.Combobox(info_frame, textvariable=self.project_var, width=28)
        self.project_combo.grid(row=3, column=1, padx=5, pady=5)
        self.load_projects()
        
        # معلومات الصرف
        payment_frame = ttk.LabelFrame(main_frame, text="معلومات الصرف", padding="10")
        payment_frame.pack(fill='x', pady=(0, 10))
        
        # المبلغ
        ttk.Label(payment_frame, text="المبلغ:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.amount_var = tk.StringVar()
        ttk.Entry(payment_frame, textvariable=self.amount_var, width=30).grid(row=0, column=1, padx=5, pady=5)
        
        # العملة
        ttk.Label(payment_frame, text="العملة:").grid(row=0, column=2, sticky='w', padx=5, pady=5)
        self.currency_var = tk.StringVar(value="ريال سعودي")
        ttk.Combobox(payment_frame, textvariable=self.currency_var, 
                   values=["ريال سعودي", "دولار أمريكي", "يورو"], width=10).grid(row=0, column=3, padx=5, pady=5)
        
        # البنك
        ttk.Label(payment_frame, text="البنك:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.bank_var = tk.StringVar()
        ttk.Entry(payment_frame, textvariable=self.bank_var, width=30).grid(row=1, column=1, padx=5, pady=5)
        
        # رقم الحساب
        ttk.Label(payment_frame, text="رقم الحساب:").grid(row=1, column=2, sticky='w', padx=5, pady=5)
        self.account_var = tk.StringVar()
        ttk.Entry(payment_frame, textvariable=self.account_var, width=20).grid(row=1, column=3, padx=5, pady=5)
        
        # المستفيد
        ttk.Label(payment_frame, text="اسم المستفيد:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.beneficiary_var = tk.StringVar()
        ttk.Entry(payment_frame, textvariable=self.beneficiary_var, width=30).grid(row=2, column=1, padx=5, pady=5)
        
        # حساب المستفيد
        ttk.Label(payment_frame, text="حساب المستفيد:").grid(row=2, column=2, sticky='w', padx=5, pady=5)
        self.beneficiary_account_var = tk.StringVar()
        ttk.Entry(payment_frame, textvariable=self.beneficiary_account_var, width=20).grid(row=2, column=3, padx=5, pady=5)
        
        # الغرض
        ttk.Label(payment_frame, text="الغرض:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.purpose_text = tk.Text(payment_frame, width=60, height=4)
        self.purpose_text.grid(row=3, column=1, columnspan=3, padx=5, pady=5)
        
        # ملاحظات
        ttk.Label(main_frame, text="ملاحظات:").pack(anchor='w', padx=5, pady=(0, 5))
        self.notes_text = tk.Text(main_frame, width=80, height=4)
        self.notes_text.pack(fill='x', padx=5, pady=(0, 10))
        
        # الأزرار
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill='x')
        
        # إضافة ModernButton
        class ModernButton(tk.Button):
            def __init__(self, master=None, **kwargs):
                kwargs.pop('style', None)
                super().__init__(master, **kwargs)
                self.configure(
                    relief=tk.FLAT,
                    cursor='hand2',
                    font=('Segoe UI', 11, 'bold'),
                    padx=20,
                    pady=10
                )
        
        save_btn = ModernButton(buttons_frame, text="💾 حفظ", command=self.save_auth,
                              bg='#27AE60', fg='white')
        save_btn.pack(side='right', padx=10, pady=10, ipady=15)
        cancel_btn = ModernButton(buttons_frame, text="❌ إلغاء", command=self.window.destroy,
                                bg='#E74C3C', fg='white')
        cancel_btn.pack(side='left', padx=10, pady=10, ipady=15)
    
    def load_customers(self):
        """تحميل العملاء"""
        try:
            customers = self.db.execute_query("SELECT id, name FROM customers ORDER BY name")
            customer_list = [f"{row[0]} - {row[1]}" for row in customers]
            self.customer_combo['values'] = customer_list
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تحميل العملاء: {str(e)}")
    
    def load_projects(self):
        """تحميل المشاريع"""
        try:
            projects = self.db.execute_query("SELECT id, name FROM projects ORDER BY name")
            project_list = [f"{row[0]} - {row[1]}" for row in projects]
            self.project_combo['values'] = project_list
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تحميل المشاريع: {str(e)}")
    
    def load_auth_data(self):
        """تحميل بيانات الإذن"""
        try:
            auth = self.db.execute_query("""
                SELECT * FROM payment_authorizations WHERE id = ?
            """, (self.auth_id,))
            
            if auth:
                auth = auth[0]
                self.auth_number_var.set(auth[1])
                self.date_var.set(auth[3])
                
                if auth[2]:
                    self.customer_var.set(f"{auth[2]} - {self.get_customer_name(auth[2])}")
                if auth[3]:
                    self.project_var.set(f"{auth[3]} - {self.get_project_name(auth[3])}")
                
                self.amount_var.set(str(auth[4]))
                self.currency_var.set(auth[5])
                self.bank_var.set(auth[6] or '')
                self.account_var.set(auth[7] or '')
                self.beneficiary_var.set(auth[8] or '')
                self.beneficiary_account_var.set(auth[9] or '')
                self.purpose_text.insert('1.0', auth[10] or '')
                self.notes_text.insert('1.0', auth[11] or '')
                
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تحميل بيانات الإذن: {str(e)}")
    
    def get_customer_name(self, customer_id):
        """الحصول على اسم العميل"""
        try:
            customer = self.db.execute_query("SELECT name FROM customers WHERE id = ?", (customer_id,))
            return customer[0][0] if customer else ''
        except:
            return ''
    
    def get_project_name(self, project_id):
        """الحصول على اسم المشروع"""
        try:
            project = self.db.execute_query("SELECT name FROM projects WHERE id = ?", (project_id,))
            return project[0][0] if project else ''
        except:
            return ''
    
    def save_auth(self):
        """حفظ الإذن"""
        try:
            # التحقق من البيانات
            if not self.auth_number_var.get():
                messagebox.showerror("خطأ", "❌ يرجى إدخال رقم الإذن")
                return
            
            if not self.amount_var.get():
                messagebox.showerror("خطأ", "❌ يرجى إدخال المبلغ")
                return
            
            # استخراج IDs
            customer_id = None
            if self.customer_var.get():
                try:
                    customer_id = int(self.customer_var.get().split(' - ')[0])
                except:
                    pass
            
            project_id = None
            if self.project_var.get():
                try:
                    project_id = int(self.project_var.get().split(' - ')[0])
                except:
                    pass
            
            # حفظ البيانات
            if self.auth_id:
                # تحديث
                self.db.execute_query("""
                    UPDATE payment_authorizations SET
                        authorization_number = ?, customer_id = ?, project_id = ?,
                        amount = ?, currency = ?, bank_name = ?, account_number = ?,
                        beneficiary_name = ?, beneficiary_account = ?, purpose = ?,
                        notes = ?, status = 'معلق'
                    WHERE id = ?
                """, (
                    self.auth_number_var.get(),
                    customer_id,
                    project_id,
                    float(self.amount_var.get()),
                    self.currency_var.get(),
                    self.bank_var.get(),
                    self.account_var.get(),
                    self.beneficiary_var.get(),
                    self.beneficiary_account_var.get(),
                    self.purpose_text.get('1.0', 'end-1c'),
                    self.notes_text.get('1.0', 'end-1c'),
                    self.auth_id
                ))
                self.status_callback("✅ تم تحديث إذن الصرف")
            else:
                # إنشاء جديد
                self.db.execute_query("""
                    INSERT INTO payment_authorizations (
                        authorization_number, customer_id, project_id, amount, currency,
                        bank_name, account_number, beneficiary_name, beneficiary_account,
                        purpose, notes, status, created_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'معلق', ?)
                """, (
                    self.auth_number_var.get(),
                    customer_id,
                    project_id,
                    float(self.amount_var.get()),
                    self.currency_var.get(),
                    self.bank_var.get(),
                    self.account_var.get(),
                    self.beneficiary_var.get(),
                    self.beneficiary_account_var.get(),
                    self.purpose_text.get('1.0', 'end-1c'),
                    self.notes_text.get('1.0', 'end-1c'),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
                self.status_callback("✅ تم إنشاء إذن صرف جديد")
            
            self.refresh_callback()
            self.window.destroy()
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حفظ الإذن: {str(e)}")
