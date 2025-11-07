import wx
from db import get_connection

class ReportPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.scrolled = wx.ScrolledWindow(self, style=wx.VSCROLL)
        self.scrolled.SetScrollRate(5, 5)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.scrolled.SetSizer(self.vbox)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.scrolled, 1, wx.EXPAND)
        self.SetSizer(main_sizer)

        self.load_order_details()

    def load_order_details(self):
        """重新載入訂單明細"""
        # 先清空舊的 panel
        for child in self.scrolled.GetChildren():
            child.Destroy()
        self.vbox.Clear()

        conn = get_connection()
        cur = conn.cursor()

        # 取得所有 order_id
        cur.execute("SELECT DISTINCT OID FROM ORDER_DETAIL ORDER BY OID")
        order_ids = [row[0] for row in cur.fetchall()]

        for oid in order_ids:
            block_panel = wx.Panel(self.scrolled, style=wx.BORDER_SIMPLE)
            block_sizer = wx.BoxSizer(wx.VERTICAL)

            # 訂單明細
            cur.execute("SELECT PID, QTY, SUBTOTAL FROM ORDER_DETAIL WHERE OID=?", (oid,))
            details = cur.fetchall()

            block_sizer.Add(wx.StaticText(block_panel, label=f"訂單編號: {oid}"), 0, wx.ALL, 5)
            for pid, qty, subtotal in details:
                cur.execute("SELECT NAME FROM PRODUCT WHERE PID=?", (pid,))
                name = cur.fetchone()[0]
                block_sizer.Add(wx.StaticText(block_panel, label=f"商品: {name}  數量: {qty}  小計: {subtotal:.2f}"), 0, wx.LEFT | wx.BOTTOM, 5)
            cur.execute("SELECT TOTAL FROM ORDER_MASTER WHERE OID=?", (oid,))
            details = cur.fetchone()[0]
            total = details
            block_sizer.Add(wx.StaticText(block_panel, label=f"總計: {total}"), 0, wx.LEFT | wx.BOTTOM, 5)

            block_panel.SetSizer(block_sizer)
            self.vbox.Add(block_panel, 0, wx.EXPAND | wx.ALL, 5)

        conn.close()
        self.scrolled.Layout()

