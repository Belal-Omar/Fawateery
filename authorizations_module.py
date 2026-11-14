#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
وحدة إذونات الصرف والسند والخزنة
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
import sqlite3
import os

class AuthorizationsModule:
    def __init__(self, parent, db, status_callback):
        self.parent = parent
        self.db = db
        self.status_callback = status_callback
        
        # إنشاء الجداول إذا لم تكن موجودة
        self.create_tables()
        
        # إعداد الواجهة
        self.frame = ttk.Frame(parent)
        
        # إنشاء ScrollArea للتبويب
        self.create_scrollable_content()
        
        self.setup_ui()
        
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
    
    def create_tables(self):
        """إنشاء جداول إذونات الصرف والسند والخزنة"""
        try:
            # جدول إذونات الصرف
            self.db.execute_query("""
                CREATE TABLE IF NOT EXISTS payment_authorizations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    authorization_number TEXT UNIQUE NOT NULL,
                    customer_id INTEGER,
                    project_id INTEGER,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'ريال سعودي',
                    purpose TEXT,
                    bank_name TEXT,
                    account_number TEXT,
                    beneficiary_name TEXT,
                    beneficiary_account TEXT,
                    status TEXT DEFAULT 'معلق',
                    created_date TEXT,
                    authorized_date TEXT,
                    authorized_by TEXT,
                    notes TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers (id),
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            """)
            
            # جدول إذونات السند
            self.db.execute_query("""
                CREATE TABLE IF NOT EXISTS check_authorizations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    authorization_number TEXT UNIQUE NOT NULL,
                    customer_id INTEGER,
                    project_id INTEGER,
                    check_number TEXT,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'ريال سعودي',
                    payee_name TEXT,
                    purpose TEXT,
                    status TEXT DEFAULT 'معلق',
                    created_date TEXT,
                    authorized_date TEXT,
                    authorized_by TEXT,
                    notes TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers (id),
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            """)
            
            # جدول الخزينة
            self.db.execute_query("""
                CREATE TABLE IF NOT EXISTS treasury (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_number TEXT UNIQUE NOT NULL,
                    transaction_type TEXT NOT NULL, -- 'صرف', 'قبض', 'مصروف'
                    customer_id INTEGER,
                    project_id INTEGER,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'ريال سعودي',
                    description TEXT,
                    reference_type TEXT, -- 'payment_auth', 'check_auth', 'invoice', 'expense'
                    reference_id INTEGER,
                    status TEXT DEFAULT 'معلق',
                    created_date TEXT,
                    processed_date TEXT,
                    processed_by TEXT,
                    notes TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers (id),
                    FOREIGN KEY (project_id) REFERENCES projects (id)
                )
            """)
            
            print("✅ تم إنشاء جداول إذونات الصرف والسند والخزنة")
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في إنشاء الجداول: {str(e)}")
    
    def setup_ui(self):
        """إعداد واجهة المستخدم"""
        # إطار رئيسي
        main_frame = ttk.Frame(self.content_frame)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # شريط الأدوات
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill='x', pady=(0, 10))
        
        ttk.Button(toolbar, text="📄 إذن صرف جديد", command=self.create_payment_auth).pack(side='right', padx=5, ipady=12)
        ttk.Button(toolbar, text="📋 إذن سند جديد", command=self.create_check_auth).pack(side='right', padx=5, ipady=12)
        ttk.Button(toolbar, text="💰 معاملة خزينة جديدة", command=self.create_treasury_transaction).pack(side='right', padx=5, ipady=12)
        ttk.Button(toolbar, text="📊 تقارير", command=self.show_reports).pack(side='right', padx=5, ipady=12)
        
        # دفتر الملاحظات
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True)
        
        # تبويب إذونات الصرف
        self.setup_payment_auth_tab(notebook)
        
        # تبويب إذونات السند
        self.setup_check_auth_tab(notebook)
        
        # تبويب الخزينة
        self.setup_treasury_tab(notebook)
    
    def setup_payment_auth_tab(self, notebook):
        """إعداد تبويب إذونات الصرف"""
        payment_frame = ttk.Frame(notebook)
        notebook.add(payment_frame, text="💳 إذونات الصرف")
        
        # إطار البحث والتصفية
        search_frame = ttk.LabelFrame(payment_frame, text="البحث والتصفية")
        search_frame.pack(fill='x', padx=5, pady=5)
        
        # حقول البحث
        ttk.Label(search_frame, text="البحث:").grid(row=0, column=0, padx=5, pady=5)
        self.payment_search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.payment_search_var, width=20).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(search_frame, text="العميل:").grid(row=0, column=2, padx=5, pady=5)
        self.payment_customer_var = tk.StringVar()
        self.payment_customer_combo = ttk.Combobox(search_frame, textvariable=self.payment_customer_var, width=15)
        self.payment_customer_combo.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(search_frame, text="المشروع:").grid(row=0, column=4, padx=5, pady=5)
        self.payment_project_var = tk.StringVar()
        self.payment_project_combo = ttk.Combobox(search_frame, textvariable=self.payment_project_var, width=15)
        self.payment_project_combo.grid(row=0, column=5, padx=5, pady=5)
        
        ttk.Label(search_frame, text="الحالة:").grid(row=0, column=6, padx=5, pady=5)
        self.payment_status_var = tk.StringVar()
        ttk.Combobox(search_frame, textvariable=self.payment_status_var, 
                   values=["الكل", "معلق", "معتمد", "مرفوض"], width=12).grid(row=0, column=7, padx=5, pady=5)
        
        ttk.Button(search_frame, text="🔍 بحث", command=self.search_payment_auths).grid(row=0, column=8, padx=5, pady=5)
        ttk.Button(search_frame, text="🔄 تحديث", command=self.load_payment_auths).grid(row=0, column=9, padx=5, pady=5)
        
        # جدول إذونات الصرف
        columns = ("الرقم", "العميل", "المشروع", "المبلغ", "العملة", "البنك", "الحالة", "التاريخ")
        self.payment_tree = ttk.Treeview(payment_frame, columns=columns, show='headings', height=15)
        
        # إعداد الأعمدة
        self.payment_tree.heading("#0", text="م")
        self.payment_tree.heading("الرقم", text="رقم الإذن")
        self.payment_tree.heading("العميل", text="العميل")
        self.payment_tree.heading("المشروع", text="المشروع")
        self.payment_tree.heading("المبلغ", text="المبلغ")
        self.payment_tree.heading("العملة", text="العملة")
        self.payment_tree.heading("البنك", text="البنك")
        self.payment_tree.heading("الحالة", text="الحالة")
        self.payment_tree.heading("التاريخ", text="التاريخ")
        
        # عرض الأعمدة
        self.payment_tree.column("#0", width=30)
        self.payment_tree.column("الرقم", width=100)
        self.payment_tree.column("العميل", width=150)
        self.payment_tree.column("المشروع", width=150)
        self.payment_tree.column("المبلغ", width=100)
        self.payment_tree.column("العملة", width=80)
        self.payment_tree.column("البنك", width=120)
        self.payment_tree.column("الحالة", width=100)
        self.payment_tree.column("التاريخ", width=100)
        
        self.payment_tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        # شريط الأدوات السفلي
        payment_toolbar = ttk.Frame(payment_frame)
        payment_toolbar.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(payment_toolbar, text="✏️ تعديل", command=self.edit_payment_auth).pack(side='left', padx=5, ipady=10)
        ttk.Button(payment_toolbar, text="🗑️ حذف", command=self.delete_payment_auth).pack(side='left', padx=5, ipady=10)
        ttk.Button(payment_toolbar, text="✅ اعتماد", command=self.authorize_payment).pack(side='left', padx=5, ipady=10)
        ttk.Button(payment_toolbar, text="❌ رفض", command=self.reject_payment).pack(side='left', padx=5, ipady=10)
        ttk.Button(payment_toolbar, text="🖨️ طباعة", command=self.print_payment_auth).pack(side='left', padx=5, ipady=10)
    
    def setup_check_auth_tab(self, notebook):
        """إعداد تبويب إذونات السند"""
        check_frame = ttk.Frame(notebook)
        notebook.add(check_frame, text="📋 إذونات السند")
        
        # إطار البحث والتصفية
        search_frame = ttk.LabelFrame(check_frame, text="البحث والتصفية")
        search_frame.pack(fill='x', padx=5, pady=5)
        
        # حقول البحث
        ttk.Label(search_frame, text="البحث:").grid(row=0, column=0, padx=5, pady=5)
        self.check_search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.check_search_var, width=20).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(search_frame, text="العميل:").grid(row=0, column=2, padx=5, pady=5)
        self.check_customer_var = tk.StringVar()
        self.check_customer_combo = ttk.Combobox(search_frame, textvariable=self.check_customer_var, width=15)
        self.check_customer_combo.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(search_frame, text="المشروع:").grid(row=0, column=4, padx=5, pady=5)
        self.check_project_var = tk.StringVar()
        self.check_project_combo = ttk.Combobox(search_frame, textvariable=self.check_project_var, width=15)
        self.check_project_combo.grid(row=0, column=5, padx=5, pady=5)
        
        ttk.Label(search_frame, text="الحالة:").grid(row=0, column=6, padx=5, pady=5)
        self.check_status_var = tk.StringVar()
        ttk.Combobox(search_frame, textvariable=self.check_status_var, 
                   values=["الكل", "معلق", "معتمد", "مرفوض"], width=12).grid(row=0, column=7, padx=5, pady=5)
        
        ttk.Button(search_frame, text="🔍 بحث", command=self.search_check_auths).grid(row=0, column=8, padx=5, pady=5)
        ttk.Button(search_frame, text="🔄 تحديث", command=self.load_check_auths).grid(row=0, column=9, padx=5, pady=5)
        
        # جدول إذونات السند
        columns = ("الرقم", "العميل", "المشروع", "رقم الشيك", "المبلغ", "العملة", "المستفيد", "الحالة", "التاريخ")
        self.check_tree = ttk.Treeview(check_frame, columns=columns, show='headings', height=15)
        
        # إعداد الأعمدة
        self.check_tree.heading("#0", text="م")
        self.check_tree.heading("الرقم", text="رقم الإذن")
        self.check_tree.heading("العميل", text="العميل")
        self.check_tree.heading("المشروع", text="المشروع")
        self.check_tree.heading("رقم الشيك", text="رقم الشيك")
        self.check_tree.heading("المبلغ", text="المبلغ")
        self.check_tree.heading("العملة", text="العملة")
        self.check_tree.heading("المستفيد", text="المستفيد")
        self.check_tree.heading("الحالة", text="الحالة")
        self.check_tree.heading("التاريخ", text="التاريخ")
        
        # عرض الأعمدة
        self.check_tree.column("#0", width=30)
        self.check_tree.column("الرقم", width=100)
        self.check_tree.column("العميل", width=150)
        self.check_tree.column("المشروع", width=150)
        self.check_tree.column("رقم الشيك", width=100)
        self.check_tree.column("المبلغ", width=100)
        self.check_tree.column("العملة", width=80)
        self.check_tree.column("المستفيد", width=150)
        self.check_tree.column("الحالة", width=100)
        self.check_tree.column("التاريخ", width=100)
        
        self.check_tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        # شريط الأدوات السفلي
        check_toolbar = ttk.Frame(check_frame)
        check_toolbar.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(check_toolbar, text="✏️ تعديل", command=self.edit_check_auth).pack(side='left', padx=5, ipady=10)
        ttk.Button(check_toolbar, text="🗑️ حذف", command=self.delete_check_auth).pack(side='left', padx=5, ipady=10)
        ttk.Button(check_toolbar, text="✅ اعتماد", command=self.authorize_check).pack(side='left', padx=5, ipady=10)
        ttk.Button(check_toolbar, text="❌ رفض", command=self.reject_check).pack(side='left', padx=5, ipady=10)
        ttk.Button(check_toolbar, text="🖨️ طباعة", command=self.print_check_auth).pack(side='left', padx=5, ipady=10)
    
    def setup_treasury_tab(self, notebook):
        """إعداد تبويب الخزينة"""
        treasury_frame = ttk.Frame(notebook)
        notebook.add(treasury_frame, text="💰 الخزينة")
        
        # إطار البحث والتصفية
        search_frame = ttk.LabelFrame(treasury_frame, text="البحث والتصفية")
        search_frame.pack(fill='x', padx=5, pady=5)
        
        # حقول البحث
        ttk.Label(search_frame, text="البحث:").grid(row=0, column=0, padx=5, pady=5)
        self.treasury_search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.treasury_search_var, width=20).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(search_frame, text="العميل:").grid(row=0, column=2, padx=5, pady=5)
        self.treasury_customer_var = tk.StringVar()
        self.treasury_customer_combo = ttk.Combobox(search_frame, textvariable=self.treasury_customer_var, width=15)
        self.treasury_customer_combo.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(search_frame, text="المشروع:").grid(row=0, column=4, padx=5, pady=5)
        self.treasury_project_var = tk.StringVar()
        self.treasury_project_combo = ttk.Combobox(search_frame, textvariable=self.treasury_project_var, width=15)
        self.treasury_project_combo.grid(row=0, column=5, padx=5, pady=5)
        
        ttk.Label(search_frame, text="النوع:").grid(row=0, column=6, padx=5, pady=5)
        self.treasury_type_var = tk.StringVar()
        ttk.Combobox(search_frame, textvariable=self.treasury_type_var, 
                   values=["الكل", "صرف", "قبض", "مصروف"], width=12).grid(row=0, column=7, padx=5, pady=5)
        
        ttk.Button(search_frame, text="🔍 بحث", command=self.search_treasury).grid(row=0, column=8, padx=5, pady=5)
        ttk.Button(search_frame, text="🔄 تحديث", command=self.load_treasury).grid(row=0, column=9, padx=5, pady=5)
        
        # جدول الخزينة
        columns = ("الرقم", "النوع", "العميل", "المشروع", "المبلغ", "العملة", "الوصف", "الحالة", "التاريخ")
        self.treasury_tree = ttk.Treeview(treasury_frame, columns=columns, show='headings', height=15)
        
        # إعداد الأعمدة
        self.treasury_tree.heading("#0", text="م")
        self.treasury_tree.heading("الرقم", text="رقم المعاملة")
        self.treasury_tree.heading("النوع", text="النوع")
        self.treasury_tree.heading("العميل", text="العميل")
        self.treasury_tree.heading("المشروع", text="المشروع")
        self.treasury_tree.heading("المبلغ", text="المبلغ")
        self.treasury_tree.heading("العملة", text="العملة")
        self.treasury_tree.heading("الوصف", text="الوصف")
        self.treasury_tree.heading("الحالة", text="الحالة")
        self.treasury_tree.heading("التاريخ", text="التاريخ")
        
        # عرض الأعمدة
        self.treasury_tree.column("#0", width=30)
        self.treasury_tree.column("الرقم", width=100)
        self.treasury_tree.column("النوع", width=100)
        self.treasury_tree.column("العميل", width=150)
        self.treasury_tree.column("المشروع", width=150)
        self.treasury_tree.column("المبلغ", width=100)
        self.treasury_tree.column("العملة", width=80)
        self.treasury_tree.column("الوصف", width=200)
        self.treasury_tree.column("الحالة", width=100)
        self.treasury_tree.column("التاريخ", width=100)
        
        self.treasury_tree.pack(fill='both', expand=True, padx=5, pady=5)
        
        # شريط الأدوات السفلي
        treasury_toolbar = ttk.Frame(treasury_frame)
        treasury_toolbar.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(treasury_toolbar, text="✏️ تعديل", command=self.edit_treasury).pack(side='left', padx=5, ipady=10)
        ttk.Button(treasury_toolbar, text="🗑️ حذف", command=self.delete_treasury).pack(side='left', padx=5, ipady=10)
        ttk.Button(treasury_toolbar, text="✅ معالجة", command=self.process_treasury).pack(side='left', padx=5, ipady=10)
        ttk.Button(treasury_toolbar, text="🖨️ طباعة", command=self.print_treasury).pack(side='left', padx=5, ipady=10)
    
    def load_data(self):
        """تحميل البيانات الأولية"""
        self.load_payment_auths()
        self.load_check_auths()
        self.load_treasury()
        self.load_customers()
        self.load_projects()
    
    def load_customers(self):
        """تحميل قائمة العملاء"""
        try:
            customers = self.db.execute_query("SELECT id, name FROM customers ORDER BY name")
            customer_list = [""] + [f"{row[0]} - {row[1]}" for row in customers]
            
            self.payment_customer_combo['values'] = customer_list
            self.check_customer_combo['values'] = customer_list
            self.treasury_customer_combo['values'] = customer_list
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تحميل العملاء: {str(e)}")
    
    def load_projects(self):
        """تحميل قائمة المشاريع"""
        try:
            projects = self.db.execute_query("SELECT id, name FROM projects ORDER BY name")
            project_list = [""] + [f"{row[0]} - {row[1]}" for row in projects]
            
            self.payment_project_combo['values'] = project_list
            self.check_project_combo['values'] = project_list
            self.treasury_project_combo['values'] = project_list
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تحميل المشاريع: {str(e)}")
    
    def load_payment_auths(self):
        """تحميل إذونات الصرف"""
        try:
            payment_auths = self.db.execute_query("""
                SELECT pa.*, c.name as customer_name, p.name as project_name
                FROM payment_authorizations pa
                LEFT JOIN customers c ON pa.customer_id = c.id
                LEFT JOIN projects p ON pa.project_id = p.id
                ORDER BY pa.created_date DESC
            """)
            
            # مسح الجدول
            for item in self.payment_tree.get_children():
                self.payment_tree.delete(item)
            
            # إضافة البيانات
            for auth in payment_auths:
                self.payment_tree.insert('', 'end', values=(
                    auth[0],  # id
                    auth[1],  # authorization_number
                    auth[13] or '---',  # customer_name
                    auth[14] or '---',  # project_name
                    f"{auth[3]:,.2f}",  # amount
                    auth[4],  # currency
                    auth[7],  # bank_name
                    auth[8],  # status
                    auth[9]   # created_date
                ))
                
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تحميل إذونات الصرف: {str(e)}")
    
    def load_check_auths(self):
        """تحميل إذونات السند"""
        try:
            check_auths = self.db.execute_query("""
                SELECT ca.*, c.name as customer_name, p.name as project_name
                FROM check_authorizations ca
                LEFT JOIN customers c ON ca.customer_id = c.id
                LEFT JOIN projects p ON ca.project_id = p.id
                ORDER BY ca.created_date DESC
            """)
            
            # مسح الجدول
            for item in self.check_tree.get_children():
                self.check_tree.delete(item)
            
            # إضافة البيانات
            for auth in check_auths:
                self.check_tree.insert('', 'end', values=(
                    auth[0],  # id
                    auth[1],  # authorization_number
                    auth[12] or '---',  # customer_name
                    auth[13] or '---',  # project_name
                    auth[3],  # check_number
                    f"{auth[4]:,.2f}",  # amount
                    auth[5],  # currency
                    auth[6],  # payee_name
                    auth[7],  # status
                    auth[8]   # created_date
                ))
                
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تحميل إذونات السند: {str(e)}")
    
    def load_treasury(self):
        """تحميل معاملات الخزينة"""
        try:
            treasury = self.db.execute_query("""
                SELECT t.*, c.name as customer_name, p.name as project_name
                FROM treasury t
                LEFT JOIN customers c ON t.customer_id = c.id
                LEFT JOIN projects p ON t.project_id = p.id
                ORDER BY t.created_date DESC
            """)
            
            # مسح الجدول
            for item in self.treasury_tree.get_children():
                self.treasury_tree.delete(item)
            
            # إضافة البيانات
            for trans in treasury:
                type_ar = {
                    'صرف': 'صرف',
                    'قبض': 'قبض',
                    'مصروف': 'مصروف'
                }
                
                self.treasury_tree.insert('', 'end', values=(
                    trans[0],  # id
                    trans[1],  # transaction_number
                    type_ar.get(trans[2], trans[2]),  # transaction_type
                    trans[11] or '---',  # customer_name
                    trans[12] or '---',  # project_name
                    f"{trans[3]:,.2f}",  # amount
                    trans[4],  # currency
                    trans[5],  # description
                    trans[6],  # status
                    trans[7]   # created_date
                ))
                
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في تحميل الخزينة: {str(e)}")
    
    def create_payment_auth(self):
        """إنشاء إذن صرف جديد"""
        from dialogs.payment_auth_dialog import PaymentAuthorizationDialog
        PaymentAuthorizationDialog(self.parent, self.db, self.status_callback, self.load_payment_auths)
    
    def create_check_auth(self):
        """إنشاء إذن سند جديد"""
        from dialogs.check_auth_dialog import CheckAuthorizationDialog
        CheckAuthorizationDialog(self.parent, self.db, self.status_callback, self.load_check_auths)
    
    def create_treasury_transaction(self):
        """إنشاء معاملة خزينة جديدة"""
        from dialogs.treasury_dialog import TreasuryTransactionDialog
        TreasuryTransactionDialog(self.parent, self.db, self.status_callback, self.load_treasury)
    
    def edit_payment_auth(self):
        """تعديل إذن صرف"""
        selected = self.payment_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار إذن صرف لتعديله")
            return
        
        auth_id = self.payment_tree.item(selected[0], 'values')[0]
        from .dialogs import PaymentAuthorizationDialog
        PaymentAuthorizationDialog(self.parent, self.db, self.status_callback, self.load_payment_auths, auth_id)
    
    def edit_check_auth(self):
        """تعديل إذن سند"""
        selected = self.check_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار إذن سند لتعديله")
            return
        
        auth_id = self.check_tree.item(selected[0], 'values')[0]
        from .dialogs import CheckAuthorizationDialog
        CheckAuthorizationDialog(self.parent, self.db, self.status_callback, self.load_check_auths, auth_id)
    
    def edit_treasury(self):
        """تعديل معاملة خزينة"""
        selected = self.treasury_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار معاملة خزينة لتعديلها")
            return
        
        trans_id = self.treasury_tree.item(selected[0], 'values')[0]
        from .dialogs import TreasuryTransactionDialog
        TreasuryTransactionDialog(self.parent, self.db, self.status_callback, self.load_treasury, trans_id)
    
    def delete_payment_auth(self):
        """حذف إذن صرف"""
        selected = self.payment_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار إذن صرف لحذفه")
            return
        
        if messagebox.askyesno("تأكيد", "⚠️ هل أنت متأكد من حذف إذن الصرف؟"):
            auth_id = self.payment_tree.item(selected[0], 'values')[0]
            self.db.execute_query("DELETE FROM payment_authorizations WHERE id = ?", (auth_id,))
            self.status_callback("✅ تم حذف إذن الصرف")
            self.load_payment_auths()
    
    def delete_check_auth(self):
        """حذف إذن سند"""
        selected = self.check_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار إذن سند لحذفه")
            return
        
        if messagebox.askyesno("تأكيد", "⚠️ هل أنت متأكد من حذف إذن السند؟"):
            auth_id = self.check_tree.item(selected[0], 'values')[0]
            self.db.execute_query("DELETE FROM check_authorizations WHERE id = ?", (auth_id,))
            self.status_callback("✅ تم حذف إذن السند")
            self.load_check_auths()
    
    def delete_treasury(self):
        """حذف معاملة خزينة"""
        selected = self.treasury_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار معاملة خزينة لحذفها")
            return
        
        if messagebox.askyesno("تأكيد", "⚠️ هل أنت متأكد من حذف المعاملة؟"):
            trans_id = self.treasury_tree.item(selected[0], 'values')[0]
            self.db.execute_query("DELETE FROM treasury WHERE id = ?", (trans_id,))
            self.status_callback("✅ تم حذف المعاملة")
            self.load_treasury()
    
    def authorize_payment(self):
        """اعتماد إذن صرف"""
        selected = self.payment_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار إذن صرف لاعتماده")
            return
        
        auth_id = self.payment_tree.item(selected[0], 'values')[0]
        self.db.execute_query("""
            UPDATE payment_authorizations 
            SET status = 'معتمد', authorized_date = ?, authorized_by = ?
            WHERE id = ?
        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'المدير', auth_id))
        
        self.status_callback("✅ تم اعتماد إذن الصرف")
        self.load_payment_auths()
    
    def authorize_check(self):
        """اعتماد إذن سند"""
        selected = self.check_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار إذن سند لاعتماده")
            return
        
        auth_id = self.check_tree.item(selected[0], 'values')[0]
        self.db.execute_query("""
            UPDATE check_authorizations 
            SET status = 'معتمد', authorized_date = ?, authorized_by = ?
            WHERE id = ?
        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'المدير', auth_id))
        
        self.status_callback("✅ تم اعتماد إذن السند")
        self.load_check_auths()
    
    def reject_payment(self):
        """رفض إذن صرف"""
        selected = self.payment_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار إذن صرف لرفضه")
            return
        
        auth_id = self.payment_tree.item(selected[0], 'values')[0]
        self.db.execute_query("""
            UPDATE payment_authorizations 
            SET status = 'مرفوض', authorized_date = ?, authorized_by = ?
            WHERE id = ?
        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'المدير', auth_id))
        
        self.status_callback("❌ تم رفض إذن الصرف")
        self.load_payment_auths()
    
    def reject_check(self):
        """رفض إذن سند"""
        selected = self.check_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار إذن سند لرفضه")
            return
        
        auth_id = self.check_tree.item(selected[0], 'values')[0]
        self.db.execute_query("""
            UPDATE check_authorizations 
            SET status = 'مرفوض', authorized_date = ?, authorized_by = ?
            WHERE id = ?
        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'المدير', auth_id))
        
        self.status_callback("❌ تم رفض إذن السند")
        self.load_check_auths()
    
    def process_treasury(self):
        """معالجة معاملة خزينة"""
        selected = self.treasury_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار معاملة لمعالجتها")
            return
        
        trans_id = self.treasury_tree.item(selected[0], 'values')[0]
        self.db.execute_query("""
            UPDATE treasury 
            SET status = 'تمت معالجتها', processed_date = ?, processed_by = ?
            WHERE id = ?
        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'المدير', trans_id))
        
        self.status_callback("✅ تم معالجة المعاملة")
        self.load_treasury()
    
    def search_payment_auths(self):
        """البحث في إذونات الصرف"""
        # تنفيذ البحث (يمكن توسيعه لاحقاً)
        self.load_payment_auths()
    
    def search_check_auths(self):
        """البحث في إذونات السند"""
        # تنفيذ البحث (يمكن توسيعه لاحقاً)
        self.load_check_auths()
    
    def search_treasury(self):
        """البحث في الخزينة"""
        # تنفيذ البحث (يمكن توسيعه لاحقاً)
        self.load_treasury()
    
    def print_payment_auth(self):
        """طباعة إذن الصرف"""
        selected = self.payment_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار إذن صرف لطباعته")
            return
        
        messagebox.showinfo("طباعة", "🖨️ سيتم طباعة إذن الصرف")
    
    def print_check_auth(self):
        """طباعة إذن السند"""
        selected = self.check_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار إذن سند لطباعته")
            return
        
        messagebox.showinfo("طباعة", "🖨️ سيتم طباعة إذن السند")
    
    def print_treasury(self):
        """طباعة معاملة الخزينة"""
        selected = self.treasury_tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "⚠️ يرجى اختيار معاملة لطباعتها")
            return
        
        messagebox.showinfo("طباعة", "🖨️ سيتم طباعة المعاملة")
    
    def show_reports(self):
        """عرض التقارير"""
        messagebox.showinfo("تقارير", "📊 سيتم عرض التقارير المتعلقة بالإذونات والخزينة")
