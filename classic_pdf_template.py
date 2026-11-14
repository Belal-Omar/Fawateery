import os
from fpdf import FPDF

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    def ar(text):
        if not text:
            return text
        return get_display(arabic_reshaper.reshape(str(text)))
except ImportError:
    def ar(text): return str(text)

class ClassicInvoicePDF(FPDF):
    def __init__(self, title="فاتورة ضريبية", is_quote=False):
        super().__init__()
        from invoices_module import get_font_path
        self.is_quote = is_quote
        self.title_text = title
        self.add_page()
        # Add fonts
        try:
            self.add_font('Amiri', '', get_font_path('Amiri-Regular.ttf'), uni=True)
            self.add_font('Amiri', 'B', get_font_path('Amiri-Bold.ttf'), uni=True)
        except Exception:
            pass
        self.set_auto_page_break(auto=True, margin=15)
        
    def draw_classic_header(self, invoice_data):
        # Header Info (Logos and Company Name)
        self.set_y(10)
        self.set_font('Amiri', 'B', 14)
        
        # Right (Arabic)
        self.set_text_color(255, 0, 0) # Red
        self.set_xy(110, 10)
        self.cell(90, 7, ar("مؤسسة لؤلؤة البحر للمقاولات"), 0, 1, 'R')
        
        self.set_font('Amiri', 'B', 10)
        self.set_text_color(0, 0, 255) # Blue
        self.set_x(110)
        self.cell(90, 5, ar("محمد بن منير بن محمد سعيد دغستاني"), 0, 1, 'R')
        self.set_x(110)
        self.cell(90, 5, ar("س . ت : 4030330926"), 0, 1, 'R')
        
        self.set_text_color(255, 0, 0) # Red
        self.set_x(110)
        self.cell(90, 5, ar("الرقم الضريبي : 300262161400003"), 0, 1, 'R')
        
        # Left (English)
        self.set_y(10)
        self.set_font('Amiri', 'B', 14)
        self.set_text_color(255, 0, 0)
        self.cell(90, 7, "Sea Pearl Contracting Est.", 0, 1, 'L')
        
        self.set_font('Amiri', 'B', 10)
        self.set_text_color(0, 0, 255)
        self.cell(90, 5, "Mohammed Bin Muneer Bin Mohammed Sayeed", 0, 1, 'L')
        self.cell(90, 5, "Gostany", 0, 1, 'L')
        self.cell(90, 5, "C.R. : 4030330926", 0, 1, 'L')
        self.set_text_color(255, 0, 0)
        self.cell(90, 5, "VAT No : 300262161400003", 0, 1, 'L')
        
        # Reset color
        self.set_text_color(0, 0, 0)
        self.ln(10)
        
        # Data Section
        start_y = self.get_y()
        self.set_font('Amiri', 'B', 12)
        
        # Date & Title Row
        # Rounded Rect for Date
        self.set_xy(135, start_y)
        self.set_draw_color(150, 150, 150)
        self.rounded_rect(135, start_y, 65, 8, 2, 'D')
        self.cell(20, 8, "Date :", 0, 0, 'C')
        self.cell(25, 8, invoice_data.get('date', ''), 0, 0, 'C')
        self.cell(20, 8, ar("التاريخ :"), 0, 0, 'C')
        
        # Title (Invoice / Tax Invoice)
        self.set_xy(50, start_y)
        self.rounded_rect(50, start_y, 80, 8, 2, 'D')
        self.cell(26, 8, "Invoice", 0, 0, 'C')
        title_ar = "عرض سعر" if self.is_quote else "فاتورة ضريبية"
        self.cell(26, 8, ar(title_ar), 0, 0, 'C')
        self.cell(28, 8, ar("فاتورة"), 0, 0, 'C')
        
        # Main Data Box (Customer, Inv No)
        y = start_y + 12
        self.set_xy(10, y)
        # We will draw lines manually to replicate the table look in the PDF
        self.rounded_rect(10, y, 190, 20, 2, 'D') # Outer box for customer details
        
        # Row 1: Cust No | Inv No | Approval
        self.line(10, y+10, 200, y+10) # Horizontal divider
        self.line(70, y, 70, y+10)     # Vertical 1
        self.line(135, y, 135, y+10)   # Vertical 2
        
        # Fill texts for row 1
        self.set_xy(10, y)
        self.cell(20, 10, "Cust No", 0, 0, 'L')
        self.cell(40, 10, ar(f"رقم العميل {invoice_data.get('customer_id', '')}"), 0, 0, 'C')
        
        self.set_xy(70, y)
        self.cell(20, 10, "Inv No.", 0, 0, 'L')
        self.set_text_color(255,0,0)
        doc_num = invoice_data.get('quote_number' if self.is_quote else 'invoice_number', '')
        self.cell(20, 10, str(doc_num), 0, 0, 'C')
        self.set_text_color(0,0,0)
        self.cell(25, 10, ar("رقم الفاتورة:"), 0, 0, 'R')
        
        self.set_xy(135, y)
        self.cell(65, 10, ar("الموافق"), 0, 0, 'R')
        
        # Row 2: Customer Name | VAT No#
        self.set_xy(10, y+10)
        self.cell(28, 10, "Customer Name", 0, 0, 'L')
        self.cell(82, 10, ar(invoice_data.get('customer_name', '')), 0, 0, 'C')
        vat_no = invoice_data.get('customer_vat', '')
        vat_display = f"VAT No# {vat_no}" if vat_no else "VAT No#"
        self.cell(80, 10, ar(vat_display), 0, 0, 'R')
        
        # Row 3: Customer Location / Address
        y += 22
        cust_addr = invoice_data.get('customer_address', '')
        self.rounded_rect(10, y, 190, 8, 2, 'D')
        self.set_xy(12, y)
        self.cell(35, 8, "Customer Address:", 0, 0, 'L')
        addr_text = f"موقع / عنوان العميل: {cust_addr}" if cust_addr else "موقع / عنوان العميل: ---"
        self.cell(140, 8, ar(addr_text), 0, 0, 'R')
        
        self.ln(12)

    def draw_classic_items(self, items_data):
        # Table Header
        self.set_font('Amiri', 'B', 10)
        gold = (244, 220, 155)
        
        col_w = [25, 75, 15, 15, 25, 35] # Code No, Description, Unit, Qty, Unit Price, Total
        headers_en = ["Code No.", "Discraption", "UNIT", "Qty.", "UNIT PRICE", "Total Amount"]
        headers_ar = ["رقم الصنف", "البيان", "الوحدة", "الكمية", "سعر الوحدة", "القيمة الإجمالية"]
        
        y = self.get_y()
        for i, w in enumerate(col_w):
            x = 10 + sum(col_w[:i])
            self.set_xy(x, y)
            if i in [0, 1, 5]: # Gold background for first two and last column
                self.set_fill_color(*gold)
                self.rect(x, y, w, 12, 'DF')
            else:
                self.rect(x, y, w, 12, 'D')
                
            self.set_xy(x, y+1)
            self.cell(w, 5, ar(headers_ar[i]), 0, 2, 'C')
            self.cell(w, 5, headers_en[i], 0, 0, 'C')
            
        self.set_y(y+12)
        
        # Table Body
        self.set_font('Amiri', '', 10)
        self.set_fill_color(*gold) # Same gold for column 0 and 5
        
        for item in items_data:
            if isinstance(item, dict):
                desc = item.get('description', item.get('product_name', ''))
                unit = item.get('unit', '')
                qty = item.get('quantity', 0)
                price = item.get('price', item.get('unit_price', 0))
                total = item.get('total', 0)
            else:
                desc = item[0] if len(item) > 0 else ''
                unit = item[1] if len(item) > 1 else ''
                qty = item[2] if len(item) > 2 else 0
                price = item[3] if len(item) > 3 else 0
                total = item[4] if len(item) > 4 else 0
            
            y = self.get_y()
            # Draw cells
            # Code No
            x = 10
            self.rect(x, y, col_w[0], 10, 'DF')
            
            # Desc
            x += col_w[0]
            self.rect(x, y, col_w[1], 10, 'D')
            self.set_xy(x, y)
            self.cell(col_w[1], 10, ar(desc), 0, 0, 'C')
            
            # Unit
            x += col_w[1]
            self.rect(x, y, col_w[2], 10, 'D')
            self.set_xy(x, y)
            self.cell(col_w[2], 10, ar(unit), 0, 0, 'C')
            
            # Qty
            x += col_w[2]
            self.rect(x, y, col_w[3], 10, 'D')
            self.set_xy(x, y)
            self.cell(col_w[3], 10, str(qty), 0, 0, 'C')
            
            # Unit Price
            x += col_w[3]
            self.rect(x, y, col_w[4], 10, 'D')
            self.set_xy(x, y)
            self.cell(col_w[4], 10, f"{float(price):.2f}", 0, 0, 'C')
            
            # Total
            x += col_w[4]
            self.rect(x, y, col_w[5], 10, 'DF')
            self.set_xy(x, y)
            self.cell(col_w[5], 10, f"{float(total):.2f}", 0, 0, 'C')
            
            self.ln(10)
            
    def draw_classic_totals(self, totals_data, invoice_no, grand_total):
        # totals_data = (total, discount, tax, grand_total)
        total, discount, tax, g_total = totals_data
        
        # Check if there is enough space for totals on current page; otherwise new page
        if self.get_y() > 228:
            self.add_page()
            
        # Move section to the very bottom before the footer info
        y = 236
        self.set_y(y)
        
        gold = (244, 220, 155)
        
        # Totals box on the right
        self.set_font('Amiri', 'B', 10)
        labels = [
            ("Total", "إجمالي المبلغ", total),
            ("Discount", "الخصم", discount),
            ("%15 VAT", "%15 VAT", tax),
            ("Net Amount", "صافي المبلغ", g_total)
        ]
        
        val_w = 30
        box_w = 35
        x_start = 200 - box_w - val_w
        
        for i, (en, ar_txt, val) in enumerate(labels):
            cur_y = y + i * 8
            # Label
            self.set_xy(x_start, cur_y)
            self.cell(15, 8, en, 0, 0, 'L')
            self.cell(20, 8, ar(ar_txt), 0, 0, 'R')
            
            # Value
            self.set_xy(x_start + box_w, cur_y)
            self.set_fill_color(*gold)
            self.rect(x_start + box_w, cur_y, val_w, 8, 'DF' if i in [0, 1, 2, 3] else 'D') 
            self.cell(val_w, 8, f"{float(val):.2f}", 1, 0, 'C', fill=True)
            
        # Condition text (أقر أنا الموقع...)
        cond_w = x_start - 75 - 5
        self.set_xy(75, y)
        self.rounded_rect(75, y, cond_w, 14, 2, 'D')
        self.set_xy(75, y+1)
        self.set_font('Amiri', '', 9)
        self.cell(cond_w, 6, ar("أقر أنا الموقع اسمي وتوقيعي ادناه بصحة صافي"), 0, 1, 'C')
        self.set_x(75)
        self.cell(cond_w, 6, ar("المبلغ بهذه الفاتورة والتزم بالدفع خلال فترة"), 0, 0, 'C')

        # Amount in Words
        from invoices_module import number_to_arabic_text
        words = number_to_arabic_text(g_total)
        self.set_xy(75, y + 16)
        self.rounded_rect(75, y + 16, cond_w, 16, 2, 'D')
        self.set_xy(75, y + 20)
        self.cell(cond_w, 8, ar(words), 0, 0, 'C')
        
        # Signature Box (Top Left)
        self.set_xy(10, y)
        self.rounded_rect(10, y, 60, 16, 2, 'D')
        self.set_xy(10, y + 5)
        self.cell(58, 6, ar("اسم البائع"), 0, 0, 'R')
        
        # QR Code (Bottom Left, directly below Signature Box)
        qr_y = y + 18
        from invoices_module import QR_AVAILABLE
        if QR_AVAILABLE:
            try:
                import qrcode
                qr = qrcode.QRCode(version=1, box_size=10, border=1)
                qr.add_data(f"Inv:{invoice_no}, Tot:{g_total}")
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                import tempfile
                qr_path = os.path.join(tempfile.gettempdir(), f"qr_{invoice_no}.png")
                img.save(qr_path)
                self.image(qr_path, x=10, y=qr_y, w=22, h=22)
            except Exception:
                pass
                
        # Footer text
        self.set_auto_page_break(auto=False)
        footer_y = 280
        self.set_y(footer_y)
        self.set_font('Amiri', '', 8)
        self.set_text_color(100, 100, 100)
        line1 = "المركز الرئيسي: جدة - حي الزمرد أبحر الشمالية - شارع أبي محمد العطار - جوال: 0582224122 / 0538833640 - صندوق بريد: 117232 جدة 21391"
        line2 = "Head Office: Jeddah - Obhur District - Abi Mohammad Alattar Street - 0582224122 / 0538833640 Mobile Po Box 117332 Jeddah 21391"
        line3 = "E-mail: seapearl.est@gmail.com البريد الإلكتروني"
        self.cell(0, 4, ar(line1), 0, 1, 'C')
        self.cell(0, 4, line2, 0, 1, 'C')
        self.cell(0, 4, ar(line3), 0, 1, 'C')
        self.set_auto_page_break(auto=True, margin=15)

    def add_invoice_data(self, invoice, customer_data):
        import ast
        try:
            items = ast.literal_eval(invoice[4]) if isinstance(invoice[4], str) else invoice[4]
        except:
            items = []
            
        cust_name = customer_data[1] if customer_data and len(customer_data) > 1 and customer_data[1] else ''
        cust_vat = customer_data[2] if customer_data and len(customer_data) > 2 and customer_data[2] else ''
        cust_addr = customer_data[3] if customer_data and len(customer_data) > 3 and customer_data[3] else ''
        
        invoice_data = {
            'invoice_number': invoice[1],
            'customer_id': invoice[2],
            'date': invoice[3],
            'customer_name': cust_name,
            'customer_vat': cust_vat,
            'customer_address': cust_addr,
            'quote_number': invoice[1] if self.is_quote else ''
        }
        self.draw_classic_header(invoice_data)
        self.draw_classic_items(items)
        self.draw_classic_totals((invoice[5], invoice[7], invoice[6], invoice[8]), invoice[1], invoice[8])

    def rounded_rect(self, x, y, w, h, r, style='', corners='1234'):
        k = self.k
        hp = self.h
        if(style=='F'): op='f'
        elif(style=='FD' or style=='DF'): op='B'
        else: op='S'
        myArc = 4/3 * (2**0.5 - 1) * r
        self._out('%.2F %.2F m' % ((x+r)*k,(hp-y)*k ))

        xc = x+w-r
        yc = y+r
        self._out('%.2F %.2F l' % (xc*k,(hp-y)*k ))
        if '2' in corners:
            self._out('%.2F %.2F %.2F %.2F %.2F %.2F c' % ((xc+myArc)*k,(hp-y)*k, (xc+r)*k,(hp-(y+myArc))*k, (xc+r)*k,(hp-yc)*k))
        else:
            self._out('%.2F %.2F l' % ((x+w)*k,(hp-y)*k))
            self._out('%.2F %.2F l' % ((x+w)*k,(hp-(y+r))*k))

        xc = x+w-r
        yc = y+h-r
        self._out('%.2F %.2F l' % ((x+w)*k,(hp-yc)*k))
        if '3' in corners:
            self._out('%.2F %.2F %.2F %.2F %.2F %.2F c' % ((x+w)*k,(hp-(yc+myArc))*k, (xc+myArc)*k,(hp-(y+h))*k, xc*k,(hp-(y+h))*k))
        else:
            self._out('%.2F %.2F l' % ((x+w)*k,(hp-(y+h))*k))
            self._out('%.2F %.2F l' % ((x+w-r)*k,(hp-(y+h))*k))

        xc = x+r
        yc = y+h-r
        self._out('%.2F %.2F l' % (xc*k,(hp-(y+h))*k))
        
        if '4' in corners:
            self._out('%.2F %.2F %.2F %.2F %.2F %.2F c' % ((xc-myArc)*k,(hp-(y+h))*k, x*k,(hp-(yc+myArc))*k, x*k,(hp-yc)*k))
        else:
            self._out('%.2F %.2F l' % (x*k,(hp-(y+h))*k))
            self._out('%.2F %.2F l' % (x*k,(hp-(y+h-r))*k))

        xc = x+r
        yc = y+r
        self._out('%.2F %.2F l' % (x*k,(hp-yc)*k ))
        if '1' in corners:
            self._out('%.2F %.2F %.2F %.2F %.2F %.2F c' % (x*k,(hp-(yc-myArc))*k, (xc-myArc)*k,(hp-y)*k, xc*k,(hp-y)*k))
        else:
            self._out('%.2F %.2F l' % (x*k,(hp-y)*k))
            self._out('%.2F %.2F l' % ((x+r)*k,(hp-y)*k))
        self._out(op)
