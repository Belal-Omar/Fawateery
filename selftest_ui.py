"""
selftest_ui.py - فحص ذاتي آلي لبرنامج فواتيري (يعمل من الكود المصدري ومن ملف EXE).

التشغيل:
    python main.py --selftest report.json
    Fawateery.exe  --selftest report.json

يقوم بـ:
  1) المرور على كل التبويبات والضغط على كل زر وكل عنصر قائمة (والنوافذ التي تُفتح منها)
     مع تعطيل رسائل التأكيد وحوارات الملفات حتى لا يتوقف الفحص.
  2) فحص وظيفي: قاعدة البيانات، الخطوط، توليد PDF عربي، الرسوم البيانية، Excel،
     QR، تفقيط الأرقام، والتحقق من نظام التحديث.
يكتب تقريرًا JSON ويُنهي البرنامج. لا يعمل أبدًا في الاستخدام العادي.
"""

import os
import sys
import json
import time
import sqlite3
import tempfile
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog

SKIP_WORDS = ("خروج", "إغلاق", "اغلاق", "إنهاء", "انهاء", "exit", "quit", "close")
TIMEOUT_PER_ACTION = 60


class Report:
    def __init__(self, path):
        self.path = path
        self.items = []     # (kind, name, status, detail)
        self.messages = []  # الرسائل التي ظهرت للمستخدم أثناء الفحص
        self.t0 = time.time()

    def add(self, kind, name, status, detail=""):
        self.items.append({"kind": kind, "name": name, "status": status, "detail": detail})
        self._flush()

    def _flush(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({
                    "frozen": bool(getattr(sys, "frozen", False)),
                    "python": sys.version,
                    "tk": tk.TkVersion,
                    "seconds": round(time.time() - self.t0, 1),
                    "items": self.items,
                    "messages": self.messages[-200:],
                }, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def summary(self):
        ok = sum(1 for i in self.items if i["status"] == "ok")
        bad = [i for i in self.items if i["status"] != "ok"]
        return ok, bad


def _install_stubs(rep):
    def mk(ret, label):
        def f(*a, **k):
            title = k.get("title") or (a[0] if a else "")
            msg = k.get("message") or (a[1] if len(a) > 1 else "")
            rep.messages.append(f"{label}: {title} | {str(msg)[:120]}")
            return ret
        return f
    for n in ("showinfo", "showwarning", "showerror"):
        setattr(messagebox, n, mk("ok", n))
    for n in ("askyesno", "askokcancel"):
        setattr(messagebox, n, mk(True, n))
    messagebox.askyesnocancel = mk(True, "askyesnocancel")
    messagebox.askretrycancel = mk(False, "askretrycancel")
    messagebox.askquestion = mk("yes", "askquestion")
    for n in ("askopenfilename", "asksaveasfilename", "askdirectory"):
        setattr(filedialog, n, mk("", n))
    filedialog.askopenfilenames = mk((), "askopenfilenames")
    filedialog.asksaveasfile = mk(None, "asksaveasfile")
    filedialog.askopenfile = mk(None, "askopenfile")
    for n in ("askstring", "askfloat", "askinteger"):
        setattr(simpledialog, n, mk(None, n))
    tk.Misc.wait_window = lambda self, window=None: None
    tk.Misc.wait_variable = lambda self, name="PY_VAR": None
    if hasattr(os, "startfile"):
        os.startfile = lambda *a, **k: rep.messages.append("startfile: %s" % (a,))
    import webbrowser
    webbrowser.open = lambda *a, **k: rep.messages.append("webbrowser: %s" % (a,)) or True
    import subprocess
    _orig_popen = subprocess.Popen

    class _Popen(_orig_popen):
        def __init__(self, args, *a, **k):
            first = args[0] if isinstance(args, (list, tuple)) and args else args
            rep.messages.append("Popen: %s" % (str(first)[:100],))
            # لا نشغّل أي برنامج خارجي (طباعة/PDF) أثناء الفحص
            super().__init__([sys.executable, "-c", "pass"] if not getattr(sys, "frozen", False)
                             else ["cmd", "/c", "exit"], **{k2: v for k2, v in k.items() if k2 in ("creationflags",)})
    subprocess.Popen = _Popen


def _walk(w):
    yield w
    for c in w.winfo_children():
        try:
            yield from _walk(c)
        except tk.TclError:
            pass


def _is_button(w):
    return isinstance(w, (tk.Button, ttk.Button))


def _btn_text(w):
    try:
        return str(w.cget("text")).strip()
    except tk.TclError:
        return ""


def _skippable(text):
    t = text.lower()
    return any(s in t for s in SKIP_WORDS)


def _select_first_rows(scope):
    for w in _walk(scope):
        if isinstance(w, ttk.Treeview):
            try:
                kids = w.get_children()
                if kids:
                    w.selection_set(kids[0])
                    w.focus(kids[0])
                    w.event_generate("<<TreeviewSelect>>")
            except tk.TclError:
                pass


def _toplevels(root):
    return [w for w in _walk(root) if isinstance(w, tk.Toplevel)]


def _close_new(root, before):
    for tl in _toplevels(root):
        if tl not in before:
            try:
                tl.destroy()
            except tk.TclError:
                pass


def _invoke(root, rep, kind, name, fn, errors):
    before = set(_toplevels(root))
    errors.clear()
    try:
        fn()
        root.update()
        root.update_idletasks()
        if errors:
            rep.add(kind, name, "error", errors[0][:600])
            return None, before
        rep.add(kind, name, "ok")
        return True, before
    except Exception:
        rep.add(kind, name, "error", traceback.format_exc()[-600:])
        return None, before


def _press_buttons(root, rep, scope, scope_name, errors, depth=0):
    """يضغط كل أزرار النطاق ثم أزرار أي نافذة فُتحت (مستوى واحد)."""
    seen = set()
    buttons = [w for w in _walk(scope) if _is_button(w)]
    for b in buttons:
        try:
            if not b.winfo_exists():
                continue
            text = _btn_text(b) or str(b)
            if _skippable(text):
                rep.add("button", f"{scope_name} / {text}", "skipped", "زر إغلاق/خروج")
                continue
            try:
                if str(b.cget("state")) == "disabled":
                    continue
            except tk.TclError:
                pass
            _select_first_rows(scope)
            name = f"{scope_name} / {text}"
            res, before = _invoke(root, rep, "button", name, b.invoke, errors)
            new = [t for t in _toplevels(root) if t not in before]
            if depth == 0:
                for t in new:
                    try:
                        title = t.title()
                    except tk.TclError:
                        title = "نافذة"
                    _press_buttons(root, rep, t, f"{name} -> [{title}]", errors, depth=1)
            _close_new(root, before)
        except tk.TclError:
            continue


def _press_menus(root, rep, errors):
    try:
        menu_name = root.cget("menu")
        if not menu_name:
            return
        top = root.nametowidget(menu_name)
    except (tk.TclError, KeyError):
        return

    def rec(menu, path):
        try:
            last = menu.index("end")
        except tk.TclError:
            return
        if last is None:
            return
        for i in range(last + 1):
            try:
                typ = menu.type(i)
            except tk.TclError:
                continue
            if typ == "cascade":
                label = menu.entrycget(i, "label")
                try:
                    sub = menu.nametowidget(menu.entrycget(i, "menu"))
                    rec(sub, path + [label])
                except (tk.TclError, KeyError):
                    pass
            elif typ in ("command", "checkbutton", "radiobutton"):
                label = menu.entrycget(i, "label")
                if _skippable(label):
                    rep.add("menu", " > ".join(path + [label]), "skipped", "خروج")
                    continue
                _invoke(root, rep, "menu", " > ".join(path + [label]),
                        lambda m=menu, idx=i: m.invoke(idx), errors)
                _close_new(root, set())
    rec(top, ["القائمة"])


def _press_cards(root, rep, errors, app):
    try:
        from main import DashboardCard
    except Exception:
        try:
            DashboardCard = sys.modules["__main__"].DashboardCard
        except Exception:
            return
    for w in _walk(root):
        if isinstance(w, DashboardCard):
            title = "بطاقة"
            for c in _walk(w):
                if isinstance(c, tk.Label) and c.cget("fg") == "#7F8C8D":
                    title = c.cget("text")
            before = set(_toplevels(root))
            _invoke(root, rep, "card", f"بطاقة الإحصاء / {title}",
                    lambda w=w: w.event_generate("<Button-1>"), errors)
            _close_new(root, before)


def _functional(rep, app):
    """فحوصات وظيفية للمكونات التي تعتمد على الملفات المضمّنة."""
    def check(name, fn):
        try:
            detail = fn()
            rep.add("function", name, "ok", str(detail or "")[:300])
        except Exception:
            rep.add("function", name, "error", traceback.format_exc()[-600:])

    tmp = tempfile.mkdtemp(prefix="fawateery_selftest_")

    def db_check():
        from database import get_db_path
        p = get_db_path()
        con = sqlite3.connect(p)
        res = con.execute("PRAGMA integrity_check").fetchone()[0]
        n = len(con.execute("select name from sqlite_master where type='table'").fetchall())
        con.close()
        assert res == "ok", res
        return f"{p} tables={n} integrity={res}"
    check("قاعدة البيانات (سلامة + مسار)", db_check)

    def fonts():
        from invoices_module import get_font_path
        out = []
        for n in ("Amiri-Regular.ttf", "Amiri-Bold.ttf"):
            p = get_font_path(n)
            assert os.path.isfile(p), f"الخط غير موجود: {n} -> {p}"
            out.append(p)
        return out
    check("خطوط Amiri", fonts)

    def icons():
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))
        found = [n for n in ("fawateery_icon.ico", "fawateery_icon_256.png") if os.path.isfile(os.path.join(base, n))]
        assert found, f"لا توجد أيقونات في {base}"
        return found
    check("أيقونات البرنامج", icons)

    def pdf():
        import arabic_reshaper
        from bidi.algorithm import get_display
        from fpdf import FPDF
        from invoices_module import get_font_path
        f = FPDF()
        f.add_page()
        f.add_font("Amiri", "", get_font_path("Amiri-Regular.ttf"))
        f.add_font("Amiri", "B", get_font_path("Amiri-Bold.ttf"))
        f.set_font("Amiri", "B", 16)
        txt = get_display(arabic_reshaper.reshape("فاتورة ضريبية - مسامير ومشمار 12345"))
        f.cell(0, 10, txt, align="R")
        out = os.path.join(tmp, "t.pdf")
        f.output(out)
        sz = os.path.getsize(out)
        assert sz > 5000, sz
        return f"{sz} bytes"
    check("توليد PDF عربي (fpdf2 + Amiri)", pdf)

    def tafqeet():
        import invoices_module as im
        s = im.number_to_arabic_text(1234.5)
        assert s and len(s) > 5
        return s
    check("تفقيط الأرقام", tafqeet)

    def charts():
        import reports
        import matplotlib
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(3, 2))
        ax.bar([1, 2], [3, 4])
        ax.set_title(reports.format_chart_arabic("الأداء المالي"))
        out = os.path.join(tmp, "c.png")
        fig.savefig(out)
        plt.close(fig)
        assert os.path.getsize(out) > 1000
        return matplotlib.get_backend()
    check("الرسوم البيانية (matplotlib)", charts)

    def excel():
        import pandas as pd
        import openpyxl
        out = os.path.join(tmp, "t.xlsx")
        pd.DataFrame({"الاسم": ["أ", "ب"], "المبلغ": [1, 2]}).to_excel(out, index=False)
        wb = openpyxl.load_workbook(out)
        assert wb.active.max_row == 3
        return "ok"
    check("تصدير Excel (pandas + openpyxl)", excel)

    def qr():
        import qrcode
        img = qrcode.make("fawateery")
        out = os.path.join(tmp, "q.png")
        img.save(out)
        assert os.path.getsize(out) > 100
        return "ok"
    check("QR code", qr)

    def calendar():
        import tkcalendar  # noqa
        return tkcalendar.__name__
    check("tkcalendar", calendar)

    def updater_check():
        import updater
        assert updater.parse_version("v1.0.10") > updater.parse_version("1.0.9")
        assert updater.parse_version("1.0.2") > updater.parse_version("1.0.1")
        info = updater.fetch_update_info()
        return f"version={updater.CURRENT_VERSION} server_info={'yes' if info else 'no'}"
    check("نظام التحديث (إصدار + اتصال)", updater_check)


