from google_sheets_manager import GoogleSheetsManager
import logging
import os
import sys
import threading
import time
from datetime import datetime

from ecommerce_app import EcommerceApp
from file_system_manager import FileSystemManager
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

app = Flask(__name__)

# PERBAIKAN CORS: Izinkan semua origin untuk development
CORS(
    app,
    origins=["*"],  # Izinkan semua origin
    supports_credentials=True,
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instance
ecommerce_app = None
last_connection_time = None
connection_status = "disconnected"


def get_local_ip():
    """Get local IP address automatically"""
    try:
        # Connect to Google DNS to find local IP
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except BaseException:
        return "127.0.0.1"


def initialize_app():
    """Initialize the ecommerce application"""
    global ecommerce_app, last_connection_time, connection_status
    try:
        from container import Container

        # GUNAKAN INSTANCE google_sheets_manager YANG SUDAH ADA
        container = Container(google_sheets_manager=google_sheets_manager)
        ecommerce_app = container.create_app()
        last_connection_time = datetime.now()
        connection_status = "connected"
        logger.info("✅ Ecommerce app initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize app: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        connection_status = "error"
        return False


@app.route("/")
def home():
    return jsonify(
        {
            "message": "Ecommerce Integration API is running",
            "status": "healthy",
            "timestamp": str(datetime.now()),
            "connection_status": connection_status,
            "local_ip": get_local_ip(),
            "host": request.host,
        }
    )


@app.route("/api/health")
def health_check():
    """Health check endpoint dengan connection tracking"""
    global last_connection_time, connection_status

    current_time = datetime.now()
    last_connection_time = current_time
    connection_status = "connected"

    logger.info(
        f"Health check called from origin: {
            request.headers.get('Origin')}")
    return jsonify(
        {
            "status": "healthy",
            "initialized": ecommerce_app is not None,
            "backend": "running",
            "timestamp": str(current_time),
            "connection_status": connection_status,
            "local_ip": get_local_ip(),
            "client_ip": request.remote_addr,
        }
    )


@app.route("/api/status")
def get_status():
    """Get application status dengan connection tracking"""
    global last_connection_time, connection_status

    try:
        current_time = datetime.now()

        # Check if this is a reconnection
        was_disconnected = connection_status != "connected"
        last_connection_time = current_time
        connection_status = "connected"

        if not ecommerce_app:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Application not initialized",
                        "connection_status": connection_status,
                        "reconnected": was_disconnected,
                    }
                ),
                500,
            )

        status = {
            "shopee": ecommerce_app.shopee.get_detailed_token_status(),
            "lazada": ecommerce_app.lazada.get_detailed_token_status(),
            "tiktok": ecommerce_app.tiktok.get_detailed_token_status(),
        }

        response_data = {
            "success": True,
            "data": status,
            "connection_status": connection_status,
            "timestamp": str(current_time),
        }

        # Only log if reconnected or first connection
        if was_disconnected:
            logger.info("✅ Backend reconnected successfully")
            response_data["reconnected"] = True

        return jsonify(response_data)

    except Exception as e:
        connection_status = "error"
        logger.error(f"Error in get_status: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "connection_status": connection_status,
                }
            ),
            500,
        )


@app.route("/api/execute", methods=["POST"])
def execute_operation():
    """Execute an operation dengan error handling yang lebih baik"""
    global connection_status

    try:
        data = request.get_json()
        if not data:
            return jsonify(
                {"success": False, "error": "No JSON data provided"}), 400

        operation = data.get("operation")
        params = data.get("params", {})

        logger.info(f"Executing operation: {operation} with params: {params}")

        if not ecommerce_app:
            connection_status = "error"
            return (
                jsonify({"success": False,
                         "error": "Application not initialized"}),
                500,
            )

        # Update connection status
        connection_status = "connected"
        last_connection_time = datetime.now()

        # Execute operation based on type
        result = execute_operation_internal(operation, params)

        # Add connection info to result
        if isinstance(result, dict):
            result["connection_status"] = connection_status
            result["timestamp"] = str(datetime.now())

        return jsonify(result)

    except Exception as e:
        connection_status = "error"
        logger.error(f"Error in execute_operation: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "connection_status": connection_status,
                }
            ),
            500,
        )


