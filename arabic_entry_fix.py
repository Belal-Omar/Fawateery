"""
arabic_entry_fix.py
-------------------
حل مشكلة "تشقلب" النص العربي عند تحديد حرف/كلمة داخل tk.Entry و ttk.Entry.

السبب: Tk 8.6 يرسم النص المحدد على ثلاث قطع منفصلة (قبل التحديد | المحدد | بعد
التحديد) من اليسار لليمين، وكل قطعة يعاد ترتيبها عربيًا لوحدها، فيظهر الكلام
مقلوبًا.

الحل: أثناء وجود التركيز على حقل فيه عربي، نرسم النص كاملًا كقطعة واحدة (صحيحة
الترتيب) فوق الحقل باستخدام Canvas شفاف الوظيفة، مع رسم التحديد والمؤشر
(caret) بشكل صحيح للاتجاه من اليمين لليسار، ونعالج الماوس ولوحة المفاتيح
بحيث تكون الفهارس منطقية (logical) وليست مبنية على ترتيب اليسار→اليمين.

الاستخدام (مرة واحدة قبل إنشاء الواجهة):
    import arabic_entry_fix
    arabic_entry_fix.apply_arabic_entry_fix()
"""

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

_HIGHLIGHT = "#9EC9FF"   # لون التحديد (فاتح ليبقى النص مقروءًا)
_PATCHED = False


def _has_arabic(s):
    for ch in s:
        o = ord(ch)
        if (0x0600 <= o <= 0x06FF or 0x0750 <= o <= 0x077F or
                0x08A0 <= o <= 0x08FF or 0xFB50 <= o <= 0xFDFF or
                0xFE70 <= o <= 0xFEFF):
            return True
    return False


