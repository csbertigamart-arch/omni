import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from file_system_manager import FileSystemManager


class IConfigManager(ABC):
    @abstractmethod
    def load_config(self):
        pass

    @abstractmethod
    def save_config(self):
        pass


class ShopeeConfigManager(IConfigManager):
    def __init__(self, fs_manager: FileSystemManager):
        self.fs = fs_manager
        self.config_file = self.fs.get_full_path(
            "config", "shopee_config.json")
        self.partner_id = ""
        self.partner_key = ""
        self.shop_id = ""
        self.code = ""
        self.access_token = ""
        self.refresh_token = ""
        self.token_expiry = None
        self.refresh_token_expiry = None
        self.load_config()

    def load_config(self):
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.partner_id = int(config.get("partner_id", 0))
                self.partner_key = str(config.get("partner_key", ""))
                self.shop_id = int(config.get("shop_id", 0))
                self.code = config.get("code", "")
                self.access_token = config.get("access_token", "")
                self.refresh_token = config.get("refresh_token", "")

                # Load expiry times
                expiry_str = config.get("token_expiry")
                self.token_expiry = (
                    datetime.fromisoformat(expiry_str) if expiry_str else None
                )

                refresh_expiry_str = config.get("refresh_token_expiry")
                self.refresh_token_expiry = (
                    datetime.fromisoformat(refresh_expiry_str)
                    if refresh_expiry_str
                    else None
                )

        except FileNotFoundError:
            self.save_config()

    def save_config(self):
        config = {
            "partner_id": self.partner_id,
            "partner_key": self.partner_key,
            "shop_id": self.shop_id,
            "code": self.code,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expiry": (
                self.token_expiry.isoformat() if self.token_expiry else None
            ),
            "refresh_token_expiry": (
                self.refresh_token_expiry.isoformat()
                if self.refresh_token_expiry
                else None
            ),
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

    def is_token_expired(self):
        """Check if access token is expired"""
        if not self.token_expiry or not self.access_token:
            return True
        return datetime.now() > self.token_expiry

    def is_refresh_token_expired(self):
        """Check if refresh token is expired"""
        if not self.refresh_token_expiry or not self.refresh_token:
            return True
        return datetime.now() > self.refresh_token_expiry

    def update_token_info(self, access_token, refresh_token, expire_in):
        """Update token information with expiry time"""
        self.access_token = access_token
        self.refresh_token = refresh_token
        # Calculate expiry times (expire_in is in seconds)
        self.token_expiry = datetime.now() + timedelta(seconds=expire_in)
        # Refresh token expires in 30 days (2592000 seconds)
        self.refresh_token_expiry = datetime.now() + timedelta(seconds=2592000)
        self.save_config()

    def update_code(self, new_code):
        self.code = new_code
        self.save_config()
        return True


class LazadaConfigManager(IConfigManager):
    def __init__(self, fs_manager: FileSystemManager):
        self.fs = fs_manager
        self.config_file = self.fs.get_full_path(
            "config", "lazada_config.json")
        self.app_key = ""
        self.app_secret = ""
        self.code = ""
        self.access_token = ""
        self.refresh_token = ""
        self.token_expiry = None
        self.refresh_token_expiry = None
        self.load_config()

    def update_token_info(self, access_token: str,
                          refresh_token: str, expires_in: int):
        """Update token information with new values"""
        if not all([access_token, refresh_token]):
            raise ValueError("Access token and refresh token cannot be empty")

        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = datetime.now() + timedelta(seconds=expires_in)

        # Lazada refresh tokens typically last 180 days
        self.refresh_token_expiry = datetime.now() + timedelta(days=180)

        self.save_config()

    def load_config(self):
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.app_key = str(config.get("app_key", ""))
                self.app_secret = str(config.get("app_secret", ""))
                self.code = str(config.get("code", ""))
                self.access_token = str(config.get("access_token", ""))
                self.refresh_token = str(config.get("refresh_token", ""))

                # Load expiry times
                expiry_str = config.get("token_expiry")
                self.token_expiry = (
                    datetime.fromisoformat(expiry_str) if expiry_str else None
                )

                refresh_expiry_str = config.get("refresh_token_expiry")
                self.refresh_token_expiry = (
                    datetime.fromisoformat(refresh_expiry_str)
                    if refresh_expiry_str
                    else None
                )

        except FileNotFoundError:
            self.save_config()

    def save_config(self):
        config = {
            "app_key": self.app_key,
            "app_secret": self.app_secret,
            "code": self.code,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expiry": (
                self.token_expiry.isoformat() if self.token_expiry else None
            ),
            "refresh_token_expiry": (
                self.refresh_token_expiry.isoformat()
                if self.refresh_token_expiry
                else None
            ),
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

    def is_token_expired(self):
        if not self.token_expiry or not self.access_token:
            return True
        return datetime.now() > self.token_expiry

    def is_refresh_token_expired(self):
        if not self.refresh_token_expiry or not self.refresh_token:
            return True
        return datetime.now() > self.refresh_token_expiry

    def update_code(self, new_code):
        self.code = new_code
        self.save_config()
        return True