# Di fungsi execute_operation_internal - tambahkan case untuk
# batch_price_update


def execute_operation_internal(operation, params):
    """Internal method to execute operations"""
    try:
        if operation == "get_token_status":
            return {
                "success": True,
                "data": {
                    "shopee": ecommerce_app.shopee.get_detailed_token_status(),
                    "lazada": ecommerce_app.lazada.get_detailed_token_status(),
                    "tiktok": ecommerce_app.tiktok.get_detailed_token_status(),
                },
            }

        elif operation == "batch_stock_update":
            ecommerce_app.exsport_before_update()
            ecommerce_app.process_batch_stock_updates()
            return {"success": True, "message": "Batch stock update completed"}

        elif operation == "batch_price_update":
            ecommerce_app.process_batch_price_updates()
            return {"success": True, "message": "Batch price update completed"}

        elif operation == "combine_sku":
            ecommerce_app.combine_qty_by_sku()
            return {"success": True, "message": "SKU combination completed"}

        elif operation == "get_wallet_transactions":
            # Handle wallet transactions
            month = params.get("month")
            year = params.get("year")
            transaction_type = params.get("transaction_type")
            result = ecommerce_app.shopee.wallet_manager.get_transactions(
                month=month, year=year, transaction_tab_type=transaction_type
            )
            if result:
                return {"success": True, "data": result}
            else:
                return {"success": False,
                        "error": "Failed to get wallet transactions"}
        # Di fungsi execute_operation_internal - tambahkan case baru
        elif operation == "export_wallet_to_sheet":
            try:
                print(f"🔄 [EXECUTE] Starting wallet export to sheets operation")

                month = params.get("month")
                year = params.get("year")
                transaction_type = params.get("transaction_type")

                print(
                    f"📋 [EXECUTE] Parameters - month: {month}, year: {year}, type: {transaction_type}")

                if not ecommerce_app or not ecommerce_app.shopee:
                    print(
                        "❌ [EXECUTE] Ecommerce app or shopee handler not available")
                    return {"success": False, "error": "Application not initialized"}

                # Panggil method di shopee handler
                print(
                    f"🔗 [EXECUTE] Calling process_wallet_to_sheets on shopee handler")
                success = ecommerce_app.shopee.process_wallet_to_sheets(
                    month=month, year=year, transaction_type=transaction_type
                )

                print(
                    f"✅ [EXECUTE] process_wallet_to_sheets completed with success: {success}")

                if success:
                    return {
                        "success": True,
                        "message": "Wallet transactions exported to Google Sheets successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to export wallet transactions to Google Sheets"
                    }

            except Exception as e:
                print(f"❌ [EXECUTE] Error in export_wallet_to_sheet: {str(e)}")
                import traceback
                traceback.print_exc()
                return {"success": False, "error": f"Export failed: {str(e)}"}
        elif operation == "process_shipping_fee":
            # Handle shipping fee processing
            option = params.get("option")
            month = params.get("month")
            year = params.get("year")
            result = ecommerce_app.shopee.process_shipping_fee_difference(
                option, month, year
            )
            if result:
                return {"success": True,
                        "message": "Shipping fee processing completed"}
            else:
                return {"success": False,
                        "error": "Failed to process shipping fee"}

        elif operation == "process_shipping_file":
            # Handle shipping file processing
            filename = params.get("filename")
            if not filename:
                return {"success": False, "error": "Filename is required"}

            result = ecommerce_app.shopee._process_selected_shipping_file(
                filename)
            if result:
                return {
                    "success": True,
                    "message": f"File {filename} processed successfully",
                }
            else:
                return {"success": False,
                        "error": f"Failed to process file {filename}"}

        elif operation.startswith(("shopee_", "lazada_", "tiktok_")):
            platform, _, op = operation.partition("_")
            return execute_platform_operation(platform, op, params)

        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

    except Exception as e:
        logger.error(f"Error executing operation {operation}: {str(e)}")
        return {"success": False, "error": str(e)}


# Di fungsi execute_platform_operation - perbaiki handling untuk update_price


