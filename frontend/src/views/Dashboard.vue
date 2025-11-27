<template>
  <div class="dashboard">
    <!-- Header -->
    <DashboardHeader
      :connection-status="connectionStatus"
      :loading="loading"
      @refresh-all="refreshAll"
      @show-debug-modal="showDebugModal"
    />

    <div class="main-layout">
      <!-- Sidebar -->
      <DashboardSidebar
        :status="status"
        :loading="loading"
        @show-token-modal="showTokenModal"
        @execute-operation="executeOperation"
        @load-status="loadStatus"
      />

      <!-- Main Content -->
      <DashboardMainContent
        :current-platform="currentPlatform"
        :logs="logs"
        :auto-scroll="autoScroll"
        @platform-change="currentPlatform = $event"
        @handle-platform-operation="handlePlatformOperation"
        @download-logs="downloadLogs"
        @clear-logs="clearLogs"
        @update-auto-scroll="autoScroll = $event"
      />
    </div>

    <!-- Status Bar -->
    <DashboardStatusBar
      :last-updated="lastUpdated"
      :loading="loading"
      :request-count="requestCount"
      :error-count="errorCount"
    />

    <!-- Modals -->
    <TokenModal
      :visible="modals.token.visible"
      @update:visible="modals.token.visible = $event"
      :platform="modals.token.platform"
      @close="closeModal('token')"
      @handle-token-operation="handleTokenOperation"
    />

    <WalletModal
      :visible="modals.wallet.visible"
      @update:visible="modals.wallet.visible = $event"
      :wallet-params="walletParams"
      @close="closeModal('wallet')"
      @update-wallet-params="updateWalletParams"
      @get-wallet-transactions="getWalletTransactions"
      @export-wallet-to-sheets="exportWalletToSheets"
    />

    <ShippingModal
      :visible="modals.shipping.visible"
      @update:visible="modals.shipping.visible = $event"
      :shipping-params="shippingParams"
      :shipping-files="shippingFiles"
      :show-shipping-form="showShippingForm"
      :show-shipping-file-list="showShippingFileList"
      @close="closeShippingModal"
      @select-shipping-option="selectShippingOption"
      @load-shipping-files="loadShippingFiles"
      @process-shipping-file="processShippingFile"
      @process-shipping-fee="processShippingFee"
      @update-shipping-params="updateShippingParams"
      @export-shipping-to-sheets="exportShippingToSheets"
    />

    <PriceModal
      :visible="modals.price.visible"
      @update:visible="modals.price.visible = $event"
      :platform="modals.price.platform"
      :current-price-option="currentPriceOption"
      @close="closeModal('price')"
      @select-price-option="selectPriceOption"
      @execute-price-update="executePriceUpdate"
    />

    <ExportOrdersModal
      :visible="modals.exportOrders.visible"
      @update:visible="modals.exportOrders.visible = $event"
      :platform="modals.exportOrders.platform"
      @close="closeModal('exportOrders')"
      @execute-export-order="executeExportOrder"
    />

    <DebugModal
      :visible="modals.debug.visible"
      @update:visible="modals.debug.visible = $event"
      :debug-info="debugInfo"
      @close="closeModal('debug')"
      @load-debug-info="loadDebugInfo"
    />

    <!-- Toast Notifications -->
    <Toast />
  </div>
</template>

<script>
import { ref, computed, onMounted } from "vue";
import { useAppStore } from "../store/app";
import { useToast } from "primevue/usetoast";

// Components
import DashboardHeader from "../components/DashboardHeader.vue";
import DashboardSidebar from "../components/DashboardSidebar.vue";
import DashboardMainContent from "../components/DashboardMainContent.vue";
import DashboardStatusBar from "../components/DashboardStatusBar.vue";

// Modal Components
import TokenModal from "../components/modals/TokenModal.vue";
import WalletModal from "../components/modals/WalletModal.vue";
import ShippingModal from "../components/modals/ShippingModal.vue";
import PriceModal from "../components/modals/PriceModal.vue";
import ExportOrdersModal from "../components/modals/ExportOrdersModal.vue";
import DebugModal from "../components/modals/DebugModal.vue";

// PrimeVue Components
import Toast from "primevue/toast";

