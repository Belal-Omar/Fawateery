import sqlite3
import os
import sys
import shutil
from datetime import datetime

def get_db_path():
    """إرجاع مسار قاعدة البيانات الدائم والموحد (AppData لمنع التكرار وحماية البيانات عند التحديثات)"""
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        app_data = os.path.join(os.environ.get('APPDATA', exe_dir), 'Fawateery')
        if not os.path.exists(app_data):
            try:
                os.makedirs(app_data, exist_ok=True)
            except Exception:
                pass
        target_db = os.path.join(app_data, 'accounting.db')
        
        # إذا لم تكن موجودة في AppData، نتحقق أولاً هل توجد قاعدة بيانات سابقة لنقلها تلقائياً بدون فقدان أي بيانات
        if not os.path.exists(target_db):
            candidate_locations = [
                os.path.join(exe_dir, 'accounting.db'),
                os.path.join(os.getcwd(), 'accounting.db')
            ]
            migrated = False
            for cand in candidate_locations:
                if os.path.exists(cand) and os.path.abspath(cand) != os.path.abspath(target_db):
                    try:
                        shutil.copy2(cand, target_db)
                        migrated = True
                        print(f"✅ تم نقل قاعدة البيانات القائمة تلقائياً من {cand} إلى {target_db}")
                        break
                    except Exception as e:
                        print(f"⚠️ فشل نقل قاعدة البيانات من {cand}: {e}")
            
            if not migrated and hasattr(sys, '_MEIPASS'):
                bundled = os.path.join(sys._MEIPASS, 'accounting.db')
                if os.path.exists(bundled):
                    try:
                        shutil.copy2(bundled, target_db)
                    except Exception:
                        pass
        return target_db
    else:
        # نحن في development
        return os.path.abspath('accounting.db')

def get_app_data_dir():
    """إرجاع مجلد AppData للبرنامج"""
    if getattr(sys, 'frozen', False):
        app_data = os.path.join(os.environ['APPDATA'], 'Fawateery')
        if not os.path.exists(app_data):
            os.makedirs(app_data)
        return app_data
    else:
        return '.'

