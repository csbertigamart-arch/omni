import json
import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime

import gspread
from api_clients import IAPIClient
from config_managers import IConfigManager
from file_system_manager import FileSystemManager
from lazop import LazopRequest
from order_managers import IOrderManager
from product_managers import IProductManager
from sheet_manager import ISheetManager
from wallet_manager import IWalletManager


class IPlatformHandler(ABC):
    """Base class for platform handlers with common functionality"""

    def __init__(
        self,
        config: IConfigManager,
        api: IAPIClient,
        product_manager: IProductManager,
        order_manager: IOrderManager,
        sheet_manager: ISheetManager,
        fs_manager: FileSystemManager,
        platform_name: str,
    ):
        self.config = config
        self.api = api
        self.product_manager = product_manager
        self.order_manager = order_manager
        self.sheet_manager = sheet_manager
        self.fs = fs_manager
        self.logger = logging.getLogger(__name__)
        self.platform_name = platform_name

    @abstractmethod
    def auto_refresh_token(self):
        """Auto-refresh platform token"""
        pass

    @abstractmethod
    def show_token_menu(self):
        """Show token management menu"""
        pass

    @abstractmethod
    def show_operations_menu(self):
        """Show platform operations menu"""
        pass

    def _log(self, message: str, level: str = "info"):
        """Unified logging method"""
        if level.lower() == "info":
            self.logger.info(message)
            print(message)
        elif level.lower() == "error":
            self.logger.error(message)
            print(f"❌ {message}")

    def get_detailed_token_status(self) -> str:
        """Get detailed token status with expiration info"""
        if self.config.is_token_expired():
            access_status = "❌ EXPIRED"
            if self.config.token_expiry:
                access_info = f"Expired since: {
                    self.config.token_expiry.strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                access_info = "No expiry information"
        else:
            access_status = "✅ VALID"
            if self.config.token_expiry:
                time_left = self.config.token_expiry - datetime.now()
                access_info = f"Expires in: {
                    time_left.days}d {
                    time_left.seconds //
                    3600}h {
                    (
                        time_left.seconds %
                        3600) //
                    60}m"
            else:
                access_info = "No expiry information"

        if self.config.is_refresh_token_expired():
            refresh_status = "❌ EXPIRED"
            if self.config.refresh_token_expiry:
                refresh_info = f"Expired since: {
                    self.config.refresh_token_expiry.strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                refresh_info = "No expiry information"
        elif not self.config.refresh_token:
            refresh_status = "❌ MISSING"
            refresh_info = "No refresh token available"
        else:
            refresh_status = "✅ VALID"
            if self.config.refresh_token_expiry:
                time_left = self.config.refresh_token_expiry - datetime.now()
                refresh_info = f"Expires in: {
                    time_left.days}d {
                    time_left.seconds //
                    3600}h {
                    (
                        time_left.seconds %
                        3600) //
                    60}m"
            else:
                refresh_info = "No expiry information"

        return (
            f"{self.platform_name} Token Status:\n"
            f"  Access Token: {access_status}\n"
            f"    {access_info}\n"
            f"  Refresh Token: {refresh_status}\n"
            f"    {refresh_info}"
        )

    def _get_or_create_worksheet(self, sheet_name: str):
        """Get or create worksheet with error handling"""
        try:
            return self.sheet_manager.sheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            try:
                return self.sheet_manager.sheet.add_worksheet(
                    sheet_name, rows=10000, cols=10
                )
            except Exception as e:
                if "already exists" in str(e):
                    return self.sheet_manager.sheet.worksheet(sheet_name)
                raise

    def _prepare_worksheet(self, worksheet, headers=None):
        """Prepare worksheet with headers"""
        worksheet.clear()
        default_headers = [
            "No. Pesanan",
            "SKU Seller",
            "Nama Produk",
            "Nama Variasi",
            "Qty",
            "Harga Jual",
            "Status Order",
        ]
        worksheet.append_row(headers or default_headers)

    def _log_result(self, processed: int, skipped: int,
                    failed: int, operation: str):
        """Log operation results"""
        result_msg = f"\n{operation} result: {processed} processed, {skipped} skipped, {failed} failed"
        self._log(result_msg)
        self.logger.info(
            f"{operation} completed: {processed} processed, {skipped} skipped, {failed} failed"
        )

    def _should_process_record(self, record):
        """Determine if record should be processed based on 'Cek' column"""
        if "Cek" not in record:
            return False

        cek_value = record["Cek"]
        if isinstance(cek_value, bool) and cek_value:
            return True
        return str(cek_value).strip().upper() in ["TRUE", "1", "YES", "Y", "X"]

    def _validate_basic_item(self, item: dict) -> bool:
        """Validate basic item from sheet"""
        if not item["item_id"] or not str(item["item_id"]).isdigit():
            self._update_item_status(item["row"], "FAILED: Invalid Product ID")
            return False
        return True

    def _get_product_info(self, item: dict) -> dict | None:
        """Get product info from API"""
        item_id = int(item["item_id"])
        model_id = (
            int(item["model_id"])
            if item["model_id"] and str(item["model_id"]).isdigit()
            else None
        )

        product_info = self.product_manager.get_product_details(
            item_id, model_id)
        if not product_info:
            self._update_item_status(item["row"], "FAILED: Product not found")
        return product_info

    def _log_product_info(self, item: dict, product_info: dict):
        """Log product information"""
        self._log(
            f"\nProcessing row {
                item['row']}: ID: {
                product_info['item_id']} - Model: {
                item.get(
                    'model_id', '')}"
        )
        self._log(f"Product: {product_info['full_name']}")

    def _handle_api_response(self, response: dict,
                             row: int, base_msg: str) -> str:
        """Handle API response and update status"""
        if response and not response.get("error"):
            if "success_list" in response.get("response", {}):
                if response["response"]["success_list"]:
                    self._update_item_status(
                        row=row, status="SUCCESS", log_msg=base_msg
                    )
                    return "processed"
                else:
                    failure_list = response["response"].get("failure_list", [])
                    reason = (
                        failure_list[0].get("failed_reason", "Unknown error")
                        if failure_list
                        else "No success or failure in response"
                    )
                    self._update_item_status(
                        row=row, status=f"FAILED: {reason}", log_msg=base_msg
                    )
                    return "failed"
            else:
                self._update_item_status(
                    row=row, status="SUCCESS", log_msg=base_msg)
                return "processed"
        else:
            error_msg = (
                response.get("message", "No response from API")
                if response
                else "No response from API"
            )
            self._update_item_status(
                row=row, status=f"FAILED: {error_msg}", log_msg=base_msg
            )
            return "failed"

    def _save_api_response(self, endpoint, payload, response):
        """Save API request/response to file for analysis (common for all platforms)"""
        try:
            log_dir = f"api_logs/{self.platform_name.lower()}"
            os.makedirs(log_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{log_dir}/{endpoint}_{timestamp}.json"

            serializable_response = response
            if hasattr(response, "body"):
                serializable_response = response.body
            elif not isinstance(
                response, (dict, list, str, int, float, bool, type(None))
            ):
                serializable_response = str(response)

            log_data = {
                "timestamp": str(datetime.now()),
                "endpoint": endpoint,
                "payload": payload,
                "response": serializable_response,
            }

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)

            self._log(f"✅ Saved API response to {filename}")
        except Exception as e:
            self._log(f"⚠️ Failed to save API log: {str(e)}")

    def _process_items(self, items: list,
                       process_type: str) -> tuple[int, int, int]:
        """Process items from sheet (stock/price)"""
        processed = skipped = failed = 0

        for item in items:
            try:
                if not self._validate_basic_item(item):
                    failed += 1
                    continue

                product_info = self._get_product_info(item)
                if not product_info:
                    failed += 1
                    continue

                self._log_product_info(item, product_info)

                if process_type == "stock":
                    result = self._process_stock_item(item, product_info)
                else:
                    result = self._process_price_item(item, product_info)

                if result == "processed":
                    processed += 1
                elif result == "skipped":
                    skipped += 1
                else:
                    failed += 1

            except Exception as e:
                self._update_item_status(item["row"], f"FAILED: {str(e)}")
                failed += 1

        return processed, skipped, failed

    def _process_stock_item(self, item: dict, product_info: dict) -> str:
        """Process stock update for a single item"""
        new_qty = int(item["new_qty"])
        current_qty = product_info["current_stock"]
        base_msg = f"Current Stock: {
            current_qty if current_qty is not None else 'N/A'}, New Stock: {new_qty}"

        if current_qty is not None and new_qty == current_qty:
            self._update_item_status(
                row=item["row"], status="SKIPPED", log_msg=base_msg
            )
            return "skipped"

        if new_qty < 0:
            self._update_item_status(
                row=item["row"],
                status="FAILED: Stock cannot be negative",
                log_msg=base_msg,
            )
            return "failed"

        if new_qty > self.MAX_STOCK:
            self._update_item_status(
                row=item["row"],
                status=f"FAILED: Stock exceeds maximum limit ({
                    self.MAX_STOCK})",
                log_msg=base_msg,
            )
            return "failed"

        if product_info["status"] != "NORMAL":
            self._update_item_status(
                row=item["row"],
                status=f"FAILED: Item status {product_info['status']}",
                log_msg=base_msg,
            )
            return "failed"

        model_id = int(item["model_id"]) if item["model_id"] else None
        response = self.product_manager.update_stock(
            product_info["item_id"], model_id, new_qty
        )

        return self._handle_api_response(
            response=response, row=item["row"], base_msg=base_msg
        )

    def _process_price_item(self, item: dict, product_info: dict) -> str:
        """Process price update for a single item"""
        try:
            new_price = float(item["new_price"])
        except ValueError:
            self._update_item_status(
                row=item["row"], status="FAILED: Invalid Price")
            return "failed"

        current_price = product_info.get("current_price")
        base_msg = f"Current Price: {
            current_price if current_price is not None else 'N/A'}, New Price: {new_price}"

        if (
            current_price is not None
            and abs(new_price - float(current_price)) < self.PRICE_TOLERANCE
        ):
            self._update_item_status(
                row=item["row"], status="SKIPPED", log_msg=base_msg
            )
            return "skipped"

        if new_price <= self.MIN_PRICE:
            self._update_item_status(
                item["row"], "FAILED: Price must be greater than 0", log_msg=base_msg
            )
            return "failed"

        if product_info["status"] != "NORMAL":
            self._update_item_status(
                item["row"],
                f"FAILED: Item status {product_info['status']}",
                log_msg=base_msg,
            )
            return "failed"

        model_id = int(item["model_id"]) if item["model_id"] else None
        response = self.product_manager.update_price(
            product_info["item_id"], model_id, new_price
        )

        return self._handle_api_response(
            response=response, row=item["row"], base_msg=base_msg
        )

    def _update_item_status(
        self,
        row: int,
        status: str,
        sheet_name: str = None,
        log_msg: str = None,
        include_status: bool = True,
    ):
        """Update item status and log"""
        try:
            if sheet_name is None:
                sheet_name = self.default_sheet_name

            if not isinstance(sheet_name, str) or len(sheet_name) > 50:
                sheet_name = self.default_sheet_name

            success = self.sheet_manager.update_status(
                row=row, status=status, sheet_name=sheet_name
            )

            if not success:
                print(
                    f"⚠️ Failed to update status for row {row} in sheet '{sheet_name}'"
                )

            if log_msg:
                full_msg = (
                    f"{log_msg} - Status: {status}" if include_status else log_msg
                )
                self._log(f">>> {full_msg}")
        except Exception as e:
            print(f"🔥 CRITICAL ERROR in _update_item_status: {str(e)}")
            import traceback

            traceback.print_exc()


