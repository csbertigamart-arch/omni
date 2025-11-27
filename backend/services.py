from api_clients import LazadaAPIClient, ShopeeAPIClient, TiktokAPIClient
from config_managers import (LazadaConfigManager, ShopeeConfigManager,
                             TiktokConfigManager)
from order_managers import (LazadaOrderManager, ShopeeOrderManager,
                            TiktokOrderManager)
from product_managers import (LazadaProductManager, ShopeeProductManager,
                              TiktokProductManager)
from wallet_manager import ShopeeWalletManager


class ShopeeServices:
    def __init__(
        self,
        fs,
        config_cls=ShopeeConfigManager,
        api_cls=ShopeeAPIClient,
        product_mgr_cls=ShopeeProductManager,
        order_mgr_cls=ShopeeOrderManager,
        wallet_mgr_cls=ShopeeWalletManager,
    ):
        self.config = config_cls(fs)
        self.api = api_cls(self.config)
        self.product_mgr = product_mgr_cls(self.api)
        self.order_mgr = order_mgr_cls(self.api)
        self.wallet_mgr = wallet_mgr_cls(self.api, fs)


class LazadaServices:
    def __init__(
        self,
        fs,
        config_cls=LazadaConfigManager,
        api_cls=LazadaAPIClient,
        product_mgr_cls=LazadaProductManager,
        order_mgr_cls=LazadaOrderManager,
    ):
        self.config = config_cls(fs)
        self.api = api_cls(self.config)
        self.product_mgr = product_mgr_cls(self.api)
        self.order_mgr = order_mgr_cls(self.api)


class TiktokServices:
    def __init__(
        self,
        fs,
        config_cls=TiktokConfigManager,
        api_cls=TiktokAPIClient,
        product_mgr_cls=TiktokProductManager,
        order_mgr_cls=TiktokOrderManager,
    ):
        self.config = config_cls(fs)
        self.api = api_cls(self.config)
        self.product_mgr = product_mgr_cls(self.api)
        self.order_mgr = order_mgr_cls(self.api)