class TiktokConfigManager(IConfigManager):
    def __init__(self, fs_manager: FileSystemManager):
        self.fs = fs_manager
        self.config_file = self.fs.get_full_path(
            "config", "tiktok_config.json")
        self.app_key = ""
        self.app_secret = ""
        self.code = ""
        self.access_token = ""
        self.refresh_token = ""
        self.token_expiry = None
        self.refresh_token_expiry = None
        self.open_id = ""
        self.seller_name = ""
        self.seller_region = ""
        self.user_type = None
        self.granted_scopes = []
        self.shops_file = self.fs.get_full_path("config", "shops.json")
        self.shop_id = ""
        self.shop_cipher = ""
        self.load_shops()
        self.load_config()

    def load_shops(self):
        try:
            with open(self.shops_file, "r", encoding="utf-8") as f:
                shops_data = json.load(f)
                if shops_data.get("code") == 0 and shops_data.get("data", {}).get(
                    "shops"
                ):
                    first_shop = shops_data["data"]["shops"][0]
                    self.shop_id = first_shop["id"]
                    self.shop_cipher = first_shop["cipher"]
        except FileNotFoundError:
            logging.error("Shops file not found")

    def load_config(self):
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.app_key = str(config.get("app_key", ""))
                self.app_secret = str(config.get("app_secret", ""))
                self.code = str(config.get("code", ""))
                self.access_token = str(config.get("access_token", ""))
                self.refresh_token = str(config.get("refresh_token", ""))
                self.open_id = str(config.get("open_id", ""))
                self.seller_name = str(config.get("seller_name", ""))
                self.seller_region = str(config.get("seller_region", ""))
                self.user_type = config.get("user_type")
                self.granted_scopes = config.get("granted_scopes", [])

                # Load expiry times
                expiry_str = config.get("token_expiry")
                self.token_expiry = (
                    datetime.fromisoformat(expiry_str) if expiry_str else None
                )

                refresh_expiry_str = config.get("refresh_token_expiry")
                self.refresh_token_expiry = (
                    datetime.fromisoformat(refresh_expiry_str)
                    if refresh_expiry_str
                    else None
                )

        except FileNotFoundError:
            self.save_config()

    def save_config(self):
        config = {
            "app_key": self.app_key,
            "app_secret": self.app_secret,
            "code": self.code,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_expiry": (
                self.token_expiry.isoformat() if self.token_expiry else None
            ),
            "refresh_token_expiry": (
                self.refresh_token_expiry.isoformat()
                if self.refresh_token_expiry
                else None
            ),
            "open_id": self.open_id,
            "seller_name": self.seller_name,
            "seller_region": self.seller_region,
            "user_type": self.user_type,
            "granted_scopes": self.granted_scopes,
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

    def is_token_expired(self):
        if not self.token_expiry or not self.access_token:
            return True
        return datetime.now() > self.token_expiry

    def is_refresh_token_expired(self):
        if not self.refresh_token_expiry or not self.refresh_token:
            return True
        return datetime.now() > self.refresh_token_expiry

    def update_token_info(self, response_data: dict):
        """Update all token information from API response"""
        if not response_data or "data" not in response_data:
            raise ValueError("Invalid response data")

        data = response_data["data"]
        self.access_token = data.get("access_token", "")
        self.refresh_token = data.get("refresh_token", "")
        self.open_id = data.get("open_id", "")
        self.seller_name = data.get("seller_name", "")
        self.seller_region = data.get("seller_base_region", "")
        self.user_type = data.get("user_type")
        self.granted_scopes = data.get("granted_scopes", [])

        # Calculate expiry times
        access_expiry = data.get("access_token_expire_in")
        if access_expiry:
            self.token_expiry = datetime.fromtimestamp(access_expiry)

        refresh_expiry = data.get("refresh_token_expire_in")
        if refresh_expiry:
            self.refresh_token_expiry = datetime.fromtimestamp(refresh_expiry)

        self.save_config()

    def update_code(self, new_code):
        self.code = new_code
        self.save_config()
        return True
