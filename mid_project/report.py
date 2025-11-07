import wx
from db import get_connection

class ReportPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        # __init__ 中，改為左右分割：

        splitter = wx.SplitterWindow(self)

        # 左：未完成
        left_panel = wx.Panel(splitter)
        left_sizer = wx.BoxSizer(wx.VERTICAL)

        title1 = wx.StaticText(left_panel, label="未完成訂單")
        title1.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        left_sizer.Add(title1, 0, wx.EXPAND | wx.ALL, 5)

        self.pending_scrolled = wx.ScrolledWindow(left_panel, style=wx.VSCROLL)
        self.pending_scrolled.SetScrollRate(5, 5)
        self.pending_vbox = wx.BoxSizer(wx.VERTICAL)
        self.pending_scrolled.SetSizer(self.pending_vbox)
        left_sizer.Add(self.pending_scrolled, 1, wx.EXPAND)

        left_panel.SetSizer(left_sizer)

        # 右：已完成
        right_panel = wx.Panel(splitter)
        right_sizer = wx.BoxSizer(wx.VERTICAL)

        title2 = wx.StaticText(right_panel, label="已完成訂單")
        title2.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        right_sizer.Add(title2, 0, wx.EXPAND | wx.ALL, 5)

        self.completed_scrolled = wx.ScrolledWindow(right_panel, style=wx.VSCROLL)
        self.completed_scrolled.SetScrollRate(5, 5)
        self.completed_vbox = wx.BoxSizer(wx.VERTICAL)
        self.completed_scrolled.SetSizer(self.completed_vbox)
        right_sizer.Add(self.completed_scrolled, 1, wx.EXPAND)

        right_panel.SetSizer(right_sizer)

        # 左右分割
        splitter.SplitVertically(left_panel, right_panel)
        splitter.SetSashGravity(0.5)  # 左右各半

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(splitter, 1, wx.EXPAND)
        self.SetSizer(main_sizer)
        self.completed_scrolled.SetBackgroundColour(self.GetBackgroundColour())
        self.pending_scrolled.SetBackgroundColour(self.GetBackgroundColour())

        self.load_order_details()

    def create_block(self, oid, parent_sizer):
        conn = get_connection()
        cur = conn.cursor()
        scrolled = self.pending_scrolled if parent_sizer == self.pending_vbox else self.completed_scrolled
        block_panel = wx.Panel(scrolled, style=wx.BORDER_SIMPLE)
        block_sizer = wx.BoxSizer(wx.VERTICAL)

        cur.execute("SELECT PID, QTY, SUBTOTAL FROM ORDER_DETAIL WHERE OID=?", (oid,))
        details = cur.fetchall()

        block_sizer.Add(wx.StaticText(block_panel, label=f"訂單編號: {oid}"), 0, wx.ALL, 5)
        # 3. report.py 的 create_block() 安全取名稱
        for pid, qty, subtotal in details:
            cur.execute("SELECT NAME FROM PRODUCT WHERE PID = ?", (pid,))
            row = cur.fetchone()
            name = row[0] if row else f"[已刪除] {pid}"
            block_sizer.Add(wx.StaticText(block_panel, label=f"商品: {name}  數量: {qty}  小計: {subtotal:.2f}"),
                            0, wx.LEFT | wx.BOTTOM, 5)
        cur.execute("SELECT TOTAL FROM ORDER_MASTER WHERE OID=?", (oid,))
        total = cur.fetchone()[0]
        block_sizer.Add(wx.StaticText(block_panel, label=f"總計: {total:.2f}"), 0, wx.LEFT | wx.BOTTOM, 5)

        block_panel.SetSizer(block_sizer)
        parent_sizer.Add(block_panel, 0, wx.EXPAND | wx.ALL, 5)

        # 點擊完成
        block_panel.Bind(wx.EVT_LEFT_DOWN, lambda e, o=oid, p=block_panel: self.complete_order(o, p))

        conn.close()
        return block_panel

    def complete_order(self, oid, panel):
        self.pending_vbox.Detach(panel)
        panel.Reparent(self.completed_scrolled)
        self.completed_vbox.Add(panel, 0, wx.EXPAND | wx.ALL, 5)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE ORDER_MASTER SET COMPLETED = 1 WHERE OID = ?", (oid,))
        conn.commit()
        conn.close()

        # 先算「新增」的右邊，再算左邊
        self.completed_scrolled.FitInside()
        self.pending_scrolled.FitInside()
        self.Layout()

    def load_order_details(self):
        # 清空
        for child in self.pending_scrolled.GetChildren():
            child.Destroy()
        for child in self.completed_scrolled.GetChildren():
            child.Destroy()
        self.pending_vbox.Clear()
        self.completed_vbox.Clear()

        conn = get_connection()
        cur = conn.cursor()

        # 讀未完成
        cur.execute("SELECT OID FROM ORDER_MASTER WHERE COMPLETED = 0 ORDER BY OID")
        for row in cur.fetchall():
            self.create_block(row[0], self.pending_vbox)

        # 讀已完成
        cur.execute("SELECT OID FROM ORDER_MASTER WHERE COMPLETED = 1 ORDER BY OID")
        for row in cur.fetchall():
            self.create_block(row[0], self.completed_vbox)

        conn.close()
        self.pending_scrolled.FitInside()
        self.completed_scrolled.FitInside()
        self.Layout()