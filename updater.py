"""
نظام التحديث التلقائي السحابي لبرنامج فواتيري (Cloud Auto-Updater)
يتصل بمستودع GitHub لجلب أحدث التحديثات وتنزيلها وتثبيتها تلقائياً
Repository: https://github.com/Belal-Omar/Fawateery
"""

import sys
import os
import json
import urllib.request
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

CURRENT_VERSION = "1.0.2"
GITHUB_REPO = "Belal-Omar/Fawateery"
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.json"
# للاختبار فقط: تحويل فحص التحديث إلى خادم محلي (لا يُستخدم عند العميل)
_TEST_VERSION_URL = os.environ.get('FAWATEERY_VERSION_URL')
if _TEST_VERSION_URL:
    VERSION_URL = _TEST_VERSION_URL
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

def parse_version(v_str):
    """تحويل نص الإصدار إلى مصفوفة أرقام للمقارنة الدقيقة"""
    if not v_str:
        return (0, 0, 0)
    cleaned = v_str.strip().lstrip('vV')
    parts = []
    for p in cleaned.split('.'):
        digits = ''.join(c for c in p if c.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])

def fetch_update_info():
    """جلب معلومات التحديث من GitHub"""
    headers = {
        'User-Agent': 'Fawateery-AutoUpdater/1.0',
        'Accept': 'application/json'
    }
    
    # 1. المحاولة الأولى: قراءة version.json المباشر
    try:
        req = urllib.request.Request(VERSION_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                if 'version' in data and 'download_url' in data:
                    return data
    except Exception as e:
        print(f"Info: version.json fetch skipped/failed: {e}")

    if _TEST_VERSION_URL:
        return None

    # 2. المحاولة الثانية: GitHub Releases API
    try:
        req = urllib.request.Request(RELEASES_API, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as response:
            if response.status == 200:
                rel = json.loads(response.read().decode('utf-8'))
                tag = rel.get('tag_name', '').lstrip('vV')
                body = rel.get('body', '')
                download_url = None
                for asset in rel.get('assets', []):
                    if asset.get('name', '').lower().endswith('.exe'):
                        download_url = asset.get('browser_download_url')
                        break
                if tag and download_url:
                    return {
                        'version': tag,
                        'download_url': download_url,
                        'changelog': body or 'تحسينات عامة وإصلاحات في الأداء',
                        'release_date': rel.get('published_at', '')[:10]
                    }
    except Exception as e:
        print(f"Info: GitHub Releases API fetch failed: {e}")

    return None

def check_for_updates(parent=None, silent=False):
    """فحص وجود تحديثات في خيط خلفي (Background Thread) لمنع تجميد الشاشة"""
    def worker():
        try:
            info = fetch_update_info()
            if not info:
                if not silent and parent and parent.winfo_exists():
                    parent.after(0, lambda: messagebox.showinfo(
                        "التحديثات",
                        f"✅ برنامج فواتيري محدّث لأحدث إصدار ({CURRENT_VERSION}).\nلم تتوفر إصدارات جديدة حالياً على السيرفر.",
                        parent=parent
                    ))
                return

            cloud_ver = info.get('version', '0.0.0')
            if parse_version(cloud_ver) > parse_version(CURRENT_VERSION):
                if parent and parent.winfo_exists():
                    parent.after(0, lambda: show_update_prompt(parent, info))
            else:
                if not silent and parent and parent.winfo_exists():
                    parent.after(0, lambda: messagebox.showinfo(
                        "أنت على أحدث إصدار",
                        f"✅ نظام فواتيري محدّث بالكامل.\nالإصدار الحالي: v{CURRENT_VERSION}\nأحدث إصدار متاح: v{cloud_ver}",
                        parent=parent
                    ))
        except Exception as ex:
            print(f"Error checking updates: {ex}")
            if not silent and parent and parent.winfo_exists():
                parent.after(0, lambda: messagebox.showerror(
                    "فحص التحديثات",
                    "تعذر الاتصال بخادم التحديثات، يرجى التأكد من اتصال الإنترنت والمحاولة لاحقاً.",
                    parent=parent
                ))

    t = threading.Thread(target=worker, daemon=True)
    t.start()

def show_update_prompt(parent, info):
    """عرض نافذة إشعار التحديث العصري مع سجل التغييرات"""
    dialog = tk.Toplevel(parent)
    dialog.title("🚀 يتوفر تحديث جديد لبرنامج فواتيري")
    dialog.geometry("540x460")
    dialog.minsize(500, 420)
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()
    dialog.configure(bg='#F8FAFC')

    # توسيط النافذة
    try:
        dialog.update_idletasks()
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        x = max(20, (sw - 540) // 2)
        y = max(20, (sh - 460) // 2)
        dialog.geometry(f"540x460+{x}+{y}")
    except Exception:
        pass

    # Header
    header = tk.Frame(dialog, bg='#1E3A8A', padx=20, pady=15)
    header.pack(fill='x')
    tk.Label(header, text="✨ يتوفر تحديث جديد للبرنامج",
             font=('Segoe UI', 15, 'bold'), fg='white', bg='#1E3A8A').pack(anchor='center')
    
    v_new = info.get('version', '')
    date_str = info.get('release_date', '')
    sub_txt = f"الإصدار الجديد: v{v_new}   (إصدارك الحالي: v{CURRENT_VERSION})"
    if date_str:
        sub_txt += f" | {date_str}"
    tk.Label(header, text=sub_txt,
             font=('Segoe UI', 9), fg='#93C5FD', bg='#1E3A8A').pack(anchor='center', pady=(4, 0))

    # محتوى التحديث وسجل التغييرات
    body = tk.Frame(dialog, bg='#F8FAFC', padx=20, pady=12)
    body.pack(fill='both', expand=True)

    tk.Label(body, text="📋 أبرز التحسينات والمميزات في هذا الإصدار:",
             font=('Segoe UI', 10, 'bold'), fg='#0F172A', bg='#F8FAFC').pack(anchor='e', pady=(0, 6))

    card = tk.Frame(body, bg='white', highlightbackground='#CBD5E1', highlightthickness=1)
    card.pack(fill='both', expand=True, pady=(0, 10))

    text_box = tk.Text(card, font=('Segoe UI', 10), bg='white', fg='#334155',
                       wrap='word', relief='flat', padx=10, pady=8)
    scroll = ttk.Scrollbar(card, orient='vertical', command=text_box.yview)
    text_box.configure(yscrollcommand=scroll.set)

    scroll.pack(side='right', fill='y')
    text_box.pack(side='left', fill='both', expand=True)

    changelog = info.get('changelog', 'تحسينات في الأداء وإصلاحات عامة.')
    text_box.insert('1.0', changelog)
    text_box.configure(state='disabled')

    # تنبيه أمان البيانات
    tk.Label(body, text="🔒 بياناتك وفواتيرك محفوظة بالكامل ولن تتأثر إطلاقاً بعملية التحديث.",
             font=('Segoe UI', 9), fg='#059669', bg='#F8FAFC').pack(anchor='e')

    # الأزرار
    footer = tk.Frame(dialog, bg='#F1F5F9', padx=20, pady=12, highlightbackground='#E2E8F0', highlightthickness=1)
    footer.pack(fill='x', side='bottom')

    def start_update():
        dialog.destroy()
        download_url = info.get('download_url')
        if download_url:
            show_download_progress(parent, download_url, v_new)

    btn_update = tk.Button(footer, text="  🚀 تحديث وتثبيت الآن  ",
                           font=('Segoe UI', 10, 'bold'), bg='#10B981', fg='white',
                           activebackground='#059669', activeforeground='white',
                           relief='flat', padx=18, pady=7, cursor='hand2', command=start_update)
    btn_update.pack(side='right', padx=(10, 0))

    btn_later = tk.Button(footer, text="تذكيري لاحقاً",
                          font=('Segoe UI', 10), bg='#64748B', fg='white',
                          activebackground='#475569', activeforeground='white',
                          relief='flat', padx=15, pady=7, cursor='hand2', command=dialog.destroy)
    btn_later.pack(side='right')

def show_download_progress(parent, url, new_ver):
    """نافذة تنزيل التحديث مع شريط تقدم حي"""
    pwin = tk.Toplevel(parent)
    pwin.title("جاري تنزيل التحديث...")
    pwin.geometry("480x230")
    pwin.resizable(False, False)
    pwin.transient(parent)
    pwin.grab_set()
    pwin.configure(bg='#F8FAFC')

    try:
        pwin.update_idletasks()
        sw = pwin.winfo_screenwidth()
        sh = pwin.winfo_screenheight()
        pwin.geometry(f"480x230+{(sw - 480)//2}+{(sh - 230)//2}")
    except Exception:
        pass

    box = tk.Frame(pwin, bg='#F8FAFC', padx=25, pady=20)
    box.pack(fill='both', expand=True)

    lbl_title = tk.Label(box, text="⬇️ جاري تنزيل الإصدار الجديد...", font=('Segoe UI', 12, 'bold'), bg='#F8FAFC', fg='#1E293B')
    lbl_title.pack(anchor='center', pady=(0, 10))

    prog_bar = ttk.Progressbar(box, orient='horizontal', mode='determinate', length=420)
    prog_bar.pack(pady=(0, 10))

    lbl_status = tk.Label(box, text="الاتصال بالخادم...", font=('Segoe UI', 9), bg='#F8FAFC', fg='#64748B')
    lbl_status.pack(anchor='center')

    cancel_flag = {'cancel': False}

    def cancel_download():
        cancel_flag['cancel'] = True
        pwin.destroy()

    btn_cancel = tk.Button(box, text="إلغاء التنزيل", font=('Segoe UI', 9), bg='#EF4444', fg='white',
                           relief='flat', padx=12, pady=4, cursor='hand2', command=cancel_download)
    btn_cancel.pack(anchor='center', pady=(15, 0))

    def download_thread():
        try:
            exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath('dist/Fawateery.exe')
            exe_dir = os.path.dirname(exe_path)
            temp_file = os.path.join(exe_dir, 'Fawateery_update.exe')

            headers = {'User-Agent': 'Fawateery-AutoUpdater/1.0'}
            req = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(req, timeout=30) as resp:
                total_size = resp.getheader('Content-Length')
                total_size = int(total_size) if total_size else 0

                downloaded = 0
                chunk_size = 1024 * 64

                with open(temp_file, 'wb') as f:
                    while True:
                        if cancel_flag['cancel']:
                            try:
                                f.close()
                                os.remove(temp_file)
                            except Exception:
                                pass
                            return

                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            pct = int(downloaded * 100 / total_size)
                            mb_curr = downloaded / (1024 * 1024)
                            mb_total = total_size / (1024 * 1024)
                            text = f"تم تنزيل: {mb_curr:.1f} MB من {mb_total:.1f} MB ({pct}%)"
                        else:
                            mb_curr = downloaded / (1024 * 1024)
                            text = f"تم تنزيل: {mb_curr:.1f} MB"
                            pct = 50

                        if pwin.winfo_exists():
                            pwin.after(0, lambda p=pct, t=text: update_ui(p, t))

            # التحقق من سلامة الملف
            if os.path.exists(temp_file) and os.path.getsize(temp_file) > 1024 * 1024:
                if pwin.winfo_exists():
                    pwin.after(0, lambda: apply_update_and_restart(temp_file, exe_path))
            else:
                raise Exception("الملف الذي تم تنزيله غير مكتمل أو تالف")

        except Exception as ex:
            print(f"Download failed: {ex}")
            if pwin.winfo_exists():
                pwin.after(0, lambda: messagebox.showerror("خطأ", f"فشل تنزيل التحديث:\n{ex}", parent=parent))
                pwin.after(0, pwin.destroy)

    def update_ui(pct, text):
        prog_bar['value'] = pct
        lbl_status.config(text=text)

    threading.Thread(target=download_thread, daemon=True).start()

def apply_update_and_restart(new_exe, current_exe):
    """استبدال الملف التنفيذي تلقائياً وإعادة تشغيله عبر PowerShell بأمان تام"""
    try:
        def q(p):
            return str(p).replace("'", "''")

        # ينتظر إغلاق البرنامج (مع إعادة المحاولة حتى يتحرر الملف) ثم يستبدله ويشغله
        ps_command = (
            "$ErrorActionPreference='Stop';"
            "Start-Sleep -Milliseconds 800;"
            "$ok=$false;"
            "for($i=0;$i -lt 60;$i++){"
            f"try{{Move-Item -LiteralPath '{q(new_exe)}' -Destination '{q(current_exe)}' -Force;$ok=$true;break}}"
            "catch{Start-Sleep -Milliseconds 500}};"
            "$env:PYINSTALLER_RESET_ENVIRONMENT='1';"
            f"Start-Process -FilePath '{q(current_exe)}' -WorkingDirectory '{q(os.path.dirname(current_exe))}';"
        )

        env = os.environ.copy()
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"  # يمنع إعادة استخدام مجلد التشغيل المؤقت القديم
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_command],
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            env=env
        )

        # إغلاق البرنامج الحالي فوراً لإتاحة استبدال الملف
        os._exit(0)
    except Exception as e:
        messagebox.showerror("خطأ", f"فشل في تطبيق التحديث تلقائياً: {e}")


