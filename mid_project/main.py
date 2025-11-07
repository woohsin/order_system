import wx
from product import ProductPanel
from order import OrderPanel
from report import ReportPanel
from db import init_db

class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="點餐系統", size=(900, 600))

        # 建立 Notebook
        nb = wx.Notebook(self)

        self.report_panel = ReportPanel(nb)
        self.order_panel = OrderPanel(nb)       # 先不用傳 report_panel / product_panel
        self.product_panel = ProductPanel(nb)   # 先不用傳 order_panel

        # OrderPanel 知道 ReportPanel 和 ProductPanel
        self.order_panel.report_panel = self.report_panel
        self.order_panel.product_panel = self.product_panel

        # ProductPanel 知道 OrderPanel
        self.product_panel.order_panel = self.order_panel

        # 分頁加入 Notebook
        nb.AddPage(self.order_panel, "點餐")
        nb.AddPage(self.product_panel, "商品")
        nb.AddPage(self.report_panel, "訂單明細")

        self.Centre()
        self.Show()


if __name__ == "__main__":
    init_db()
    app = wx.App(False)
    frame = MainFrame()
    app.MainLoop()
