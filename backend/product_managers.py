import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional

from api_clients import IAPIClient
from lazop import LazopRequest


class IProductManager(ABC):
    @abstractmethod
    def update_wholesale_price(self, item_id, wholesale_tiers):
        pass

    @abstractmethod
    def get_product_details(self, item_id, model_id=None):
        pass

    @abstractmethod
    def update_stock(self, item_id, model_id, new_qty):
        pass

    @abstractmethod
    def update_price(self, item_id, model_id, new_price):
        pass


class BaseProductManager(IProductManager):
    """Base class for product managers with common functionality"""

    def __init__(self, api_client: IAPIClient):
        self.api = api_client
        self.logger = logging.getLogger(__name__)

    def update_wholesale_price(self, item_id, wholesale_tiers):
        """Default implementation for unsupported wholesale updates"""
        self.logger.warning(
            f"{self.__class__.__name__} does not support wholesale tiers"
        )
        return False

    @abstractmethod
    def get_product_details(self, item_id, model_id=None):
        pass

    @abstractmethod
    def update_stock(self, item_id, model_id, new_qty):
        pass

    @abstractmethod
    def update_price(self, item_id, model_id, new_price):
        pass


class ShopeeProductManager(BaseProductManager):
    """Shopee-specific product operations"""

    def _get_model_variation_info(self, model_response, model_id):
        """Extract variation information for a specific model"""
        variations = []
        for model in model_response.get("model", []):
            if model.get("model_id") == model_id:
                tier_indexes = model.get("tier_index", [])
                tier_variations = model_response.get("tier_variation", [])

                for i, tier_idx in enumerate(tier_indexes):
                    if i < len(tier_variations):
                        tier = tier_variations[i]
                        if tier_idx < len(tier["option_list"]):
                            option = tier["option_list"][tier_idx]["option"]
                            variations.append(f"{tier['name']}: {option}")
                return ", ".join(variations)
        return None

    def _get_model_price_info(self, model):
        """Extract price information from model data"""
        if "price_info" in model and model["price_info"]:
            return model["price_info"][0].get("current_price")
        return model.get("price")

    def _get_model_stock_info(self, model):
        """Extract stock information from model data"""
        if "stock_info_v2" in model:
            return (
                model["stock_info_v2"]
                .get("summary_info", {})
                .get("total_available_stock")
            )
        return None

    def _get_base_product_info(self, item_data):
        """Extract base product information from item data"""
        return {
            "item_id": item_data.get("item_id"),
            "name": item_data.get("item_name", "Unknown Product"),
            "status": item_data.get("item_status", "UNKNOWN"),
            "has_model": item_data.get("has_model", False),
            "current_stock": None,
            "current_price": None,
            "variation_name": None,
            "full_name": item_data.get("item_name", "Unknown Product"),
            "item_sku": item_data.get("item_sku", ""),
            "model_sku": item_data.get("model_sku", ""),
        }

    def get_product_details(self, item_id, model_id=None):
        """Get complete product details including name, variation info, current stock, and current price"""
        try:
            params = {
                "item_id_list": str(item_id),
                "need_tax_info": False,
                "need_complaint_policy": False,
            }

            response = self.api.make_request(
                endpoint="/api/v2/product/get_item_base_info", params=params
            )

            if not self._is_valid_response(response):
                return None

            item_data = response["response"]["item_list"][0]
            product_info = self._get_base_product_info(item_data)

            if not product_info["has_model"] or not model_id:
                self._fill_non_variation_product_info(item_data, product_info)
                return product_info

            self._fill_variation_product_info(item_id, model_id, product_info)
            return product_info

        except Exception as e:
            self.logger.error(f"Error getting product details: {str(e)}")
            return None

    def _is_valid_response(self, response):
        """Check if API response is valid"""
        return (
            response
            and "response" in response
            and "item_list" in response["response"]
            and response["response"]["item_list"]
        )

    def _fill_non_variation_product_info(self, item_data, product_info):
        """Fill product info for non-variation products"""
        if "price_info" in item_data and item_data["price_info"]:
            product_info["current_price"] = item_data["price_info"][0].get(
                "current_price"
            )

        if "stock_info_v2" in item_data:
            product_info["current_stock"] = (
                item_data["stock_info_v2"]
                .get("summary_info", {})
                .get("total_available_stock")
            )
        elif "stock_info" in item_data:
            product_info["current_stock"] = (
                item_data["stock_info"][0].get("stock")
                if isinstance(item_data["stock_info"], list)
                else item_data["stock_info"].get("stock")
            )

    def _fill_variation_product_info(self, item_id, model_id, product_info):
        """Fill product info for variation products"""
        model_response = self.api.make_request(
            endpoint="/api/v2/product/get_model_list", params={"item_id": item_id}
        )

        if not model_response or "response" not in model_response:
            return

        for model in model_response["response"].get("model", []):
            if model.get("model_id") == model_id:
                product_info["variation_name"] = self._get_model_variation_info(
                    model_response["response"], model_id
                )
                product_info["full_name"] = (
                    f"{product_info['name']} - {product_info['variation_name']}"
                )
                product_info["current_price"] = self._get_model_price_info(
                    model)
                product_info["current_stock"] = self._get_model_stock_info(
                    model)
                product_info["model_sku"] = model.get("model_sku", "")
                return

        self.logger.warning(f"Model {model_id} not found for item {item_id}")

    def update_stock(self, item_id, model_id, new_qty):
        """Update stock for a product or variation"""
        stock_data = {
            "item_id": item_id,
            "stock_list": [{"seller_stock": [{"stock": new_qty}]}],
        }

        if model_id:
            stock_data["stock_list"][0]["model_id"] = model_id

        return self.api.make_request(
            endpoint="/api/v2/product/update_stock", method="POST", payload=stock_data
        )

    def update_price(self, item_id, model_id, new_price):
        """Update price for a product or variation"""
        payload = {
            "item_id": item_id,
            "price_list": [
                {"model_id": model_id if model_id else 0,
                    "original_price": new_price}
            ],
        }

        return self.api.make_request(
            endpoint="/api/v2/product/update_price", method="POST", payload=payload
        )

    def update_wholesale_price(self, item_id, wholesale_tiers):
        """Update wholesale price tiers for a product with better validation"""
        try:
            if not isinstance(item_id, int) or item_id <= 0:
                raise ValueError("Invalid item ID")

            if not isinstance(wholesale_tiers, list) or not wholesale_tiers:
                raise ValueError("Wholesale tiers must be a non-empty list")

            for tier in wholesale_tiers:
                if not all(
                    isinstance(tier.get(key), (int, float))
                    for key in ["min_count", "unit_price", "max_count"]
                ):
                    raise ValueError("Invalid tier data types")

            payload = {"item_id": item_id, "wholesale": wholesale_tiers}

            self.logger.info(
                f"Updating wholesale for item {item_id} with tiers: {wholesale_tiers}"
            )
            response = self.api.make_request(
                endpoint="/api/v2/product/update_item", method="POST", payload=payload
            )

            if response and "error" in response:
                self.logger.error(f"API Error: {response.get('message')}")

            return response

        except Exception as e:
            self.logger.error(f"Error in update_wholesale_price: {str(e)}")
            raise

    def delete_wholesale_tiers(self, item_id):
        """Delete all wholesale tiers for an item"""
        try:
            if not isinstance(item_id, int) or item_id <= 0:
                raise ValueError("Invalid item ID")

            payload = {"item_id": item_id, "wholesale": []}

            self.logger.info(f"Deleting wholesale for item {item_id}")
            response = self.api.make_request(
                endpoint="/api/v2/product/update_item", method="POST", payload=payload
            )

            if response and "error" in response:
                self.logger.error(f"API Error: {response.get('message')}")
                return response

            return response
        except Exception as e:
            self.logger.error(f"Error deleting wholesale: {str(e)}")
            raise


