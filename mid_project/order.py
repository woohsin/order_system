import wx
import sqlite3
import datetime
from db import get_connection

class OrderPanel(wx.Panel):
    def __init__(self, parent, report_panel=None, product_panel=None):
        super().__init__(parent)
        self.report_panel = report_panel
        self.product_panel = product_panel

        # order_items: list of tuples (pid, name, qty, subtotal)
        self.order_items = []

        # product UI state (暫存於 UI，送出前不寫 DB)
        self.product_btns = {}    # pid -> button
        self.product_stock = {}   # pid -> current available stock (int)
        self.product_info = {}    # pid -> (name, price)

        main_vbox = wx.BoxSizer(wx.VERTICAL)

        main_vbox.Add(wx.StaticText(self, label="可點餐商品："), 0, wx.LEFT | wx.TOP, 10)

        # ScrolledWindow for buttons
        self.btn_panel = wx.ScrolledWindow(self, size=(-1, 200))
        self.btn_panel.SetScrollRate(5, 5)
        self.btn_sizer = wx.WrapSizer(wx.HORIZONTAL, wx.WRAPSIZER_DEFAULT_FLAGS)
        self.btn_panel.SetSizer(self.btn_sizer)
        main_vbox.Add(self.btn_panel, 0, wx.EXPAND | wx.ALL, 10)

        # 已加入訂單的 ListCtrl
        self.order_list = wx.ListCtrl(self, style=wx.LC_REPORT)
        self.order_list.InsertColumn(0, "商品名稱", width=200)
        self.order_list.InsertColumn(1, "數量", width=80)
        self.order_list.InsertColumn(2, "小計", width=100)
        main_vbox.Add(self.order_list, 1, wx.EXPAND | wx.ALL, 5)

        # 總金額顯示
        self.total_label = wx.StaticText(self, label="總金額：$0.00")
        font = self.total_label.GetFont()
        font.PointSize += 2
        font.MakeBold()
        self.total_label.SetFont(font)
        main_vbox.Add(self.total_label, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 25)

        # 修改 / 刪除 按鈕（放在送出按鈕上方）
        h_op = wx.BoxSizer(wx.HORIZONTAL)
        modify_btn = wx.Button(self, label="修改選取項目")
        delete_btn = wx.Button(self, label="刪除選取項目")
        h_op.Add(modify_btn, 0, wx.ALL, 5)
        h_op.Add(delete_btn, 0, wx.ALL, 5)
        main_vbox.Add(h_op, 0, wx.ALIGN_RIGHT | wx.RIGHT, 10)

        modify_btn.Bind(wx.EVT_BUTTON, self.on_modify_selected)
        delete_btn.Bind(wx.EVT_BUTTON, self.on_delete_selected)

        # 另外綁定 ListCtrl 的雙擊也可直接觸發修改（選擇性）
        self.order_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)


        # 送出按鈕
        submit_btn = wx.Button(self, label="送出訂單")
        submit_btn.Bind(wx.EVT_BUTTON, self.submit_order)
        main_vbox.Add(submit_btn, 0, wx.ALL | wx.ALIGN_RIGHT, 10)

        self.SetSizer(main_vbox)

        # 用來快速在 ListCtrl 中找到 pid 對應的 index
        self.list_index_by_pid = {}  # pid -> list index

        # 初始載入（從 DB 讀取原始庫存）
        self.load_products()

    # ---------------------------
    def load_products(self):
        """從 PRODUCT 表載入所有商品（DB -> UI），建立按鈕與暫存庫存"""
        # 清掉舊的按鈕與暫存結構
        self.btn_sizer.Clear(True)
        self.product_btns.clear()
        self.product_stock.clear()
        self.product_info.clear()

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT PID, NAME, PRICE, STOCK FROM PRODUCT WHERE DELETED = 0")
        products = cur.fetchall()
        conn.close()

        for pid, name, price, stock in products:
            # 建立按鈕時把 DB 的 stock 複製到 self.product_stock（UI 暫存）
            self.product_stock[pid] = stock
            self.product_info[pid] = (name, price)

            label = f"{name}\n價格: {price:.2f}\n庫存: {stock}"
            btn = wx.Button(self.btn_panel, label=label, size=(140, 80))
            btn.Bind(wx.EVT_BUTTON, lambda evt, p=pid: self.on_product_btn(evt, p))
            self.btn_sizer.Add(btn, 0, wx.ALL, 5)
            self.product_btns[pid] = btn

            # 若庫存為 0，Disabled 並變色
            if stock <= 0:
                btn.Disable()
                try:
                    btn.SetBackgroundColour(wx.Colour(200, 200, 200))
                except Exception:
                    pass

        self.btn_panel.Layout()
        self.btn_panel.FitInside()

    # ---------------------------
    def on_product_btn(self, event, pid):
        """處理按鈕點擊：利用 pid 查暫存資料，再呼叫 add_item"""
        if pid not in self.product_info:
            wx.MessageBox("找不到商品資訊", "錯誤", wx.OK | wx.ICON_ERROR)
            return
        name, price = self.product_info[pid]
        stock = self.product_stock.get(pid, 0)
        self.add_item(pid, name, price, stock)

    # ---------------------------
    def add_item(self, pid, name, price, stock):
        """加入訂單（若已存在則合併），但不修改 DB，只更新 UI 暫存庫存"""
        # 庫存為 0 時
        if stock <= 0:
            wx.MessageBox(f"{name} 已售完！", "提示", wx.OK | wx.ICON_WARNING)
            return

        dlg = wx.TextEntryDialog(self, f"請輸入 {name} 數量（庫存：{stock}）：", "輸入數量", "1")
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return

        # 解析數量與檢查
        try:
            qty = int(dlg.GetValue())
        except ValueError:
            wx.MessageBox("請輸入正整數數量！", "錯誤", wx.OK | wx.ICON_ERROR)
            dlg.Destroy()
            return

        if qty <= 0:
            wx.MessageBox("數量必須大於 0！", "錯誤", wx.OK | wx.ICON_ERROR)
            dlg.Destroy()
            return

        # 使用 UI 暫存的 stock 檢查（而非 DB）
        cur_stock = self.product_stock.get(pid, 0)
        if qty > cur_stock:
            wx.MessageBox(f"庫存不足！目前僅剩 {cur_stock}。", "錯誤", wx.OK | wx.ICON_ERROR)
            dlg.Destroy()
            return

        # 合併相同商品（若已存在則更新數量與小計）
        found = False
        for i, (p_pid, p_name, p_qty, p_subtotal) in enumerate(self.order_items):
            if p_pid == pid:
                new_qty = p_qty + qty
                # 加總後仍需檢查不超過當前 UI 暫存庫存（cur_stock）
                if new_qty > (cur_stock):
                    # 注意：cur_stock 表示加入前的暫存，可被當作剩餘數量+已點數量? 
                    # 但我們已設計 cur_stock 為當前可賣量（未包含 order_items 中已佔的量）
                    # 更簡潔的做法：cur_stock 是剩餘可用量（已考慮先前扣除），
                    # 因此 new_qty > (p_qty + cur_stock_before?) 會複雜。
                    # 我們採用簡單檢查：如果 qty > cur_stock 就會在前面被拒絕，所以此處一般可通過。
                    pass

                new_subtotal = new_qty * price
                self.order_items[i] = (pid, name, new_qty, new_subtotal)

                # 更新 ListCtrl（使用 list_index_by_pid 找到正確 index）
                idx = self.list_index_by_pid.get(pid)
                if idx is not None:
                    self.order_list.SetItem(idx, 1, str(new_qty))
                    self.order_list.SetItem(idx, 2, f"{new_subtotal:.2f}")
                found = True
                break

        if not found:
            subtotal = price * qty
            idx = self.order_list.InsertItem(self.order_list.GetItemCount(), name)
            self.order_list.SetItem(idx, 1, str(qty))
            self.order_list.SetItem(idx, 2, f"{subtotal:.2f}")
            self.order_items.append((pid, name, qty, subtotal))
            self.list_index_by_pid[pid] = idx

        # 🔹 更新 UI 暫存庫存（減掉剛剛加入的 qty）
        self.product_stock[pid] = cur_stock - qty
        self._refresh_product_button(pid)

        # 更新總金額顯示
        self.update_total()

        dlg.Destroy()

    # ---------------------------
    def _refresh_product_button(self, pid):
        """根據 self.product_stock 更新該按鈕的 label/狀態（灰化或顯示庫存）"""
        if pid not in self.product_btns:
            return
        btn = self.product_btns[pid]
        name, price = self.product_info[pid]
        stock = self.product_stock.get(pid, 0)
        # 更新按鈕文字
        new_label = f"{name}\n價格: {price:.2f}\n庫存: {stock}"
        try:
            btn.SetLabel(new_label)
        except Exception:
            # 某些平台上 SetLabel 可能需要其他處理
            pass

        # 若庫存剩 0，disable 並變色
        if stock <= 0:
            try:
                btn.Disable()
                btn.SetBackgroundColour(wx.Colour(200, 200, 200))
            except Exception:
                pass
        else:
            # 若先前被禁用、現在仍有庫存，確保按鈕啟用並恢復預設顏色
            try:
                btn.Enable()
                btn.SetBackgroundColour(wx.NullColour)
            except Exception:
                pass

        # 重新 layout
        self.btn_panel.Layout()
        self.btn_panel.FitInside()

    # ---------------------------
    def update_total(self):
        total = sum(item[3] for item in self.order_items)
        self.total_label.SetLabel(f"總金額：${total:.2f}")

        # ---------------------------
    def rebuild_list_index(self):
        """重新建立 pid -> list index 映射（呼叫在 order_items 變動後）"""
        self.list_index_by_pid.clear()
        for idx, (pid, name, qty, subtotal) in enumerate(self.order_items):
            self.list_index_by_pid[pid] = idx

    # ---------------------------
    def get_selected_index(self):
        """取得 ListCtrl 被選取的 index；若未選則回傳 None"""
        idx = -1
        idx = self.order_list.GetFirstSelected()
        if idx == -1:
            return None
        return idx

    # ---------------------------
    def on_item_activated(self, event):
        """雙擊 ListCtrl 直接修改（觸發修改流程）"""
        self.on_modify_selected(event)

    # ---------------------------
    def on_delete_selected(self, event):
        """刪除 ListCtrl 選取項目，並把數量回補至 product_stock，更新按鈕與總金額"""
        sel = self.get_selected_index()
        if sel is None:
            wx.MessageBox("請先選取要刪除的項目！", "提示", wx.OK | wx.ICON_INFORMATION)
            return

        # 取得資料
        pid, name, qty, subtotal = self.order_items[sel]

        confirm = wx.MessageBox(f"確定要刪除 {name}（數量：{qty}）？", "確認", wx.YES_NO | wx.ICON_QUESTION)
        if confirm != wx.YES:
            return

        # 回補 UI 暫存庫存
        self.product_stock[pid] = self.product_stock.get(pid, 0) + qty
        # 刪除 order_items 與 ListCtrl
        self.order_items.pop(sel)
        self.order_list.DeleteItem(sel)

        # 重新建立索引映射
        self.rebuild_list_index()

        # 更新按鈕顯示（恢復或更新庫存）
        self._refresh_product_button(pid)

        # 更新總金額
        self.update_total()

    # ---------------------------
    def on_modify_selected(self, event):
        """修改選取項目的數量：檢查上限、更新 order_items、調整 product_stock、更新 UI"""
        sel = self.get_selected_index()
        if sel is None:
            wx.MessageBox("請先選取要修改的項目！", "提示", wx.OK | wx.ICON_INFORMATION)
            return

        pid, name, old_qty, old_subtotal = self.order_items[sel]
        price = self.product_info[pid][1]

        # 計算可用上限：目前 UI 暫存庫存 + 該筆原有數量
        # product_stock 設計為「尚未被占用的剩餘量」
        available = self.product_stock.get(pid, 0) + old_qty

        dlg = wx.TextEntryDialog(self, f"修改 {name} 數量（可用：{available}）：", "修改數量", str(old_qty))
        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return

        try:
            new_qty = int(dlg.GetValue())
        except ValueError:
            wx.MessageBox("請輸入正整數數量！", "錯誤", wx.OK | wx.ICON_ERROR)
            dlg.Destroy()
            return

        if new_qty <= 0:
            wx.MessageBox("數量必須大於 0（若要移除請使用刪除）！", "錯誤", wx.OK | wx.ICON_ERROR)
            dlg.Destroy()
            return

        if new_qty > available:
            wx.MessageBox(f"庫存不足！最多可設為 {available}。", "錯誤", wx.OK | wx.ICON_ERROR)
            dlg.Destroy()
            return

        # 計算差值：如果 new_qty > old_qty 則需扣更多暫存庫存
        delta = new_qty - old_qty

        # 調整 product_stock（因為 product_stock 是剩餘量）
        # 當 delta > 0: 減少 product_stock； delta < 0: 回補 product_stock
        self.product_stock[pid] = self.product_stock.get(pid, 0) - delta

        # 更新 order_items
        new_subtotal = new_qty * price
        self.order_items[sel] = (pid, name, new_qty, new_subtotal)

        # 更新 ListCtrl 顯示
        self.order_list.SetItem(sel, 1, str(new_qty))
        self.order_list.SetItem(sel, 2, f"{new_subtotal:.2f}")

        # 更新按鈕顯示
        self._refresh_product_button(pid)

        # 更新總金額
        self.update_total()

        dlg.Destroy()


    # ---------------------------
    def submit_order(self, event):
        if not self.order_items:
            wx.MessageBox("請先加入商品！", "提示", wx.OK | wx.ICON_WARNING)
            return

        oid = "O" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = sum(item[3] for item in self.order_items)

        conn = get_connection()
        cur = conn.cursor()
        try:
            # 正確插入：明確欄位，避免欄位數不符
            cur.execute("""
                INSERT INTO ORDER_MASTER (OID, DATE, TOTAL, COMPLETED) 
                VALUES (?, ?, ?, 0)
            """, (oid, date, total))

            # 明細與庫存更新
            for pid, name, qty, subtotal in self.order_items:
                cur.execute("INSERT INTO ORDER_DETAIL (OID, PID, QTY, SUBTOTAL) VALUES (?, ?, ?, ?)", 
                        (oid, pid, qty, subtotal))
                cur.execute("UPDATE PRODUCT SET STOCK = STOCK - ? WHERE PID = ?", (qty, pid))

            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            wx.MessageBox(f"訂單送出失敗：{e}", "錯誤", wx.OK | wx.ICON_ERROR)
            return
        finally:
            conn.close()

        wx.MessageBox(f"訂單 {oid} 已送出！\n總金額 ${total:.2f}", "完成", wx.OK | wx.ICON_INFORMATION)

        # 清空 UI
        self.order_list.DeleteAllItems()
        self.order_items.clear()
        self.list_index_by_pid.clear()
        self.update_total()

        # 重新載入商品（從 DB 取最新庫存）
        self.load_products()

        # 更新報表與商品頁
        if self.report_panel:
            try:
                self.report_panel.load_order_details()
            except Exception:
                pass
        if self.product_panel:
            try:
                self.product_panel.load_products()
            except Exception:
                pass