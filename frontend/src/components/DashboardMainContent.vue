<template>
  <div class="main-content">
    <TabView class="custom-tabview">
      <TabPanel header="Operations" class="custom-tabpanel">
        <div class="platform-tabs">
          <Button
            v-for="platform in ['shopee', 'lazada', 'tiktok']"
            :key="platform"
            :label="platform.charAt(0).toUpperCase() + platform.slice(1)"
            :class="[
              'platform-tab',
              { active: currentPlatform === platform },
            ]"
            @click="$emit('platform-change', platform)"
          />
        </div>

        <div class="platform-content">
          <!-- Shopee Operations -->
          <div v-if="currentPlatform === 'shopee'" class="platform-ops">
            <div class="ops-grid">
              <Card
                v-for="op in shopeeOperations"
                :key="op.id"
                class="ops-card"
                @click="$emit('handle-platform-operation', op.operation, op.params)"
              >
                <template #content>
                  <div class="ops-card-content">
                    <i :class="op.icon"></i>
                    <span>{{ op.label }}</span>
                  </div>
                </template>
              </Card>
            </div>
          </div>

          <!-- Lazada Operations -->
          <div v-if="currentPlatform === 'lazada'" class="platform-ops">
            <div class="ops-grid">
              <Card
                v-for="op in lazadaOperations"
                :key="op.id"
                class="ops-card"
                @click="$emit('handle-platform-operation', op.operation, op.params)"
              >
                <template #content>
                  <div class="ops-card-content">
                    <i :class="op.icon"></i>
                    <span>{{ op.label }}</span>
                  </div>
                </template>
              </Card>
            </div>
          </div>

          <!-- Tiktok Operations -->
          <div v-if="currentPlatform === 'tiktok'" class="platform-ops">
            <div class="ops-grid">
              <Card
                v-for="op in tiktokOperations"
                :key="op.id"
                class="ops-card"
                @click="$emit('handle-platform-operation', op.operation, op.params)"
              >
                <template #content>
                  <div class="ops-card-content">
                    <i :class="op.icon"></i>
                    <span>{{ op.label }}</span>
                  </div>
                </template>
              </Card>
            </div>
          </div>
        </div>
      </TabPanel>

      <TabPanel header="Logs" class="custom-tabpanel">
        <div class="pane-header">
          <h3><i class="pi pi-list"></i> Operation Logs</h3>
          <div class="pane-controls">
            <Button
              icon="pi pi-download"
              label="Download"
              class="p-button-sm log-control-btn"
              @click="$emit('download-logs')"
            />
            <Button
              icon="pi pi-trash"
              label="Clear"
              class="p-button-sm log-control-btn"
              @click="$emit('clear-logs')"
            />
            <div class="auto-scroll-control">
              <Checkbox v-model="internalAutoScroll" binary />
              <label>Auto Scroll</label>
            </div>
          </div>
        </div>
        <div class="logs-container">
          <pre class="logs-content">{{ logs }}</pre>
        </div>
      </TabPanel>
      <TabPanel header="Settings" class="custom-tabpanel">
        <GoogleSheetsSettings />
      </TabPanel>
    </TabView>
  </div>
</template>

<script>
import { ref, watch } from "vue";
import TabView from "primevue/tabview";
import TabPanel from "primevue/tabpanel";
import Card from "primevue/card";
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import GoogleSheetsSettings from './GoogleSheetsSettings.vue';

export default {
  name: "DashboardMainContent",
  components: {
    TabView,
    TabPanel,
    Card,
    Button,
    Checkbox,
    GoogleSheetsSettings
  },
  props: {
    currentPlatform: {
      type: String,
      default: "shopee",
    },
    logs: {
      type: String,
      default: "",
    },
    autoScroll: {
      type: Boolean,
      default: true,
    },
  },
  emits: [
    "platform-change",
    "handle-platform-operation",
    "download-logs",
    "clear-logs",
    "update-auto-scroll",
  ],
  setup(props, { emit }) {
    const internalAutoScroll = ref(props.autoScroll);

    const shopeeOperations = ref([
      {
        id: 1,
        icon: "pi pi-file-export",
        label: "Export Orders",
        operation: "export_orders",
      },
      {
        id: 2,
        icon: "pi pi-box",
        label: "Update Stock",
        operation: "update_stock",
      },
      {
        id: 3,
        icon: "pi pi-tag",
        label: "Update Prices",
        operation: "update_price",
      },
      {
        id: 4,
        icon: "pi pi-truck",
        label: "Shipping Fees",
        operation: "shipping_fee",
      },
      { id: 5, icon: "pi pi-wallet", label: "Wallet", operation: "wallet" },
    ]);

    const lazadaOperations = ref([
      {
        id: 1,
        icon: "pi pi-file-export",
        label: "Export Orders",
        operation: "export_orders",
      },
      {
        id: 2,
        icon: "pi pi-box",
        label: "Update Stock",
        operation: "update_stock",
      },
      {
        id: 3,
        icon: "pi pi-tag",
        label: "Update Prices",
        operation: "update_price",
      },
    ]);

    const tiktokOperations = ref([
      {
        id: 1,
        icon: "pi pi-file-export",
        label: "Export Orders",
        operation: "export_orders",
      },
      {
        id: 2,
        icon: "pi pi-box",
        label: "Update Stock",
        operation: "update_stock",
      },
      {
        id: 3,
        icon: "pi pi-tag",
        label: "Update Prices",
        operation: "update_price",
      },
    ]);

    // Watch for autoScroll changes
    watch(internalAutoScroll, (newValue) => {
      emit("update-auto-scroll", newValue);
    });

    return {
      internalAutoScroll,
      shopeeOperations,
      lazadaOperations,
      tiktokOperations,
    };
  },
};
</script>