def execute_platform_operation(platform, operation, params):
    """Execute platform-specific operations"""
    try:
        platform_handler = getattr(ecommerce_app, platform, None)
        if not platform_handler:
            return {"success": False, "error": f"Unknown platform: {platform}"}

        if operation == "operation":
            # Handle platform operations like update_stock, update_price, etc.
            op_type = params.get("operation")
            if op_type == "update_stock":
                platform_handler.process_stock_updates()
                return {
                    "success": True,
                    "message": f"{platform} stock update completed",
                }

            elif op_type == "update_price":
                price_type = params.get("price_type", "regular")

                if platform == "shopee":
                    # Shopee has different price types
                    result = platform_handler.process_price_updates_direct(
                        price_type)
                    return result
                else:
                    # Lazada and Tiktok use direct price update
                    result = platform_handler.process_price_updates_direct()
                    return result

            elif op_type == "export_orders":
                export_type = params.get("export_type", "all")
                platform_handler.export_orders_by_type(export_type, 7)
                return {"success": True,
                        "message": f"{platform} orders exported"}

            elif op_type == "get_token":
                if platform_handler.api.get_access_token():
                    return {"success": True,
                            "message": f"{platform} token obtained"}
                else:
                    return {
                        "success": False,
                        "error": f"Failed to get {platform} token",
                    }

            elif op_type == "refresh_token":
                if platform_handler.api.refresh_access_token():
                    return {"success": True,
                            "message": f"{platform} token refreshed"}
                else:
                    return {
                        "success": False,
                        "error": f"Failed to refresh {platform} token",
                    }

            elif op_type == "update_code":
                new_code = params.get("code")
                if new_code and platform_handler.config.update_code(new_code):
                    return {"success": True,
                            "message": f"{platform} code updated"}
                else:
                    return {
                        "success": False,
                        "error": f"Failed to update {platform} code",
                    }

            elif op_type == "shipping_fee":
                # Handle shipping fee operations
                return {
                    "success": True,
                    "message": f"{platform} shipping fee operation",
                }

            elif op_type == "wallet":
                # Handle wallet operations
                return {"success": True,
                        "message": f"{platform} wallet operation"}

        return {"success": False, "error": f"Unknown operation: {operation}"}

    except Exception as e:
        logger.error(
            f"Error in platform operation {platform}.{operation}: {
                str(e)}"
        )
        return {"success": False, "error": str(e)}


@app.route("/api/shipping/files")
def get_shipping_files():
    """Get shipping files list"""
    try:
        if not ecommerce_app:
            return jsonify({"success": False, "error": "App not initialized"})

        file_info = ecommerce_app.shopee.show_shipping_file_list()
        return jsonify({"success": True, "files": file_info})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/shipping/process-file", methods=["POST"])
