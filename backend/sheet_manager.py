import logging
import os
import random
import time
from abc import ABC, abstractmethod

import gspread
from google.oauth2.service_account import \
    Credentials as ServiceAccountCredentials
from oauth2client.service_account import ServiceAccountCredentials


class ISheetManager(ABC):
    """Abstract base class for sheet managers"""

    @abstractmethod
    def get_data(self, sheet_name, config):
        pass

    @abstractmethod
    def update_status(self, row, status, sheet_name):
        pass

    @abstractmethod
    def hide_sheet(self, sheet_name):
        pass


class GSheetManager(ISheetManager):
    def __init__(self, credentials_files: list, gsheet_id: str):
        self.scope = ["https://www.googleapis.com/auth/spreadsheets"]
        self.credentials_files = credentials_files
        self.current_account_index = 0
        self.gsheet_id = gsheet_id
        self._initialize_client()
        self.last_request_time = 0
        self.request_delay = 1.5
        self.max_delay = 60
        self.retry_count = 0
        self.logger = logging.getLogger(__name__)

    def _switch_account(self):
        self.current_account_index = (self.current_account_index + 1) % len(
            self.credentials_files
        )
        print(
            f"🔁 Switching to Google account: {self.credentials_files[self.current_account_index]}"
        )
        self._initialize_client()
        self.last_request_time = 0
        self.retry_count = 0

    def _initialize_client(self):
        try:
            current_file = self.credentials_files[self.current_account_index]
            full_path = os.path.join("config", current_file)

            self.credentials = ServiceAccountCredentials.from_json_keyfile_name(
                full_path, self.scope
            )
            self.client = gspread.authorize(self.credentials)
            self.sheet = self.client.open_by_key(self.gsheet_id)
        except Exception as e:
            raise Exception(f"Failed to initialize Google Sheets: {str(e)}")

    def _rate_limit(self):
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        dynamic_delay = min(self.request_delay *
                            (2**self.retry_count), self.max_delay)

        if elapsed < dynamic_delay:
            sleep_time = dynamic_delay - elapsed
            print(f"⏳ Enforcing rate limit: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def update_status(self, row, status, sheet_name):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self._rate_limit()

                if not isinstance(sheet_name, str) or len(sheet_name) > 50:
                    sheet_name = "Update Sheet"

                worksheet = self._get_worksheet(sheet_name)
                status_col = self._get_column_index_by_header(
                    worksheet, "Status")

                worksheet.update_cell(row, status_col, status)
                print(f"✅ Updated status: '{status}' at row {row}")
                self.retry_count = 0
                return True

            except Exception as e:
                error_msg = str(e)
                print(
                    f"⚠️ Attempt {
                        attempt + 1}/{max_retries} failed: {error_msg}"
                )
                print(f"Sheet: {sheet_name}, Row: {row}, Status: {status}")

                base_delay = min(
                    self.request_delay * (2**self.retry_count), self.max_delay
                )
                jitter = random.uniform(0.5, 1.5)
                wait_time = min(base_delay * jitter, self.max_delay)

                is_quota_error = (
                    "quota" in error_msg.lower() or "exceeded" in error_msg.lower()
                )
                should_switch = (
                    len(self.credentials_files) > 1
                    and self.retry_count >= 2
                    and is_quota_error
                )

                if should_switch:
                    print(
                        f"🔄 Switching account after {
                            self.retry_count} failures"
                    )
                    self._switch_account()
                    self.retry_count = 0
                else:
                    print(f"⏳ Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    self.retry_count += 1

        print(f"❌ Permanent failure after {max_retries} attempts")
        return False

    def print_headers(self, sheet_name):
        try:
            worksheet = self._get_worksheet(sheet_name)
            headers = worksheet.row_values(1)
            print("\n=== Sheet Headers ===")
            for idx, header in enumerate(headers, start=1):
                print(f"{idx}. {header}")
        except Exception as e:
            print(f"❌ Error printing headers: {str(e)}")

    def _get_worksheet(self, sheet_name):
        return self.sheet.worksheet(sheet_name)

    def _should_process_record(self, record, check_column):
        if check_column not in record:
            return False

        cek_value = record[check_column]
        if isinstance(cek_value, bool) and cek_value:
            return True
        return str(cek_value).strip().upper() in ["TRUE", "1", "YES", "Y", "X"]

    def _get_column_index_by_header(self, worksheet, header_name):
        headers = worksheet.row_values(1)
        for idx, header in enumerate(headers, start=1):
            if header.lower() == header_name.lower():
                return idx
        raise ValueError(f"Column '{header_name}' not found in sheet")

    def get_data(self, sheet_name, config):
        """
        Generic method to get data from sheet
        Config format:
        {
            "type": "stock"|"price"|"wholesale",
            "id_column": "Product ID",
            "model_id_column": "SKU ID",
            "value_column": "Stock",  # For stock/price
            "check_column": "Cek",
            "tiers": [  # For wholesale only
                {"min": "Min1", "price": "Price1", "max": "Max1"},
                {"min": "Min2", "price": "Price2", "max": "Max2"}
            ]
        }
        """
        try:
            worksheet = self._get_worksheet(sheet_name)
            records = worksheet.get_all_records()

            if not records:
                self.print_headers(sheet_name)
                return []

            data_type = config.get("type", "stock")
            id_col = config["id_column"]
            model_col = config.get("model_id_column", "")
            check_col = config["check_column"]
            value_col = config.get("value_column", "")

            processed_data = []

            for i, record in enumerate(records):
                if not self._should_process_record(record, check_col):
                    continue

                row_data = {"row": i + 2}

                # Common fields
                row_data["item_id"] = record.get(id_col, "")
                if model_col:
                    row_data["model_id"] = record.get(model_col, "")

                # Type-specific processing
                if data_type == "stock":
                    row_data["new_qty"] = record.get(value_col, "")
                    processed_data.append(row_data)

                elif data_type == "price":
                    try:
                        row_data["new_price"] = float(record.get(value_col, 0))

                        # Add wholesale price if column exists
                        if "wholesale_price_column" in config:
                            row_data["wholesale_price"] = record.get(
                                config["wholesale_price_column"], ""
                            )

                        # Add MOQ fields if they exist
                        if "min_order_check_column" in config:
                            row_data["min_order_check"] = record.get(
                                config["min_order_check_column"], ""
                            )
                        if "min_order_value_column" in config:
                            row_data["min_order_value"] = record.get(
                                config["min_order_value_column"], ""
                            )

                        processed_data.append(row_data)
                    except ValueError:
                        continue
                elif data_type == "wholesale":
                    tiers = []
                    for tier_config in config.get("tiers", []):
                        tier = self._process_wholesale_tier(
                            record,
                            tier_config["min"],
                            tier_config["price"],
                            tier_config["max"],
                        )
                        if tier:
                            tiers.append(tier)

                    if tiers:
                        row_data["wholesale_tiers"] = tiers
                        processed_data.append(row_data)

                elif data_type == "wholesale_delete":
                    # Only need item ID for deletion
                    row_data["item_id"] = record.get(id_col, "")
                    processed_data.append(row_data)
            return processed_data

        except Exception as e:
            error_msg = f"Error reading {sheet_name}: {str(e)}"
            print(error_msg)
            self.print_headers(sheet_name)
            return []

    def _process_wholesale_tier(self, record, min_col, price_col, max_col):
        try:
            min_val = int(record.get(min_col, 0))
            price_val = float(record.get(price_col, 0))
            max_val = int(record.get(max_col, 0))

            if min_val >= 0 and price_val > 0 and max_val > min_val:
                return {
                    "min_count": min_val,
                    "unit_price": price_val,
                    "max_count": max_val,
                }
        except (ValueError, TypeError):
            pass
        return None

    def hide_sheet(self, sheet_name):
        """Hide specified worksheet"""
        try:
            worksheet = self._get_worksheet(sheet_name)
            sheet_id = worksheet.id

            body = {
                "requests": [
                    {
                        "updateSheetProperties": {
                            "properties": {"sheetId": sheet_id, "hidden": True},
                            "fields": "hidden",
                        }
                    }
                ]
            }

            self.sheet.batch_update(body)
            print(f"Sheet '{sheet_name}' hidden successfully")
            return True
        except gspread.WorksheetNotFound:
            print(f"⚠️ Worksheet '{sheet_name}' not found - skipping hide")
            return False
        except Exception as e:
            print(f"❌ Error hiding sheet {sheet_name}: {str(e)}")
            return False

    def combine_qty_by_sku(self):
        """Combine quantity by SKU from multiple summary sheets with additional price columns and formulas"""
        try:
            sheet_names = [
                "Tiktok Summary",
                "Lazada Summary",
                "Shopee Summary"]
            data_map = {}
            sheet_status = []

            # Process each sheet
            for sheet_name in sheet_names:
                try:
                    worksheet = self._get_worksheet(sheet_name)
                    data = worksheet.get_all_values()

                    if len(data) <= 1:
                        status_msg = f"⚠️ Sheet '{sheet_name}' kosong"
                        sheet_status.append(status_msg)
                        print(status_msg)
                        continue

                    platform = None
                    if "Shopee" in sheet_name:
                        platform = "shopee"
                    elif "Tiktok" in sheet_name:
                        platform = "tiktok"
                    elif "Lazada" in sheet_name:
                        platform = "lazada"

                    valid_rows = 0
                    for i in range(1, len(data)):
                        row = data[i]
                        if len(row) < 5:
                            continue

                        sku = row[0].strip()
                        qty_str = row[3]
                        price_str = row[4]

                        if not sku:
                            continue

                        if sku not in data_map:
                            data_map[sku] = {
                                "total_qty": 0.0,
                                "shopee_price": "",
                                "tiktok_price": "",
                                "lazada_price": "",
                            }

                        try:
                            qty_val = float(
                                qty_str.replace(
                                    ",", "").replace(
                                    ".", "").strip()
                            )
                            data_map[sku]["total_qty"] += qty_val
                        except (ValueError, TypeError):
                            pass

                        if platform:
                            price_key = f"{platform}_price"
                            data_map[sku][price_key] = price_str

                        valid_rows += 1

                    if valid_rows > 0:
                        status_msg = (
                            f"✅ Sheet '{sheet_name}' diproses: {valid_rows} baris"
                        )
                    else:
                        status_msg = f"⚠️ Sheet '{sheet_name}' tidak ada data valid"

                    sheet_status.append(status_msg)
                    print(status_msg)

                except gspread.WorksheetNotFound:
                    status_msg = f"❌ Sheet '{sheet_name}' tidak ditemukan!"
                    sheet_status.append(status_msg)
                    print(status_msg)
                except Exception as e:
                    status_msg = f"❌ Error processing sheet {sheet_name}: {
                        str(e)}"
                    sheet_status.append(status_msg)
                    print(status_msg)

            headers = [
                "SKU Seller",
                "Nama Barang",
                "Variasi",
                "Total Qty",
                "Harga Jual Shopee",
                "Harga Jual Tiktok",
                "Harga Jual Lazada",
            ]

            try:
                output_sheet = self.sheet.worksheet("Combined Result")
                output_sheet.clear()
            except gspread.WorksheetNotFound:
                output_sheet = self.sheet.add_worksheet(
                    title="Combined Result", rows="10000", cols="7"
                )

            result = [headers]

            sorted_skus = sorted(data_map.keys())
            for sku in sorted_skus:
                entry = data_map[sku]
                result.append(
                    [
                        sku,
                        "",
                        "",
                        entry["total_qty"],
                        entry["shopee_price"],
                        entry["tiktok_price"],
                        entry["lazada_price"],
                    ]
                )

            if result:
                output_sheet.update(range_name="A1", values=result)

            row_count = len(result)
            if row_count > 1:
                formulas_b = []
                formulas_c = []

                for i in range(2, row_count + 1):
                    formula_b = f'=IF($A{i}="";"";XLOOKUP($A{i};\'Data Utama\'!$A:$A;\'Data Utama\'!B:B;"Cek";0))'
                    formula_c = f'=IF($A{i}="";"";XLOOKUP($A{i};\'Data Utama\'!$A:$A;\'Data Utama\'!C:C;"Cek";0))'
                    formulas_b.append([formula_b])
                    formulas_c.append([formula_c])

                output_sheet.update(
                    range_name=f"B2:B{row_count}",
                    values=formulas_b,
                    value_input_option="USER_ENTERED",
                )

                output_sheet.update(
                    range_name=f"C2:C{row_count}",
                    values=formulas_c,
                    value_input_option="USER_ENTERED",
                )

            final_report = [
                "=== Laporan Penggabungan ===",
                f"Total SKU unik: {len(data_map)}",
                f"Total Qty digabungkan: {
                    sum(
                        entry['total_qty'] for entry in data_map.values())}",
                "",
                "Detail Sheet:",
            ]
            final_report.extend(sheet_status)

            print("\n".join(final_report))
            return True

        except Exception as e:
            print(f"❌ Error in combine_qty_by_sku: {str(e)}")
            import traceback

            traceback.print_exc()
            return False