def run(root, app, report_path):
    rep = Report(report_path)
    errors = []
    _install_stubs(rep)

    def on_cb_exc(exc, val, tb):
        errors.append("".join(traceback.format_exception(exc, val, tb))[-600:])
    root.report_callback_exception = on_cb_exc

    try:
        root.update()
        rep.add("startup", "تشغيل البرنامج وبناء الواجهة", "ok")
        nb = getattr(app, "notebook", None)
        if nb is not None:
            tabs = nb.tabs()
            for idx, tid in enumerate(tabs):
                try:
                    label = nb.tab(tid, "text").strip()
                except tk.TclError:
                    label = f"tab{idx}"
                nb.select(tid)
                root.update()
                frame = root.nametowidget(tid)
                rep.add("tab", f"فتح تبويب: {label}", "ok")
                _press_buttons(root, rep, frame, f"[{label}]", errors)
        # أزرار خارج التبويبات (الهيدر/الإجراءات السريعة)
        outside = [w for w in root.winfo_children() if not isinstance(w, (ttk.Notebook, tk.Toplevel, tk.Menu))]
        for w in outside:
            _press_buttons(root, rep, w, "[الواجهة الرئيسية]", errors)
        _press_cards(root, rep, errors, app)
        _press_menus(root, rep, errors)
        _functional(rep, app)
    except Exception:
        rep.add("selftest", "خطأ في أداة الفحص نفسها", "error", traceback.format_exc()[-800:])

    ok, bad = rep.summary()
    bad = [b for b in bad if b["status"] == "error"]
    rep.add("summary", f"ناجح={ok} أخطاء={len(bad)}", "ok" if not bad else "error")
    try:
        root.destroy()
    except tk.TclError:
        pass
    os._exit(1 if bad else 0)

