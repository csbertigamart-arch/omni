import hashlib
import hmac
import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

import numpy as np
import requests
from config_managers import IConfigManager
from lazop import LazopClient, LazopRequest


class IAPIClient(ABC):
    @abstractmethod
    def make_request(self, endpoint, method="GET", params=None, payload=None):
        pass

    @abstractmethod
    def refresh_access_token(self) -> bool:
        pass

    @abstractmethod
    def get_access_token(self) -> bool:
        pass


class ShopeeAPIClient(IAPIClient):
    def __init__(self, config_manager: IConfigManager):
        self.config = config_manager
        self.base_url = "https://partner.shopeemobile.com"
        self.auth_endpoints = [
            "/api/v2/auth/token/get",
            "/api/v2/auth/access_token/get",
        ]

    def _raw_make_request(self, endpoint, method="GET",
                          params=None, payload=None):
        """Make API request without token checks with debug info"""
        timestamp, signature = self._generate_signature(endpoint)
        url = f"{self.base_url}{endpoint}"
        request_params = {
            "partner_id": self.config.partner_id,
            "timestamp": timestamp,
            "sign": signature,
        }

        if params:
            request_params.update(params)

        headers = {
            "Content-Type": "application/json"} if method == "POST" else {}

        try:
            if method == "GET":
                response = requests.get(
                    url, params=request_params, headers=headers)
            else:
                response = requests.post(
                    url, json=payload, headers=headers, params=request_params
                )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"\nDEBUG: Request failed: {str(e)}")
            if hasattr(e, "response") and e.response:
                print(f"DEBUG: Error response: {e.response.text}")
            raise

    def refresh_access_token(self):
        """Refresh access token using refresh token with proper parameter types"""
        try:
            # Ensure all IDs are integers
            payload = {
                "refresh_token": str(self.config.refresh_token),
                "partner_id": int(self.config.partner_id),
                "shop_id": int(self.config.shop_id),
            }

            response = self._raw_make_request(
                endpoint="/api/v2/auth/access_token/get", method="POST", payload=payload
            )

            if not response:
                print("❌ Empty response from server")
                return False

            if "error" in response and response["error"]:
                print(
                    f"❌ API Error: {
                        response.get(
                            'message',
                            'Unknown error')}"
                )
                return False

            if "access_token" not in response:
                print("❌ Missing access_token in response")
                return False

            expire_in = response.get("expire_in", 14312)
            new_refresh_token = response.get(
                "refresh_token", self.config.refresh_token)

            self.config.update_token_info(
                response["access_token"], new_refresh_token, expire_in
            )

            return True

        except ValueError as e:
            print(f"❌ Invalid ID format: {str(e)}")
            return False
        except Exception as e:
            print(f"❌ Token refresh failed: {str(e)}")
            return False

    def make_request(self, endpoint, method="GET", params=None, payload=None):
        """Main API request method with auto-refresh"""
        # Skip token check for auth endpoints
        if endpoint not in self.auth_endpoints:
            if self.config.is_token_expired():
                if not self.config.is_refresh_token_expired():
                    print("🔃 Auto-refreshing expired access token...")
                    if not self.refresh_access_token():
                        raise Exception("Failed to refresh access token")
                else:
                    raise Exception(
                        "Both tokens expired. Please re-authenticate.")

        # Prepare request with proper authentication
        extra_string = (
            f"{self.config.access_token}{self.config.shop_id}"
            if endpoint not in self.auth_endpoints
            else ""
        )
        timestamp, signature = self._generate_signature(endpoint, extra_string)

        request_params = {
            "partner_id": self.config.partner_id,
            "timestamp": timestamp,
            "sign": signature,
        }

        if endpoint not in self.auth_endpoints:
            request_params.update(
                {
                    "access_token": self.config.access_token,
                    "shop_id": self.config.shop_id,
                }
            )

        if params:
            request_params.update(params)

        # Process payload if needed
        if method == "POST" and payload:
            payload = self._process_price_payload(payload)
            payload = json.loads(
                json.dumps(
                    payload,
                    default=lambda x: (
                        int(x)
                        if isinstance(x, (np.int32, np.int64))
                        else (
                            float(x)
                            if isinstance(x, (np.float32, np.float64))
                            else str(x)
                        )
                    ),
                )
            )

        # Make the request
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json"} if method == "POST" else {}

        try:
            if method == "GET":
                response = requests.get(
                    url, params=request_params, headers=headers)
            else:
                response = requests.post(
                    url, json=payload, headers=headers, params=request_params
                )

            response.raise_for_status()
            json_response = response.json()

            # Tambahkan pengecekan struktur respons
            if not isinstance(json_response, dict):
                error_msg = f"Invalid API response structure: {
                    type(json_response)}"
                raise Exception(error_msg)
            return response.json()

        except requests.exceptions.RequestException as e:
            error_msg = f"API request to {endpoint} failed: {str(e)}"
            if hasattr(e, "response") and e.response:
                try:
                    error_details = e.response.json()
                    error_msg += f"\nError details: {error_details}"
                except ValueError:
                    error_msg += f"\nResponse: {e.response.text}"
            raise Exception(error_msg)

    def _generate_signature(self, endpoint, extra_string=""):
        timestamp = int(time.time())
        base_string = f"{
            self.config.partner_id}{endpoint}{timestamp}{extra_string}"
        signature = hmac.new(
            self.config.partner_key.encode(), base_string.encode(), hashlib.sha256
        ).hexdigest()
        return timestamp, signature

    def _process_price_payload(self, payload):
        """Process price payload to ensure proper formatting"""
        if "price_list" in payload:
            for price_item in payload["price_list"]:
                price = price_item.get("original_price")
                if price is not None:
                    price_item["original_price"] = round(float(price), 2)
        return payload

    def get_access_token(self):
        if not self.config.code:
            raise ValueError(
                "Authorization code is empty. Please update code first.")

        payload = {
            "shop_id": self.config.shop_id,
            "code": self.config.code,
            "partner_id": self.config.partner_id,
        }

        response = self.make_request(
            endpoint="/api/v2/auth/token/get", method="POST", payload=payload
        )

        if response and "access_token" in response:
            # Default 4 hours if not provided
            expire_in = response.get("expire_in", 14312)
            self.config.update_token_info(
                response["access_token"], response["refresh_token"], expire_in
            )

            # Display token info
            print("\n✅ Access token obtained successfully!")
            print(
                f"Access Token will expire at: {
                    self.config.token_expiry.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            print(
                f"Refresh Token will expire at: {
                    self.config.refresh_token_expiry.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            print(
                f"Duration: {
                    expire_in //
                    3600} hours {
                    expire_in %
                    3600 //
                    60} minutes"
            )
            return True
        return False

    def get_wallet_transactions(
        self, month=None, year=None, transaction_tab_type=None, page_size=100
    ):
        """Get ALL wallet transactions with inclusive date ranges"""
        try:
            if month is None:
                month = datetime.now().month
            if year is None:
                year = datetime.now().year

            # Calculate date range (inclusive of entire month)
            first_day = datetime(year, month, 1)
            if month == 12:
                last_day = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                last_day = datetime(year, month + 1, 1) - timedelta(seconds=1)

            print(
                f"\nProcessing transactions from {
                    first_day.date()} to {
                    last_day.date()} (inclusive)"
            )

            # Split into chunks of exactly 15 days (including both start and
            # end dates)
            return self._get_wallet_transactions_chunked(
                first_day, last_day, transaction_tab_type, page_size
            )

        except Exception as e:
            print(f"\nError in get_wallet_transactions: {str(e)}")
            import traceback

            traceback.print_exc()
            return None

    def _get_wallet_transactions_chunked(
        self, first_day, last_day, transaction_tab_type, page_size
    ):
        """Process date ranges with inclusive end dates"""
        all_transactions = []
        processed_transactions = set()
        current_start = first_day

        while current_start <= last_day:
            # Calculate end date (14 days after start to make 15-day chunks
            # including both ends)
            current_end = current_start + timedelta(days=14)

            # Ensure we don't go beyond last day
            if current_end > last_day:
                current_end = last_day

            print(
                f"\nProcessing chunk: {
                    current_start.date()} to {
                    current_end.date()} (inclusive)"
            )

            chunk_result = self._process_date_range(
                current_start, current_end, transaction_tab_type, page_size
            )

            if chunk_result and chunk_result.get("response", {}).get(
                "transaction_list"
            ):
                # Deduplicate across chunks
                new_transactions = []
                for tx in chunk_result["response"]["transaction_list"]:
                    tx_key = self._get_transaction_key(tx)
                    if tx_key not in processed_transactions:
                        processed_transactions.add(tx_key)
                        new_transactions.append(tx)

                if new_transactions:
                    all_transactions.extend(new_transactions)
                    print(
                        f"Added {
                            len(new_transactions)} unique transactions from this chunk"
                    )

            # Move to next chunk (current_end + 1 second to avoid overlap)
            current_start = current_end + timedelta(seconds=1)

        if all_transactions:
            # Verify we got all dates
            self._verify_date_coverage(all_transactions, first_day, last_day)
            return {"response": {
                "transaction_list": all_transactions, "more": False}}
        return None

    def _process_date_range(
        self, start_date, end_date, transaction_tab_type, page_size
    ):
        """Process a single date range with inclusive end date"""
        transactions = []
        page_no = 0
        has_more = True
        processed_in_range = set()

        while has_more:
            page_no += 1
            print(f"  Processing page {page_no}...")

            params = {
                "page_no": page_no,
                "page_size": min(page_size, 100),
                "create_time_from": int(start_date.timestamp()),
                "create_time_to": int(end_date.timestamp()),
                "money_flow": "MONEY_IN",
                "transaction_tab_type": transaction_tab_type,
            }

            try:
                response = self.make_request(
                    endpoint="/api/v2/payment/get_wallet_transaction_list",
                    params=params,
                )

                if not response or "response" not in response:
                    break

                new_transactions = response["response"].get(
                    "transaction_list", [])

                if not new_transactions:
                    print("    No more transactions in this date range")
                    break

                # Deduplicate within this date range
                unique_transactions = []
                for tx in new_transactions:
                    tx_key = self._get_transaction_key(tx)
                    if tx_key not in processed_in_range:
                        processed_in_range.add(tx_key)
                        unique_transactions.append(tx)

                if unique_transactions:
                    transactions.extend(unique_transactions)
                    print(
                        f"    Found {
                            len(unique_transactions)} new transactions"
                    )
                else:
                    print("    No new transactions on this page")

                # Stop if we got fewer transactions than requested
                if len(new_transactions) < page_size:
                    has_more = False

                time.sleep(0.5)  # Rate limiting

            except Exception as e:
                print(f"    Error processing page: {str(e)}")
                break

        return (
            {"response": {"transaction_list": transactions, "more": False}}
            if transactions
            else None
        )

    def _verify_date_coverage(self, transactions, first_day, last_day):
        """Verify we have transactions for all expected dates"""
        dates = set()
        for tx in transactions:
            tx_date = datetime.fromtimestamp(tx["create_time"]).date()
            dates.add(tx_date)

        missing_dates = []
        current_date = first_day.date()
        while current_date <= last_day.date():
            if current_date not in dates:
                missing_dates.append(current_date)
            current_date += timedelta(days=1)

        if missing_dates:
            print("\n⚠️ Missing transactions for the following dates:")
            for i, date in enumerate(missing_dates, 1):
                print(
                    f"  {i}. {date.strftime('%Y-%m-%d')} ({date.strftime('%A')})")
        else:
            print("\n✅ Complete date coverage verified")

    def _get_transaction_key(self, transaction):
        """Create a unique key for deduplication"""
        return (
            transaction.get("create_time"),
            transaction.get("order_sn", ""),
            transaction.get("amount"),
            transaction.get("transaction_type"),
            transaction.get("description", "")[:100],
        )