<style scoped>
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: white;
}

/* Improved TabView Styles */
.custom-tabview {
  height: 100%;
}

.custom-tabview :deep(.p-tabview-nav) {
  background: white;
  border-bottom: 1px solid #e1e5e9;
  padding: 0 20px;
  margin-bottom: 0;
}

.custom-tabview :deep(.p-tabview-nav-link) {
  padding: 16px 24px !important;
  margin: 0 4px !important;
  border: none !important;
  background: none !important;
  color: #6c757d !important;
  font-weight: 500;
  transition: all 0.3s ease !important;
  border-bottom: 3px solid transparent !important;
}

.custom-tabview :deep(.p-tabview-nav-link:hover) {
  background: #f8f9fa !important;
  color: #495057 !important;
}

.custom-tabview :deep(.p-highlight .p-tabview-nav-link) {
  color: #3498db !important;
  border-bottom-color: #3498db !important;
  background: #f8fafc !important;
}

.platform-tabs {
  display: flex;
  padding: 0 20px;
  background: white;
  border-bottom: 1px solid #e1e5e9;
  margin-top: 10px;
}

.platform-tab {
  padding: 12px 20px;
  border: none;
  background: none;
  cursor: pointer;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
  font-weight: 500;
  color: #6c757d;
  position: relative;
  min-width: 120px;
  text-align: center;
  margin: 0 2px;
  border-radius: 6px 6px 0 0;
}

.platform-tab.active {
  border-bottom-color: #3498db;
  color: #3498db;
  background: #f8fafc;
}

.platform-tab:hover:not(.active) {
  background: #f8f9fa;
  color: #495057;
}

.ops-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  padding: 24px;
}

.ops-card {
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
  padding: 0;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  background: white;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 120px;
}

.ops-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
  border-color: #3498db;
  background: #f8fafc;
}

.ops-card-content {
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  width: 100%;
  height: 100%;
}

.ops-card i {
  font-size: 2rem;
  color: #3498db;
  transition: transform 0.3s ease;
}

.ops-card:hover i {
  transform: scale(1.1);
}

.ops-card span {
  font-weight: 500;
  color: #2c3e50;
  font-size: 0.9rem;
}

.pane-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e1e5e9;
}

.pane-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #2c3e50;
  display: flex;
  align-items: center;
  gap: 8px;
}

.pane-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.85rem;
}

.log-control-btn {
  padding: 6px 12px !important;
  border-radius: 4px !important;
  transition: all 0.3s ease !important;
}

.log-control-btn:hover {
  transform: translateY(-1px);
}

.auto-scroll-control {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 4px;
  background: #f8f9fa;
}

.logs-container {
  flex: 1;
  background: #1a1a1a;
  overflow-y: auto;
  padding: 0;
  position: relative;
}

.logs-content {
  color: #00d9ff;
  font-family: "Courier New", monospace;
  white-space: pre-wrap;
  line-height: 1.4;
  margin: 0;
  padding: 20px;
  font-size: 0.85rem;
  min-height: 100%;
  overflow-wrap: break-word;
  word-break: break-all;
}

/* Improved scrollbar styling */
.logs-container::-webkit-scrollbar {
  width: 8px;
}

.logs-container::-webkit-scrollbar-track {
  background: #2a2a2a;
}

.logs-container::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 4px;
}

.logs-container::-webkit-scrollbar-thumb:hover {
  background: #777;
}

/* Ensure the tab panel has proper height */
/* Pastikan tab panel Settings bisa scroll */
/* Pastikan tab panel Settings bisa scroll */
.custom-tabpanel {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Untuk tab Settings khusus */
.custom-tabpanel:has(.google-sheets-settings) {
  overflow-y: auto;
}



/* Responsive Design */
@media (max-width: 768px) {
  .platform-tabs {
    flex-wrap: wrap;
  }

  .platform-tab {
    min-width: auto;
    flex: 1;
    padding: 12px 16px;
    font-size: 0.85rem;
    margin: 1px;
  }

  .ops-grid {
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    padding: 16px;
  }

  .pane-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .pane-controls {
    width: 100%;
    justify-content: space-between;
  }
}
</style>