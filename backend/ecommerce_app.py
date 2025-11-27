import logging
import time

from file_system_manager import FileSystemManager
from platform_handlers import IPlatformHandler
from sheet_manager import ISheetManager


class EcommerceApp:
    """Main application class with dependency injection and modular design"""

    DEFAULT_DAYS = 7
    MAX_STOCK = 99999
    MIN_PRICE = 0
    PRICE_TOLERANCE = 0.01

    def __init__(
        self,
        fs_manager: FileSystemManager,
        shopee_handler: IPlatformHandler,
        lazada_handler: IPlatformHandler,
        tiktok_handler: IPlatformHandler,
        sheet_manager: ISheetManager,
    ):
        self.shopee = shopee_handler
        self.lazada = lazada_handler
        self.tiktok = tiktok_handler
        self.fs = fs_manager
        self.sheet_manager = sheet_manager
        self._auto_refresh_tokens()
        self.logger = self._setup_logging()

    def _setup_logging(self):
        """Configure logging settings"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename=self.fs.get_full_path("log", "ecommerce.log"),
        )
        return logging.getLogger(__name__)

    def _auto_refresh_tokens(self):
        """Auto-refresh tokens for both platforms"""
        self.shopee.auto_refresh_token()
        self.lazada.auto_refresh_token()
        self.tiktok.auto_refresh_token()

    def _log(self, message: str, level: str = "info"):
        """Unified logging method"""
        if level.lower() == "info":
            self.logger.info(message)
            print(message)
        elif level.lower() == "error":
            self.logger.error(message)
            print(message)

    def show_menu(self):
        """Display main menu with detailed token status for all platforms"""
        self._log("\n" + "=" * 60)
        self._log("E-COMMERCE PLATFORM TOKEN STATUS:")
        self._log("=" * 60)

        self._log(self.shopee.get_detailed_token_status())
        self._log("-" * 40)
        self._log(self.lazada.get_detailed_token_status())
        self._log("-" * 40)
        self._log(self.tiktok.get_detailed_token_status())

        self._log("=" * 60)
        self._log("\nE-Commerce Integration Menu:")
        self._log("1. Token Management")
        self._log("2. Shopee Operations")
        self._log("3. Lazada Operations")
        self._log("4. Tiktok Operations")
        self._log("5. Batch Operations")
        self._log("6. Exit")

    def show_batch_operations_menu(self):
        """Show batch operations menu"""
        self._log("\nBatch Operations:")
        self._log("1. Update Stock for All Platforms")
        self._log("2. Update Prices for All Platforms")
        self._log("3. Combine Qty by SKU")
        self._log("4. Back to Main Menu")

        choice = input("Enter your choice (1-4): ").strip()

        if choice == "1":
            self.exsport_before_update()
            self.process_batch_stock_updates()
        elif choice == "2":
            self.process_batch_price_updates()
        elif choice == "3":
            self.combine_qty_by_sku()
        elif choice != "4":
            self._log("Invalid choice")

    def exsport_before_update(self):
        """Combine quantity by SKU from summary sheets"""
        self._log("\n=== Combining Quantity by SKU ===")
        self.shopee.export_orders_and_bookings()
        time.sleep(2)
        self.lazada.export_orders_and_bookings()
        time.sleep(2)
        self.tiktok.export_orders_and_bookings()
        time.sleep(3)
        success = self.sheet_manager.combine_qty_by_sku()
        if success:
            self._log("✅ Data combined successfully!.")

    def combine_qty_by_sku(self):
        """Combine quantity by SKU from summary sheets"""
        self._log("\n=== Combining Quantity by SKU ===")
        self.shopee.export_orders_today()
        time.sleep(2)
        self.lazada.export_orders_today()
        time.sleep(2)
        self.tiktok.export_orders_today()
        time.sleep(3)
        success = self.sheet_manager.combine_qty_by_sku()

        sheets_to_hide = [
            "Shopee Orders",
            "Lazada Orders",
            "Tiktok Orders",
            "Shopee Summary",
            "Tiktok Summary",
            "Lazada Summary",
        ]

        self._log("\n--- Hiding Sheets ---")
        for sheet_name in sheets_to_hide:
            success = self.sheet_manager.hide_sheet(sheet_name)
            status = "✅" if success else "❌"
            self._log(f"{status} {sheet_name}")
        if success:
            self._log("\n✅ Data combined successfully! and sheets hidden!")

    def process_batch_stock_updates(self):
        """Process stock updates for all platforms"""
        self._log("\n=== BATCH STOCK UPDATE FOR ALL PLATFORMS ===")

        self._log("\n--- Processing Shopee Stock Updates ---")
        self.shopee.process_stock_updates()

        self._log("\n--- Processing Lazada Stock Updates ---")
        self.lazada.process_stock_updates()

        self._log("\n--- Processing Tiktok Stock Updates ---")
        self.tiktok.process_stock_updates()

        sheets_to_hide = [
            "Shopee Orders",
            "Lazada Orders",
            "Tiktok Orders",
            "Shopee Summary",
            "Tiktok Summary",
            "Lazada Summary",
        ]

        self._log("\n--- Hiding Sheets ---")
        for sheet_name in sheets_to_hide:
            success = self.sheet_manager.hide_sheet(sheet_name)
            status = "✅" if success else "❌"
            self._log(f"{status} {sheet_name}")

        self._log("\n✅ Batch stock update completed and sheets hidden!")

    def process_batch_price_updates(self):
        """Process price updates for all platforms - FIXED VERSION"""
        self._log("\n=== BATCH PRICE UPDATE FOR ALL PLATFORMS ===")

        results = {}

        try:
            self._log("\n--- Processing Shopee Price Updates ---")
            # For batch update, use regular price for Shopee
            shopee_result = self.shopee.process_price_updates_direct("regular")
            results["shopee"] = shopee_result

            self._log("\n--- Processing Lazada Price Updates ---")
            lazada_result = self.lazada.process_price_updates_direct()
            results["lazada"] = lazada_result

            self._log("\n--- Processing Tiktok Price Updates ---")
            tiktok_result = self.tiktok.process_price_updates_direct()
            results["tiktok"] = tiktok_result

            # Check if all operations were successful
            all_success = all(
                result.get(
                    "success",
                    False) if isinstance(
                    result,
                    dict) else False
                for result in results.values()
            )

            if all_success:
                self._log("\n✅ Batch price update completed for all platforms!")
                return {
                    "success": True,
                    "message": "Batch price update completed for all platforms!",
                    "results": results,
                }
            else:
                self._log("\n⚠️ Batch price update completed with some errors")
                return {
                    "success": False,
                    "message": "Batch price update completed with some errors",
                    "results": results,
                }

        except Exception as e:
            error_msg = f"❌ Error in batch price update: {str(e)}"
            self._log(error_msg)
            return {"success": False, "message": error_msg, "results": results}

    def show_token_management_menu(self):
        """Token management menu for all platforms"""
        self._log("\nToken Management:")
        self._log("1. Shopee Token Operations")
        self._log("2. Lazada Token Operations")
        self._log("3. Tiktok Token Operations")
        self._log("4. Back to Main Menu")

        choice = input("Enter your choice (1-4): ").strip()

        if choice == "1":
            self.shopee.show_token_menu()
        elif choice == "2":
            self.lazada.show_token_menu()
        elif choice == "3":
            self.tiktok.show_token_menu()
        elif choice != "4":
            self._log("Invalid choice")

    def show_shopee_operations_menu(self):
        """Shopee operations menu"""
        self.shopee.show_operations_menu()

    def show_lazada_operations_menu(self):
        """Lazada operations menu"""
        self.lazada.show_operations_menu()

    def show_tiktok_operations_menu(self):
        """Tiktok operations menu"""
        self.tiktok.show_operations_menu()

    def run(self):
        """Run the application"""
        while True:
            self.show_menu()
            choice = input("Enter your choice (1-6): ").strip()

            try:
                if choice == "1":
                    self.show_token_management_menu()
                elif choice == "2":
                    self.show_shopee_operations_menu()
                elif choice == "3":
                    self.show_lazada_operations_menu()
                elif choice == "4":
                    self.show_tiktok_operations_menu()
                elif choice == "5":
                    self.show_batch_operations_menu()
                elif choice == "6":
                    self._log("Exiting...")
                    break
                else:
                    self._log("Invalid choice. Please try again.")
            except Exception as e:
                self._log(f"🔥 Unexpected error: {str(e)}", "error")