def create_database(db_path=None):
    db_path = db_path or get_db_path()
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # جدول العملاء
    c.execute('''CREATE TABLE IF NOT EXISTS customers
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                tax_number TEXT,
                address TEXT,
                phone TEXT,
                email TEXT)''')
    
    # جدول الفواتير
    c.execute('''CREATE TABLE IF NOT EXISTS invoices
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT UNIQUE,
                customer_id INTEGER,
                date TEXT,
                items TEXT,
                total REAL,
                tax REAL,
                discount REAL,
                grand_total REAL,
                project_id INTEGER,
                FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    
    # جدول الموظفين
    c.execute('''CREATE TABLE IF NOT EXISTS employees
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                position TEXT,
                salary REAL,
                hire_date TEXT,
                phone TEXT,
                address TEXT,
                project_id INTEGER)''')
    
    # Add missing columns to employees table if they don't exist
    try:
        c.execute("ALTER TABLE employees ADD COLUMN department TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        c.execute("ALTER TABLE employees ADD COLUMN national_id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        c.execute("ALTER TABLE employees ADD COLUMN email TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Create company_settings table
    c.execute('''CREATE TABLE IF NOT EXISTS company_settings
                (id INTEGER PRIMARY KEY,
                company_name_ar TEXT,
                company_name_en TEXT,
                owner_name TEXT,
                tax_number TEXT,
                commercial_register TEXT,
                address TEXT,
                address_en TEXT,
                phone1 TEXT,
                phone2 TEXT,
                po_box TEXT,
                postal_code TEXT,
                email TEXT,
                website TEXT)''')
    
    # جدول الرواتب
    c.execute('''CREATE TABLE IF NOT EXISTS salaries
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                month_year TEXT,
                basic_salary REAL,
                bonuses REAL,
                deductions REAL,
                net_salary REAL,
                payment_date TEXT)''')
    
    # جدول المعاملات المالية
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                amount REAL,
                description TEXT,
                date TEXT,
                category TEXT,
                project_id INTEGER)''')
    
    # جدول المشاريع
    c.execute('''CREATE TABLE IF NOT EXISTS projects
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                start_date TEXT,
                end_date TEXT,
                budget REAL,
                status TEXT,
                client_name TEXT,
                customer_id INTEGER,
                description TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    
    # جدول حسابات المدينين (العملاء)
    c.execute('''CREATE TABLE IF NOT EXISTS accounts_receivable
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 customer_id INTEGER,
                 invoice_id INTEGER,
                 project_id INTEGER,
                 amount REAL,
                 paid_amount REAL DEFAULT 0,
                 remaining_amount REAL,
                 due_date TEXT,
                 status TEXT DEFAULT 'معلق',
                 created_date TEXT,
                 last_payment_date TEXT,
                 notes TEXT,
                 FOREIGN KEY (customer_id) REFERENCES customers (id),
                 FOREIGN KEY (invoice_id) REFERENCES invoices (id),
                 FOREIGN KEY (project_id) REFERENCES projects (id))''')
    
    # جدول حسابات الدائنين (الموردين)
    c.execute('''CREATE TABLE IF NOT EXISTS accounts_payable
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 supplier_name TEXT,
                 project_id INTEGER,
                 amount REAL,
                 paid_amount REAL DEFAULT 0,
                 remaining_amount REAL,
                 due_date TEXT,
                 status TEXT DEFAULT 'معلق',
                 created_date TEXT,
                 last_payment_date TEXT,
                 category TEXT,
                 notes TEXT,
                 FOREIGN KEY (project_id) REFERENCES projects (id))''')
    
    # جدول سداد المدفوعات
    c.execute('''CREATE TABLE IF NOT EXISTS payment_records
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 account_type TEXT,
                 account_id INTEGER,
                 amount REAL,
                 payment_date TEXT,
                 payment_method TEXT,
                 reference_number TEXT,
                 notes TEXT,
                 created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    
    # جدول عروض الأسعار
    c.execute('''CREATE TABLE IF NOT EXISTS price_quotes
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 customer_id INTEGER,
                 quote_number TEXT UNIQUE,
                 date TEXT,
                 valid_until TEXT,
                 notes TEXT,
                 subtotal REAL,
                 discount REAL,
                 tax REAL,
                 grand_total REAL,
                 items TEXT,
                 status TEXT DEFAULT 'pending',
                 created_date TEXT,
                 FOREIGN KEY (customer_id) REFERENCES customers (id))''')
    
    # جدول الإعدادات
    c.execute('''CREATE TABLE IF NOT EXISTS settings
               (key TEXT PRIMARY KEY,
                value TEXT)''')
    
    # جدول معاملات الخزينة
    c.execute('''CREATE TABLE IF NOT EXISTS treasury_transactions
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                type TEXT,
                description TEXT,
                amount REAL,
                account_name TEXT,
                project_id INTEGER,
                customer_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    
    # جدول بنود الحسابات
    c.execute('''CREATE TABLE IF NOT EXISTS account_items
               (id INTEGER PRIMARY KEY AUTOINCREMENT,
                number TEXT UNIQUE,
                name TEXT,
                type TEXT)''')
    
    # إضافة بيانات أولية للعملاء
    c.execute('''INSERT OR IGNORE INTO customers (name, tax_number, address, phone, email) 
                 VALUES (?, ?, ?, ?, ?)''', 
              ('مؤسسة ميار العربية لتنمية المعلومات', '310431653500003', 
               'طريق المدينة المنورة حتى السلامة جدة 8256', '0555555555', 'info@example.com'))
    
    # إعدادات أولية
    c.execute('''INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)''',
              ('tax_rate', '15'))
    c.execute('''INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)''',
              ('auto_backup_enabled', '1'))
    c.execute('''INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)''',
              ('auto_backup_interval', 'daily'))
    c.execute('''INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)''',
              ('auto_backup_folder', ''))
    
    # بنود حسابات أولية
    c.execute('''INSERT OR IGNORE INTO account_items (number, name, type) VALUES (?, ?, ?)''',
              ('100', 'الصندوق', 'دائن'))
    c.execute('''INSERT OR IGNORE INTO account_items (number, name, type) VALUES (?, ?, ?)''',
              ('200', 'المصاريف الإدارية', 'مدين'))
    c.execute('''INSERT OR IGNORE INTO account_items (number, name, type) VALUES (?, ?, ?)''',
              ('300', 'مصاريف التشغيل', 'مدين'))
    c.execute('''INSERT OR IGNORE INTO account_items (number, name, type) VALUES (?, ?, ?)''',
              ('400', 'مصاريف متنوعة', 'مدين'))
    c.execute('''INSERT OR IGNORE INTO account_items (number, name, type) VALUES (?, ?, ?)''',
              ('500', 'الإيرادات', 'دائن'))
    
    conn.commit()
    conn.close()

class Database:
    def __init__(self):
        self.db_path = get_db_path()
        
        # التحقق من وجود قاعدة البيانات
        if not os.path.exists(self.db_path):
            create_database(self.db_path)
            print(f"📁 تم إنشاء قاعدة البيانات: {self.db_path}")
        else:
            self.verify_tables()
        
        self.conn = sqlite3.connect(self.db_path)
        self.c = self.conn.cursor()
    
    def verify_tables(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        tables = ['customers', 'invoices', 'employees', 'salaries', 'transactions', 'projects', 'accounts_receivable', 'accounts_payable', 'payment_records', 'price_quotes', 'settings', 'treasury_transactions', 'account_items']
        existing_tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        existing_tables = [table[0] for table in existing_tables]
        
        for table in tables:
            if table not in existing_tables:
                create_database()
                break
        
        # ⚠️ التحقق من وجود عمود customer_id في جدول projects
        try:
            c.execute("SELECT customer_id FROM projects LIMIT 1")
        except sqlite3.OperationalError:
            # العمود غير موجود، أضفه
            print("⚠️ إضافة عمود customer_id لجدول projects...")
            c.execute("ALTER TABLE projects ADD COLUMN customer_id INTEGER")
            conn.commit()
            print("✅ تم إضافة عمود customer_id بنجاح")
        
        # ⚠️ التحقق من وجود عمود description في جدول projects
        try:
            c.execute("SELECT description FROM projects LIMIT 1")
        except sqlite3.OperationalError:
            # العمود غير موجود، أضفه
            print("⚠️ إضافة عمود description لجدول projects...")
            c.execute("ALTER TABLE projects ADD COLUMN description TEXT")
            conn.commit()
            print("✅ تم إضافة عمود description بنجاح")
        
        # ⚠️ التحقق من وجود عمود customer_id في جدول treasury_transactions
        try:
            c.execute("SELECT customer_id FROM treasury_transactions LIMIT 1")
        except sqlite3.OperationalError:
            # العمود غير موجود، أضفه
            print("⚠️ إضافة عمود customer_id لجدول treasury_transactions...")
            c.execute("ALTER TABLE treasury_transactions ADD COLUMN customer_id INTEGER")
            conn.commit()
            print("✅ تم إضافة عمود customer_id بنجاح")
        
        conn.close()
    
    def migrate_database(self):
        """ترقية قاعدة البيانات لإضافة الأعمدة المفقودة"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # التحقق من وجود عمود customer_id في جدول projects
            try:
                c.execute("SELECT customer_id FROM projects LIMIT 1")
                print("✅ عمود customer_id موجود بالفعل")
            except sqlite3.OperationalError:
                print("⚠️ إضافة عمود customer_id لجدول projects...")
                c.execute("ALTER TABLE projects ADD COLUMN customer_id INTEGER REFERENCES customers(id)")
                conn.commit()
                print("✅ تم إضافة عمود customer_id بنجاح")
            
            # التحقق من وجود عمود description
            try:
                c.execute("SELECT description FROM projects LIMIT 1")
            except sqlite3.OperationalError:
                print("⚠️ إضافة عمود description لجدول projects...")
                c.execute("ALTER TABLE projects ADD COLUMN description TEXT")
                conn.commit()
            
            conn.close()
            return True
        except Exception as e:
            print(f"❌ خطأ في ترقية قاعدة البيانات: {e}")
            return False
    
    def execute_query(self, query, params=None):
        try:
            if params:
                self.c.execute(query, params)
            else:
                self.c.execute(query)
            self.conn.commit()
            result = self.c.fetchall()
            return result if result is not None else []
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            print(f"Query was: {query}")
            print(f"Params were: {params}")
            return []
    
    def get_setting(self, key, default=None):
        """قراءة إعداد من جدول settings"""
        try:
            res = self.execute_query("SELECT value FROM settings WHERE key = ?", (key,))
            if res and res[0] and res[0][0] is not None:
                return res[0][0]
            return default
        except Exception:
            return default

    def set_setting(self, key, value):
        """حفظ أو تحديث إعداد في جدول settings"""
        try:
            self.execute_query(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value))
            )
            return True
        except Exception as e:
            print(f"Error saving setting {key}: {e}")
            return False

    def get_backup_settings(self):
        """الحصول على إعدادات النسخ الاحتياطي التلقائي"""
        enabled = self.get_setting('auto_backup_enabled', '1') == '1'
        interval = self.get_setting('auto_backup_interval', 'daily')  # each_close, daily, weekly, monthly
        folder = self.get_setting('auto_backup_folder', '')
        last_backup = self.get_setting('last_auto_backup_time', '')
        if not folder or not os.path.exists(folder):
            folder = os.path.join(os.path.dirname(self.db_path), 'backups')
        return {
            'enabled': enabled,
            'interval': interval,
            'folder': folder,
            'last_backup': last_backup
        }

    def save_backup_settings(self, enabled, interval, folder):
        """حفظ إعدادات النسخ الاحتياطي التلقائي"""
        self.set_setting('auto_backup_enabled', '1' if enabled else '0')
        self.set_setting('auto_backup_interval', str(interval))
        self.set_setting('auto_backup_folder', str(folder))

    def backup_database(self, backup_path=None):
        """عمل نسخة احتياطية من قاعدة البيانات"""
        try:
            if backup_path is None:
                settings = self.get_backup_settings()
                backup_dir = settings['folder']
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir, exist_ok=True)
                
                # اسم النسخة الاحتياطية مع التاريخ
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = os.path.join(backup_dir, f'accounting_backup_{timestamp}.db')
            else:
                backup_dir = os.path.dirname(backup_path)
                if backup_dir and not os.path.exists(backup_dir):
                    os.makedirs(backup_dir, exist_ok=True)
            
            # نسخ الملف بأمان عبر sqlite backup
            src_conn = sqlite3.connect(self.db_path)
            dst_conn = sqlite3.connect(backup_path)
            with dst_conn:
                src_conn.backup(dst_conn)
            src_conn.close()
            dst_conn.close()
            
            # تحديث تاريخ آخر نسخ
            self.set_setting('last_auto_backup_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            print(f"✅ تم إنشاء نسخة احتياطية: {backup_path}")
            
            # تنظيف النسخ القديمة جداً (الاحتفاظ بآخر 30 نسخة لتجنب امتلاء القرص)
            try:
                if backup_dir and os.path.exists(backup_dir):
                    files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith('accounting_backup_') and f.endswith('.db')]
                    if len(files) > 30:
                        files.sort(key=os.path.getmtime)
                        for old_file in files[:-30]:
                            try:
                                os.remove(old_file)
                            except Exception:
                                pass
            except Exception:
                pass

            return backup_path
        except Exception as e:
            print(f"❌ خطأ في النسخ الاحتياطي: {e}")
            return None
    
    def auto_backup(self):
        """نسخ احتياطي تلقائي مجدول عند الإغلاق بحسب تفضيل المستخدم"""
        try:
            settings = self.get_backup_settings()
            if not settings['enabled']:
                print("ℹ️ النسخ الاحتياطي التلقائي معطل حسب رغبة المستخدم")
                return None
            
            interval = settings['interval']
            last_backup_str = settings['last_backup']
            now = datetime.now()

            should_backup = False
            if interval == 'each_close' or not last_backup_str:
                should_backup = True
            else:
                try:
                    last_backup_dt = datetime.strptime(last_backup_str, '%Y-%m-%d %H:%M:%S')
                    delta_days = (now.date() - last_backup_dt.date()).days
                    if interval == 'daily' and delta_days >= 1:
                        should_backup = True
                    elif interval == 'weekly' and delta_days >= 7:
                        should_backup = True
                    elif interval == 'monthly' and delta_days >= 30:
                        should_backup = True
                except Exception:
                    should_backup = True
            
            if should_backup:
                return self.backup_database()
            else:
                print(f"ℹ️ تم تجاوز النسخ التلقائي: تم مسبقاً وفق جدولة ({interval}) بتاريخ {last_backup_str}")
                return None
        except Exception as e:
            print(f"⚠️ خطأ في معالجة النسخ التلقائي: {e}")
            return None
    
    def get_data_directory(self):
        """إرجاع مجلد بيانات البرنامج"""
        return os.path.dirname(self.db_path)
    
    def close(self):
        self.conn.close()
