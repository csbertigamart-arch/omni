import logging
from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd
from api_clients import IAPIClient
from file_system_manager import FileSystemManager


class IWalletManager(ABC):
    """Abstract base class for wallet transaction management"""

    @abstractmethod
    def get_transactions(self, month=None, year=None,
                         transaction_tab_type=None):
        pass

    @abstractmethod
    def display_transactions(self, transactions):
        pass

    @abstractmethod
    def export_to_csv(self, transactions, filename):
        pass


class ShopeeWalletManager(IWalletManager):

    def __init__(self, api_client: IAPIClient, fs_manager: FileSystemManager, google_sheets_manager=None):
        self.fs = fs_manager
        self.api = api_client
        self.google_sheets_manager = google_sheets_manager  # TAMBAH INI
        self.logger = logging.getLogger(__name__)

    def _log(self, message, level="info"):
        """Helper method for logging"""
        if level == "info":
            self.logger.info(message)
            print(message)
        elif level == "error":
            self.logger.error(message)
            print(f"❌ {message}")

    def _shorten_text(self, text, max_length):
        """Helper method to shorten long text for display"""
        return (text[:max_length] + "...") if len(text) > max_length else text

    def _format_amount(self, amount):
        """Format amount with currency"""
        return f"Rp{amount:,.2f}"

    def _get_default_filename(self, month, year, transaction_type):
        """Generate default filename for export"""
        type_str = transaction_type if transaction_type else "all"
        return f"wallet_transactions_{month}_{year}_{type_str}.csv"

    def get_transactions(self, month=None, year=None,
                         transaction_tab_type=None):
        """Get wallet transactions from Shopee API"""
        try:
            response = self.api.get_wallet_transactions(
                month=month, year=year, transaction_tab_type=transaction_tab_type
            )

            if (
                response is None
                or not isinstance(response, dict)
                or not response.get("response")
            ):
                self.logger.warning(
                    "No transaction data found in API response")
                return None

            return response["response"].get("transaction_list", [])

        except Exception as e:
            self.logger.error(f"Error getting transactions: {str(e)}")
            raise

    def process_transactions(self, raw_transactions):
        """Process raw transaction data into structured format"""
        transaction_records = []
        total_amount = 0

        for tx in raw_transactions:
            try:
                date = datetime.fromtimestamp(tx["create_time"])
                amount = float(tx.get("amount", 0))
                total_amount += amount

                transaction_records.append(
                    {
                        "Date": date,
                        "Order SN": tx.get("order_sn", ""),
                        "Description": tx.get("description", ""),
                        "Amount": amount,
                        "Status": tx.get("status", ""),
                        "Transaction Type": tx.get("transaction_type", ""),
                        "Tab Type": tx.get("transaction_tab_type", ""),
                        "Buyer Name": tx.get("buyer_name", "Unknown"),
                    }
                )
            except Exception as e:
                self.logger.warning(
                    f"Skipping malformed transaction: {
                        str(e)}"
                )
                continue

        return {
            "transactions": transaction_records,
            "total_amount": total_amount,
            "count": len(transaction_records),
        }

    def display_transactions(self, processed_data):
        """Display transactions in formatted table"""
        if not processed_data or not processed_data["transactions"]:
            print("No transactions to display")
            return

        # Create DataFrame for display
        df = pd.DataFrame(processed_data["transactions"])
        df.sort_values("Date", inplace=True)

        # Format for display
        df_display = df.copy()
        df_display["Date"] = df_display["Date"].dt.strftime("%Y-%m-%d %H:%M")
        df_display["Order"] = df_display["Order SN"].apply(
            lambda x: self._shorten_text(x, 12)
        )
        df_display["Buyer"] = df_display["Buyer Name"].apply(
            lambda x: self._shorten_text(x, 10)
        )
        df_display["Amount"] = df_display["Amount"].apply(self._format_amount)

        # Print summary
        print(f"\n📊 Total transactions: {processed_data['count']}")
        print(
            f"💰 Total amount: {
                self._format_amount(
                    processed_data['total_amount'])}\n"
        )

    def export_to_csv(self, processed_data, filename):
        """Export transactions to CSV file"""
        if not processed_data or not processed_data["transactions"]:
            self.logger.warning("No transactions to export")
            return False

        try:
            df = pd.DataFrame(processed_data["transactions"])

            # Sort by Date before exporting
            df.sort_values("Date", inplace=True)

            # Format date for CSV
            df["Date"] = df["Date"].dt.strftime("%Y-%m-%d %H:%M")

            df.to_csv(filename, index=False, encoding="utf-8")
            return True
        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {str(e)}")
            return False

    def export_order_numbers_to_file(self, transactions, month, year):
        """Export order numbers to text file dengan logging detail"""
        try:
            # Create directories if they don't exist
            filename = f"order_numbers_{month:02d}_{year}.txt"
            filepath = self.fs.get_full_path("temp_file", filename)

            self._log(f"🔄 Starting export_order_numbers_to_file: {filepath}")
            self._log(f"📊 Processing {len(transactions)} transactions")

            order_numbers = set()
            order_count = 0

            for tx in transactions:
                if tx.get("order_sn"):
                    order_numbers.add(tx["order_sn"])
                    order_count += 1
                else:
                    self._log(f"⚠️ Transaction without order_sn: {tx}")

            self._log(f"📋 Found {order_count} transactions with order_sn")
            self._log(f"📦 Unique order numbers: {len(order_numbers)}")

            # Write to file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(order_numbers))

            # Verify file was written
            with open(filepath, "r", encoding="utf-8") as f:
                written_lines = f.readlines()
                self._log(
                    f"📝 File written: {len(written_lines)} lines in file")

            self._log(
                f"✅ Successfully exported {len(order_numbers)} order numbers to {filepath}")
            return filepath, len(order_numbers)

        except Exception as e:
            self._log(f"❌ Error in export_order_numbers_to_file: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, 0

    def show_wallet_transactions(self):
        """Interactive method to show and export transactions"""
        print("\n=== Wallet Transactions ===")

        try:
            # Get month/year selection
            month, year = self._get_month_year_selection()

            # Get transaction type selection
            transaction_type = self._get_transaction_type_selection()

            # Get transactions
            raw_transactions = self.get_transactions(
                month=month, year=year, transaction_tab_type=transaction_type
            )

            if not raw_transactions:
                print("No transactions found for selected criteria")
                return

            # Process transactions
            processed_data = self.process_transactions(raw_transactions)

            # Display transactions
            self.display_transactions(processed_data)

            # Export to CSV
            filename = self.fs.get_full_path(
                "report", self._get_default_filename(
                    month, year, transaction_type)
            )
            if self.export_to_csv(processed_data, filename):
                print(f"💾 Saved data to {filename}")
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            self.logger.exception("Error in show_wallet_transactions")

    def _process_get_order_numbers(self):
        """Option 1: Get order numbers from wallet transactions and process - FIXED"""
        try:
            month, year = self._get_month_year_selection()

            transaction_type = "wallet_order_income"

            self._log(
                f"Getting wallet transactions for {month}/{year}, type: {transaction_type}"
            )

            raw_transactions = self.get_transactions(
                month=month, year=year, transaction_tab_type=transaction_type
            )

            if not raw_transactions:
                self._log("No transactions found for selected criteria")
                return

            filename, count = self.export_order_numbers_to_file(
                raw_transactions, month, year
            )

            self._log(f"\n✅ Saved {count} order numbers to {filename}")

            # Return the filename for processing by the platform handler
            return filename

        except Exception as e:
            self._log(
                f"Error in _process_get_order_numbers: {
                    str(e)}",
                "error",
            )
            import traceback

            traceback.print_exc()
            return None

    def _get_month_year_selection(self):
        """Helper method to get month/year from user - IMPROVED"""
        current_month = datetime.now().month
        current_year = datetime.now().year

        print(f"\nCurrent month: {current_month}, Year: {current_year}")
        print("Select month:")
        for i in range(1, 13):
            print(f"{i}. {datetime(2023, i, 1).strftime('%B')}")
        print("0. Current month")

        while True:
            try:
                month_choice = input("Enter month choice (0-12): ").strip()
                if month_choice.isdigit() and 0 <= int(month_choice) <= 12:
                    break
                print("Invalid input. Please enter a number between 0-12")
            except KeyboardInterrupt:
                raise
            except BaseException:
                print("Invalid input. Please enter a number between 0-12")

        month_choice = int(month_choice)
        if month_choice == 0:
            return current_month, current_year
        else:
            month = month_choice
            # Handle year logic properly
            if month_choice > current_month:
                year = (
                    current_year - 1
                )  # Previous year if selected month is in the future
            else:
                year = current_year
            return month, year

    def _get_transaction_type_selection(self):
        """Helper method to get transaction type from user"""
        tab_types = {
            "0": None,
            "1": "wallet_order_income",
            "2": "wallet_adjustment_filter",
            "3": "wallet_wallet_payment",
            "4": "wallet_refund_from_order",
            "5": "wallet_withdrawals",
            "6": "fast_escrow_repayment",
            "7": "fast_pay",
            "8": "seller_loan",
            "9": "corporate_loan",
        }

        print("\nSelect transaction type:")
        print("0. All transaction types")
        print("1. Order income")
        print("2. Adjustment")
        print("3. Wallet payment")
        print("4. Refund from order")
        print("5. Withdrawals")
        print("6. Fast escrow repayment")
        print("7. Fast pay")
        print("8. Seller loan")
        print("9. Corporate loan")

        while True:
            tab_choice = input("Enter transaction type (0-9): ").strip()
            if tab_choice in tab_types:
                return tab_types[tab_choice]
            print("Invalid input. Please enter a number between 0-9")