class _ArabicEntryFix:
    def __init__(self, w):
        self.w = w
        self.is_ttk = isinstance(w, ttk.Entry)
        self.cv = None
        self.anchor = 0
        self.focused = False
        self.blink_on = True
        self.tick_n = 0
        self.ticking = False
        self.ox = self.oy = 0
        self._font_key = None
        self._font = None

        for target in (w,):
            target.bind("<Button-1>", self.on_press, add="+")
            target.bind("<Double-Button-1>", self.on_double, add="+")
            target.bind("<Triple-Button-1>", self.on_triple, add="+")
            target.bind("<B1-Motion>", self.on_motion, add="+")
            target.bind("<Left>", lambda e: self.on_arrow(e, +1, False), add="+")
            target.bind("<Right>", lambda e: self.on_arrow(e, -1, False), add="+")
            target.bind("<Shift-Left>", lambda e: self.on_arrow(e, +1, True), add="+")
            target.bind("<Shift-Right>", lambda e: self.on_arrow(e, -1, True), add="+")
            target.bind("<FocusIn>", self.on_focus_in, add="+")
            target.bind("<FocusOut>", self.on_focus_out, add="+")
            target.bind("<KeyPress>", self.on_key, add="+")
            target.bind("<KeyRelease>", self.on_key, add="+")
            target.bind("<Destroy>", self.on_destroy, add="+")

    # ------------------------------------------------------------ helpers
    def _alive(self):
        try:
            return bool(self.w.winfo_exists())
        except tk.TclError:
            return False

    def _disabled(self):
        w = self.w
        try:
            if self.is_ttk:
                return bool(w.instate(["disabled"]))
            return str(w.cget("state")) == "disabled"
        except tk.TclError:
            return True

    def _has_focus(self):
        try:
            return str(self.w.tk.call("focus")) == str(self.w)
        except tk.TclError:
            return False

    def _arabic(self):
        try:
            if self._disabled():
                return False
            if str(self.w.cget("show")):
                return False
            return _has_arabic(self.w.get())
        except tk.TclError:
            return False

    def _get_font(self):
        w = self.w
        spec = ""
        try:
            spec = str(w.cget("font"))
        except tk.TclError:
            pass
        if not spec and self.is_ttk:
            try:
                spec = str(ttk.Style(w).lookup("TEntry", "font"))
            except tk.TclError:
                spec = ""
        if not spec:
            spec = "TkTextFont"
        if spec != self._font_key:
            self._font_key = spec
            try:
                self._font = tkfont.Font(root=w, font=spec)
            except tk.TclError:
                self._font = tkfont.nametofont("TkTextFont", root=w)
        return self._font

    def _colors(self):
        w = self.w
        try:
            if self.is_ttk:
                st = ttk.Style(w)
                bg = st.lookup("TEntry", "fieldbackground") or "white"
                fg = st.lookup("TEntry", "foreground") or "black"
                try:
                    c = str(w.cget("foreground"))
                    if c:
                        fg = c
                except tk.TclError:
                    pass
            else:
                bg = w.cget("background")
                fg = w.cget("foreground")
                if str(w.cget("state")) == "readonly":
                    bg = w.cget("readonlybackground") or bg
        except tk.TclError:
            bg, fg = "white", "black"
        return bg, fg

    def _inset(self):
        if self.is_ttk:
            return 3
        try:
            return int(float(self.w.cget("bd"))) + int(float(self.w.cget("highlightthickness")))
        except (tk.TclError, ValueError):
            return 2

    def _prefix_widths(self, text):
        # قياس البادئة وحدها يغيّر شكل آخر حرف (يصبح "نهائي")، فتتحرك الحدود
        # ويظهر التحديد/الاختيار مزاحًا بحرف. نضيف ZWJ (عرضه صفر) ليحتفظ الحرف
        # بشكله المتصل كما هو في النص الكامل.
        f = self._get_font()
        n = len(text)
        res = [0]
        for i in range(1, n + 1):
            part = text[:i]
            if i < n and 0x0620 <= ord(text[i]) <= 0x06FF and \
                    not (0x064B <= ord(text[i]) <= 0x065F):
                part += "\u200d"
            res.append(max(res[-1], f.measure(part)))
        if n:
            res[n] = f.measure(text)
        return res

    def _right_edge(self, text):
        """الحافة اليمنى (بإحداثيات الحقل) للكتلة النصية المرسومة."""
        n = len(text)
        try:
            bb = self.w.bbox(n - 1)
        except tk.TclError:
            bb = None
        if bb and len(bb) == 4 and bb[2] > 0:
            return bb[0] + bb[2]
        # bbox غير متاح (أو صفري): نحسب الموضع يدويًا حسب justify
        w = self.w
        W = w.winfo_width()
        inset = self._inset() + 1
        tw = self._get_font().measure(w.get())
        try:
            j = str(w.cget("justify"))
        except tk.TclError:
            j = "left"
        if j == "right":
            return W - inset
        if j == "center":
            return (W + tw) / 2
        return inset + tw

    def _gap_at(self, x):
        """أقرب فهرس منطقي (gap) لإحداثي x (بإحداثيات الحقل)."""
        text = self.w.get()
        pw = self._prefix_widths(text)
        R = self._right_edge(text)
        best, bd = 0, None
        for g, width in enumerate(pw):
            d = abs((R - width) - x)
            if bd is None or d < bd:
                best, bd = g, d
        return best

    def _char_at(self, x):
        text = self.w.get()
        n = len(text)
        if n == 0:
            return 0
        g = self._gap_at(x)
        return min(g, n - 1)

    def _xy(self, e):
        if e.widget is self.cv:
            return e.x + self.ox, e.y + self.oy
        return e.x, e.y

    # -------------------------------------------------------------- mouse
    def on_press(self, e):
        if not self._arabic():
            return None
        x, _ = self._xy(e)
        w = self.w
        w.focus_set()
        g = self._gap_at(x)
        try:
            w.selection_clear()
        except tk.TclError:
            pass
        w.icursor(g)
        self.anchor = g
        self.blink_on = True
        self.refresh()
        return "break"

    def on_motion(self, e):
        if not self._arabic():
            return None
        x, _ = self._xy(e)
        w = self.w
        g = self._gap_at(x)
        a, b = min(self.anchor, g), max(self.anchor, g)
        if a != b:
            w.selection_range(a, b)
        else:
            w.selection_clear()
        w.icursor(g)
        self.refresh()
        return "break"

    def on_double(self, e):
        if not self._arabic():
            return None
        x, _ = self._xy(e)
        w = self.w
        w.focus_set()
        text = w.get()
        i = self._char_at(x)
        a = b = i
        if text[i].isspace():
            while a > 0 and text[a - 1].isspace():
                a -= 1
            while b < len(text) and text[b].isspace():
                b += 1
        else:
            while a > 0 and not text[a - 1].isspace():
                a -= 1
            while b < len(text) and not text[b].isspace():
                b += 1
        w.selection_range(a, b)
        w.icursor(b)
        self.anchor = a
        self.refresh()
        return "break"

    def on_triple(self, e):
        if not self._arabic():
            return None
        w = self.w
        w.focus_set()
        w.selection_range(0, "end")
        w.icursor("end")
        self.anchor = 0
        self.refresh()
        return "break"

    # ----------------------------------------------------------- keyboard
    def on_arrow(self, e, step, extend):
        if not self._arabic():
            return None
        w = self.w
        n = len(w.get())
        cur = w.index("insert")
        new = max(0, min(n, cur + step))
        if extend:
            if not w.selection_present():
                self.anchor = cur
            a, b = min(self.anchor, new), max(self.anchor, new)
            if a != b:
                w.selection_range(a, b)
            else:
                w.selection_clear()
        else:
            if w.selection_present():
                s, t = w.index("sel.first"), w.index("sel.last")
                new = t if step > 0 else s
            w.selection_clear()
            self.anchor = new
        w.icursor(new)
        self.blink_on = True
        self.refresh()
        return "break"

    def on_key(self, e=None):
        self.blink_on = True
        try:
            self.w.after_idle(self.refresh)
        except tk.TclError:
            pass

    # -------------------------------------------------------------- focus
    def on_focus_in(self, e=None):
        self.focused = True
        self.refresh()
        if not self.ticking:
            self.ticking = True
            self.w.after(50, self._tick)

    def on_focus_out(self, e=None):
        self.focused = False
        # أثناء فقدان التركيز نلغي التحديد لتجنب ظهور النص مقلوبًا
        try:
            if self._arabic() and self.w.selection_present():
                self.w.selection_clear()
        except tk.TclError:
            pass
        self.refresh()

    def on_destroy(self, e=None):
        self.ticking = False

    def _tick(self):
        if not self._alive():
            self.ticking = False
            return
        self.focused = self._has_focus()
        self.tick_n += 1
        if self.tick_n % 10 == 0:
            self.blink_on = not self.blink_on
        self.refresh()
        if self.focused or self.cv is not None:
            self.w.after(50, self._tick)
        else:
            self.ticking = False

    # ------------------------------------------------------------ drawing
    def _hide(self):
        if self.cv is not None:
            try:
                self.cv.place_forget()
            except tk.TclError:
                pass

    def _ensure_canvas(self):
        if self.cv is None:
            self.cv = tk.Canvas(self.w, highlightthickness=0, bd=0,
                                takefocus=0, cursor="xterm")
            c = self.cv
            c.bind("<Button-1>", self.on_press)
            c.bind("<Double-Button-1>", self.on_double)
            c.bind("<Triple-Button-1>", self.on_triple)
            c.bind("<B1-Motion>", self.on_motion)
        return self.cv

    def refresh(self):
        try:
            if not self._alive():
                return
            w = self.w
            self.focused = self._has_focus()
            if not (self.focused and self._arabic() and w.winfo_viewable()):
                self._hide()
                return
            self._draw()
        except tk.TclError:
            pass

    def _draw(self):
        w = self.w
        text = w.get()
        cv = self._ensure_canvas()
        inset = self._inset()
        right_margin = 0
        if isinstance(w, ttk.Combobox):
            right_margin = 20
        W, H = w.winfo_width(), w.winfo_height()
        cw = max(1, W - 2 * inset - right_margin)
        ch = max(1, H - 2 * inset)
        self.ox, self.oy = inset, inset
        cv.place(x=inset, y=inset, width=cw, height=ch)

        bg, fg = self._colors()
        cv.configure(bg=bg)
        cv.delete("all")

        font = self._get_font()
        pw = self._prefix_widths(text)
        R = self._right_edge(text) - self.ox
        n = len(text)
        ls = font.metrics("linespace")
        y1, y2 = max(0, (ch - ls) / 2), min(ch, (ch + ls) / 2)

        if w.selection_present():
            a = max(0, min(n, w.index("sel.first")))
            b = max(0, min(n, w.index("sel.last")))
            if a != b:
                cv.create_rectangle(R - pw[b], y1, R - pw[a], y2,
                                    fill=_HIGHLIGHT, outline="")

        cv.create_text(R, ch / 2, anchor="e", text=text, font=font, fill=fg)

        if self.blink_on and not w.selection_present():
            ins = max(0, min(n, w.index("insert")))
            x = R - pw[ins]
            cv.create_line(x, y1, x, y2, fill=fg, width=1)


def _attach(widget):
    if getattr(widget, "_arabic_fix", None) is not None:
        return
    if isinstance(widget, ttk.Spinbox):
        return
    try:
        widget._arabic_fix = _ArabicEntryFix(widget)
    except tk.TclError:
        pass


def _patch_class(cls):
    orig = cls.__init__

    def __init__(self, *args, **kwargs):
        orig(self, *args, **kwargs)
        _attach(self)

    __init__._arabic_orig = orig
    cls.__init__ = __init__


def apply_arabic_entry_fix(root=None):
    """يفعّل الإصلاح على كل tk.Entry و ttk.Entry (و Combobox) تُنشأ بعد الاستدعاء.
    يمكن استدعاؤها أكثر من مرة بأمان. المعامل root متروك للتوافق فقط."""
    global _PATCHED
    if not _PATCHED:
        _patch_class(tk.Entry)
        _patch_class(ttk.Entry)
        _PATCHED = True
    return True