class ShopeePlatformHandler(IPlatformHandler):
    MAX_STOCK = 99999
    MIN_PRICE = 1000
    PRICE_TOLERANCE = 50
    default_sheet_name = "Shopee Update"

    def __init__(self, config, api, product_manager, order_manager, wallet_manager, sheet_manager, fs_manager, google_sheets_manager=None):
        super().__init__(
            config,
            api,
            product_manager,
            order_manager,
            sheet_manager,
            fs_manager,
            "Shopee",
        )
        self.wallet_manager = wallet_manager
        self.google_sheets_manager = google_sheets_manager  # TAMBAH INI

    def auto_refresh_token(self):
        """Auto-refresh platform token if needed with detailed info"""
        if self.config.is_token_expired():
            if self.config.is_refresh_token_expired():
                self._log(
                    f"⚠️ {
                        self.platform_name} refresh token has expired. Please re-authenticate."
                )
                return False

            if not self.config.refresh_token:
                self._log(
                    f"⚠️ {
                        self.platform_name} no refresh token available"
                )
                return False

            try:
                if self.api.refresh_access_token():
                    expiry_time = self.config.token_expiry.strftime(
                        "%Y-%m-%d %H:%M:%S")
                    self._log(
                        f"🔃 {
                            self.platform_name} token refreshed successfully!"
                    )
                    self._log(f"   New expiry: {expiry_time}")
                    return True
                else:
                    self._log(
                        f"❌ Failed to refresh {
                            self.platform_name} token"
                    )
                    return False
            except Exception as e:
                self._log(
                    f"🔥 Error refreshing {
                        self.platform_name} token: {
                        str(e)}"
                )
                return False
        else:
            expiry_time = self.config.token_expiry.strftime(
                "%Y-%m-%d %H:%M:%S")
            self._log(
                f"✅ {
                    self.platform_name} token is valid until {expiry_time}"
            )
            return True

    def show_token_menu(self):
        """Show Shopee token management menu"""
        while True:
            self._log("\nShopee Token Management:")
            self._log("1. Update Authorization Code")
            self._log("2. Get Access Token")
            self._log("3. Back to Token Menu")

            choice = input("Enter your choice (1-3): ").strip()

            if choice == "1":
                new_code = input("Enter new Shopee authorization code: ")
                if self.config.update_code(new_code):
                    self._log("✅ Shopee code updated successfully!")
            elif choice == "2":
                if self.api.get_access_token():
                    self._log("✅ Shopee access token obtained successfully!")
            elif choice == "3":
                break
            else:
                self._log("Invalid choice")

    def show_operations_menu(self):
        """Show Shopee operations menu"""
        self._log("\nShopee Operations:")
        self._log("1. Export Orders")
        self._log("2. Update Stock")
        self._log("3. Update Prices")
        self._log("4. Check Shipping Fees")
        self._log("5. Wallet Transactions")
        self._log("6. Back to Main Menu")

        choice = input("Enter your choice (1-6): ").strip()

        if choice == "1":
            self.show_export_menu()
        elif choice == "2":
            success = self.export_orders_and_bookings()
            if success:
                time.sleep(1)
                self.process_stock_updates()
        elif choice == "3":
            self.process_price_updates()
        elif choice == "4":
            self.check_shipping_fee_difference()
        elif choice == "5":
            self.wallet_manager.show_wallet_transactions()
        elif choice != "6":
            self._log("Invalid choice")

    def show_export_menu(self):
        """Display Shopee export options with token verification"""
        if not self.config.access_token:
            self._log("\n🔐 No access token found. Please get access token first!")
            return

        self._log("\n📤 Export Shopee Orders to Google Sheet")
        self._log("1. Export UNPAID orders")
        self._log("2. Export READY_TO_SHIP orders")
        self._log("3. Export PROCESSED orders")
        self._log("4. Export COMPLETED orders")
        self._log("5. Export ALL orders (combined)")
        self._log("6. Back to Shopee menu")

        choice = input("Enter your choice (1-6): ").strip()

        status_mapping = {
            "1": "UNPAID",
            "2": "READY_TO_SHIP",
            "3": "PROCESSED",
            "4": "COMPLETED",
            "5": "ALL",
        }

        if choice in status_mapping:
            self._log(f"\n🔄 Processing {status_mapping[choice]} orders...")
            if choice == "5":
                self.export_orders_and_bookings()
            else:
                self.export_orders_by_type(status_mapping[choice], 7)
        elif choice != "6":
            self._log("❌ Invalid choice")

    def export_orders_by_type(self, order_type, days=7):
        """Export orders by specific type"""
        try:
            worksheet = self._get_or_create_worksheet("Shopee Orders")

            if order_type == "ALL":
                # Export all order types
                self._prepare_worksheet(worksheet)
                all_data = []

                order_types = [
                    "UNPAID",
                    "READY_TO_SHIP",
                    "PROCESSED",
                    "COMPLETED"]
                for order_type in order_types:
                    orders = self.order_manager.get_order_list(
                        order_type, days)
                    if orders:
                        order_sns = [order["order_sn"] for order in orders]
                        order_details = self.order_manager.get_order_details(
                            order_sns)
                        time.sleep(2)
                        if order_details:
                            formatted_data = self.order_manager.format_items_for_export(
                                order_details
                            )
                            all_data.extend(formatted_data)

                if all_data:
                    worksheet.append_rows(all_data)
                    self._log(
                        f"✅ Successfully exported {
                            len(all_data)} total orders"
                    )
                    return True
            else:
                # Export specific order type
                self._prepare_worksheet(worksheet)
                orders = self.order_manager.get_order_list(order_type, days)
                if not orders:
                    self._log(f"❌ No {order_type} orders found")
                    return False

                order_sns = [order["order_sn"] for order in orders]
                order_details = self.order_manager.get_order_details(order_sns)
                time.sleep(2)
                if not order_details:
                    self._log(f"❌ No details for {order_type} orders")
                    return False

                formatted_data = self.order_manager.format_items_for_export(
                    order_details
                )
                if not formatted_data:
                    return False

                worksheet.append_rows(formatted_data)
                unique_orders = len({row[0] for row in formatted_data})
                self._log(
                    f"✅ Successfully exported {unique_orders} {order_type} orders"
                )
                return True

        except Exception as e:
            self._log(
                f"\n🔥 Error exporting {order_type} orders: {
                    str(e)}",
                "error",
            )
            return False
        finally:
            self.sheet_manager.hide_sheet("Shopee Orders")

    def export_orders(
        self, days: int, status: str, is_first_batch: bool = True
    ) -> bool:
        """Export single status orders to sheet with accurate row counting"""
        try:
            worksheet = self._get_or_create_worksheet("Shopee Orders")

            if is_first_batch:
                worksheet.clear()
                self._prepare_worksheet(worksheet)

            orders = self.order_manager.get_order_list(status, days)
            if not orders:
                self._log(f"❌ No {status} orders found")
                return False

            order_sns = [order["order_sn"] for order in orders]
            order_details = self.order_manager.get_order_details(order_sns)
            time.sleep(2)
            if not order_details:
                self._log(f"❌ No details for {status} orders")
                return False

            formatted_data = self.order_manager.format_items_for_export(
                order_details)
            if not formatted_data:
                return False

            worksheet.append_rows(formatted_data)

            unique_orders = len({row[0] for row in formatted_data})

            self._log(
                f"✅ Successfully exported {unique_orders} {status} orders")
            return True

        except Exception as e:
            self._log(
                f"\n🔥 Error exporting {status} orders: {
                    str(e)}",
                "error",
            )
            return False
        finally:
            self.sheet_manager.hide_sheet("Shopee Orders")

    def export_orders_and_bookings(self) -> bool:
        """Export orders and bookings to sheet"""
        self._log("\n=== Exporting Shopee Orders and Bookings ===")

        try:
            worksheet = self._get_or_create_worksheet("Shopee Orders")
            self._prepare_worksheet(worksheet)

            all_data = []
            counts = {
                "UNPAID": 0,
                "READY_TO_SHIP_ORDERS": 0,
                "READY_TO_SHIP_BOOKINGS": 0,
            }

            unpaid_data = self._process_orders("UNPAID")
            counts["UNPAID"] = len(unpaid_data)
            all_data.extend(unpaid_data)

            ready_order_data = self._process_orders("READY_TO_SHIP")
            counts["READY_TO_SHIP_ORDERS"] = len(ready_order_data)
            all_data.extend(ready_order_data)

            booking_data = self._process_bookings("READY_TO_SHIP")
            counts["READY_TO_SHIP_BOOKINGS"] = len(booking_data)
            all_data.extend(booking_data)

            if all_data:
                worksheet.append_rows(all_data)
                return True

            self._log("⚠️ No data to export")
            return False

        except Exception as e:
            self._log(f"🔥 Error: {str(e)}")
            return False
        finally:
            self.sheet_manager.hide_sheet("Shopee Orders")

    def export_orders_today(self) -> bool:
        """Export orders and bookings to sheet"""
        self._log("\n=== Exporting Shopee Orders and Bookings ===")

        try:
            worksheet = self._get_or_create_worksheet("Shopee Orders")
            self._prepare_worksheet(worksheet)

            all_data = []
            counts = {
                "UNPAID": 0,
                "READY_TO_SHIP_ORDERS": 0,
                "PROCESSED_ORDERS": 0,
                "READY_TO_SHIP_BOOKINGS": 0,
            }

            unpaid_data = self._process_orders("UNPAID")
            counts["UNPAID"] = len(unpaid_data)
            all_data.extend(unpaid_data)

            ready_order_data = self._process_orders("READY_TO_SHIP")
            counts["READY_TO_SHIP_ORDERS"] = len(ready_order_data)
            all_data.extend(ready_order_data)

            processed_order_data = self._process_orders("PROCESSED")
            counts["PROCESSED_ORDERS"] = len(processed_order_data)
            all_data.extend(processed_order_data)

            booking_data = self._process_bookings("READY_TO_SHIP")
            counts["READY_TO_SHIP_BOOKINGS"] = len(booking_data)
            all_data.extend(booking_data)

            if all_data:
                worksheet.append_rows(all_data)
                return True

            self._log("⚠️ No data to export")
            return False

        except Exception as e:
            self._log(f"🔥 Error: {str(e)}")
            return False
        finally:
            self.sheet_manager.hide_sheet("Shopee Orders")

    def check_shipping_fee_difference(self):
        """Shipping fee checker"""
        self._log("\n=== Shipping Fee Difference Checker ===")
        self._log("1. Get Order Numbers & Process")
        self._log("2. Process Existing Order Numbers")
        self._log("3. Back to Main Menu")

        choice = input("Enter your choice (1-3): ").strip()

        if choice == "1":
            self._process_get_order_numbers()
        elif choice == "2":
            self._process_existing_order_numbers()
        elif choice == "3":
            return
        else:
            self._log("Invalid choice")

    def process_stock_updates(self):
        """Process stock updates from Google Sheet"""
        self._log("\n=== Processing Shopee Stock Updates ===")
        items = self._get_items_to_process("stock")

        if items:
            processed, skipped, failed = self._process_items(items, "stock")
            self._log_result(processed, skipped, failed, "Stock update")

    def _process_single_wholesale_item(self, item):
        """Process wholesale price for a single item with duplicate check and status display"""
        try:
            item_id = int(item["item_id"])
            if not item_id:
                status_msg = "FAILED: Invalid Product ID"
                self._update_item_status(item["row"], status_msg)
                self._log(f">>> Status: {status_msg}")
                return

            current_tiers = self._get_current_wholesale_tiers(item_id)
            new_tiers = item["wholesale_tiers"]

            if self._compare_wholesale_tiers(current_tiers, new_tiers):
                status_msg = "SKIPPED: Wholesale tiers unchanged"
                self._update_item_status(item["row"], status_msg)
                self._log(f">>> Status: {status_msg}")
                return

            product_info = self.product_manager.get_product_details(item_id)
            if not product_info:
                status_msg = "FAILED: Product not found"
                self._update_item_status(item["row"], status_msg)
                self._log(f">>> Status: {status_msg}")
                return

            self._log(f"\nProcessing row {item['row']}: ID: {item_id}")
            self._log(f"Product: {product_info['full_name']}")

            if product_info["status"] != "NORMAL":
                status_msg = f"FAILED: Item status {product_info['status']}"
                self._update_item_status(item["row"], status_msg)
                self._log(f">>> Status: {status_msg}")
                return

            if not new_tiers:
                status_msg = "FAILED: No wholesale tiers provided"
                self._update_item_status(item["row"], status_msg)
                self._log(f">>> Status: {status_msg}")
                return

            for tier in new_tiers:
                if not all(
                    key in tier for key in ["min_count", "unit_price", "max_count"]
                ):
                    status_msg = "FAILED: Invalid wholesale tier structure"
                    self._update_item_status(item["row"], status_msg)
                    self._log(f">>> Status: {status_msg}")
                    return

            response = self.product_manager.update_wholesale_price(
                item_id, new_tiers)

            if response and not response.get("error"):
                status_msg = "SUCCESS"
                self._update_item_status(item["row"], status_msg)
                self._log(f">>> Status: {status_msg}")
            else:
                error_msg = (
                    response.get("message", "No response from API")
                    if response
                    else "No response from API"
                )
                status_msg = f"FAILED: {error_msg}"
                self._update_item_status(item["row"], status_msg)
                self._log(f">>> Status: {status_msg}")

        except Exception as e:
            status_msg = f"FAILED: Unexpected error - {str(e)}"
            self._update_item_status(item["row"], status_msg)
            self._log(f">>> Status: {status_msg}")
            self.logger.exception(f"Error processing row {item['row']}")

    def _get_current_wholesale_tiers(self, item_id):
        """Get current wholesale tiers from API"""
        try:
            params = {"item_id": item_id}
            response = self.api.make_request(
                endpoint="/api/v2/product/get_item_base_info", params=params
            )

            if (
                response
                and "response" in response
                and "item_list" in response["response"]
            ):
                item_data = response["response"]["item_list"][0]
                return item_data.get("wholesale_tier_list", [])
        except Exception:
            pass
        return []

    def _compare_wholesale_tiers(self, current_tiers, new_tiers):
        """Compare if wholesale tiers are identical"""
        if len(current_tiers) != len(new_tiers):
            return False

        def normalize_tier(tier):
            return {
                "min_count": int(tier.get("min_count", 0)),
                "max_count": int(tier.get("max_count", 0)),
                "unit_price": float(tier.get("unit_price", 0)),
            }

        current_normalized = [normalize_tier(t) for t in current_tiers]
        new_normalized = [normalize_tier(t) for t in new_tiers]

        return current_normalized == new_normalized

    def _process_regular_price_updates(self):
        """Process regular price updates"""
        items = self._get_items_to_process("price")
        if items:
            processed, skipped, failed = self._process_items(items, "price")
            self._log_result(
                processed,
                skipped,
                failed,
                "Regular price update")

    def _process_get_order_numbers(self, month=None, year=None):
        """Option 1: Get order numbers from wallet transactions and process - FIXED VERSION"""
        try:
            if month is None or year is None:
                # Use current month/year if not provided
                now = datetime.now()
                month = month or now.month
                year = year or now.year

            transaction_type = "wallet_order_income"

            self._log(
                f"🔄 Getting wallet transactions for {month}/{year}, type: {transaction_type}"
            )

            # Get transactions from wallet
            raw_transactions = self.wallet_manager.get_transactions(
                month=month, year=year, transaction_tab_type=transaction_type
            )

            if not raw_transactions:
                self._log("❌ No transactions found for selected criteria")
                return False

            # Export order numbers to file
            filename, count = self.wallet_manager.export_order_numbers_to_file(
                raw_transactions, month, year
            )

            self._log(f"✅ Saved {count} order numbers to {filename}")

            # LANGSUNG PROSES FILE SETELAH DIAMBIL
            self._log("🔄 Automatically processing the extracted order numbers...")
            return self._process_order_numbers_file(filename, month, year)

        except Exception as e:
            self._log(
                f"❌ Error in _process_get_order_numbers: {
                    str(e)}",
                "error",
            )
            import traceback

            traceback.print_exc()
            return False

    def _process_order_numbers_file(self, input_file, month, year):
        """Process order numbers from file and generate report - FIXED"""
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                order_sn_list = [line.strip() for line in f if line.strip()]

            if not order_sn_list:
                self._log("No order numbers found in file")
                return False

            output_file = self.fs.get_full_path(
                "report", f"Selisih_Ongkir_Shopee_{month:02d}_{year}.csv"
            )

            self._log(f"\nProcessing {len(order_sn_list)} orders...")
            self._log(f"Output will be saved to: {output_file}")

            results = self.order_manager.process_shipping_fee_difference(
                order_sn_list, output_file=output_file
            )

            if results:
                self._display_shipping_fee_summary(results)
                self._log(f"\n✅ Final results saved to {output_file}")
                return True
            else:
                self._log("❌ No results generated")
                return False

        except Exception as e:
            self._log(f"Error processing file: {str(e)}", "error")
            return False

    def _display_shipping_fee_summary(self, results: list):
        """Display summary of shipping fee differences"""
        if not results:
            self._log("No results to display")
            return

        self._log("\nShipping Fee Difference Summary:")
        self._log("-" * 110)
        self._log(
            f"{
                'Create Time':<20} {
                'Order SN':<20} {
                'Buyer Paid':>12} {
                'Actual':>12} {
                    'Shopee Rebate':>14} {
                        'Difference':>12} {
                            'Shipping Carrier':<30}"
        )
        self._log("-" * 110)

        total_difference = 0
        for result in results:
            self._log(
                f"{result.get('Create Time', ''):<20} "
                f"{result.get('Order SN', ''):<20} "
                f"{result.get('Buyer Paid', 0):>12.2f} "
                f"{result.get('Actual', 0):>12.2f} "
                f"{result.get('Shopee Rebate', 0):>14.2f} "
                f"{result.get('Difference', 0):>12.2f} "
                f"{result.get('Shipping Carrier', ''):<30}"
            )
            total_difference += result.get("Difference", 0)

        self._log("-" * 110)
        self._log(f"{'TOTAL DIFFERENCE':<72} {total_difference:>12.2f}")
        self._log("-" * 110)

    def _process_orders(self, status: str) -> list:
        """Process orders of specific status"""
        self._log(f"\n🔍 Processing {status} orders...")
        orders = self.order_manager.get_order_list(status, 7)

        if not orders:
            self._log(f"No {status} orders found")
            return []

        order_sns = [order["order_sn"] for order in orders]
        order_details = self.order_manager.get_order_details(order_sns)

        if not order_details:
            self._log(f"No details for {status} orders")
            return []

        print(f"📊 Found {len(orders)} {status} orders")
        formatted_orders = self.order_manager.format_items_for_export(
            order_details)

        return formatted_orders

    def _get_items_to_process(self, process_type: str) -> list:
        config_map = {
            "stock": {
                "type": "stock",
                "id_column": "Kode Produk",
                "model_id_column": "Kode Variasi",
                "value_column": "Stok",
                "check_column": "Cek",
            },
            "price": {
                "type": "price",
                "id_column": "Kode Produk",
                "model_id_column": "Kode Variasi",
                "value_column": "Harga",
                "check_column": "Cek",
            },
            "wholesale": {
                "type": "wholesale",
                "id_column": "Kode Produk",
                "check_column": "Cek",
                "tiers": [
                    {"min": "Min_Order1",
                     "price": "Price_Order1",
                     "max": "Max_Order1"},
                    {"min": "Min_Order2",
                     "price": "Price_Order2",
                     "max": "Max_Order2"},
                    {"min": "Min_Order3",
                     "price": "Price_Order3",
                     "max": "Max_Order3"},
                ],
            },
            "wholesale_delete": {
                "type": "wholesale_delete",
                "id_column": "Kode Produk",
                "check_column": "Cek",
            },
        }

        if process_type not in config_map:
            return []

        return self.sheet_manager.get_data(
            "Shopee Update", config_map[process_type])

    def _process_bookings(self, status: str) -> list:
        """Process bookings with detailed validation and enhanced logging"""
        self._log(f"\n🔍 Processing {status} bookings...")
        try:
            bookings = self.order_manager.get_booking_list(status, 7)
            self._log(
                f"📊 Found {
                    len(bookings)} {status} bookings in initial response"
            )

            if not bookings:
                self._log(f"No {status} bookings found")
                return []

            booking_sns = [b["booking_sn"] for b in bookings]

            booking_details = self.order_manager.get_booking_detail(
                booking_sns)

            if not booking_details:
                self._log(f"❌ No details for {status} bookings")
                return []

            valid_bookings = []
            for b in booking_details:
                if b.get("booking_status") == status:
                    valid_bookings.append(b)
                else:
                    self._log(
                        f"⚠️ Booking SN {
                            b.get('booking_sn')} has status {
                            b.get('booking_status')} (expected {status})"
                    )

            if len(valid_bookings) != len(booking_details):
                self._log(
                    f"⚠️ Filtered {
                        len(booking_details) -
                        len(valid_bookings)} invalid bookings"
                )

            formatted_bookings = self.order_manager.format_bookings_for_export(
                valid_bookings
            )

            return formatted_bookings

        except Exception as e:
            self._log(f"🔥 Error processing bookings: {str(e)}", "error")
            import traceback

            self._log(traceback.format_exc(), "debug")
            return []

    def process_price_updates(self):
        """Process price updates from Google Sheet with wholesale option"""
        self._log("\n=== Processing Price Updates from Google Sheet ===")
        self._log("1. Update Regular Price")
        self._log("2. Update Wholesale Price")
        self._log("3. Delete Wholesale Tiers")
        self._log("4. Back to Main Menu")

        choice = input("Enter your choice (1-4): ").strip()

        if choice == "1":
            self._process_regular_price_updates()
        elif choice == "2":
            self.process_delete_wholesale()
            regular_result = self._process_regular_price_updates_for_wholesale()
            if regular_result["processed"] > 0 or regular_result["skipped"] > 0:
                processed_item_ids = set()
                wholesale_items = self._get_items_to_process("wholesale")
                for item in wholesale_items:
                    item_id = int(item["item_id"])
                    if item_id in processed_item_ids:
                        self._update_item_status(
                            item["row"], "SKIPPED: Duplicate item ID"
                        )
                        continue
                    processed_item_ids.add(item_id)
                    self._process_single_wholesale_item(item)
        elif choice == "3":
            self.process_delete_wholesale()
        elif choice == "4":
            return
        else:
            self._log("Invalid choice")

    def process_delete_wholesale(self):
        """Process wholesale deletion from Google Sheet"""
        self._log("\n=== Processing Wholesale Deletion ===")
        items = self._get_items_to_process("wholesale_delete")
        if not items:
            self._log("No items marked for wholesale deletion")
            return

        processed = skipped = failed = 0
        processed_item_ids = set()

        for item in items:
            try:
                item_id = int(item["item_id"])

                if item_id in processed_item_ids:
                    self._update_item_status(
                        item["row"], "SKIPPED: Duplicate item ID")
                    skipped += 1
                    continue

                processed_item_ids.add(item_id)

                product_info = self.product_manager.get_product_details(
                    item_id)
                if not product_info:
                    self._update_item_status(
                        item["row"], "FAILED: Product not found")
                    failed += 1
                    continue

                self._log(f"\nProcessing row {item['row']}: ID: {item_id}")
                self._log(f"Product: {product_info['full_name']}")

                response = self.product_manager.delete_wholesale_tiers(item_id)

                if response and not response.get("error"):
                    self._update_item_status(item["row"], "SUCCESS")
                    processed += 1
                else:
                    error_msg = (
                        response.get("message", "No response from API")
                        if response
                        else "No response from API"
                    )
                    self._update_item_status(
                        item["row"], f"FAILED: {error_msg}")
                    failed += 1

            except Exception as e:
                self._update_item_status(item["row"], f"FAILED: {str(e)}")
                failed += 1

        self._log_result(processed, skipped, failed, "Wholesale deletion")

    def show_shipping_file_list(self):
        """Display list of available shipping files for processing - FIXED VERSION"""
        try:
            temp_dir = self.fs.get_full_path("temp_file")
            files = [
                f
                for f in os.listdir(temp_dir)
                if f.startswith("order_numbers_") and f.endswith(".txt")
            ]

            if not files:
                self._log("❌ No order number files found in temp_file directory")
                return False

            self._log("\n📁 Available order number files:")
            self._log("-" * 50)

            file_info = []
            for i, filename in enumerate(files, 1):
                file_path = os.path.join(temp_dir, filename)
                stats = os.stat(file_path)
                file_size = stats.st_size
                modified_time = datetime.fromtimestamp(stats.st_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                # Extract month and year from filename
                parts = filename.split("_")
                if len(parts) >= 4:
                    month = parts[2]
                    year = parts[3].split(".")[0]
                    description = f"Orders from {month}/{year}"
                else:
                    description = "Unknown date"

                self._log(f"{i}. {filename}")
                self._log(
                    f"   📊 {description} | Size: {file_size} bytes | Modified: {modified_time}"
                )

                file_info.append(
                    {
                        "filename": filename,
                        "description": description,
                        "size": file_size,
                        "modified": modified_time,
                    }
                )

            self._log("-" * 50)

            # Return file list untuk web interface
            return file_info

        except Exception as e:
            self._log(f"❌ Error listing shipping files: {str(e)}")
            return False

    def _process_selected_shipping_file(self, filename):
        """Process the selected shipping file - FIXED VERSION"""
        try:
            temp_dir = self.fs.get_full_path("temp_file")
            file_path = os.path.join(temp_dir, filename)

            if not os.path.exists(file_path):
                self._log(f"❌ File {filename} not found")
                return False

            # Extract month and year from filename
            parts = filename.split("_")
            if len(parts) >= 4:
                month = int(parts[2])
                year = int(parts[3].split(".")[0])

                self._log(f"🔄 Processing file: {filename}")
                self._log(f"📅 Month: {month}, Year: {year}")

                result = self._process_order_numbers_file(
                    file_path, month, year)

                if result:
                    self._log(
                        "✅ Shipping fee processing completed successfully!")
                    return True
                else:
                    self._log("❌ Failed to process shipping file")
                    return False
            else:
                self._log("❌ Invalid filename format")
                return False

        except Exception as e:
            self._log(f"❌ Error processing shipping file: {str(e)}")
            return False

    def _process_existing_order_numbers(self):
        """Option 2: Process existing order number files - FIXED VERSION"""
        try:
            self._log("\n🔄 Processing existing order number files...")

            # Get list of files
            file_info = self.show_shipping_file_list()

            if not file_info:
                return False

            # In web version, return the file list for selection
            # The actual processing will be handled by the API endpoint
            return file_info

        except Exception as e:
            self._log(f"❌ Error in _process_existing_order_numbers: {str(e)}")
            return False

    def _process_wholesale_updates(self):
        """Process wholesale updates dengan logging yang lebih baik"""
        items = self._get_items_to_process("wholesale")
        if not items:
            self._log("❌ No items marked for wholesale processing")
            return {"processed": 0, "skipped": 0, "failed": 0}

        processed = skipped = failed = 0
        processed_item_ids = set()

        for item in items:
            try:
                item_id = int(item["item_id"])

                if item_id in processed_item_ids:
                    self._update_item_status(
                        item["row"], "SKIPPED: Duplicate item ID")
                    skipped += 1
                    continue

                processed_item_ids.add(item_id)

                # Get product info
                product_info = self._get_product_info(item)
                if not product_info:
                    failed += 1
                    continue

                self._log_product_info(item, product_info)

                # Check product status
                if product_info["status"] != "NORMAL":
                    status_msg = f"FAILED: Item status {
                        product_info['status']}"
                    self._update_item_status(item["row"], status_msg)
                    failed += 1
                    continue

                # Validate wholesale tiers
                if not item.get("wholesale_tiers"):
                    self._update_item_status(
                        item["row"], "FAILED: No wholesale tiers provided"
                    )
                    failed += 1
                    continue

                # Check for duplicate tiers
                current_tiers = self._get_current_wholesale_tiers(item_id)
                if self._compare_wholesale_tiers(
                    current_tiers, item["wholesale_tiers"]
                ):
                    self._update_item_status(
                        item["row"], "SKIPPED: Wholesale tiers unchanged"
                    )
                    skipped += 1
                    continue

                # Update wholesale price
                response = self.product_manager.update_wholesale_price(
                    item_id, item["wholesale_tiers"]
                )

                if response and not response.get("error"):
                    self._update_item_status(item["row"], "SUCCESS")
                    processed += 1
                    self._log(
                        f"✅ Successfully updated wholesale price for item {item_id}"
                    )
                else:
                    error_msg = (
                        response.get("message", "No response from API")
                        if response
                        else "No response from API"
                    )
                    status_msg = f"FAILED: {error_msg}"
                    self._update_item_status(item["row"], status_msg)
                    failed += 1
                    self._log(
                        f"❌ Failed to update wholesale price for item {item_id}: {error_msg}"
                    )

            except Exception as e:
                error_msg = f"FAILED: {str(e)}"
                self._update_item_status(item["row"], error_msg)
                failed += 1
                self._log(
                    f"❌ Error processing wholesale for row {
                        item['row']}: {
                        str(e)}"
                )

        self._log_result(processed, skipped, failed, "Wholesale price update")
        return {"processed": processed, "skipped": skipped, "failed": failed}

    def _process_regular_price_updates_for_wholesale(self):
        """Process regular price updates dengan logging yang lebih baik"""
        items = self._get_items_to_process("price")
        if not items:
            self._log("❌ No items marked for regular price processing")
            return {"processed": 0, "skipped": 0, "failed": 0}

        processed, skipped, failed = self._process_items(items, "price")
        self._log_result(processed, skipped, failed, "Regular price update")
        return {"processed": processed, "skipped": skipped, "failed": failed}

    def process_shipping_fee_difference(self, option, month=None, year=None):
        """Process shipping fee difference based on option"""
        try:
            if option == 1:
                self._log(
                    f"Processing shipping fee difference from wallet - {month}/{year}"
                )
                return self._process_get_order_numbers(month, year)
            elif option == 2:
                self._log("Processing existing order number files")
                return self._process_existing_order_numbers()
            return True
        except Exception as e:
            self._log(
                f"Error processing shipping fee difference: {
                    str(e)}",
                "error",
            )
            return False

    def process_price_updates_direct(self, price_type="regular"):
        """Process price updates directly without submenu"""
        try:
            self._log(
                f"\n=== Processing Shopee {
                    price_type.capitalize()} Price Updates ==="
            )

            if price_type == "regular":
                result = self._process_regular_price_updates_for_wholesale()
                return result
            elif price_type == "wholesale":
                # First delete existing wholesale tiers
                delete_result = self.process_delete_wholesale()

                # Then update regular prices
                regular_result = self._process_regular_price_updates_for_wholesale()

                # Finally process wholesale tiers
                wholesale_result = self._process_wholesale_updates()
                return {
                    "regular": regular_result,
                    "wholesale": wholesale_result,
                    "delete": delete_result,
                }
            elif price_type == "delete_wholesale":
                result = self.process_delete_wholesale()
                return result
            else:
                self._log(f"❌ Unknown price type: {price_type}")
                return {
                    "success": False,
                    "message": f"Unknown price type: {price_type}",
                }
        except Exception as e:
            error_msg = f"❌ Error in process_price_updates_direct: {str(e)}"
            self._log(error_msg)
            return {"success": False, "message": error_msg}

    def process_wallet_to_sheets(self, month=None, year=None, transaction_type=None):
        """Process wallet transactions and export directly to Google Sheets - OPTIMIZED VERSION"""
        try:
            print(f"🔄 [SHOPEE] Starting optimized wallet export process")

            # 1. Validasi Google Sheets Manager
            if not hasattr(self, 'google_sheets_manager') or not self.google_sheets_manager:
                print("❌ [SHOPEE] Google Sheets Manager not available")
                return False

            if not self.google_sheets_manager.is_authenticated():
                print("❌ [SHOPEE] Google Sheets not authenticated")
                return False

            # 2. Dapatkan wallet spreadsheet ID dari settings
            wallet_spreadsheet_id = self.google_sheets_manager.settings.get(
                "wallet_spreadsheet_id")
            if not wallet_spreadsheet_id:
                print("❌ [SHOPEE] Wallet spreadsheet not configured")
                return False

            print(f"📊 [SHOPEE] Using spreadsheet: {wallet_spreadsheet_id}")

            # 3. Dapatkan transactions dari wallet
            print("🔍 [SHOPEE] Fetching wallet transactions...")
            raw_transactions = self.wallet_manager.get_transactions(
                month=month, year=year, transaction_tab_type=transaction_type
            )

            if not raw_transactions:
                print("❌ [SHOPEE] No transactions found")
                return False

            print(f"📄 [SHOPEE] Found {len(raw_transactions)} raw transactions")

            # 4. Process transactions
            processed_data = self.wallet_manager.process_transactions(
                raw_transactions)
            if not processed_data or not processed_data.get("transactions"):
                print("❌ [SHOPEE] No processed data available")
                return False

            print(
                f"📊 [SHOPEE] Processed {len(processed_data['transactions'])} transactions")

            # 5. Generate safe sheet name
            safe_sheet_name = self._generate_wallet_sheet_name(
                month, year, transaction_type)
            print(f"📝 [SHOPEE] Using sheet name: {safe_sheet_name}")

            # 6. Export ke Google Sheets
            success = self.google_sheets_manager.upload_to_sheet(
                spreadsheet_id=wallet_spreadsheet_id,
                sheet_name=safe_sheet_name,
                data=self._prepare_wallet_data_for_sheets(processed_data)
            )

            if success:
                print(f"✅ [SHOPEE] Successfully exported to Google Sheets")
                return True
            else:
                print("❌ [SHOPEE] Failed to export to Google Sheets")
                return False

        except Exception as e:
            print(f"❌ [SHOPEE] Error in wallet export: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _generate_wallet_sheet_name(self, month, year, transaction_type):
        """Generate safe sheet name for wallet export"""
        import re
        from datetime import datetime

        # Default values jika tidak ada
        if not month:
            month = datetime.now().month
        if not year:
            year = datetime.now().year

        # Clean transaction type untuk nama sheet
        clean_type = "all"
        if transaction_type:
            clean_type = re.sub(r'[^a-zA-Z0-9]', '_', transaction_type).lower()

        base_name = f"Wallet_{month:02d}_{year}_{clean_type}"

        # Clean untuk Google Sheets requirements (max 31 chars, no special chars)
        safe_name = re.sub(r'[^\w\s-]', '', base_name)
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        safe_name = safe_name.strip('_')

        return safe_name[:31]  # Google Sheets limit

    def _prepare_wallet_data_for_sheets(self, processed_data):
        """Prepare wallet data for Google Sheets format"""
        headers = ["Date", "Order SN", "Description", "Amount",
                   "Status", "Transaction Type", "Tab Type", "Buyer Name"]
        data = [headers]

        for tx in processed_data["transactions"]:
            row = [
                tx["Date"].strftime("%Y-%m-%d %H:%M"),
                tx["Order SN"],
                tx["Description"],
                tx["Amount"],
                tx["Status"],
                tx["Transaction Type"],
                tx["Tab Type"],
                tx["Buyer Name"]
            ]
            data.append(row)

        return data

    def process_shipping_fee_to_sheets(self, option, month=None, year=None):
        """Process shipping fee difference and export directly to Google Sheets - FIXED VERSION"""
        try:
            self._log(
                f"🔄 Starting process_shipping_fee_to_sheets: option={option}, {month}/{year}")

            if not hasattr(self, 'google_sheets_manager') or not self.google_sheets_manager:
                self._log(
                    "❌ Google Sheets Manager not available in ShopeePlatformHandler")
                return False

            # Get shipping configuration from settings
            shipping_spreadsheet_id = self.google_sheets_manager.settings.get(
                "shipping_spreadsheet_id")
            if not shipping_spreadsheet_id:
                self._log(
                    "❌ Shipping spreadsheet not configured in Google Sheets settings")
                return False

            results = []

            if option == 1:
                self._log(
                    f"🔄 Processing shipping fee from wallet - {month}/{year}")

                # Get order numbers from wallet
                transaction_type = "wallet_order_income"
                raw_transactions = self.wallet_manager.get_transactions(
                    month=month, year=year, transaction_tab_type=transaction_type
                )

                if not raw_transactions:
                    self._log("❌ No transactions found for selected criteria")
                    return False

                self._log(
                    f"📊 Retrieved {len(raw_transactions)} raw transactions from wallet")

                # Export order numbers to file
                filename, count = self.wallet_manager.export_order_numbers_to_file(
                    raw_transactions, month, year
                )

                if not filename or count == 0:
                    self._log("❌ Failed to export order numbers to file")
                    return False

                self._log(f"✅ Exported {count} order numbers to {filename}")

                # Read the file
                import os
                if not os.path.exists(filename):
                    self._log(f"❌ File {filename} does not exist")
                    return False

                with open(filename, "r", encoding="utf-8") as f:
                    file_content = f.read().strip()
                    order_sn_list = [
                        line.strip() for line in file_content.split('\n') if line.strip()]

                self._log(
                    f"📖 Read file: {len(order_sn_list)} order numbers from file")

                if not order_sn_list:
                    self._log(
                        "❌ No order numbers found in the file after reading")
                    return False

                self._log(
                    f"🔄 Processing {len(order_sn_list)} orders for shipping fee calculation")

                # Process shipping fee difference - TANPA output file lokal
                results = self.order_manager.process_shipping_fee_difference(
                    order_sn_list, output_file=None  # Tidak pakai file lokal
                )

                self._log(
                    f"📊 Shipping fee processing completed: {len(results)} results")

            elif option == 2:
                self._log(
                    "🔄 Processing existing order number files for Google Sheets")
                # Implementasi untuk file yang sudah ada bisa ditambahkan di sini
                return False
            else:
                self._log("❌ Invalid option")
                return False

            # Export to Google Sheets
            if results:
                self._log(
                    f"📤 Exporting {len(results)} results to Google Sheets...")

                # Buat nama sheet yang lebih baik
                import datetime
                current_date = datetime.datetime.now().strftime("%Y%m%d")
                sheet_name = f"Shipping_{month:02d}_{year}_{current_date}"

                success = self.order_manager.export_shipping_fee_to_google_sheets(
                    results=results,
                    spreadsheet_id=shipping_spreadsheet_id,
                    sheet_name=sheet_name,
                    google_sheets_manager=self.google_sheets_manager
                )

                if success:
                    self._log(
                        f"✅ Successfully exported {len(results)} shipping fee records to Google Sheets")
                    # Hapus file temporary setelah berhasil export ke Google Sheets
                    try:
                        if 'filename' in locals():
                            os.remove(filename)
                            self._log(
                                f"🧹 Temporary file {filename} cleaned up")
                    except Exception as e:
                        self._log(
                            f"⚠️ Failed to clean up temporary file: {str(e)}")
                else:
                    self._log(
                        "❌ Failed to export shipping fee to Google Sheets")

                return success
            else:
                self._log("❌ No shipping fee results to export")
                return False

        except Exception as e:
            self._log(f"❌ Error in process_shipping_fee_to_sheets: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def process_shipping_fee_difference(self, option, month=None, year=None):
        """Process shipping fee difference based on option"""
        try:
            if option == 1:
                self._log(
                    f"Processing shipping fee difference from wallet - {month}/{year}"
                )
                return self._process_get_order_numbers(month, year)
            elif option == 2:
                self._log("Processing existing order number files")
                return self._process_existing_order_numbers()
            return True
        except Exception as e:
            self._log(
                f"Error processing shipping fee difference: {
                    str(e)}",
                "error",
            )
            return False


class LazadaPlatformHandler(IPlatformHandler):
    MAX_STOCK = 99999
    MIN_PRICE = 1000
    PRICE_TOLERANCE = 50
    default_sheet_name = "Lazada Update"

    def __init__(
        self,
        config: IConfigManager,
        api: IAPIClient,
        product_manager: IProductManager,
        order_manager: IOrderManager,
        sheet_manager: ISheetManager,
        fs_manager: FileSystemManager,
    ):
        super().__init__(
            config,
            api,
            product_manager,
            order_manager,
            sheet_manager,
            fs_manager,
            "Lazada",
        )

    def auto_refresh_token(self):
        """Auto-refresh platform token if needed with detailed info"""
        if self.config.is_token_expired():
            if self.config.is_refresh_token_expired():
                self._log(
                    f"⚠️ {
                        self.platform_name} refresh token has expired. Please re-authenticate."
                )
                return False

            if not self.config.refresh_token:
                self._log(
                    f"⚠️ {
                        self.platform_name} no refresh token available"
                )
                return False

            try:
                if self.api.refresh_access_token():
                    expiry_time = self.config.token_expiry.strftime(
                        "%Y-%m-%d %H:%M:%S")
                    self._log(
                        f"🔃 {
                            self.platform_name} token refreshed successfully!"
                    )
                    self._log(f"   New expiry: {expiry_time}")
                    return True
                else:
                    self._log(
                        f"❌ Failed to refresh {
                            self.platform_name} token"
                    )
                    return False
            except Exception as e:
                self._log(
                    f"🔥 Error refreshing {
                        self.platform_name} token: {
                        str(e)}"
                )
                return False
        else:
            expiry_time = self.config.token_expiry.strftime(
                "%Y-%m-%d %H:%M:%S")
            self._log(
                f"✅ {
                    self.platform_name} token is valid until {expiry_time}"
            )
            return True

    def show_token_menu(self):
        """Show Lazada token management menu"""
        while True:
            self._log("\nLazada Token Management:")
            self._log("1. Update Authorization Code")
            self._log("2. Get Access Token")
            self._log("3. Back to Token Menu")

            choice = input("Enter your choice (1-3): ").strip()

            if choice == "1":
                new_code = input(
                    "Enter new Lazada authorization code: ").strip()
                if self.config.update_code(new_code):
                    self._log("✅ Lazada code updated successfully!")
            elif choice == "2":
                try:
                    self._log("🔄 Getting Lazada access token...")
                    if self.api.get_access_token():
                        self._log("\n✅ Lazada token obtained successfully!")
                        self._log(f"Access Token: {self.config.access_token}")
                        self._log(f"Expires: {self.config.token_expiry}")
                    else:
                        self._log("❌ Failed to get access token")
                except Exception as e:
                    self._log(f"🔥 Error: {str(e)}")
                    if hasattr(e, "response"):
                        self._log(f"API Response: {e.response.text}")
            elif choice == "3":
                break
            else:
                self._log("Invalid choice")

    def show_operations_menu(self):
        """Show Lazada operations menu"""
        self._log("\nLazada Operations:")
        self._log("1. Update Stock")
        self._log("2. Update Prices")
        self._log("3. Export Orders")
        self._log("4. Back to Main Menu")
        choice = input("Enter your choice (1-4): ").strip()

        if choice == "1":
            success = self.export_orders_and_bookings()
            if success:
                time.sleep(1)
            self.process_stock_updates()
        elif choice == "2":
            self.process_price_updates()
        elif choice == "3":
            self.show_export_menu()
        elif choice != "4":
            self._log("Invalid choice")

    def _get_order_items(self, order_id: str) -> list:
        """Get detailed items for a specific order"""
        try:
            request = LazopRequest("/order/items/get", "GET")
            request.add_api_param("order_id", order_id)

            response = self.api.client.execute(
                request, self.api.config.access_token)

            if response and "code" in response.body and response.body["code"] == "0":
                return response.body.get("data", [])
            return []

        except Exception as e:
            self._log(
                f"Error getting items for order {order_id}: {
                    str(e)}",
                "error",
            )
            return []

    def export_orders(self, status: str, days: int = 7) -> bool:
        """Export Lazada orders to Google Sheets with item details"""
        self._log(f"\n=== Exporting Lazada {status} Orders ===")

        try:
            if self.config.is_token_expired():
                if not self.config.is_refresh_token_expired():
                    self._log("🔃 Refreshing Lazada token...")
                    if not self.api.refresh_access_token():
                        self._log("❌ Failed to refresh Lazada token")
                        return False
                else:
                    self._log(
                        "❌ Lazada refresh token expired. Please re-authenticate."
                    )
                    return False

            worksheet = self._get_or_create_worksheet("Lazada Orders")
            self._prepare_worksheet(worksheet)

            orders = self.order_manager.get_order_list(status, days)
            if not orders:
                self._log(f"No {status} orders found")
                return False

            formatted_data = []
            for order in orders:
                order_id = order.get("order_id")
                if not order_id:
                    continue

                items = self._get_order_items(order_id)
                if not items:
                    self._log(f"No items found for order {order_id}")
                    continue

                order_id_str = str(order_id)

                for item in items:
                    formatted_data.append(
                        [
                            order_id_str,
                            item.get("sku", ""),
                            item.get("name", ""),
                            item.get("variation", ""),
                            int(item.get("quantity", 1)),
                            item.get("item_price", ""),
                            status.upper(),
                        ]
                    )

            if formatted_data:
                worksheet.append_rows(formatted_data)
                self._log(
                    f"✅ Successfully exported {
                        len(formatted_data)} order items"
                )
                return True

            return False

        except Exception as e:
            self._log(f"Error exporting Lazada orders: {str(e)}", "error")
            return False
        finally:
            self.sheet_manager.hide_sheet("Lazada Orders")

    def _process_updates(
        self, update_type: str, process_function: callable, operation_name: str
    ):
        """Common method to process updates (stock or price) with DRY principle"""
        self._log(f"\n=== Processing Lazada {operation_name} ===")
        try:
            if self.config.is_token_expired():
                if not self.config.is_refresh_token_expired():
                    self._log("🔃 Refreshing Lazada token...")
                    if not self.api.refresh_access_token():
                        self._log("❌ Failed to refresh Lazada token")
                        return
                else:
                    self._log(
                        "❌ Lazada refresh token expired. Please re-authenticate."
                    )
                    return

            items = self._get_items_to_process(update_type)
            self._log(f"Found {len(items)} items to process")

            if not items:
                self._log(
                    f"No items marked for {update_type} update in 'Lazada Update' sheet"
                )
                return

            processed = 0
            skipped = 0
            failed = 0

            for item in items:
                try:
                    if not item["item_id"] or not str(item["item_id"]).strip():
                        self._update_item_status(
                            row=item["row"],
                            status=f"FAILED: Invalid Product ID",
                            sheet_name="Lazada Update",
                        )
                        failed += 1
                        continue

                    sku_id = item.get("model_id", "")
                    if sku_id and not str(sku_id).strip():
                        self._update_item_status(
                            row=item["row"],
                            status="FAILED: Invalid SKU ID",
                            sheet_name="Lazada Update",
                        )
                        failed += 1
                        continue

                    product_info = self.product_manager.get_product_details(
                        item["item_id"], sku_id=sku_id
                    )
                    if not product_info:
                        self._update_item_status(
                            row=item["row"],
                            status="FAILED: Product not found",
                            sheet_name="Lazada Update",
                        )
                        failed += 1
                        continue

                    model_display = f" - Model: {sku_id}" if sku_id else ""
                    self._log(
                        f"\nProcessing row {
                            item['row']}: ID: {
                            item['item_id']}{model_display}"
                    )
                    self._log(f"Product: {product_info['full_name']}")

                    result = process_function(item, product_info)
                    if result == "processed":
                        processed += 1
                    elif result == "skipped":
                        skipped += 1
                    else:
                        failed += 1

                except Exception as e:
                    error_msg = f"FAILED: {str(e)}"
                    self._update_item_status(
                        row=item["row"], status=error_msg, sheet_name="Lazada Update"
                    )
                    failed += 1
                    self.logger.exception(
                        f"Error processing row {
                            item['row']}"
                    )

            self._log(
                f"\n{operation_name} result: {processed} processed, {skipped} skipped, {failed} failed"
            )

        except Exception as e:
            self._log(f"🔥 Error in {operation_name.lower()}: {str(e)}")
            import traceback

            traceback.print_exc()

    def process_stock_updates(self):
        """Process Lazada stock updates using common method"""
        self._process_updates(
            update_type="stock",
            process_function=self._process_stock_item,
            operation_name="Stock update",
        )

    def process_price_updates(self):
        """Process Lazada price updates using common method"""
        self._process_updates(
            update_type="price",
            process_function=self._process_price_item,
            operation_name="Price update",
        )

    def _get_items_to_process(self, process_type: str) -> list:
        config = {
            "id_column": "Product ID",
            "model_id_column": "SKU ID",
            "check_column": "Cek",
        }

        if process_type == "stock":
            return self.sheet_manager.get_data(
                "Lazada Update", {
                    **config, "type": "stock", "value_column": "Stok"}
            )
        elif process_type == "price":
            return self.sheet_manager.get_data(
                "Lazada Update", {
                    **config, "type": "price", "value_column": "Harga"}
            )
        return []

    def _process_stock_item(self, item: dict, product_info: dict) -> str:
        """Process stock update for a single item (PERBAIKAN)"""
        try:
            new_qty = int(item["new_qty"])
            current_qty = product_info["current_stock"]
            base_msg = f"Current Stock: {current_qty}, New Stock: {new_qty}"

            if new_qty == current_qty:
                status_msg = "SKIPPED: Stock unchanged"
                self._update_item_status(
                    row=item["row"],
                    status=status_msg,
                    sheet_name="Lazada Update",
                    log_msg=base_msg,
                )
                return "skipped"

            payload = [
                {
                    "ItemId": item["item_id"],
                    "SkuId": item.get("model_id", ""),
                    "Quantity": new_qty,
                }
            ]

            success, response = self.product_manager.update_stock(payload)
            if success:
                status_msg = "SUCCESS"
                self._update_item_status(
                    row=item["row"],
                    status=status_msg,
                    sheet_name="Lazada Update",
                    log_msg=base_msg,
                )
                return "processed"
            else:
                error_msg = (
                    response
                    if isinstance(response, str)
                    else response.get("message", "Unknown error")
                )
                status_msg = f"FAILED: {error_msg}"
                self._update_item_status(
                    row=item["row"],
                    status=status_msg,
                    sheet_name="Lazada Update",
                    log_msg=base_msg,
                )
                return "failed"

        except Exception as e:
            status_msg = f"FAILED: {str(e)}"
            self._update_item_status(
                row=item["row"], status=status_msg, sheet_name="Lazada Update"
            )
            return "failed"

    def _process_price_item(self, item: dict, product_info: dict) -> str:
        """Process price update for a single item (PERBAIKAN)"""
        try:
            new_price = float(item["new_price"])
            current_price = product_info["current_price"]
            base_msg = f"Current Price: {current_price}, New Price: {new_price}"

            if abs(new_price - current_price) < 0.01:
                status_msg = "SKIPPED: Price unchanged"
                self._update_item_status(
                    row=item["row"],
                    status=status_msg,
                    sheet_name="Lazada Update",
                    log_msg=base_msg,
                )
                return "skipped"

            payload = [
                {
                    "ItemId": item["item_id"],
                    "SkuId": item.get("model_id", ""),
                    "Price": new_price,
                }
            ]

            success, response = self.product_manager.update_price(payload)

            if success:
                status_msg = "SUCCESS"
                self._update_item_status(
                    row=item["row"],
                    status=status_msg,
                    sheet_name="Lazada Update",
                    log_msg=base_msg,
                )
                return "processed"
            else:
                error_msg = (
                    response
                    if isinstance(response, str)
                    else response.get("message", "Unknown error")
                )
                status_msg = f"FAILED: {error_msg}"
                self._update_item_status(
                    row=item["row"],
                    status=status_msg,
                    sheet_name="Lazada Update",
                    log_msg=base_msg,
                )
                return "failed"

        except Exception as e:
            status_msg = f"FAILED: {str(e)}"
            self._update_item_status(
                row=item["row"], status=status_msg, sheet_name="Lazada Update"
            )
            return "failed"

    def export_orders_today(self) -> bool:
        """Export Lazada orders for today - FIXED VERSION"""
        self._log("\n=== Exporting Lazada Orders Today ===")

        try:
            if self.config.is_token_expired():
                if not self.config.is_refresh_token_expired():
                    self._log("🔃 Refreshing Lazada token...")
                    if not self.api.refresh_access_token():
                        self._log("❌ Failed to refresh Lazada token")
                        return False
                else:
                    self._log(
                        "❌ Lazada refresh token expired. Please re-authenticate."
                    )
                    return False

            worksheet = self._get_or_create_worksheet("Lazada Orders")
            self._prepare_worksheet(worksheet)

            # Status untuk order hari ini
            statuses = [
                "unpaid",
                "pending",
                "ready_to_ship",
                "packed",
                "shipped",
                "delivered",
            ]
            all_data = []

            for status in statuses:
                self._log(f"\n🔍 Processing {status} orders...")
                orders = self.order_manager.get_order_list(
                    status, 1)  # Hanya 1 hari

                if not orders:
                    self._log(f"No {status} orders found")
                    continue

                self._log(f"Found {len(orders)} {status} orders")

                for order in orders:
                    order_id = order.get("order_id")
                    if not order_id:
                        continue

                    items = self._get_order_items(order_id)
                    if not items:
                        continue

                    for item in items:
                        formatted_data = [
                            str(order_id),
                            item.get("sku", ""),
                            item.get("name", ""),
                            item.get("variation", ""),
                            int(item.get("quantity", 1)),
                            item.get("item_price", ""),
                            status.upper(),
                        ]
                        all_data.append(formatted_data)

            if all_data:
                worksheet.append_rows(all_data)
                self._log(
                    f"✅ Successfully exported {
                        len(all_data)} order items"
                )
                return True

            self._log("⚠️ No data to export")
            return False

        except Exception as e:
            self._log(f"🔥 Error exporting orders: {str(e)}", "error")
            return False
        finally:
            self.sheet_manager.hide_sheet("Lazada Orders")

    def export_orders_by_type(self, export_type, days=7):
        """Export orders by specific type for Lazada"""
        try:
            worksheet = self._get_or_create_worksheet("Lazada Orders")

            if export_type == "ALL":
                # Export all order types combined
                self._prepare_worksheet(worksheet)
                all_data = []

                order_types = [
                    "unpaid",
                    "pending",
                    "ready_to_ship",
                    "packed",
                    "shipped",
                    "delivered",
                    "returned",
                    "failed",
                    "topack",
                    "toship",
                ]
                for order_type in order_types:
                    orders = self.order_manager.get_order_list(
                        order_type, days)
                    if orders:
                        for order in orders:
                            order_id = order.get("order_id")
                            if not order_id:
                                continue

                            items = self._get_order_items(order_id)
                            if not items:
                                continue

                            for item in items:
                                formatted_data = [
                                    str(order_id),
                                    item.get("sku", ""),
                                    item.get("name", ""),
                                    item.get("variation", ""),
                                    int(item.get("quantity", 1)),
                                    item.get("item_price", ""),
                                    order_type.upper(),
                                ]
                                all_data.append(formatted_data)

                if all_data:
                    worksheet.append_rows(all_data)
                    self._log(
                        f"✅ Successfully exported {
                            len(all_data)} total order items"
                    )
                    return True
            else:
                # Export specific order type
                self._prepare_worksheet(worksheet)
                orders = self.order_manager.get_order_list(export_type, days)
                if not orders:
                    self._log(f"❌ No {export_type} orders found")
                    return False

                all_data = []
                for order in orders:
                    order_id = order.get("order_id")
                    if not order_id:
                        continue

                    items = self._get_order_items(order_id)
                    if not items:
                        continue

                    for item in items:
                        formatted_data = [
                            str(order_id),
                            item.get("sku", ""),
                            item.get("name", ""),
                            item.get("variation", ""),
                            int(item.get("quantity", 1)),
                            item.get("item_price", ""),
                            export_type.upper(),
                        ]
                        all_data.append(formatted_data)

                if all_data:
                    worksheet.append_rows(all_data)
                    self._log(
                        f"✅ Successfully exported {
                            len(all_data)} {export_type} order items"
                    )
                    return True

            return False

        except Exception as e:
            self._log(
                f"🔥 Error exporting {export_type} orders: {
                    str(e)}",
                "error",
            )
            return False
        finally:
            self.sheet_manager.hide_sheet("Lazada Orders")

    def process_price_updates_direct(self):
        """Process Lazada price updates langsung tanpa sub-menu"""
        try:
            self._log("\n=== Processing Lazada Price Updates ===")

            # Gunakan method yang sudah ada
            result = self.process_price_updates()

            if result:
                self._log("✅ Lazada price update completed successfully")
                return {"success": True,
                        "message": "Lazada price updates completed"}
            else:
                self._log("❌ Lazada price update failed")
                return {"success": False,
                        "message": "Lazada price updates failed"}

        except Exception as e:
            error_msg = f"❌ Error in Lazada price update: {str(e)}"
            self._log(error_msg)
            return {"success": False, "message": error_msg}

    # Di class TiktokPlatformHandler - tambahkan method

    def process_price_updates_direct(self):
        """Process Lazada price updates directly without submenu"""
        try:
            self._log("\n=== Processing Lazada Price Updates ===")

            # Gunakan method yang sudah ada
            result = self.process_price_updates()

            if result:
                self._log("✅ Lazada price update completed successfully")
                return {"success": True,
                        "message": "Lazada price updates completed"}
            else:
                self._log("❌ Lazada price update failed")
                return {"success": False,
                        "message": "Lazada price updates failed"}

        except Exception as e:
            error_msg = f"❌ Error in Lazada price update: {str(e)}"
            self._log(error_msg)
            return {"success": False, "message": error_msg}

    def show_export_menu(self):
        """Display Lazada export options dengan status yang diinginkan"""
        self._log("\nLazada Export Orders:")
        self._log("1. Export UNPAID orders")
        self._log("2. Export PENDING orders")
        self._log("3. Export TOPACK orders")
        self._log("4. Export TOSHIP orders")
        self._log("5. Export ALL orders")
        self._log("6. Back to Lazada menu")

        choice = input("Enter your choice (1-6): ").strip()

        status_mapping = {
            "1": "unpaid",
            "2": "pending",
            "3": "topack",
            "4": "toship",
            "5": None,  # ALL
        }

        if choice in status_mapping:
            self._log(f"\n🔄 Processing {status_mapping[choice]} orders...")
            if choice == "5":
                self.export_orders_and_bookings()
            else:
                self.export_orders(days=7, status=status_mapping[choice])
        elif choice != "6":
            self._log("❌ Invalid choice")

    def export_orders_and_bookings(self) -> bool:
        """Export Lazada orders dari status yang diinginkan"""
        self._log("\n=== Exporting Lazada Orders ===")

        try:
            if self.config.is_token_expired():
                if not self.config.is_refresh_token_expired():
                    self._log("🔃 Refreshing Lazada token...")
                    if not self.api.refresh_access_token():
                        self._log("❌ Failed to refresh Lazada token")
                        return False
                else:
                    self._log(
                        "❌ Lazada refresh token expired. Please re-authenticate."
                    )
                    return False

            worksheet = self._get_or_create_worksheet("Lazada Orders")
            self._prepare_worksheet(worksheet)

            # Status yang diinginkan untuk Lazada
            statuses = ["unpaid", "pending", "topack", "toship"]
            all_data = []

            for status in statuses:
                self._log(f"\n🔍 Processing {status} orders...")
                orders = self.order_manager.get_order_list(status, 7)

                if not orders:
                    self._log(f"No {status} orders found")
                    continue

                self._log(f"Found {len(orders)} {status} orders")

                for order in orders:
                    order_id = order.get("order_id")
                    if not order_id:
                        continue

                    items = self._get_order_items(order_id)
                    if not items:
                        self._log(f"No items found for order {order_id}")
                        continue

                    for item in items:
                        formatted_data = [
                            str(order_id),
                            item.get("sku", ""),
                            item.get("name", ""),
                            item.get("variation", ""),
                            int(item.get("quantity", 1)),
                            item.get("item_price", ""),
                            status.upper(),
                        ]
                        all_data.append(formatted_data)

            if all_data:
                worksheet.append_rows(all_data)
                self._log(
                    f"✅ Successfully exported {
                        len(all_data)} order items")
                return True

            self._log("⚠️ No data to export")
            return False

        except Exception as e:
            self._log(f"🔥 Error exporting orders: {str(e)}", "error")
            return False
        finally:
            self.sheet_manager.hide_sheet("Lazada Orders")