class LazadaProductManager(BaseProductManager):
    """Lazada-specific product operations"""

    def get_product_details(
        self, item_id: str, sku_id: Optional[str] = None
    ) -> Optional[Dict]:
        """Get product details from Lazada API with variation information"""
        try:
            if not item_id:
                self.logger.error("Item ID is required")
                return None

            request = LazopRequest("/product/item/get", "GET")
            request.add_api_param("item_id", str(item_id))

            response = self.api.client.execute(
                request, self.api.config.access_token)

            if not hasattr(response, "body") or not isinstance(
                    response.body, dict):
                self.logger.error(
                    f"Invalid API response for item {item_id}: {
                        type(response)}"
                )
                return None

            if not self._is_valid_response(response):
                self.logger.error(
                    f"Invalid API response for item {item_id}: {
                        response.body.get(
                            'message', 'Unknown error')}"
                )
                return None

            data = response.body["data"]
            attributes = data.get("attributes", {})
            skus = data.get("skus", [])

            target_sku = None
            if sku_id:
                for sku in skus:
                    if str(sku.get("SkuId", "")).strip() == str(
                            sku_id).strip():
                        target_sku = sku
                        break
            elif skus:
                target_sku = skus[0]

            if not target_sku:
                self.logger.error(f"No matching SKU found for item {item_id}")
                return None

            variation_name = ""
            sale_prop = target_sku.get("saleProp", {})
            if sale_prop:
                variations = [
                    f"{key}: {value}" for key,
                    value in sale_prop.items()]
                variation_name = ", ".join(variations)

            product_name = str(attributes.get("name", "Unknown Product"))
            full_name = product_name
            if variation_name:
                full_name = f"{product_name} - {variation_name}"

            current_stock = int(target_sku.get("quantity", 0))
            current_price = self._get_current_price(target_sku)

            return {
                "item_id": str(item_id),
                "name": product_name,
                "status": str(data.get("status", "Unknown")),
                "current_stock": current_stock,
                "current_price": current_price,
                "variation_name": variation_name,
                "full_name": full_name,
                "sku_id": str(target_sku.get("SkuId", "")),
                "seller_sku": str(target_sku.get("SellerSku", "")),
            }

        except Exception as e:
            self.logger.error(
                f"Error getting product details for item {item_id}: {str(e)}"
            )
            return None

    def _is_valid_response(self, response):
        """Check if Lazada response is valid"""
        return (
            response
            and hasattr(response, "body")
            and isinstance(response.body, dict)
            and response.body.get("code") == "0"
            and "data" in response.body
        )

    def _get_current_price(self, sku: dict) -> float:
        """Get current price (prioritize special price if available)"""
        try:
            price = float(sku.get("price", 0))
            special_price = sku.get("special_price")

            if special_price:
                try:
                    special_price = float(special_price)
                    return min(price, special_price)
                except (ValueError, TypeError):
                    pass

            return price
        except (ValueError, TypeError):
            return 0.0

    def update_price(self, payload_items):
        """Update only price with empty SalePrice"""
        try:
            payload_xml = "<Request><Product><Skus>"

            for item in payload_items:
                payload_xml += f"""
                <Sku>
                    <ItemId>{item['ItemId']}</ItemId>
                    <SkuId>{item['SkuId']}</SkuId>
                    <Price>{item['Price']:.2f}</Price>
                    <SalePrice>{item['Price']:.2f}</SalePrice>
                    <SaleStartDate>2025-01-11</SaleStartDate>
                    <SaleEndDate>2025-01-15</SaleEndDate>
                </Sku>"""

            payload_xml += "</Skus></Product></Request>"

            request = LazopRequest("/product/price_quantity/update")
            request.add_api_param("payload", payload_xml)

            response = self.api.client.execute(
                request, self.api.config.access_token)
            return self._parse_response(response)

        except Exception as e:
            self.logger.error(f"Error updating price: {str(e)}")
            return False, str(e)

    def update_stock(self, payload_items):
        """Update only stock quantity"""
        try:
            payload_xml = "<Request><Product><Skus>"

            for item in payload_items:
                payload_xml += f"""
                <Sku>
                    <ItemId>{item['ItemId']}</ItemId>
                    <SkuId>{item['SkuId']}</SkuId>
                    <Quantity>{item['Quantity']}</Quantity>
                </Sku>"""

            payload_xml += "</Skus></Product></Request>"

            request = LazopRequest("/product/price_quantity/update")
            request.add_api_param("payload", payload_xml)

            response = self.api.client.execute(
                request, self.api.config.access_token)
            return self._parse_response(response)

        except Exception as e:
            self.logger.error(f"Error updating stock: {str(e)}")
            return False, str(e)

    def _parse_response(self, response):
        """Parse API response"""
        if response and "code" in response.body and response.body["code"] == "0":
            return True, response.body
        else:
            error_msg = (
                response.body.get("message", "Unknown error")
                if response
                else "No response from API"
            )
            return False, error_msg


