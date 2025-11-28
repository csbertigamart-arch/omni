import csv
import logging
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from api_clients import IAPIClient
from lazop import LazopRequest


class IOrderManager(ABC):
    @abstractmethod
    def get_order_list(self, status, days=7):
        pass

    @abstractmethod
    def get_order_details(self, order_sn_list):
        pass

    @abstractmethod
    def get_booking_list(self, status, days=7):
        pass


class BaseOrderManager(IOrderManager):
    """Base class for order managers with common functionality"""

    MAX_DAYS = 15
    BATCH_SIZE = 50
    RATE_LIMIT_DELAY = 0.5

    def __init__(self, api_client: IAPIClient):
        self.api = api_client
        self.logger = logging.getLogger(__name__)

    def _get_time_range(self, days: int) -> tuple[int, int]:
        """Calculate time range for API requests"""
        days = min(days, self.MAX_DAYS)
        time_to = int(time.time())
        time_from = time_to - (86400 * days)
        return time_from, time_to

    def _fetch_paginated_data(self, endpoint, base_params, data_key):
        """Generic pagination handler"""
        all_data = []
        next_cursor = None
        page_count = 0

        while True:
            page_count += 1
            params = base_params.copy()
            if next_cursor:
                params["cursor"] = next_cursor

            try:
                response = self.api.make_request(endpoint, params=params)
                if not response or "response" not in response:
                    break

                page_data = response["response"].get(data_key, [])
                if not page_data:
                    break

                all_data.extend(page_data)
                next_cursor = response["response"].get("next_cursor")
                has_more = response["response"].get("more", False)

                if not has_more or not next_cursor:
                    break

                time.sleep(self.RATE_LIMIT_DELAY)
            except Exception as e:
                self.logger.error(f"Page {page_count} failed: {str(e)}")
                break

        self.logger.info(
            f"Fetched {
                len(all_data)} items in {page_count} pages"
        )
        return all_data

    def format_items_for_export(self, orders, is_booking=False):
        """Generic item formatter for orders/bookings"""
        formatted_data = []
        processed_items = set()

        for order in orders:
            order_key = "booking_sn" if is_booking else "order_sn"
            status_key = "booking_status" if is_booking else "order_status"

            order_id = order.get(order_key, "")
            status = order.get(status_key, "UNKNOWN").upper()

            for item in order.get("item_list", []):
                item_id = item.get("item_id", "")
                model_id = item.get("model_id", "")
                item_key = f"{order_id}_{item_id}_{model_id}"

                if item_key in processed_items:
                    continue
                processed_items.add(item_key)

                sku = item.get("model_sku", "") or item.get("item_sku", "")
                model_name = item.get("model_name", "") or ""
                quantity = item.get("model_quantity_purchased", 0)

                formatted_data.append(
                    [
                        order_id,
                        sku,
                        item.get("item_name", ""),
                        model_name,
                        quantity,
                        item.get("model_original_price", ""),
                        status,
                    ]
                )

        return formatted_data

    def _process_batch(self, order_ids, endpoint, id_field, optional_fields):
        if not order_ids:
            return []

        all_data = []
        for i in range(0, len(order_ids), self.BATCH_SIZE):
            batch = order_ids[i: i + self.BATCH_SIZE]

            # self.logger.info(
            #     f"Making request to {endpoint} with {len(batch)} IDs: {batch}"
            # )

            params = {
                id_field: ",".join(batch),
                "response_optional_fields": ",".join(optional_fields),
            }

            try:
                start_time = time.time()
                response = self.api.make_request(endpoint, params=params)
                elapsed = time.time() - start_time

                self.logger.info(f"API call completed in {elapsed:.2f}s")

                request_id = response.get(
                    "request_id", "Not available") if response else "No response"
                self.logger.info(f"📝 Request ID: {request_id}")
                if not response or not isinstance(response, dict):
                    self.logger.error(
                        f"Invalid response structure: {response}")
                    continue

                if response.get("error"):
                    error_msg = response.get("message", "Unknown error")
                    self.logger.error(f"API error: {error_msg}")
                    continue

                if "/api/v2/order/get_booking_detail" in endpoint:
                    data_key = "booking_list"
                elif "/api/v2/order/get_order_detail" in endpoint:
                    data_key = "order_list"
                elif "/api/v2/order/get_booking_list" in endpoint:
                    data_key = "booking_list"
                else:
                    data_key = "item_list"

                api_response = response.get("response", {})
                data = api_response.get(data_key, [])

                self.logger.info(
                    f"Extracted {
                        len(data)} items using key '{data_key}'"
                )

                if not data:
                    self.logger.warning(
                        f"No data found using key '{data_key}'")

                all_data.extend(data)

            except Exception as e:
                self.logger.error(f"Error processing batch: {str(e)}")
                import traceback

                self.logger.error(traceback.format_exc())

            time.sleep(self.RATE_LIMIT_DELAY)

        return all_data