class TiktokPlatformHandler(IPlatformHandler):
    MAX_STOCK = 99999
    MIN_PRICE = 1000
    PRICE_TOLERANCE = 50
    default_sheet_name = "Tiktok Update"

    def __init__(
        self,
        config: IConfigManager,
        api: IAPIClient,
        product_manager: IProductManager,
        order_manager: IOrderManager,
        sheet_manager: ISheetManager,
        fs_manager: FileSystemManager,
    ):
        super().__init__(
            config,
            api,
            product_manager,
            order_manager,
            sheet_manager,
            fs_manager,
            "Tiktok",
        )

    def auto_refresh_token(self):
        """Auto-refresh platform token if needed with detailed info"""
        if self.config.is_token_expired():
            if self.config.is_refresh_token_expired():
                self._log(
                    f"⚠️ {
                        self.platform_name} refresh token has expired. Please re-authenticate."
                )
                return False

            if not self.config.refresh_token:
                self._log(
                    f"⚠️ {
                        self.platform_name} no refresh token available"
                )
                return False

            try:
                if self.api.refresh_access_token():
                    expiry_time = self.config.token_expiry.strftime(
                        "%Y-%m-%d %H:%M:%S")
                    self._log(
                        f"🔃 {
                            self.platform_name} token refreshed successfully!"
                    )
                    self._log(f"   New expiry: {expiry_time}")
                    return True
                else:
                    self._log(
                        f"❌ Failed to refresh {
                            self.platform_name} token"
                    )
                    return False
            except Exception as e:
                self._log(
                    f"🔥 Error refreshing {
                        self.platform_name} token: {
                        str(e)}"
                )
                return False
        else:
            expiry_time = self.config.token_expiry.strftime(
                "%Y-%m-%d %H:%M:%S")
            self._log(
                f"✅ {
                    self.platform_name} token is valid until {expiry_time}"
            )
            return True

    def show_token_menu(self):
        """Show Tiktok token management menu"""
        while True:
            self._log("\nTiktok Token Management:")
            self._log("1. Update Authorization Code")
            self._log("2. Get Access Token")
            self._log("3. Back to Token Menu")

            choice = input("Enter your choice (1-3): ").strip()

            if choice == "1":
                new_code = input(
                    "Enter new Tiktok authorization code: ").strip()
                if self.config.update_code(new_code):
                    self._log("✅ Tiktok code updated successfully!")
            elif choice == "2":
                try:
                    self._log("🔄 Getting Tiktok access token...")
                    if self.api.get_access_token():
                        self._log("\n✅ Tiktok token obtained successfully!")
                        self._log(f"Access Token: {self.config.access_token}")
                        self._log(f"Expires: {self.config.token_expiry}")
                    else:
                        self._log("❌ Failed to get access token")
                except Exception as e:
                    self._log(f"🔥 Error: {str(e)}")
            elif choice == "3":
                break
            else:
                self._log("Invalid choice")

    def show_operations_menu(self):
        """Show Tiktok operations menu"""
        self._log("\nTiktok Operations:")
        self._log("1. Update Stock")
        self._log("2. Update Prices")
        self._log("3. Export Orders")
        self._log("4. Back to Main Menu")

        choice = input("Enter your choice (1-4): ").strip()

        if choice == "1":
            success = self.export_orders_and_bookings()
            if success:
                time.sleep(1)
                self.process_stock_updates()
        elif choice == "2":
            self.process_price_updates()
        elif choice == "3":
            self.show_export_menu()
        elif choice != "4":
            self._log("Invalid choice")

    def export_orders(self, status: str, days: int = 7) -> bool:
        """Export Tiktok orders to Google Sheets for a specific status"""
        self._log(f"\n=== Exporting Tiktok {status} Orders ===")
        return self._export_orders_by_statuses([status], days)

    def _process_orders(self, orders: list, default_status: str) -> list:
        """Process orders and format data for export"""
        formatted_data = []
        for order in orders:
            order_id = order.get("id", "")
            order_status = order.get("status", default_status)
            sku_details = {}

            for item in order.get("line_items", []):
                sku = item.get("seller_sku", "")
                qty = int(item.get("quantity", 1))
                original_price = item.get("original_price", "")

                if sku not in sku_details:
                    sku_details[sku] = {
                        "name": item.get("product_name", ""),
                        "variant": item.get("sku_name", ""),
                        "qty": 0,
                        "original_price": original_price,
                        "status": order_status,
                    }
                sku_details[sku]["qty"] += qty

            for sku, details in sku_details.items():
                formatted_data.append(
                    [
                        order_id,
                        sku,
                        details["name"],
                        details["variant"],
                        details["qty"],
                        details["original_price"],
                        details["status"],
                    ]
                )

        return formatted_data

    def _process_stock_item(self, item: dict, product_info: dict) -> str:
        """Process stock update for a single item"""
        new_qty = int(item["new_qty"])
        current_qty = product_info["current_stock"]
        base_msg = f"Current Stock: {
            current_qty if current_qty is not None else 'N/A'}, New Stock: {new_qty}"

        if current_qty is not None and new_qty == current_qty:
            self._update_item_status(
                row=item["row"], status="SKIPPED", log_msg=base_msg
            )
            return "skipped"

        if new_qty < 0:
            self._update_item_status(
                row=item["row"],
                status="FAILED: Stock cannot be negative",
                log_msg=base_msg,
            )
            return "failed"

        if new_qty > self.MAX_STOCK:
            self._update_item_status(
                row=item["row"],
                status=f"FAILED: Stock exceeds maximum limit ({
                    self.MAX_STOCK})",
                log_msg=base_msg,
            )
            return "failed"

        if product_info["status"] != "ACTIVATE":
            self._update_item_status(
                row=item["row"],
                status=f"FAILED: Item status {product_info['status']}",
                log_msg=base_msg,
            )
            return "failed"

        model_id = int(item["model_id"]) if item["model_id"] else None
        success = self.product_manager.update_stock(
            product_info["item_id"], model_id, new_qty
        )

        if success:
            self._update_item_status(
                row=item["row"], status="SUCCESS", log_msg=base_msg
            )
            return "processed"
        else:
            self._update_item_status(
                row=item["row"], status="FAILED: API error", log_msg=base_msg
            )
            return "failed"

    def process_stock_updates(self):
        """Process Tiktok stock updates from Google Sheet"""
        self._log("\n=== Processing Tiktok Stock Updates ===")
        items = self._get_items_to_process("stock")

        if items:
            processed, skipped, failed = self._process_items(items, "stock")
            self._log_result(processed, skipped, failed, "Stock update")

    def process_price_updates(self):
        """Process Tiktok price updates from Google Sheet"""
        self._log("\n=== Processing Tiktok Price Updates ===")
        items = self._get_items_to_process("price")

        if items:
            processed, skipped, failed = self._process_items(items, "price")
            self._log_result(processed, skipped, failed, "Price update")

    def _get_items_to_process(self, process_type: str) -> list:
        config = {
            "id_column": "ID Produk",
            "model_id_column": "ID SKU",
            "check_column": "Cek",
        }

        if process_type == "stock":
            return self.sheet_manager.get_data(
                "Tiktok Update", {
                    **config, "type": "stock", "value_column": "Stok"}
            )
        elif process_type == "price":
            return self.sheet_manager.get_data(
                "Tiktok Update",
                {
                    **config,
                    "type": "price",
                    "value_column": "Harga",
                    "min_order_check_column": "MinOrder",
                    "min_order_value_column": "Min_Order1",
                    "wholesale_price_column": "Price_Order1",
                },
            )
        return []

    def _process_price_item(self, item: dict, product_info: dict) -> str:
        """Process price update with optional MOQ update"""
        try:
            update_moq = item.get("min_order_check") and str(
                item.get("min_order_check")
            ).upper() in ["TRUE", "1", "YES", "Y", "X"]

            if update_moq:
                new_price = float(item.get("wholesale_price", 0))
            else:
                new_price = float(item["new_price"])

            current_price = product_info.get("current_price")
            base_msg = f"Current Price: {
                current_price if current_price is not None else 'N/A'}, New Price: {new_price}"

            if (
                current_price is not None
                and abs(new_price - float(current_price)) < self.PRICE_TOLERANCE
            ):
                if update_moq:
                    min_order_qty = int(item.get("min_order_value", 1))
                    current_moq = self._get_current_moq(
                        product_info["item_id"])

                    if current_moq == min_order_qty:
                        base_msg += f", MOQ unchanged: {min_order_qty}"
                        self._update_item_status(
                            item["row"], "SKIPPED", log_msg=base_msg
                        )
                        return "skipped"
                    else:
                        self._log(
                            f"Updating MOQ only for product {
                                product_info['item_id']}"
                        )
                        success = self._update_moq_only(
                            product_info["item_id"],
                            min_order_qty,
                            item["row"],
                            base_msg,
                        )
                        return "processed" if success else "failed"
                else:
                    self._update_item_status(
                        item["row"], "SKIPPED", log_msg=base_msg)
                    return "skipped"

            if new_price <= self.MIN_PRICE:
                self._update_item_status(
                    item["row"],
                    "FAILED: Price must be greater than 0",
                    log_msg=base_msg,
                )
                return "failed"

            if product_info["status"] != "ACTIVATE":
                self._update_item_status(
                    item["row"],
                    f"FAILED: Item status {product_info['status']}",
                    log_msg=base_msg,
                )
                return "failed"

            model_id = int(item["model_id"]) if item["model_id"] else None
            success = self.product_manager.update_price(
                product_info["item_id"], model_id, new_price
            )

            if success:
                if update_moq:
                    min_order_qty = int(item.get("min_order_value", 1))
                    current_moq = self._get_current_moq(
                        product_info["item_id"])

                    if current_moq == min_order_qty:
                        base_msg += f", MOQ unchanged: {min_order_qty}"
                        self._update_item_status(
                            item["row"], "SUCCESS", log_msg=base_msg
                        )
                    else:
                        success_moq = self.product_manager.update_min_order_quantity(
                            product_info["item_id"], min_order_qty, None
                        )
                        if success_moq:
                            base_msg += f", MOQ: {min_order_qty}"
                            self._update_item_status(
                                item["row"], "SUCCESS", log_msg=base_msg
                            )
                        else:
                            self._update_item_status(
                                item["row"],
                                "PARTIAL: Price updated but MOQ failed",
                                log_msg=base_msg,
                            )
                    return "processed"
                else:
                    self._update_item_status(
                        item["row"], "SUCCESS", log_msg=base_msg)
                    return "processed"
            else:
                self._update_item_status(
                    item["row"], "FAILED: API error", log_msg=base_msg
                )
                return "failed"

        except Exception as e:
            self._update_item_status(item["row"], f"FAILED: {str(e)}")
            return "failed"

    def _get_current_moq(self, item_id: str) -> int:
        """Get current MOQ value from API"""
        try:
            product_data = self.product_manager.get_raw_product_details(
                item_id)
            return product_data.get(
                "minimum_order_quantity", 1) if product_data else 1
        except Exception as e:
            self.logger.error(f"Error getting current MOQ: {str(e)}")
            return 1

    def _update_moq_only(
        self, item_id: str, min_order_qty: int, row: int, base_msg: str
    ) -> bool:
        """Update only MOQ without changing price"""
        try:
            success = self.product_manager.update_min_order_quantity(
                item_id, min_order_qty, None
            )
            if success:
                base_msg += f", MOQ updated: {min_order_qty}"
                self._update_item_status(row, "SUCCESS", log_msg=base_msg)
                return True
            else:
                self._update_item_status(
                    row, "FAILED: MOQ update failed", log_msg=base_msg
                )
                return False
        except Exception as e:
            self._update_item_status(row, f"FAILED: {str(e)}")
            return False

    def export_orders_today(self) -> bool:
        """Export TikTok orders for today - FIXED VERSION"""
        self._log("\n=== Exporting TikTok Orders Today ===")
        statuses = [
            "UNPAID",
            "ON_HOLD",
            "AWAITING_SHIPMENT",
            "AWAITING_COLLECTION",
            "COMPLETED",
        ]
        return self._export_orders_by_statuses(statuses, 1)  # Hanya 1 hari

    def export_orders_by_type(self, export_type, days=7):
        """Export orders by specific type for TikTok"""
        try:
            worksheet = self._get_or_create_worksheet("Tiktok Orders")

            if export_type == "ALL":
                # Export all order types combined
                self._prepare_worksheet(worksheet)
                all_data = []

                order_types = [
                    "UNPAID",
                    "ON_HOLD",
                    "AWAITING_SHIPMENT",
                    "AWAITING_COLLECTION",
                    "COMPLETED",
                    "CANCELLED",
                ]
                for order_type in order_types:
                    orders = self.order_manager.get_order_list(
                        order_type, days)
                    if orders:
                        for order in orders:
                            order_id = order.get("id", "")
                            if not order_id:
                                continue

                            line_items = order.get("line_items", [])
                            for item in line_items:
                                formatted_data = [
                                    order_id,
                                    item.get("seller_sku", ""),
                                    item.get("product_name", ""),
                                    item.get("sku_name", ""),
                                    int(item.get("quantity", 1)),
                                    item.get("original_price", ""),
                                    order_type,
                                ]
                                all_data.append(formatted_data)

                if all_data:
                    worksheet.append_rows(all_data)
                    self._log(
                        f"✅ Successfully exported {
                            len(all_data)} total order items"
                    )
                    return True
            else:
                # Export specific order type
                self._prepare_worksheet(worksheet)
                orders = self.order_manager.get_order_list(export_type, days)
                if not orders:
                    self._log(f"❌ No {export_type} orders found")
                    return False

                all_data = []
                for order in orders:
                    order_id = order.get("id", "")
                    if not order_id:
                        continue

                    line_items = order.get("line_items", [])
                    for item in line_items:
                        formatted_data = [
                            order_id,
                            item.get("seller_sku", ""),
                            item.get("product_name", ""),
                            item.get("sku_name", ""),
                            int(item.get("quantity", 1)),
                            item.get("original_price", ""),
                            export_type,
                        ]
                        all_data.append(formatted_data)

                if all_data:
                    worksheet.append_rows(all_data)
                    self._log(
                        f"✅ Successfully exported {
                            len(all_data)} {export_type} order items"
                    )
                    return True

            return False

        except Exception as e:
            self._log(
                f"🔥 Error exporting {export_type} orders: {
                    str(e)}",
                "error",
            )
            return False
        finally:
            self.sheet_manager.hide_sheet("Tiktok Orders")

    def process_price_updates_direct(self):
        """Process Tiktok price updates langsung tanpa sub-menu"""
        try:
            self._log("\n=== Processing Tiktok Price Updates ===")

            # Gunakan method yang sudah ada
            result = self.process_price_updates()

            if result:
                self._log("✅ Tiktok price update completed successfully")
                return {"success": True,
                        "message": "Tiktok price updates completed"}
            else:
                self._log("❌ Tiktok price update failed")
                return {"success": False,
                        "message": "Tiktok price updates failed"}

        except Exception as e:
            error_msg = f"❌ Error in Tiktok price update: {str(e)}"
            self._log(error_msg)
            return {"success": False, "message": error_msg}

    def process_price_updates_direct(self):
        """Process Tiktok price updates directly without submenu"""
        try:
            self._log("\n=== Processing Tiktok Price Updates ===")

            # Gunakan method yang sudah ada
            result = self.process_price_updates()

            if result:
                self._log("✅ Tiktok price update completed successfully")
                return {"success": True,
                        "message": "Tiktok price updates completed"}
            else:
                self._log("❌ Tiktok price update failed")
                return {"success": False,
                        "message": "Tiktok price updates failed"}

        except Exception as e:
            error_msg = f"❌ Error in Tiktok price update: {str(e)}"
            self._log(error_msg)
            return {"success": False, "message": error_msg}

    def show_export_menu(self):
        """Display Tiktok export options dengan status yang diinginkan"""
        self._log("\nTiktok Export Orders:")
        self._log("1. Export UNPAID orders")
        self._log("2. Export AWAITING_SHIPMENT orders")
        self._log("3. Export AWAITING_COLLECTION orders")
        self._log("4. Export COMPLETED orders")
        self._log("5. Export ALL orders (combined)")
        self._log("6. Back to Tiktok menu")

        choice = input("Enter your choice (1-6): ").strip()

        status_mapping = {
            "1": "UNPAID",
            "2": "AWAITING_SHIPMENT",
            "3": "AWAITING_COLLECTION",
            "4": "COMPLETED",
            "5": "ALL",
        }

        if choice in status_mapping:
            self._log(f"\n🔄 Processing {status_mapping[choice]} orders...")
            if choice == "5":
                self.export_orders_and_bookings()
            else:
                self.export_orders(days=7, status=status_mapping[choice])
        elif choice != "6":
            self._log("❌ Invalid choice")

    def export_orders_and_bookings(self) -> bool:
        """Export TikTok orders dari status yang diinginkan"""
        self._log("\n=== Exporting TikTok Orders ===")

        # Status yang diinginkan untuk Tiktok
        statuses = [
            "UNPAID",
            "AWAITING_SHIPMENT",
            "AWAITING_COLLECTION",
            "COMPLETED"]
        return self._export_orders_by_statuses(statuses, 7)

    def _export_orders_by_statuses(self, statuses: list, days: int) -> bool:
        """Helper function untuk export orders multiple statuses"""
        try:
            worksheet = self._get_or_create_worksheet("Tiktok Orders")
            self._prepare_worksheet(worksheet)

            all_data = []
            for status in statuses:
                self._log(f"\n🔍 Processing {status} orders...")
                orders = self.order_manager.get_order_list(status, days)

                if not orders:
                    self._log(f"No {status} orders found")
                    continue

                self._log(f"Found {len(orders)} {status} orders")

                for order in orders:
                    order_id = order.get("id", "")
                    if not order_id:
                        continue

                    line_items = order.get("line_items", [])
                    if not line_items:
                        self._log(f"No line items found for order {order_id}")
                        continue

                    for item in line_items:
                        formatted_data = [
                            order_id,
                            item.get("seller_sku", ""),
                            item.get("product_name", ""),
                            item.get("sku_name", ""),
                            int(item.get("quantity", 1)),
                            item.get("original_price", ""),
                            status,
                        ]
                        all_data.append(formatted_data)

            if not all_data:
                self._log("No orders found to export")
                return False

            worksheet.append_rows(all_data)
            self._log(f"✅ Successfully exported {len(all_data)} order items")
            return True

        except Exception as e:
            self._log(f"Error exporting TikTok orders: {str(e)}", "error")
            return False
        finally:
            self.sheet_manager.hide_sheet("Tiktok Orders")