class TiktokProductManager(BaseProductManager):
    """Tiktok-specific product operations"""

    API_VERSION = "202309"

    def update_stock(self, item_id: str,
                     model_id: Optional[str], new_qty: int) -> bool:
        try:
            endpoint = (
                f"/product/{self.API_VERSION}/products/{item_id}/inventory/update"
            )
            payload = {
                "skus": [
                    {
                        "id": str(model_id or item_id),
                        "inventory": [{"quantity": int(new_qty)}],
                    }
                ]
            }

            return self._make_tiktok_request(endpoint, payload)
        except Exception as e:
            self.logger.error(f"Update failed: {str(e)}")
            return False

    def update_price(
        self, item_id: str, model_id: Optional[str], new_price: float
    ) -> bool:
        try:
            endpoint = f"/product/{self.API_VERSION}/products/{item_id}/prices/update"
            payload = {
                "skus": [
                    {
                        "id": str(model_id or item_id),
                        "price": {
                            "currency": "IDR",
                            "amount": str(round(new_price, 2)),
                        },
                        "external_list_prices": [],
                    }
                ]
            }

            return self._make_tiktok_request(endpoint, payload)
        except Exception as e:
            self.logger.error(f"Price update failed: {str(e)}")
            return False

    def get_product_details(
        self, item_id: str, model_id: Optional[str] = None
    ) -> Optional[Dict]:
        """Get product details from Tiktok API using new endpoint"""
        try:
            endpoint = f"/product/{self.API_VERSION}/products/{item_id}"
            response = self.api.make_request(endpoint, method="GET")

            if not self._is_valid_response(response):
                return None

            data = response.get("data", {})

            base_info = {
                "item_id": item_id,
                "name": data.get("title", ""),
                "status": data.get("status"),
            }

            if model_id:
                for sku in data.get("skus", []):
                    if str(sku.get("id")) == str(model_id):
                        variation_name = ""
                        sales_attributes = sku.get("sales_attributes", [])
                        if sales_attributes:
                            variation_name = sales_attributes[0].get(
                                "value_name", "")

                        return {
                            **base_info,
                            "model_id": model_id,
                            "current_price": self._parse_price(sku.get("price")),
                            "current_stock": self._calculate_total_stock(sku),
                            "variation_name": variation_name,
                            "seller_sku": sku.get("seller_sku", ""),
                            "full_name": (
                                f"{base_info['name']} - Varian: {variation_name}"
                                if variation_name
                                else base_info["name"]
                            ),
                        }
                return None

            first_sku = data.get("skus", [{}])[0]
            variation_name = ""
            sales_attributes = first_sku.get("sales_attributes", [])
            if sales_attributes:
                variation_name = sales_attributes[0].get("value_name", "")

            return {
                **base_info,
                "current_price": self._parse_price(first_sku.get("price")),
                "current_stock": self._calculate_total_stock(first_sku),
                "variation_name": variation_name,
                "seller_sku": first_sku.get("seller_sku", ""),
                "full_name": (
                    f"{base_info['name']} - Varian: {variation_name}"
                    if variation_name
                    else base_info["name"]
                ),
            }

        except Exception as e:
            self.logger.error(f"Error getting Tiktok product: {str(e)}")
            return None

    def _parse_price(self, price_data: dict) -> float:
        """Parse price from Tiktok response"""
        if not price_data:
            return 0.0
        price_str = price_data.get("sale_price") or price_data.get(
            "tax_exclusive_price"
        )
        return float(price_str) if price_str else 0.0

    def _calculate_total_stock(self, sku: dict) -> int:
        """Calculate total stock across all warehouses"""
        return sum(inv.get("quantity", 0) for inv in sku.get("inventory", []))

    def _is_valid_response(self, response):
        """Check if Tiktok response is valid"""
        return (
            response
            and response.get("code") == 0
            and "data" in response
            and "skus" in response["data"]
        )

    def _make_tiktok_request(self, endpoint, payload):
        """Helper method for Tiktok API requests"""
        response = self.api.make_request(
            endpoint=endpoint, method="POST", payload=payload
        )

        if not response:
            return False

        if response.get("code") == 0:
            return True

        error_msg = response.get("message", "Unknown error")
        self.logger.error(f"Tiktok API Error: {error_msg}")
        return False

    def get_raw_product_details(self, item_id: str):
        """Get raw product details from Tiktok API"""
        try:
            endpoint = f"/product/{self.API_VERSION}/products/{item_id}"
            response = self.api.make_request(endpoint, method="GET")

            if response and response.get("code") == 0:
                return response.get("data", {})
            return None
        except Exception as e:
            self.logger.error(f"Error getting raw product details: {str(e)}")
            return None

    def update_min_order_quantity(
        self, item_id: str, min_order_quantity: int, new_price: float = None
    ) -> bool:
        """Update minimum order quantity and optionally price for a product"""
        try:
            product_data = self.get_raw_product_details(item_id)
            if not product_data:
                self.logger.error(f"Product {item_id} not found")
                return False

            current_moq = product_data.get("minimum_order_quantity", 1)
            self.logger.info(f"Current MOQ for {item_id}: {current_moq}")
            self.logger.info(f"Requested MOQ: {min_order_quantity}")

            product_data["minimum_order_quantity"] = min_order_quantity

            if new_price is not None:
                for sku in product_data.get("skus", []):
                    sku["price"]["sale_price"] = str(new_price)
                    sku["price"]["tax_exclusive_price"] = str(new_price)

            payload = {}

            if product_data.get("brand", {}).get("id"):
                payload["brand_id"] = product_data["brand"]["id"]

            if product_data.get(
                    "category_chains") and product_data["category_chains"]:
                payload["category_id"] = product_data["category_chains"][-1].get(
                    "id")

            if product_data.get("description"):
                payload["description"] = product_data["description"]

            if product_data.get("main_images"):
                payload["main_images"] = product_data["main_images"]

            payload["minimum_order_quantity"] = min_order_quantity

            if product_data.get("video"):
                payload["video"] = product_data["video"]

            if product_data.get("package_weight"):
                payload["package_weight"] = product_data["package_weight"]

            if product_data.get("product_attributes"):
                payload["product_attributes"] = product_data["product_attributes"]

            if product_data.get("skus"):
                payload["skus"] = product_data["skus"]

            if product_data.get("title"):
                payload["title"] = product_data["title"]

            payload["is_cod_allowed"] = True
            # self.logger.info(f"MOQ Update Request Payload: {payload}")

            endpoint = f"/product/{self.API_VERSION}/products/{item_id}"
            response = self.api.make_request(
                endpoint=endpoint, method="PUT", payload=payload
            )

            # self.logger.info(f"MOQ Update Response: {response}")

            if response and response.get("code") == 0:
                return True
            else:
                error_msg = (
                    response.get("message", "Unknown error")
                    if response
                    else "No response"
                )
                self.logger.error(f"Failed to update MOQ: {error_msg}")
                return False

        except Exception as e:
            self.logger.error(f"Error updating MOQ: {str(e)}")
            return False
