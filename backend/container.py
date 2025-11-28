from ecommerce_app import EcommerceApp
from file_system_manager import FileSystemManager
from google_sheets_manager import GoogleSheetsManager  # TAMBAH IMPORT INI
from platform_handlers import (LazadaPlatformHandler, ShopeePlatformHandler,
                               TiktokPlatformHandler)
from services import LazadaServices, ShopeeServices, TiktokServices
from sheet_manager import GSheetManager


class Container:
    def __init__(self, google_sheets_manager=None):  # TERIMA PARAMETER
        self.fs = FileSystemManager()
        self.shopee = ShopeeServices(self.fs)
        self.lazada = LazadaServices(self.fs)
        self.tiktok = TiktokServices(self.fs)
        self.gsheet = GSheetManager(
            credentials_files=[
                "bertigamart-f887630c1a21.json",
                "bertigahemat-f1bd6932b229.json",
            ],
            gsheet_id="1lSpIkQhVZURatSdM5DsYyF7pc8-5Zyiq4wYGnLp6jlc",
        )
        # GUNAKAN INSTANCE YANG DITERIMA ATAU BUAT BARU
        if google_sheets_manager is None:
            from google_sheets_manager import GoogleSheetsManager
            self.google_sheets_manager = GoogleSheetsManager(self.fs)
        else:
            self.google_sheets_manager = google_sheets_manager

    def create_shopee_handler(self) -> ShopeePlatformHandler:
        return ShopeePlatformHandler(
            config=self.shopee.config,
            api=self.shopee.api,
            product_manager=self.shopee.product_mgr,
            order_manager=self.shopee.order_mgr,
            wallet_manager=self.shopee.wallet_mgr,
            sheet_manager=self.gsheet,
            fs_manager=self.fs,
            google_sheets_manager=self.google_sheets_manager  # GUNAKAN INSTANCE SAMA
        )

    def create_lazada_handler(self) -> LazadaPlatformHandler:
        return LazadaPlatformHandler(
            config=self.lazada.config,
            api=self.lazada.api,
            product_manager=self.lazada.product_mgr,
            order_manager=self.lazada.order_mgr,
            sheet_manager=self.gsheet,
            fs_manager=self.fs,
            google_sheets_manager=self.google_sheets_manager
        )

    def create_tiktok_handler(self) -> TiktokPlatformHandler:
        return TiktokPlatformHandler(
            config=self.tiktok.config,
            api=self.tiktok.api,
            product_manager=self.tiktok.product_mgr,
            order_manager=self.tiktok.order_mgr,
            sheet_manager=self.gsheet,
            fs_manager=self.fs,
            google_sheets_manager=self.google_sheets_manager
        )

    def create_app(self):
        return EcommerceApp(
            fs_manager=self.fs,
            shopee_handler=self.create_shopee_handler(),
            lazada_handler=self.create_lazada_handler(),
            tiktok_handler=self.create_tiktok_handler(),
            sheet_manager=self.gsheet,
        )