class LazadaAPIClient(IAPIClient):
    BASE_URL = "https://api.lazada.co.id/rest"

    def __init__(self, config_manager: IConfigManager):
        self.config = config_manager
        self.client = LazopClient(
            self.BASE_URL, self.config.app_key, self.config.app_secret
        )
        self.logger = logging.getLogger(__name__)

    def make_request(
        self, endpoint: str, method: str = "GET", params=None, payload=None
    ):
        """Wrapper untuk menyeragamkan request dengan Shopee"""
        try:
            request = LazopRequest(endpoint, method.upper())

            if params:
                for key, value in params.items():
                    request.add_api_param(key, value)

            if payload:
                request.add_api_param("payload", json.dumps(payload))

            response = self.client.execute(request, self.config.access_token)

            # Standarisasi response seperti Shopee
            if "code" in response.body and response.body["code"] == "0":
                return {"response": response.body["data"]}
            else:
                return {"error": response.body.get("message", "Unknown error")}
        except Exception as e:
            self.logger.error(f"API request failed: {str(e)}")
            return {"error": str(e)}

    def get_access_token(self):
        """Get access token using Lazop SDK"""
        try:
            if not self.config.code:
                raise ValueError(
                    "Authorization code is empty. Please update code first."
                )

            self.logger.info(f"Requesting token with code: {self.config.code}")

            request = LazopRequest("/auth/token/create")
            request.add_api_param("code", self.config.code)

            response = self.client.execute(request)

            # Debug raw response
            self.logger.info(f"Raw API response: {response.body}")

            if "access_token" in response.body:
                self.config.update_token_info(
                    response.body["access_token"],
                    response.body.get("refresh_token", ""),
                    # Default 30 days
                    response.body.get("expires_in", 2592000),
                )
                return True

            error_msg = response.body.get("message", "Unknown error")
            raise Exception(f"API Error: {error_msg}")

        except Exception as e:
            self.logger.error(f"Failed to get Lazada token: {str(e)}")
            raise

    def _generate_signature(self, params):
        """Generate Lazada signature correctly"""
        # Urutkan parameter secara alfabet
        sorted_params = sorted(params.items(), key=lambda x: x[0])

        # Bangun string untuk signature
        concatenated = "".join(f"{k}{v}" for k, v in sorted_params)

        # Generate HMAC-SHA256
        signature = (
            hmac.new(
                self.config.app_secret.encode("utf-8"),
                concatenated.encode("utf-8"),
                hashlib.sha256,
            )
            .hexdigest()
            .upper()
        )

        return signature

    def refresh_access_token(self) -> bool:
        """Refresh Lazada access token using refresh token"""
        try:
            if not self.config.refresh_token:
                self.logger.error("No refresh token available")
                return False

            if self.config.is_refresh_token_expired():
                self.logger.error("Refresh token has expired")
                return False

            self.logger.info("Refreshing Lazada access token...")

            request = LazopRequest("/auth/token/refresh")
            request.add_api_param("refresh_token", self.config.refresh_token)

            response = self.client.execute(request)

            # Debug raw response
            self.logger.info(f"Refresh token response: {response.body}")

            if "access_token" in response.body:
                # Lazada token typically expires in 30 days (2592000 seconds)
                expires_in = response.body.get("expires_in", 2592000)

                self.config.update_token_info(
                    access_token=response.body["access_token"],
                    refresh_token=response.body.get(
                        "refresh_token", self.config.refresh_token
                    ),
                    expires_in=expires_in,
                )
                self.logger.info("Successfully refreshed Lazada access token")
                return True
            else:
                error_msg = response.body.get("message", "Unknown error")
                self.logger.error(f"Failed to refresh token: {error_msg}")
                return False

        except Exception as e:
            self.logger.error(f"Error refreshing Lazada token: {str(e)}")
            return False