def process_shipping_file():
    """Process shipping file"""
    try:
        data = request.get_json()
        if not data:
            return jsonify(
                {"success": False, "error": "No JSON data provided"}), 400

        filename = data.get("filename")

        if not ecommerce_app:
            return jsonify({"success": False, "error": "App not initialized"})

        result = ecommerce_app.shopee._process_selected_shipping_file(filename)
        return jsonify(
            {
                "success": result,
                "message": (
                    f"File {filename} processed"
                    if result
                    else f"Failed to process {filename}"
                ),
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/debug/check-functions")
def debug_check_functions():
    """Debug endpoint to check if all functions are connected properly"""
    try:
        if not ecommerce_app:
            return jsonify({"success": False, "error": "App not initialized"})

        # Test basic functionality
        functions_status = {
            "app_initialized": ecommerce_app is not None,
            "shopee_handler": hasattr(ecommerce_app, "shopee"),
            "lazada_handler": hasattr(ecommerce_app, "lazada"),
            "tiktok_handler": hasattr(ecommerce_app, "tiktok"),
            "sheet_manager": hasattr(ecommerce_app, "sheet_manager"),
            "shopee_token_status": (
                ecommerce_app.shopee.get_detailed_token_status()
                if hasattr(ecommerce_app, "shopee")
                else "No shopee handler"
            ),
            "lazada_token_status": (
                ecommerce_app.lazada.get_detailed_token_status()
                if hasattr(ecommerce_app, "lazada")
                else "No lazada handler"
            ),
            "tiktok_token_status": (
                ecommerce_app.tiktok.get_detailed_token_status()
                if hasattr(ecommerce_app, "tiktok")
                else "No tiktok handler"
            ),
        }

        return jsonify(
            {
                "success": True,
                "data": functions_status,
                "message": "Debug check completed",
            }
        )

    except Exception as e:
        return jsonify(
            {"success": False, "error": f"Debug check failed: {str(e)}"})


# Tambahkan route untuk test koneksi sederhana


@app.route("/api/test")
def test_connection():
    return jsonify({"message": "Backend is working!", "status": "success"})


def monitor_connections():
    """Monitor and cleanup stale connections"""
    global last_connection_time, connection_status

    while True:
        try:
            current_time = datetime.now()
            if last_connection_time:
                time_diff = (
                    current_time -
                    last_connection_time).total_seconds()
                if time_diff > 60:  # 1 minute without activity
                    connection_status = "disconnected"
                    logger.warning(
                        f"Connection lost - last activity: {
                            time_diff:.0f} seconds ago"
                    )

            time.sleep(30)  # Check every 30 seconds
        except Exception as e:
            logger.error(f"Error in connection monitor: {str(e)}")
            time.sleep(60)


@app.route("/api/google/auth/debug-scopes")
def google_auth_debug_scopes():
    """Debug endpoint untuk memeriksa scope OAuth"""
    try:
        from google_sheets_manager import GoogleSheetsManager
        from file_system_manager import FileSystemManager

        fs = FileSystemManager()
        gsm = GoogleSheetsManager(fs)

        debug_info = {
            "requested_scopes": gsm.SCOPES,
            "has_credentials": os.path.exists(gsm.credentials_file),
            "is_authenticated": gsm.is_authenticated(),
            "token_file_exists": os.path.exists(gsm.token_file),
            "current_scopes": gsm.creds.scopes if gsm.creds else None
        }

        return jsonify({"success": True, "data": debug_info})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# Initialize Google Sheets Manager
google_sheets_manager = GoogleSheetsManager(FileSystemManager())


@app.route("/api/google/auth/status")
def google_auth_status():
    """Get Google Sheets authentication status"""
    try:
        status = google_sheets_manager.get_auth_status()
        # print(f"🔍 Auth status: {status}")
        return jsonify({"success": True, "data": status})
    except Exception as e:
        print(f"❌ Error getting auth status: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/google/auth/initiate")
def google_auth_initiate():
    """Initiate Google OAuth flow"""
    try:
        print("🔄 Initiating Google OAuth flow...")
        auth_url = google_sheets_manager.get_auth_url()
        if auth_url:
            print(f"✅ Auth URL generated: {auth_url}")
            return jsonify({"success": True, "auth_url": auth_url})
        else:
            print("❌ Failed to generate auth URL")
            return jsonify({"success": False, "error": "Failed to generate auth URL. Check credentials file."})
    except Exception as e:
        print(f"❌ Error initiating auth: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/google/auth/callback")
def google_auth_callback():
    """Handle Google OAuth callback"""
    try:
        code = request.args.get('code')
        error = request.args.get('error')

        if error:
            print(f"❌ OAuth error: {error}")
            return f"""
            <html>
                <head><title>Authentication Failed</title></head>
                <body>
                    <h2>❌ Authentication Failed</h2>
                    <p>Error: {error}</p>
                    <script>
                        window.opener.postMessage({{type: 'google_auth_error', error: '{error}'}}, '*');
                        setTimeout(() => window.close(), 3000);
                    </script>
                </body>
            </html>
            """

        if not code:
            print("❌ No authorization code provided")
            return """
            <html>
                <head><title>Authentication Failed</title></head>
                <body>
                    <h2>❌ Authentication Failed</h2>
                    <p>No authorization code received from Google.</p>
                    <script>
                        window.opener.postMessage({type: 'google_auth_error', error: 'No authorization code received'}, '*');
                        setTimeout(() => window.close(), 5000);
                    </script>
                </body>
            </html>
            """

        success = google_sheets_manager.handle_callback(code)
        if success:
            print("✅ OAuth authentication successful")
            return """
            <html>
                <head><title>Authentication Successful</title></head>
                <body style="font-family: Arial, sans-serif; padding: 20px; text-align: center;">
                    <h2 style="color: green;">✅ Google Authentication Successful!</h2>
                    <p>You can close this window and return to the application.</p>
                    <script>
                        window.opener.postMessage({type: 'google_auth_success'}, '*');
                        setTimeout(() => window.close(), 2000);
                    </script>
                </body>
            </html>
            """
        else:
            print("❌ OAuth authentication failed")
            return """
            <html>
                <head><title>Authentication Failed</title></head>
                <body>
                    <h2>❌ Authentication Failed</h2>
                    <p>Failed to exchange code for tokens.</p>
                    <script>
                        window.opener.postMessage({type: 'google_auth_error', error: 'Token exchange failed'}, '*');
                        setTimeout(() => window.close(), 5000);
                    </script>
                </body>
            </html>
            """

    except Exception as e:
        print(f"❌ Error in OAuth callback: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"""
        <html>
            <head><title>Error</title></head>
            <body>
                <h2>❌ Error</h2>
                <p>{str(e)}</p>
                <script>
                    window.opener.postMessage({{type: 'google_auth_error', error: '{str(e)}'}}, '*');
                    setTimeout(() => window.close(), 5000);
                </script>
            </body>
        </html>
        """


@app.route('/api/google/auth/debug')
def google_auth_debug():
    """Debug Google OAuth parameters"""
    try:
        from google_sheets_manager import GoogleSheetsManager
        from file_system_manager import FileSystemManager

        fs = FileSystemManager()
        gsm = GoogleSheetsManager(fs)

        auth_url = gsm.get_auth_url()

        debug_info = {
            "auth_url": auth_url,
            "redirect_uri": "http://localhost:5000/api/google/auth/callback",
            "scopes": gsm.SCOPES,
            "has_credentials": os.path.exists(gsm.credentials_file)
        }

        return jsonify({"success": True, "data": debug_info})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/google/sheets/list")
def google_sheets_list():
    """Get list of available spreadsheets"""
    try:
        if not google_sheets_manager.is_authenticated():
            return jsonify({"success": False, "error": "Not authenticated"})

        spreadsheets = google_sheets_manager.get_spreadsheets()
        return jsonify({"success": True, "data": spreadsheets})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/google/worksheets/<spreadsheet_id>")
def google_worksheets_list(spreadsheet_id):
    """Get list of worksheets in a spreadsheet"""
    try:
        if not google_sheets_manager.is_authenticated():
            return jsonify({"success": False, "error": "Not authenticated"})

        worksheets = google_sheets_manager.get_worksheets(spreadsheet_id)
        return jsonify({"success": True, "data": worksheets})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/google/settings/update", methods=["POST"])
def google_settings_update():
    """Update Google Sheets settings"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"})

        spreadsheet_id = data.get("spreadsheet_id")
        selected_sheet = data.get("selected_sheet")
        manual_mode = data.get("manual_mode", False)

        success = google_sheets_manager.update_settings(
            spreadsheet_id, selected_sheet, manual_mode
        )

        if success:
            # Test connection if not in manual mode
            if not manual_mode:
                connection_ok = google_sheets_manager.test_connection(
                    spreadsheet_id)
                if not connection_ok:
                    return jsonify({
                        "success": False,
                        "error": "Failed to connect to the selected spreadsheet"
                    })

            return jsonify({
                "success": True,
                "message": "Settings updated successfully"
            })
        else:
            return jsonify({"success": False, "error": "Failed to update settings"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/google/settings/test")
def google_settings_test():
    """Test current Google Sheets connection"""
    try:
        connection_ok = google_sheets_manager.test_connection()
        return jsonify({
            "success": True,
            "connected": connection_ok,
            "message": "Connection test successful" if connection_ok else "Connection test failed"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/google/auth/logout")
def google_auth_logout():
    """Logout from Google"""
    try:
        success = google_sheets_manager.logout()
        if success:
            return jsonify({"success": True, "message": "Successfully logged out"})
        else:
            return jsonify({"success": False, "error": "Failed to logout"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/google/spreadsheets/create", methods=["POST"])
def google_create_spreadsheet():
    """Create new Google Spreadsheet"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"})

        title = data.get("title")
        if not title:
            return jsonify({"success": False, "error": "Title is required"})

        new_spreadsheet = google_sheets_manager.create_spreadsheet(title)
        if new_spreadsheet:
            return jsonify({
                "success": True,
                "data": new_spreadsheet,
                "message": f"Spreadsheet '{title}' created successfully"
            })
        else:
            return jsonify({"success": False, "error": "Failed to create spreadsheet"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/google/settings/update-detailed", methods=["POST"])
def google_settings_update_detailed():
    """Update detailed Google Sheets settings"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"})

        wallet_spreadsheet_id = data.get("wallet_spreadsheet_id")
        shipping_spreadsheet_id = data.get("shipping_spreadsheet_id")

        success = google_sheets_manager.update_detailed_settings(
            wallet_spreadsheet_id, shipping_spreadsheet_id
        )

        if success:
            return jsonify({
                "success": True,
                "message": "Settings updated successfully"
            })
        else:
            return jsonify({"success": False, "error": "Failed to update settings"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
# Di app.py - tambahkan endpoint baru


@app.route("/api/execute-sheets", methods=["POST"])
def execute_sheets_operation():
    """Execute operations with direct Google Sheets export"""
    try:
        logger.info("📥 /api/execute-sheets endpoint called")
        data = request.get_json()
        if not data:
            logger.error("❌ No JSON data provided in execute-sheets")
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        operation = data.get("operation")
        params = data.get("params", {})

        logger.info(
            f"🔄 Execute-sheets request: {operation} with params: {params}")

        if not ecommerce_app:
            logger.error("❌ Ecommerce app not initialized in execute-sheets")
            return jsonify({"success": False, "error": "Application not initialized"}), 500

        # Execute sheets operation
        result = execute_sheets_operation_internal(operation, params)

        logger.info(f"✅ Execute-sheets result: {result}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"❌ Error in execute_sheets_operation: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


def execute_sheets_operation_internal(operation, params):
    try:
        print(f"🔍 [BACKEND-SHEETS] Executing sheets operation: {operation}")
        print(f"📋 [BACKEND-SHEETS] Parameters: {params}")

        if operation == "wallet_to_sheets":
            month = params.get("month")
            year = params.get("year")
            transaction_type = params.get("transaction_type")

            print(
                f"📊 [BACKEND-SHEETS] Processing wallet to sheets: {month}/{year}, type: {transaction_type}")

            # Validasi ecommerce_app dan shopee handler
            if not ecommerce_app:
                print("❌ [BACKEND-SHEETS] ecommerce_app not available!")
                return {"success": False, "error": "Ecommerce app not initialized"}

            if not hasattr(ecommerce_app, 'shopee'):
                print("❌ [BACKEND-SHEETS] shopee handler not available!")
                return {"success": False, "error": "Shopee handler not available"}

            # Panggil method yang sudah dioptimalkan
            print("🔗 [BACKEND-SHEETS] Calling optimized process_wallet_to_sheets...")
            success = ecommerce_app.shopee.process_wallet_to_sheets(
                month=month, year=year, transaction_type=transaction_type
            )

            print(
                f"✅ [BACKEND-SHEETS] process_wallet_to_sheets completed with success: {success}")

            if success:
                return {
                    "success": True,
                    "message": f"Wallet transactions ({month}/{year}) exported to Google Sheets successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to export wallet transactions to Google Sheets"
                }

        elif operation == "shipping_fee_to_sheets":
            option = params.get("option")
            month = params.get("month")
            year = params.get("year")

            logger.info(
                f"📊 Processing shipping fee to sheets: option={option}, {month}/{year}")

            success = ecommerce_app.shopee.process_shipping_fee_to_sheets(
                option=option, month=month, year=year
            )
            return {
                "success": success,
                "message": "Shipping fee differences exported to Google Sheets" if success else "Failed to export shipping fee differences"
            }
        else:
            logger.error(f"❌ Unknown sheets operation: {operation}")
            return {"success": False, "error": f"Unknown sheets operation: {operation}"}

    except Exception as e:
        logger.error(f"❌ Error in execute_sheets_operation_internal: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}


@app.route("/api/debug/wallet-test")
def debug_wallet_test():
    """Debug endpoint untuk testing wallet functionality"""
    try:
        if not ecommerce_app:
            return jsonify({"success": False, "error": "App not initialized"})

        # Test Google Sheets Manager
        gsm_status = {
            "has_google_sheets_manager": hasattr(ecommerce_app.shopee, 'google_sheets_manager'),
            "google_sheets_manager_is_none": ecommerce_app.shopee.google_sheets_manager is None if hasattr(ecommerce_app.shopee, 'google_sheets_manager') else True,
            "is_authenticated": ecommerce_app.shopee.google_sheets_manager.is_authenticated() if hasattr(ecommerce_app.shopee, 'google_sheets_manager') and ecommerce_app.shopee.google_sheets_manager else False,
            "wallet_spreadsheet_id": ecommerce_app.shopee.google_sheets_manager.settings.get("wallet_spreadsheet_id") if hasattr(ecommerce_app.shopee, 'google_sheets_manager') and ecommerce_app.shopee.google_sheets_manager else None
        }

        return jsonify({
            "success": True,
            "data": gsm_status,
            "message": "Wallet debug information"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/debug/wallet-export-test", methods=["POST"])
def debug_wallet_export_test():
    """Debug endpoint untuk testing wallet export"""
    try:
        data = request.get_json()
        print(f"🔧 DEBUG WALLET EXPORT TEST: {data}")

        # Test langsung panggil method
        success = ecommerce_app.shopee.process_wallet_to_sheets(
            month=data.get('month'),
            year=data.get('year'),
            transaction_type=data.get('transaction_type')
        )

        return jsonify({
            "success": success,
            "message": "Debug test completed",
            "google_sheets_manager_available": hasattr(ecommerce_app.shopee, 'google_sheets_manager'),
            "google_sheets_authenticated": ecommerce_app.shopee.google_sheets_manager.is_authenticated() if hasattr(ecommerce_app.shopee, 'google_sheets_manager') and ecommerce_app.shopee.google_sheets_manager else False
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/google/sheets/refresh")
def google_sheets_refresh():
    """Refresh list of available spreadsheets - FIXED VERSION"""
    try:
        if not google_sheets_manager.is_authenticated():
            return jsonify({"success": False, "error": "Not authenticated"})

        print("🔄 API: Refreshing spreadsheet list...")
        spreadsheets = google_sheets_manager.refresh_spreadsheets()
        
        # Debug information
        print(f"📊 API Response: {len(spreadsheets)} spreadsheets")
        
        return jsonify({
            "success": True, 
            "data": spreadsheets,
            "count": len(spreadsheets),
            "message": f"Refreshed {len(spreadsheets)} spreadsheets"
        })
    except Exception as e:
        print(f"❌ API Error refreshing spreadsheets: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})

connection_monitor = threading.Thread(target=monitor_connections, daemon=True)
connection_monitor.start()

initialize_app()

if __name__ == "__main__":
    print("🚀 Starting Ecommerce Integration Server...")
    print(f"📁 Current directory: {os.getcwd()}")

    local_ip = get_local_ip()
    print(f"🌐 Local IP Address: {local_ip}")
    print(f"🐍 Python path: {sys.path}")

    if ecommerce_app is None:
        print("🔄 Initializing application...")
        initialize_app()

    if ecommerce_app:
        print("✅ Application initialized successfully")
        print("🔧 Available endpoints:")
        print("   - GET  /api/health")
        print("   - GET  /api/status")
        print("   - GET  /api/test")
        print("   - POST /api/execute")
        print("   - GET  /api/shipping/files")
        print("   - POST /api/shipping/process-file")
        print("   - GET  /api/debug/check-functions")
        print("\n🌐 Server accessible via:")
        print(f"   - Local: http://localhost:5000")
        print(f"   - Network: http://{local_ip}:5000")
        print(f"   - Any IP: http://0.0.0.0:5000")

        # Jalankan di semua interface (0.0.0.0) agar bisa diakses dari jaringan
        app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
    else:
        print("❌ Failed to initialize application")
