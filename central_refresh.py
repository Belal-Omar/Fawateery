"""
Central Refresh System - نظام التحديث المركزي
يضمن تحديث جميع الأجزاء المتصلة فوراً عند أي تغيير
"""

import tkinter as tk
from typing import Dict, Callable, List, Any

class CentralRefreshSystem:
    """نظام التحديث المركزي للبرنامج"""
    
    def __init__(self):
        self.refresh_callbacks: Dict[str, List[Callable]] = {}
        self.data_changed_signals: Dict[str, List[Callable]] = {}
        
    def register_refresh_callback(self, module_name: str, callback: Callable):
        """تسجيل دالة تحديث لوحدة معينة"""
        if module_name not in self.refresh_callbacks:
            self.refresh_callbacks[module_name] = []
        self.refresh_callbacks[module_name].append(callback)
        
    def register_data_changed_signal(self, signal_name: str, callback: Callable):
        """تسجيل دالة للاستماع إلى إشارة تغيير البيانات"""
        if signal_name not in self.data_changed_signals:
            self.data_changed_signals[signal_name] = []
        self.data_changed_signals[signal_name].append(callback)
        
    def emit_data_changed(self, signal_name: str, data: Any = None):
        """إرسال إشارة تغيير البيانات"""
        if signal_name in self.data_changed_signals:
            for callback in self.data_changed_signals[signal_name]:
                try:
                    callback(data)
                except Exception as e:
                    print(f"Error in refresh callback: {e}")
                    
    def refresh_module(self, module_name: str):
        """تحديث وحدة معينة"""
        if module_name in self.refresh_callbacks:
            for callback in self.refresh_callbacks[module_name]:
                try:
                    callback()
                except Exception as e:
                    print(f"Error in refresh callback: {e}")
                    
    def refresh_all_modules(self):
        """تحديث جميع الوحدات المسجلة"""
        for module_name in self.refresh_callbacks:
            self.refresh_module(module_name)
            
    def emit_customer_changed(self, customer_id: int = None):
        """إرسال إشارة تغيير بيانات العميل"""
        self.emit_data_changed("customer_changed", customer_id)
        
    def emit_project_changed(self, project_id: int = None):
        """إرسال إشارة تغيير بيانات المشروع"""
        self.emit_data_changed("project_changed", project_id)
        
    def emit_employee_changed(self, employee_id: int = None):
        """إرسال إشارة تغيير بيانات الموظف"""
        self.emit_data_changed("employee_changed", employee_id)
        
    def emit_invoice_changed(self, invoice_id: int = None):
        """إرسال إشارة تغيير بيانات الفاتورة"""
        self.emit_data_changed("invoice_changed", invoice_id)
        
    def emit_transaction_changed(self, transaction_id: int = None):
        """إرسال إشارة تغيير بيانات المعاملة"""
        self.emit_data_changed("transaction_changed", transaction_id)


# إنشاء نسخة عالمية من النظام
central_refresh = CentralRefreshSystem()


class RefreshableModule:
    """فئة أساسية للوحدات القابلة للتحديث"""
    
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.setup_refresh_system()
        
    def setup_refresh_system(self):
        """إعداد نظام التحديث"""
        central_refresh.register_refresh_callback(self.module_name, self.refresh_data)
        
    def refresh_data(self):
        """دالة تحديث البيانات - يجب تعريفها في الفئة الفرعية"""
        pass
        
    def emit_data_changed(self, signal_name: str, data: Any = None):
        """إرسال إشارة تغيير البيانات"""
        central_refresh.emit_data_changed(signal_name, data)


class AutoRefreshMixin:
    """Mixin لإضافة التحديث التلقائي للوحدات"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_auto_refresh()
        
    def setup_auto_refresh(self):
        """إعداد التحديث التلقائي"""
        if hasattr(self, 'module_name'):
            central_refresh.register_refresh_callback(self.module_name, self.auto_refresh)
            
    def auto_refresh(self):
        """التحديث التلقائي"""
        if hasattr(self, 'load_data'):
            self.load_data()
        elif hasattr(self, 'refresh_data'):
            self.refresh_data()


def after_save_refresh(signal_name: str, data: Any = None):
    """ديكوراتور للتحديث التلقائي بعد الحفظ"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            central_refresh.emit_data_changed(signal_name, data)
            return result
        return wrapper
    return decorator


# استخدام سهل للنظام
def setup_global_refresh():
    """إعداد النظام العالمي للتحديث"""
    return central_refresh


def refresh_all():
    """تحديث جميع الوحدات"""
    central_refresh.refresh_all_modules()


def emit_customer_change(customer_id: int = None):
    """إرسال إشارة تغيير العميل"""
    central_refresh.emit_customer_changed(customer_id)


def emit_project_change(project_id: int = None):
    """إرسال إشارة تغيير المشروع"""
    central_refresh.emit_project_changed(project_id)


def emit_employee_change(employee_id: int = None):
    """إرسال إشارة تغيير الموظف"""
    central_refresh.emit_employee_changed(employee_id)


def emit_invoice_change(invoice_id: int = None):
    """إرسال إشارة تغيير الفاتورة"""
    central_refresh.emit_invoice_changed(invoice_id)


def emit_transaction_change(transaction_id: int = None):
    """إرسال إشارة تغيير المعاملة"""
    central_refresh.emit_transaction_changed(transaction_id)


def emit_account_items_change():
    """إرسال إشارة تغيير بيانات الأصناف"""
    central_refresh.emit_data_changed("account_items_changed")

def emit_treasury_change():
    """إرسال إشارة تغيير الخزينة"""
    central_refresh.emit_data_changed("treasury_changed")
