import wx
from db import generate_pid, get_connection

class ProductPanel(wx.Panel):
    def __init__(self, parent, order_panel=None):
        super().__init__(parent)
        self.order_panel = order_panel

        vbox = wx.BoxSizer(wx.VERTICAL)

        # ---- 商品列表 ----
        self.list = wx.ListCtrl(self, style=wx.LC_REPORT)
        for i, col in enumerate(["商品編號", "名稱", "價格", "庫存"]):
            self.list.InsertColumn(i, col, width=150)
        vbox.Add(self.list, 1, wx.ALL | wx.EXPAND, 10)

        
        # ---- 輸入區 ----
        grid = wx.FlexGridSizer(4, 2, 10, 10)
        labels = ["商品編號", "名稱", "價格", "庫存"]
        self.inputs = {}

        for label in labels:
            grid.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            txt = wx.TextCtrl(self)
            grid.Add(txt, 1, wx.EXPAND)
            self.inputs[label] = txt

        vbox.Add(grid, 0, wx.ALL | wx.EXPAND, 10)

        # ---- 按鈕 ----
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        add_btn = wx.Button(self, label="新增")
        update_btn = wx.Button(self, label="修改")
        delete_btn = wx.Button(self, label="刪除")

        hbox.Add(add_btn, 0, wx.ALL, 5)
        hbox.Add(update_btn, 0, wx.ALL, 5)
        hbox.Add(delete_btn, 0, wx.ALL, 5)
        vbox.Add(hbox, 0, wx.CENTER)

        self.SetSizer(vbox)

        # 隱藏 PID 輸入框（或設為唯讀）
        self.inputs["商品編號"].Disable()  # 不可編輯
        self.inputs["商品編號"].SetValue("自動產生")
        
        # 綁定事件後
        self.load_products()

        # 綁定事件
        add_btn.Bind(wx.EVT_BUTTON, self.on_add)
        update_btn.Bind(wx.EVT_BUTTON, self.on_update)
        delete_btn.Bind(wx.EVT_BUTTON, self.on_delete)
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)

        self.load_products()

    # ---------------------------------------------------------
    # 新增商品
    # ---------------------------------------------------------
    def on_add(self, event):
        try:
            name = self.inputs["名稱"].GetValue().strip()
            price = float(self.inputs["價格"].GetValue().strip())
            stock = int(self.inputs["庫存"].GetValue().strip())

            if not name:
                raise ValueError("名稱不可為空！")
            if price < 0 or stock < 0:
                raise ValueError("價格與庫存不可為負數！")

            # 自動產生 PID
            pid = generate_pid()

            conn = get_connection()
            cur = conn.cursor()
            
            # 檢查名稱重複
            cur.execute("SELECT 1 FROM PRODUCT WHERE NAME = ? AND DELETED = 0", (name,))
            if cur.fetchone():
                raise ValueError("商品名稱已存在！")

            cur.execute("""
                INSERT INTO PRODUCT (PID, NAME, PRICE, STOCK, DELETED) 
                VALUES (?, ?, ?, ?, 0)
            """, (pid, name, price, stock))
            conn.commit()
            conn.close()

            wx.MessageBox(f"商品已新增\n編號：{pid}", "完成", wx.OK | wx.ICON_INFORMATION)
            self.load_products()
            if self.order_panel:
                self.order_panel.load_products()

            # 清空輸入（PID 保持自動）
            self.inputs["名稱"].SetValue("")
            self.inputs["價格"].SetValue("")
            self.inputs["庫存"].SetValue("")

        except ValueError as ve:
            wx.MessageBox(str(ve), "輸入錯誤", wx.OK | wx.ICON_ERROR)
        except Exception as e:
            wx.MessageBox(f"新增商品時發生錯誤：{e}", "錯誤", wx.OK | wx.ICON_ERROR)

    # ---------------------------------------------------------
    # 修改商品
    # ---------------------------------------------------------
    def on_update(self, event):
        try:
            pid = self.inputs["商品編號"].GetValue().strip()
            name = self.inputs["名稱"].GetValue().strip()
            price = float(self.inputs["價格"].GetValue().strip())
            stock = int(self.inputs["庫存"].GetValue().strip())

            if not pid or pid == "自動產生":
                raise ValueError("請先選擇要修改的商品！")
            if not name:
                raise ValueError("名稱不可為空！")
            if price < 0 or stock < 0:
                raise ValueError("價格與庫存不可為負數！")

            conn = get_connection()
            cur = conn.cursor()

            # 確認商品存在
            cur.execute("SELECT * FROM PRODUCT WHERE PID = ? AND DELETED = 0", (pid,))
            if not cur.fetchone():
                raise ValueError("找不到該商品編號！")

            cur.execute("""
                UPDATE PRODUCT SET NAME = ?, PRICE = ?, STOCK = ? 
                WHERE PID = ? AND DELETED = 0
            """, (name, price, stock, pid))
            conn.commit()
            conn.close()

            wx.MessageBox("商品資料已更新", "完成", wx.OK | wx.ICON_INFORMATION)
            self.load_products()
            if self.order_panel:
                self.order_panel.load_products()

        except ValueError as ve:
            wx.MessageBox(str(ve), "輸入錯誤", wx.OK | wx.ICON_ERROR)
        except Exception as e:
            wx.MessageBox(f"修改商品時發生錯誤：{e}", "錯誤", wx.OK | wx.ICON_ERROR)

    # ---------------------------------------------------------
    # 刪除商品
    # ---------------------------------------------------------
    def on_delete(self, event):
        pid = self.inputs["商品編號"].GetValue().strip()
        if not pid:
            wx.MessageBox("請先選擇要刪除的商品！", "提示", wx.OK | wx.ICON_WARNING)
            return

        confirm = wx.MessageBox(f"確定要刪除商品 {pid} 嗎？", "確認", wx.YES_NO | wx.ICON_WARNING)
        if confirm != wx.YES:
            return

        try:
            conn = get_connection()
            cur = conn.cursor()
            # 錯誤修正：
            cur.execute("UPDATE PRODUCT SET DELETED = 1 WHERE PID = ?", (pid,))
            conn.commit()
            conn.close()

            wx.MessageBox("商品已刪除", "完成", wx.OK | wx.ICON_INFORMATION)
            self.load_products()

            if self.order_panel:
                self.order_panel.load_products()

            for txt in self.inputs.values():
                txt.SetValue("")

        except Exception as e:
            wx.MessageBox(f"刪除商品時發生錯誤：{e}", "錯誤", wx.OK | wx.ICON_ERROR)

    # ---------------------------------------------------------
    # 點擊商品 → 顯示資料到輸入框
    # ---------------------------------------------------------
    def on_item_selected(self, event):
        index = event.GetIndex()
        if index >= 0:
            self.inputs["商品編號"].SetValue(self.list.GetItemText(index, 0))
            self.inputs["名稱"].SetValue(self.list.GetItemText(index, 1))
            self.inputs["價格"].SetValue(self.list.GetItemText(index, 2))
            self.inputs["庫存"].SetValue(self.list.GetItemText(index, 3))

    # ---------------------------------------------------------
    # 載入商品資料
    # ---------------------------------------------------------
    def load_products(self):
        conn = get_connection()
        cur = conn.cursor()
        
        # 選 PID, NAME, PRICE, STOCK（不選 DELETED）
        cur.execute("SELECT PID, NAME, PRICE, STOCK FROM PRODUCT WHERE DELETED = 0")
        rows = cur.fetchall()
        conn.close()

        self.list.DeleteAllItems()
        self.list.DeleteAllColumns()  # 建議清空，避免欄位錯亂

        # 設定欄位（4 欄，對應 PID, 名稱, 價格, 庫存）
        self.list.InsertColumn(0, "商品編號", width=100)
        self.list.InsertColumn(1, "名稱", width=150)
        self.list.InsertColumn(2, "價格", width=80)
        self.list.InsertColumn(3, "庫存", width=80)

        # 加入資料
        for pid, name, price, stock in rows:
            self.list.Append([pid, name, f"{price:.2f}", str(stock)])