class TiktokAPIClient(IAPIClient):
    BASE_URL = "https://open-api.tiktokglobalshop.com"
    AUTH_URL = "https://auth.tiktok-shops.com"

    def __init__(self, config_manager: IConfigManager):
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        self.api_version = "202309"
        self.auth_endpoints = ["/api/v2/token/get", "/api/v2/token/refresh"]

    def make_request(
        self, endpoint: str, method: str = "POST", params=None, payload=None
    ):
        if params is None:
            params = {}

        mandatory_params = {
            "app_key": self.config.app_key,
            "timestamp": str(int(time.time())),
            "version": self.api_version,
            "shop_cipher": self.config.shop_cipher,
            "shop_id": str(self.config.shop_id),
        }
        params.update(mandatory_params)

        # Convert timestamp to readable format for logging
        readable_timestamp = datetime.fromtimestamp(int(params["timestamp"])).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        # self.logger.info(
        #     f"🕒 Request timestamp: {readable_timestamp} ({params['timestamp']})"
        # )

        # Generate signature - pastikan payload di-serialize dengan benar
        json_payload = None
        if payload is not None:
            # Pastikan payload menggunakan parameter yang benar untuk TikTok
            if "create_time_from" in payload and "create_time_to" in payload:
                # Konversi ke format yang diharapkan TikTok
                payload = {
                    "create_time_ge": payload["create_time_from"],
                    "create_time_lt": payload["create_time_to"],
                    "order_status": payload["order_status"],
                }

            json_payload = json.dumps(
                payload, separators=(
                    ",", ":"), sort_keys=True)
            params["sign"] = self.generate_signature(
                endpoint, params, json_payload)
        else:
            params["sign"] = self.generate_signature(endpoint, params)

        # Pastikan access token selalu disertakan
        if self.config.access_token:
            params["access_token"] = self.config.access_token

        headers = {
            "Content-Type": "application/json",
            "x-tts-access-token": self.config.access_token,  # Header juga diperlukan
        }

        url = f"{self.BASE_URL}{endpoint}"

        try:
            # Debug: print full request details
            # self.logger.info(f"🔧 Making request to: {url}")
            # self.logger.info(f"🔧 Method: {method}")
            # self.logger.info(f"🔧 Params: {params}")
            # self.logger.info(f"🔧 Headers: {headers}")
            # if json_payload:
            #     self.logger.info(f"🔧 Payload: {json_payload}")

            response = requests.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                data=json_payload,
                timeout=30,
            )

            # Log response
            # self.logger.info(f"📥 Response status: {response.status_code}")
            # self.logger.info(f"📥 Response body: {response.text}")

            if response.status_code != 200:
                error_msg = f"API Error {
                    response.status_code}: {
                    response.text}"
                self.logger.error(error_msg)
                return None

            return response.json()

        except Exception as e:
            self.logger.error(f"Request failed: {str(e)}")
            return None

    def generate_signature(
        self, endpoint: str, params: dict, payload_str: str = None
    ) -> str:
        # 1. Filter parameter (exclude access_token dan sign)
        exclude_keys = ["access_token", "sign"]
        filtered_params = {
            k: str(v)
            for k, v in params.items()
            if k not in exclude_keys and v is not None
        }

        # 2. Urutkan parameter secara alfabet
        sorted_params = sorted(filtered_params.items(), key=lambda x: x[0])

        # 3. Bangun parameter string format {key}{value}
        param_string = "".join([f"{k}{v}" for k, v in sorted_params])

        # 4. Gunakan FULL endpoint path
        sign_string = f"{endpoint}{param_string}"

        # 5. Tambahkan payload jika ada (dalam bentuk string sudah
        # di-serialize)
        if payload_str is not None:
            sign_string += payload_str  # Gunakan string yang sudah di-serialize

        # 6. Bungkus dengan app_secret
        wrapped_string = (
            f"{self.config.app_secret}{sign_string}{self.config.app_secret}"
        )

        # 7. Generate HMAC-SHA256
        signature = hmac.new(
            self.config.app_secret.encode("utf-8"),
            wrapped_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Debug
        # self.logger.info(f"Signature base string: {wrapped_string}")
        # self.logger.info(f"Generated signature: {signature}")

        return signature

    def refresh_access_token(self) -> bool:
        """Refresh Tiktok access token using refresh token"""
        try:
            if not self.config.refresh_token:
                self.logger.error("No refresh token available")
                return False

            if self.config.is_refresh_token_expired():
                self.logger.error("Refresh token has expired")
                return False

            params = {
                "app_key": self.config.app_key,
                "app_secret": self.config.app_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.config.refresh_token,
            }

            # Use the auth endpoint URL
            response = requests.get(
                f"{self.AUTH_URL}/api/v2/token/refresh", params=params, timeout=10
            )

            response_data = response.json()
            self.logger.info(f"Token refresh response: {response_data}")

            if response_data.get("code") == 0:
                self.config.update_token_info(response_data)
                self.logger.info("Successfully refreshed Tiktok access token")
                return True

            error_msg = response_data.get("message", "Unknown error")
            self.logger.error(f"Failed to refresh token: {error_msg}")
            return False

        except Exception as e:
            self.logger.error(f"Error refreshing Tiktok token: {str(e)}")
            return False

    def get_access_token(self) -> bool:
        """Get Tiktok access token using authorization code"""
        try:
            if not self.config.code:
                raise ValueError("Authorization code is empty")

            params = {
                "app_key": self.config.app_key,
                "app_secret": self.config.app_secret,
                "auth_code": self.config.code,
                "grant_type": "authorized_code",
            }

            response = requests.get(
                f"{self.AUTH_URL}/api/v2/token/get", params=params)
            response.raise_for_status()
            response_data = response.json()

            if response_data.get("code") == 0:
                self.config.update_token_info(response_data)
                self.logger.info("Successfully obtained Tiktok access token")
                return True
            else:
                error_msg = response_data.get("message", "Unknown error")
                self.logger.error(f"Failed to get token: {error_msg}")
                return False

        except Exception as e:
            self.logger.error(f"Error getting Tiktok token: {str(e)}")
            return False