export default {
  name: "AppDashboard",
  components: {
    DashboardHeader,
    DashboardSidebar,
    DashboardMainContent,
    DashboardStatusBar,
    TokenModal,
    WalletModal,
    ShippingModal,
    PriceModal,
    ExportOrdersModal,
    DebugModal,
    Toast,
  },
  setup() {
    const toast = useToast();
    const appStore = useAppStore();

    // Reactive data
    const currentPlatform = ref("shopee");
    const autoScroll = ref(true);
    const lastUpdated = ref(new Date().toLocaleString());
    const currentPriceOption = ref(null);
    const showShippingForm = ref(false);
    const showShippingFileList = ref(false);

    // Form data
    const walletParams = ref({
      month: new Date().getMonth() + 1,
      year: new Date().getFullYear(),
      transaction_type: "wallet_order_income",
    });

    const shippingParams = ref({
      month: new Date().getMonth() + 1,
      year: new Date().getFullYear(),
      option: 1,
    });

    // Computed properties
    const status = computed(() => appStore.status);
    const loading = computed(() => appStore.loading);
    const logs = computed(() => appStore.logs);
    const connectionStatus = computed(() => appStore.connectionStatus);
    const requestCount = computed(() => appStore.requestCount);
    const errorCount = computed(() => appStore.errorCount);
    const modals = computed(() => appStore.modals);
    const shippingFiles = computed(() => appStore.shippingFiles);
    const debugInfo = computed(() => appStore.debugInfo);

    // Methods
    function showTokenModal(platform) {
      appStore.showModal("token", platform);
    }

    function showWalletModal() {
      appStore.showModal("wallet");
    }

    function showShippingModal() {
      appStore.showModal("shipping");
      resetShippingModal();
    }

    function showPriceModal(platform) {
      appStore.showModal("price", platform);
      currentPriceOption.value = null;
    }

    function showExportOrdersModal(platform) {
      appStore.showModal("exportOrders", platform);
    }

    function showDebugModal() {
      appStore.showModal("debug");
      loadDebugInfo();
    }

    function closeModal(modalType) {
      appStore.closeModal(modalType);
    }

    function closeShippingModal() {
      appStore.closeModal("shipping");
      resetShippingModal();
    }

    function resetShippingModal() {
      showShippingForm.value = false;
      showShippingFileList.value = false;
    }

    async function exportWalletToSheets() {
      console.log("🔄 [FRONTEND] Starting wallet export to sheets...");
      
      try {
        // Gunakan executeSheetsOperation untuk export langsung ke Google Sheets
        const result = await appStore.executeSheetsOperation(
          "wallet_to_sheets", 
          walletParams.value
        );
        
        if (result.success) {
          showToast("success", "Success", result.message);
          closeModal("wallet");
        } else {
          showToast("error", "Error", result.error || result.message);
        }
      } catch (error) {
        console.error("❌ [FRONTEND] Export failed:", error);
        showToast("error", "Error", error.message);
      }
    }


    async function getWalletTransactions() {
      try {
        console.log("🔄 [FRONTEND] Getting wallet transactions...");
        
        // 1. First get the transactions
        const result = await appStore.getWalletTransactions(walletParams.value);
        
        if (result.success) {
          showToast("success", "Success", "Transactions retrieved, starting export to Google Sheets...");
          
          // 2. Automatically trigger export to Google Sheets after getting transactions
          await exportWalletToSheets();
        } else {
          showToast("error", "Error", result.error);
        }
      } catch (error) {
        showToast("error", "Error", error.message);
      }
    }
    async function exportShippingToSheets() {
      try {
        const result = await appStore.executeSheetsOperation("shipping_fee_to_sheets", shippingParams.value);
        if (result.success) {
          showToast("success", "Success", result.message);
          closeShippingModal();
        } else {
          showToast("error", "Error", result.message);
        }
      } catch (error) {
        showToast("error", "Error", error.message);
      }
    }



    async function handleTokenOperation(operation) {
      const platform = modals.value.token.platform;
      let code = null;

      if (operation === "update_code") {
        code = prompt(`Enter new authorization code for ${platform}:`);
        if (!code) return;
      }

      try {
        const result = await appStore.handleTokenOperation(
          platform,
          operation,
          code
        );
        if (result.success) {
          showToast("success", "Success", result.message);
        } else {
          showToast("error", "Error", result.message);
        }
      } catch (error) {
        showToast("error", "Error", error.message);
      }
    }


    function selectShippingOption(option) {
      shippingParams.value.option = option;
      if (option === 1) {
        showShippingForm.value = true;
        showShippingFileList.value = false;
      } else {
        showShippingForm.value = false;
        showShippingFileList.value = true;
        loadShippingFiles();
      }
    }

    async function loadShippingFiles() {
      try {
        await appStore.getShippingFiles();
      } catch (error) {
        showToast("error", "Error", error.message);
      }
    }

    async function processShippingFile(filename) {
      try {
        const result = await appStore.processShippingFile(filename);
        if (result.success) {
          showToast("success", "Success", result.message);
          closeShippingModal();
        } else {
          showToast("error", "Error", result.message);
        }
      } catch (error) {
        showToast("error", "Error", error.message);
      }
    }

    async function processShippingFee() {
      try {
        const result = await appStore.processShippingFee(shippingParams.value);
        if (result.success) {
          showToast("success", "Success", result.message);
          closeShippingModal();
        } else {
          showToast("error", "Error", result.message);
        }
      } catch (error) {
        showToast("error", "Error", error.message);
      }
    }

    function selectPriceOption(option) {
      currentPriceOption.value = option;
    }



    async function executeExportOrder(exportType) {
      const platform = modals.value.exportOrders.platform;
      try {
        const result = await appStore.exportOrders(platform, exportType);
        if (result.success) {
          showToast("success", "Success", result.message);
          closeModal("exportOrders");
        } else {
          showToast("error", "Error", result.message);
        }
      } catch (error) {
        showToast("error", "Error", error.message);
      }
    }

    async function loadDebugInfo() {
      try {
        await appStore.debugCheckFunctions();
        showToast("success", "Success", "Debug information loaded");
      } catch (error) {
        showToast("error", "Error", error.message);
      }
    }






  // Di method handlePlatformOperation - perbaiki handling untuk update_price

  async function handlePlatformOperation(operation, params = {}) {
    const platform = currentPlatform.value;

    // Handle special operations that need modals
    if (operation === "export_orders") {
      showExportOrdersModal(platform);
      return;
    } else if (operation === "update_price") {
      if (platform === "shopee") {
        // Shopee needs price type selection
        showPriceModal(platform);
        return;
      } else {
        // Lazada and Tiktok - direct price update
        try {
          const result = await appStore.executeOperation(
            `${platform}_operation`,
            { 
              operation: "update_price",
              price_type: "regular" // Default for non-Shopee platforms
            }
          );
          if (result.success) {
            showToast("success", "Success", result.message);
          } else {
            showToast("error", "Error", result.message);
          }
        } catch (error) {
          showToast("error", "Error", error.message);
        }
        return;
      }
    } else if (operation === "shipping_fee") {
      showShippingModal();
      return;
    } else if (operation === "wallet") {
      showWalletModal();
      return;
    }

    // Execute regular operations
    try {
      const result = await appStore.executeOperation(
        `${platform}_operation`,
        { operation, ...params }
      );
      if (result.success) {
        showToast("success", "Success", result.message);
      } else {
        showToast("error", "Error", result.message);
      }
    } catch (error) {
      showToast("error", "Error", error.message);
    }
  }

  // Tambahkan method executePriceUpdate yang baru



  
  async function executePriceUpdate() {
    const platform = modals.value.price.platform;
    const priceType = currentPriceOption.value;
    
    try {
      const result = await appStore.executeOperation(
        `${platform}_operation`,
        { 
          operation: "update_price",
          price_type: priceType 
        }
      );
      
      if (result.success) {
        showToast("success", "Success", result.message);
        closeModal("price");
      } else {
        showToast("error", "Error", result.message);
      }
    } catch (error) {
      showToast("error", "Error", error.message);
    }
  }

    async function executeOperation(operation, params = {}) {
      try {
        const result = await appStore.executeOperation(operation, params);
        if (result.success) {
          showToast("success", "Success", result.message);
        } else {
          showToast("error", "Error", result.message);
        }
      } catch (error) {
        showToast("error", "Error", error.message);
      }
    }

    function showToast(severity, summary, detail) {
      toast.add({ severity, summary, detail, life: 3000 });
    }

    async function refreshAll() {
      await appStore.refreshAll();
      lastUpdated.value = new Date().toLocaleString();
    }

    async function loadStatus() {
      await appStore.loadStatus();
      lastUpdated.value = new Date().toLocaleString();
    }

    function clearLogs() {
      appStore.clearLogs();
    }

    function downloadLogs() {
      const blob = new Blob([logs.value], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ecommerce-logs-${
        new Date().toISOString().split("T")[0]
      }.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      appStore.addLog("Logs downloaded");
    }

    function updateWalletParams(newParams) {
      walletParams.value = { ...walletParams.value, ...newParams };
    }

    function updateShippingParams(newParams) {
      shippingParams.value = { ...shippingParams.value, ...newParams };
    }

    // Lifecycle
    onMounted(() => {
      appStore.initializeApp();
    });

    return {
      // Reactive data
      currentPlatform,
      autoScroll,
      lastUpdated,
      currentPriceOption,
      showShippingForm,
      showShippingFileList,
      walletParams,
      shippingParams,

      // Computed
      status,
      loading,
      logs,
      connectionStatus,
      requestCount,
      errorCount,
      modals,
      shippingFiles,
      debugInfo,

      // Methods
      showTokenModal,
      showWalletModal,
      showShippingModal,
      showPriceModal,
      showExportOrdersModal,
      showDebugModal,
      closeModal,
      closeShippingModal,
      handleTokenOperation,
      getWalletTransactions,
      exportWalletToSheets,
      exportShippingToSheets,
      selectShippingOption,
      loadShippingFiles,
      processShippingFile,
      processShippingFee,
      selectPriceOption,
      executePriceUpdate,
      executeExportOrder,
      loadDebugInfo,
      handlePlatformOperation,
      executeOperation,
      refreshAll,
      loadStatus,
      clearLogs,
      downloadLogs,
      updateWalletParams,
      updateShippingParams,
    };
  },
};
</script>

<style scoped>
.dashboard {
  height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
  background: #f5f7fa;
}

.main-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
  gap: 0;
}

/* Responsive Design */
@media (max-width: 768px) {
  .main-layout {
    flex-direction: column;
  }
}
</style>