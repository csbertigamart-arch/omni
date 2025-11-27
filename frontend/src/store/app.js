import { defineStore } from "pinia";
import { ref, computed } from "vue";
import apiService from "../services/api";

export const useAppStore = defineStore("app", () => {
  const status = ref(null);
  const loading = ref(false);
  const logs = ref("");
  const connectionStatus = ref("connecting");
  const requestCount = ref(0);
  const errorCount = ref(0);
  const modals = ref({
    token: { visible: false, platform: null },
    wallet: { visible: false },
    shipping: { visible: false },
    price: { visible: false, platform: null },
    exportOrders: { visible: false, platform: null },
    debug: { visible: false },
  });
  const shippingFiles = ref([]);
  const debugInfo = ref(null);
  
  // New state for connection management
  const lastStatusUpdate = ref(null);
  const isReconnecting = ref(false);
  const statusPollingInterval = ref(null);

  const isConnected = computed(() => connectionStatus.value === "connected");

  async function initializeApp() {
    try {
      loading.value = true;
      connectionStatus.value = "connecting";
      addLog("🔄 Connecting to backend server...");

      const health = await apiService.healthCheck();
      if (health.status === "healthy") {
        connectionStatus.value = "connected";
        addLog("✅ Backend connected successfully");
        await loadStatus();

        // Start status polling dengan interval yang lebih baik
        startStatusPolling();
      } else {
        connectionStatus.value = "error";
        addLog("❌ Backend health check failed");
      }
    } catch (error) {
      connectionStatus.value = "error";
      addLog(`❌ Failed to connect to backend: ${error.message}`);
      console.error("Failed to initialize app:", error);
      
      // Retry connection after delay
      setTimeout(() => {
        if (connectionStatus.value !== "connected") {
          addLog("🔄 Retrying connection...");
          initializeApp();
        }
      }, 5000);
    } finally {
      loading.value = false;
    }
  }

  function startStatusPolling() {
    // Clear existing interval
    if (statusPollingInterval.value) {
      clearInterval(statusPollingInterval.value);
    }
    
    // Auto-refresh status every 30 seconds, tapi hanya jika connected
    statusPollingInterval.value = setInterval(async () => {
      if (!loading.value && document.visibilityState === "visible" && connectionStatus.value === "connected") {
        await loadStatus(false); // false = jangan log jika normal
      }
    }, 30000);
  }

  async function loadStatus(shouldLog = true) {
    try {
      const response = await apiService.getStatus();
      if (response.success) {
        status.value = response.data;
        
        // Handle reconnection
        if (response.reconnected || connectionStatus.value !== "connected") {
          connectionStatus.value = "connected";
          isReconnecting.value = true;
          addLog("✅ Backend reconnected successfully");
          
          // Clear reconnection flag after a delay
          setTimeout(() => {
            isReconnecting.value = false;
          }, 3000);
        } else if (shouldLog && !isReconnecting.value) {
          // Only log normal status updates if not reconnecting and shouldLog is true
          addLog("✅ Status loaded successfully");
        }
        
        lastStatusUpdate.value = new Date();
      } else {
        if (shouldLog) {
          addLog("❌ Failed to load status");
        }
      }
      return response;
    } catch (error) {
      if (connectionStatus.value === "connected") {
        connectionStatus.value = "error";
        addLog(`❌ Connection lost: ${error.message}`);
        
        // Try to reconnect
        setTimeout(() => {
          if (connectionStatus.value !== "connected") {
            addLog("🔄 Attempting to reconnect...");
            loadStatus(true);
          }
        }, 3000);
      }
      console.error("Failed to load status:", error);
      throw error;
    }
  }

// Di method executeOperation - tidak perlu perubahan besar, 
// karena sudah menggunakan parameter yang dikirim dari frontend

async function executeOperation(operation, params = {}) {
  try {
    loading.value = true;
    requestCount.value++;
    
    // Only log operation start if not a status check
    if (!operation.includes('status') && operation !== 'get_token_status') {
      addLog(`🔄 Executing operation: ${operation}`);
    }

    const response = await apiService.executeOperation(operation, params);

    if (response.success) {
      // Only log success for significant operations
      if (!operation.includes('status') && operation !== 'get_token_status') {
        addLog(`✅ Operation ${operation} completed successfully`);
        
        // Log detailed results if available
        if (response.results) {
          for (const [platform, result] of Object.entries(response.results)) {
            if (result && typeof result === 'object') {
              const processed = result.processed || 0;
              const skipped = result.skipped || 0;
              const failed = result.failed || 0;
              addLog(`   ${platform}: ${processed} processed, ${skipped} skipped, ${failed} failed`);
            }
          }
        }
      }
      await loadStatus(false); // Refresh status after successful operation tanpa logging
    } else {
      errorCount.value++;
      addLog(`❌ Operation ${operation} failed: ${response.error}`);
    }

    return response;
  } catch (error) {
    errorCount.value++;
    
    // Check if this is a connection error
    if (error.message.includes('Network error') || error.message.includes('cannot connect')) {
      connectionStatus.value = "error";
      addLog(`❌ Operation ${operation} error: ${error.message}`);
      
      // Try to reconnect
      setTimeout(() => {
        if (connectionStatus.value !== "connected") {
          addLog("🔄 Attempting to reconnect after operation failure...");
          loadStatus(true);
        }
      }, 3000);
    } else {
      addLog(`❌ Operation ${operation} error: ${error.message}`);
    }
    
    console.error("Operation failed:", error);
    throw error;
  } finally {
    loading.value = false;
  }
}

  // Modal management
  function showModal(modalType, platform = null) {
    modals.value[modalType] = { visible: true, platform };
  }

  function closeModal(modalType) {
    modals.value[modalType] = { visible: false, platform: null };
  }

  // Token operations
  async function handleTokenOperation(platform, operation, code = null) {
    let params = { operation };
    if (operation === "update_code" && code) {
      params.code = code;
    }

    const result = await executeOperation(`${platform}_operation`, params);
    closeModal("token");
    return result;
  }

  // Wallet operations
  async function getWalletTransactions(params) {
    return await executeOperation("get_wallet_transactions", params);
  }

  // Shipping operations
  async function getShippingFiles() {
    try {
      const response = await apiService.getShippingFiles();
      if (response.success) {
        shippingFiles.value = response.files || [];
        return response;
      }
      return response;
    } catch (error) {
      addLog(`❌ Error getting shipping files: ${error.message}`);
      throw error;
    }
  }

  async function processShippingFile(filename) {
    try {
      // Gunakan endpoint khusus untuk processing shipping file, bukan executeOperation
      const response = await apiService.processShippingFile(filename);
      if (response.success) {
        addLog(`✅ Shipping file ${filename} processed successfully`);
      } else {
        addLog(`❌ Failed to process shipping file: ${response.message || response.error}`);
      }
      return response;
    } catch (error) {
      addLog(`❌ Error processing shipping file: ${error.message}`);
      throw error;
    }
  }

  async function processShippingFee(params) {
    return await executeOperation("process_shipping_fee", params);
  }

  // Price update operations
  async function updatePrice(platform, priceType) {
    return await executeOperation(`${platform}_operation`, {
      operation: "update_price",
      price_type: priceType,
    });
  }

  // Export orders operations
  async function exportOrders(platform, exportType, days = 7) {
    return await executeOperation(`${platform}_operation`, {
      operation: "export_orders",
      export_type: exportType,
      days: days,
    });
  }

  // Di store/app.js - tambahkan method ini
  async function executeSheetsOperation(operation, params = {}) {
    try {
      loading.value = true;
      requestCount.value++;
      addLog(`🔄 Executing sheets operation: ${operation}`);
      
      const response = await apiService.executeSheetsOperation(operation, params);

      if (response.success) {
        addLog(`✅ Sheets operation ${operation} completed successfully`);
        await loadStatus(false);
      } else {
        errorCount.value++;
        addLog(`❌ Sheets operation ${operation} failed: ${response.error}`);
      }

      return response;
    } catch (error) {
      errorCount.value++;
      addLog(`❌ Sheets operation ${operation} error: ${error.message}`);
      console.error("Sheets operation failed:", error);
      throw error;
    } finally {
      loading.value = false;
    }
  }


  // Debug functions
  async function debugCheckFunctions() {
    try {
      const response = await apiService.debugCheckFunctions();
      debugInfo.value = response.data;
      return response;
    } catch (error) {
      addLog(`❌ Debug check failed: ${error.message}`);
      throw error;
    }
  }

  function addLog(message) {
    const timestamp = new Date().toLocaleTimeString();
    logs.value += `[${timestamp}] ${message}\n`;

    // Auto-scroll to bottom if logs container exists dan logs tidak terlalu panjang
    setTimeout(() => {
      const logsContainer = document.querySelector(".logs-content");
      if (logsContainer && logsContainer.scrollHeight - logsContainer.scrollTop - logsContainer.clientHeight < 100) {
        logsContainer.scrollTop = logsContainer.scrollHeight;
      }
    }, 100);
    
    // Limit log size to prevent memory issues (keep last 1000 lines)
    const logLines = logs.value.split('\n');
    if (logLines.length > 1000) {
      logs.value = logLines.slice(-500).join('\n');
    }
  }

  function clearLogs() {
    logs.value = "";
    addLog("📋 Logs cleared");
  }

  async function refreshAll() {
    addLog("🔄 Manual refresh triggered");
    await loadStatus(true);
  }
  
  // Cleanup function
  function cleanup() {
    if (statusPollingInterval.value) {
      clearInterval(statusPollingInterval.value);
      statusPollingInterval.value = null;
    }
  }

  return {
    // State
    status,
    loading,
    logs,
    connectionStatus,
    requestCount,
    errorCount,
    modals,
    shippingFiles,
    debugInfo,
    lastStatusUpdate,
    isReconnecting,

    // Getters
    isConnected,

    // Actions
    initializeApp,
    loadStatus,
    executeOperation,
    showModal,
    closeModal,
    handleTokenOperation,
    getWalletTransactions,
    getShippingFiles,
    processShippingFile,
    processShippingFee,
    updatePrice,
    exportOrders,
    debugCheckFunctions,
    addLog,
    clearLogs,
    refreshAll,
    cleanup,
    executeSheetsOperation
  };
});