class ShopeeOrderManager(BaseOrderManager):
    """Shopee-specific order operations"""

    ORDER_DETAIL_FIELDS = [
        "item_list",
        "package_list",
        "shipping_carrier",
        "recipient_address",
        "item_name",
        "item_sku",
        "model_name",
        "model_sku",
        "model_id",
        "model_quantity_purchased",
        "variation_name",
        "original_price",
        "current_price",
        "item_info",
        "model_info",
        "item_sku_list",
        "model_sku_list",
        "product_location_id",
    ]

    BOOKING_DETAIL_FIELDS = [
        "item_list",
        "cancel_by",
        "cancel_reason",
        "fulfillment_flag",
        "pickup_done_time",
        "shipping_carrier",
        "recipient_address",
        "dropshipper",
        "dropshipper_phone",
    ]

    def get_booking_list(self, status, days=7):
        """Get booking list with pagination"""
        time_from, time_to = self._get_time_range(days)
        base_params = {
            "time_range_field": "create_time",
            "time_from": time_from,
            "time_to": time_to,
            "page_size": 100,
            "booking_status": status,
        }
        return self._fetch_paginated_data(
            "/api/v2/order/get_booking_list", base_params, "booking_list"
        )

    def get_order_list(self, status, days=7):
        """Get order list with pagination"""
        time_from, time_to = self._get_time_range(days)
        base_params = {
            "time_range_field": "create_time",
            "time_from": time_from,
            "time_to": time_to,
            "page_size": 100,
            "order_status": status,
            "response_optional_fields": "order_status",
        }
        return self._fetch_paginated_data(
            "/api/v2/order/get_order_list", base_params, "order_list"
        )

    def get_order_details(self, order_sn_list):
        """Get detailed order information"""
        return self._process_batch(
            order_sn_list,
            "/api/v2/order/get_order_detail",
            "order_sn_list",
            self.ORDER_DETAIL_FIELDS,
        )

    def get_escrow_details_batch(self, order_sn_list):
        """Batch fetch escrow details"""
        if not order_sn_list or len(order_sn_list) > self.BATCH_SIZE:
            raise ValueError(f"Batch size must be 1-{self.BATCH_SIZE} orders")

        try:
            response = self.api.make_request(
                "/api/v2/payment/get_escrow_detail_batch",
                method="POST",
                payload={"order_sn_list": order_sn_list},
            )

            if not response or "response" not in response:
                return [None] * len(order_sn_list)

            result_map = {
                detail["escrow_detail"]["order_sn"]: detail["escrow_detail"]
                for detail in response["response"]
            }
            return [result_map.get(sn) for sn in order_sn_list]

        except Exception as e:
            self.logger.error(f"Batch API failed: {str(e)}")
            return [None] * len(order_sn_list)

    def process_shipping_fee_difference(
        self, order_sn_list, output_file=None, start_from=0
    ):
        """Process shipping fee differences - FIXED VERSION untuk Google Sheets"""
        if not order_sn_list:
            self.logger.error("Order SN list is empty")
            return []

        fieldnames = [
            "Create Time",
            "Order SN",
            "Buyer Paid",
            "Actual",
            "Shopee Rebate",
            "Difference",
            "Shipping Carrier",
        ]

        # Jika output_file tidak disediakan, kita hanya kumpulkan results
        processed_orders = set()
        if output_file:
            processed_orders = self._init_output_file(output_file, fieldnames)

        total_orders = len(order_sn_list)
        results = []

        # Process in batches
        for i in range(start_from, total_orders, self.BATCH_SIZE):
            batch = order_sn_list[i: i + self.BATCH_SIZE]
            if output_file:
                batch = [sn for sn in batch if sn not in processed_orders]

            if not batch:
                continue

            try:
                batch_results = self._process_shipping_batch(batch)
                if batch_results:
                    if output_file:
                        self._save_results(
                            output_file, fieldnames, batch_results)
                        processed_orders.update(
                            [r["Order SN"] for r in batch_results])

                    results.extend(batch_results)
                    self.logger.info(
                        f"Processed batch {i // self.BATCH_SIZE + 1}: {len(batch_results)} orders"
                    )
            except Exception as e:
                self.logger.error(
                    f"Batch {i // self.BATCH_SIZE + 1} failed: {str(e)}")
                continue

            time.sleep(self.RATE_LIMIT_DELAY)

        self.logger.info(f"Completed processing {len(results)} orders")
        return results

    def _init_output_file(self, output_file, fieldnames):
        """Initialize output file and return processed orders"""
        processed_orders = set()
        if os.path.exists(output_file):
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    processed_orders = {row["Order SN"] for row in reader}
            except Exception as e:
                self.logger.error(f"Error reading file: {str(e)}")
        else:
            try:
                with open(output_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
            except Exception as e:
                self.logger.error(f"Error creating file: {str(e)}")
        return processed_orders

    def _process_shipping_batch(self, batch):
        """Process a batch of shipping fee calculations - FIXED"""
        results = []

        self.logger.info(
            f"🔄 _process_shipping_batch processing {len(batch)} orders")
        self.logger.info(f"📋 Batch order numbers: {batch}")

        try:
            # Get escrow details
            self.logger.info("🔍 Getting escrow details...")
            escrow_results = self.get_escrow_details_batch(batch)
            self.logger.info(f"📊 Got {len(escrow_results)} escrow results")

            # Get order details
            self.logger.info("🔍 Getting order details...")
            order_details = self.get_order_details(batch)
            self.logger.info(f"📊 Got {len(order_details)} order details")

            processed_count = 0
            for escrow_data, order_sn in zip(escrow_results, batch):
                if not escrow_data:
                    self.logger.warning(
                        f"⚠️ No escrow data for order {order_sn}")
                    continue

                shipping_carrier = ""
                create_time = ""

                # Find matching order details
                order_found = False
                for order in order_details:
                    if order.get("order_sn") == order_sn:
                        order_found = True
                        timestamp = order.get("create_time", 0)
                        if timestamp:
                            create_time = datetime.fromtimestamp(
                                timestamp).strftime("%d %B %Y")

                        # Get shipping carrier from package list
                        package_list = order.get("package_list", [])
                        if package_list and isinstance(package_list, list):
                            shipping_carrier = package_list[0].get(
                                "shipping_carrier", "")
                        break

                if not order_found:
                    self.logger.warning(
                        f"⚠️ No order details found for {order_sn}")

                order_income = escrow_data.get("order_income", {})
                buyer_paid = float(order_income.get(
                    "buyer_paid_shipping_fee", 0))
                actual = float(order_income.get("actual_shipping_fee", 0))
                rebate = float(order_income.get("shopee_shipping_rebate", 0))

                result = {
                    "Create Time": create_time,
                    "Order SN": order_sn,
                    "Buyer Paid": buyer_paid,
                    "Actual": actual,
                    "Shopee Rebate": rebate,
                    "Difference": buyer_paid - actual + rebate,
                    "Shipping Carrier": shipping_carrier,
                }

                results.append(result)
                processed_count += 1

            self.logger.info(
                f"✅ Processed {processed_count} orders in this batch")

        except Exception as e:
            self.logger.error(f"❌ Error processing shipping batch: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())

        self.logger.info(
            f"📤 Returning {len(results)} results from _process_shipping_batch")
        return results

    def _save_results(self, output_file, fieldnames, results):
        """Save results to CSV file"""
        if not results:
            return

        try:
            with open(output_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerows(results)
            self.logger.info(f"Saved {len(results)} results")
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")

    def get_booking_detail(self, booking_sn_list):
        """Get detailed booking information with enhanced logging"""
        self.logger.info(
            f"Getting booking details for {
                len(booking_sn_list)} bookings"
        )

        if not booking_sn_list:
            self.logger.warning("Empty booking_sn_list provided")
            return []

        results = self._process_batch(
            booking_sn_list,
            "/api/v2/order/get_booking_detail",
            "booking_sn_list",
            self.BOOKING_DETAIL_FIELDS,
        )

        return results

    def format_bookings_for_export(self, bookings):
        """Format bookings for export with additional validation"""
        formatted_data = []
        processed_items = set()

        if not isinstance(bookings, list):
            self.logger.error(
                f"Invalid bookings type: {type(bookings)}. Expected list."
            )
            return formatted_data

        for booking in bookings:
            self.logger.info(f"Booking structure: {list(booking.keys())}")

        for booking in bookings:
            booking_sn = booking.get("booking_sn", "")
            status = booking.get("booking_status", "UNKNOWN").upper()

            if not booking_sn:
                self.logger.warning("Skipping booking without booking_sn")
                continue

            item_list = booking.get("item_list", [])

            if not item_list:
                self.logger.warning(f"Booking {booking_sn} has no items")
                continue

            for item in item_list:
                item_id = item.get("item_id", "")
                model_id = item.get("model_id", "")
                item_key = f"{booking_sn}_{item_id}_{model_id}"

                if item_key in processed_items:
                    self.logger.info(f"Skipping duplicate item: {item_key}")
                    continue

                processed_items.add(item_key)

                sku = item.get("model_sku", "") or item.get("item_sku", "")
                model_name = item.get("model_name", "") or ""
                quantity = item.get("model_quantity_purchased", 0)

                if not sku:
                    self.logger.warning(
                        f"Item in booking {booking_sn} has no SKU")

                formatted_data.append(
                    [
                        booking_sn,
                        sku,
                        item.get("item_name", ""),
                        model_name,
                        quantity,
                        status,
                    ]
                )

        self.logger.info(
            f"Formatted {
                len(formatted_data)} items from {
                len(bookings)} bookings"
        )
        return formatted_data

    def export_shipping_fee_to_google_sheets(self, results, spreadsheet_id, sheet_name, google_sheets_manager):
        """Export shipping fee differences directly to Google Sheets - FIXED VERSION"""
        try:
            self.logger.info(
                f"🔄 Starting export_shipping_fee_to_google_sheets to {spreadsheet_id}")

            if not google_sheets_manager:
                self.logger.error("❌ Google Sheets Manager not provided")
                return False

            if not results:
                self.logger.warning("❌ No shipping fee results to export")
                return False

            # Buat nama sheet yang lebih aman
            def create_safe_sheet_name(base_name):
                # Ganti karakter yang tidak valid dengan underscore
                import re
                safe_name = re.sub(r'[^\w\s-]', '_', base_name)
                safe_name = re.sub(r'[-\s]+', '_', safe_name)
                safe_name = safe_name.strip('_')
                return safe_name[:31]  # Batasi panjang

            safe_sheet_name = create_safe_sheet_name(sheet_name)
            self.logger.info(
                f"📝 Using safe sheet name: '{safe_sheet_name}' (original: '{sheet_name}')")

            # Prepare data for Google Sheets
            headers = ["Create Time", "Order SN", "Buyer Paid", "Actual",
                       "Shopee Rebate", "Difference", "Shipping Carrier"]
            data = [headers]

            for result in results:
                row = [
                    result.get("Create Time", ""),
                    result.get("Order SN", ""),
                    float(result.get("Buyer Paid", 0)),
                    float(result.get("Actual", 0)),
                    float(result.get("Shopee Rebate", 0)),
                    float(result.get("Difference", 0)),
                    result.get("Shipping Carrier", "")
                ]
                data.append(row)

            # Use Google Sheets Manager to upload
            success = google_sheets_manager.upload_to_sheet(
                spreadsheet_id=spreadsheet_id,
                sheet_name=safe_sheet_name,
                data=data
            )

            if success:
                self.logger.info(
                    f"✅ Exported {len(results)} shipping fee records to Google Sheets")
                return True
            else:
                self.logger.error(
                    "❌ Failed to export shipping fee to Google Sheets")
                return False

        except Exception as e:
            self.logger.error(
                f"❌ Error exporting shipping fee to Google Sheets: {str(e)}")
            return False


class LazadaOrderManager(BaseOrderManager):
    """Lazada-specific order operations - FIXED VERSION"""

    BASE_URL = "https://api.lazada.co.id/rest"

    def get_booking_list(self, status, days=7):
        """Lazada doesn't have booking concept - return empty list"""
        return []

    def get_order_list(self, status, days=7):
        """Get Lazada order list with proper signature handling - FIXED"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            created_after = start_date.strftime("%Y-%m-%dT%H:%M:%S+07:00")
            created_before = end_date.strftime("%Y-%m-%dT%H:%M:%S+07:00")

            request = LazopRequest("/orders/get", "GET")
            request.add_api_param("created_after", created_after)
            request.add_api_param("created_before", created_before)

            if status and status != "None" and status != "ALL":
                request.add_api_param("status", status)

            request.add_api_param("offset", "0")
            request.add_api_param("limit", "100")

            response = self.api.client.execute(
                request, self.api.config.access_token)

            if not response or not hasattr(response, "body"):
                self.logger.error("Invalid API response")
                return []

            response_body = response.body

            if "code" in response_body and response_body["code"] != "0":
                error_msg = response_body.get("message", "Unknown error")
                self.logger.error(f"API error: {error_msg}")
                return []

            orders_data = response_body.get("data", {}).get("orders", [])

            # Enhanced logging for debugging
            self.logger.info(
                f"Found {
                    len(orders_data)} orders for status: {status}"
            )

            return orders_data

        except Exception as e:
            self.logger.error(f"Error getting orders: {str(e)}", exc_info=True)
            return []

    def get_order_details(self, order_id_list):
        """Get Lazada order details with proper error handling - FIXED"""
        if not order_id_list:
            return []

        all_details = []
        for order_id in order_id_list:
            try:
                # Get order items
                items_request = LazopRequest("/order/items/get", "GET")
                items_request.add_api_param("order_id", order_id)
                items_response = self.api.client.execute(
                    items_request, self.api.config.access_token
                )

                if items_response and hasattr(items_response, "body"):
                    items_body = items_response.body
                    if "code" in items_body and items_body["code"] == "0":
                        items_data = items_body.get("data", [])

                        # Get order basic info
                        order_request = LazopRequest("/order/get", "GET")
                        order_request.add_api_param("order_id", order_id)
                        order_response = self.api.client.execute(
                            order_request, self.api.config.access_token
                        )

                        order_data = {}
                        if order_response and hasattr(order_response, "body"):
                            order_body = order_response.body
                            if "code" in order_body and order_body["code"] == "0":
                                order_data = order_body.get("data", {})

                        # Combine order info with items
                        for item in items_data:
                            combined_data = {
                                "order_id": order_id,
                                "order_sn": order_data.get("order_number", ""),
                                "status": order_data.get("status", ""),
                                "created_at": order_data.get("created_at", ""),
                                "item_id": item.get("item_id", ""),
                                "sku": item.get("sku", ""),
                                "name": item.get("name", ""),
                                "variation": item.get("variation", ""),
                                "quantity": int(item.get("quantity", 1)),
                                "item_price": item.get("item_price", ""),
                                "seller_sku": item.get("seller_sku", ""),
                            }
                            all_details.append(combined_data)

                time.sleep(self.RATE_LIMIT_DELAY)
            except Exception as e:
                self.logger.error(
                    f"Error getting details for {order_id}: {
                        str(e)}"
                )

        return all_details

    def format_items_for_export(self, order_details):
        """Format Lazada order items for export - FIXED"""
        formatted_data = []
        processed_items = set()

        for order in order_details:
            order_id = order.get("order_id", "")
            status = order.get("status", "UNKNOWN").upper()

            item_key = f"{order_id}_{order.get('sku', '')}"

            if item_key in processed_items:
                continue
            processed_items.add(item_key)

            formatted_data.append(
                [
                    order_id,
                    order.get("seller_sku", "") or order.get("sku", ""),
                    order.get("name", ""),
                    order.get("variation", ""),
                    order.get("quantity", 1),
                    order.get("item_price", ""),
                    status,
                ]
            )

        return formatted_data


class TiktokOrderManager(BaseOrderManager):
    """Tiktok-specific order operations"""

    def get_booking_list(self, status, days=7):
        """Tiktok doesn't have booking concept - return empty list"""
        return []

    def get_order_list(self, status, days=7):
        """Get Tiktok order list"""
        try:
            time_from = int(
                (datetime.now() -
                 timedelta(
                    days=days)).timestamp())
            time_to = int(datetime.now().timestamp())
            all_orders = []
            next_page_token = ""

            while True:
                payload = {
                    "create_time_ge": time_from,
                    "create_time_lt": time_to,
                    "order_status": status,
                }
                params = {"page_size": "100"}
                if next_page_token:
                    params["next_page_token"] = next_page_token

                response = self.api.make_request(
                    "/order/202309/orders/search",
                    method="POST",
                    params=params,
                    payload=payload,
                )

                if not response or response.get("code") != 0:
                    break

                data = response.get("data", {})
                all_orders.extend(data.get("orders", []))
                next_page_token = data.get("next_page_token", "")

                if not next_page_token:
                    break
                time.sleep(self.RATE_LIMIT_DELAY)

            return all_orders
        except Exception as e:
            self.logger.error(f"Error getting orders: {str(e)}")
            return []

    def get_order_details(self, order_id_list):
        """Get Tiktok order details"""
        if not order_id_list:
            return []

        try:
            response = self.api.make_request(
                "/api/orders/detail/query",
                method="POST",
                payload={"order_id_list": order_id_list},
            )
            if response and response.get("code") == 0:
                return response.get("data", {}).get("order_list", [])
            return []
        except Exception as e:
            self.logger.error(f"Error getting details: {str(e)}")
            return []
