<template>
  <div class="sidebar">
    <!-- Token Status -->
    <Card class="section">
      <template #title>
        <div class="section-title">
          <i class="pi pi-key"></i>
          <span>Token Status</span>
        </div>
      </template>
      <template #content>
        <div v-if="status" class="token-status-container">
          <div
            v-for="(statusData, platform) in status"
            :key="platform"
            class="token-item"
            :class="getTokenStatusClass(statusData)"
          >
            <div class="token-platform">
              <span class="platform-icon">{{ getPlatformIcon(platform) }}</span>
              <strong>{{ platform.toUpperCase() }}</strong>
            </div>
            <div
              class="token-details"
              v-html="formatStatusText(statusData)"
            ></div>
          </div>
        </div>
        <div v-else class="loading">Loading token status...</div>
        <Button
          icon="pi pi-refresh"
          label="Refresh Status"
          class="p-button-sm refresh-status-btn"
          @click="$emit('load-status')"
          :loading="loading"
        />
      </template>
    </Card>

    <!-- Quick Actions -->
    <Card class="section">
      <template #title>
        <div class="section-title">
          <i class="pi pi-bolt"></i>
          <span>Quick Actions</span>
        </div>
      </template>
      <template #content>
        <div class="quick-actions">
          <Button
            icon="pi pi-box"
            label="Update Stock All"
            class="p-button-secondary quick-action-btn"
            @click="$emit('execute-operation', 'batch_stock_update')"
            :loading="loading"
          />
          <Button
            icon="pi pi-tag"
            label="Update Prices All"
            class="p-button-secondary quick-action-btn"
            @click="$emit('execute-operation', 'batch_price_update')"
            :loading="loading"
          />
          <Button
            icon="pi pi-layer-group"
            label="Combine Qty by SKU"
            class="p-button-secondary quick-action-btn"
            @click="$emit('execute-operation', 'combine_sku')"
            :loading="loading"
          />
        </div>
      </template>
    </Card>

    <!-- Token Management -->
    <Card class="section">
      <template #title>
        <div class="section-title">
          <i class="pi pi-cog"></i>
          <span>Token Management</span>
        </div>
      </template>
      <template #content>
        <div class="platform-token-buttons">
          <Button
            v-for="platform in ['shopee', 'lazada', 'tiktok']"
            :key="platform"
            :label="platform.charAt(0).toUpperCase() + platform.slice(1)"
            class="p-button-outlined token-management-btn"
            @click="$emit('show-token-modal', platform)"
          />
        </div>
      </template>
    </Card>
  </div>
</template>

<script>
import { computed } from "vue";
import Card from "primevue/card";
import Button from "primevue/button";

export default {
  name: "DashboardSidebar",
  components: {
    Card,
    Button,
  },
  props: {
    status: {
      type: Object,
      default: null,
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["show-token-modal", "execute-operation", "load-status"],
  setup() {
    const getTokenStatusClass = (statusData) => {
      if (typeof statusData === "string") {
        if (statusData.includes("EXPIRED") || statusData.includes("MISSING")) {
          return "token-expired";
        } else if (statusData.includes("VALID")) {
          return "token-valid";
        }
      }
      return "token-warning";
    };

    const getPlatformIcon = (platform) => {
      const icons = {
        shopee: "🛍️",
        lazada: "📦",
        tiktok: "🎵",
      };
      return icons[platform] || "🛒";
    };

    const formatStatusText = (statusData) => {
      if (typeof statusData === "string") {
        return statusData
          .replace(/\n/g, "<br>")
          .replace(/✅/g, '<span style="color: #27ae60;">✅</span>')
          .replace(/❌/g, '<span style="color: #e74c3c;">❌</span>')
          .replace(/⚠️/g, '<span style="color: #f39c12;">⚠️</span>');
      }
      return "Status unavailable";
    };

    return {
      getTokenStatusClass,
      getPlatformIcon,
      formatStatusText,
    };
  },
};
</script>

<style scoped>
.sidebar {
  width: 300px;
  background: white;
  padding: 20px;
  overflow-y: auto;
  border-right: 1px solid #e1e5e9;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
}

.section {
  margin-bottom: 20px;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  overflow: hidden;
  transition: box-shadow 0.2s ease;
}

.section:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  color: #2c3e50;
}

.section :deep(.p-card-title) {
  padding: 15px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e1e5e9;
  margin: 0;
}

.section :deep(.p-card-content) {
  padding: 20px;
}

.token-status-container {
  margin-bottom: 15px;
}

.token-item {
  padding: 12px;
  margin: 8px 0;
  background: white;
  border-radius: 6px;
  border-left: 4px solid;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #e1e5e9;
}

.token-valid {
  border-left-color: #27ae60;
}

.token-expired {
  border-left-color: #e74c3c;
}

.token-warning {
  border-left-color: #f39c12;
}

.token-platform {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.platform-icon {
  font-size: 1.1rem;
}

.token-details {
  font-size: 0.8rem;
  line-height: 1.4;
  color: #555;
}

.loading {
  text-align: center;
  color: #6c757d;
  padding: 20px;
  font-style: italic;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quick-action-btn {
  padding: 10px 16px !important;
  border-radius: 6px !important;
  transition: all 0.3s ease !important;
  font-weight: 500 !important;
}

.quick-action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.platform-token-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.token-management-btn {
  padding: 10px 16px !important;
  border-radius: 6px !important;
  transition: all 0.3s ease !important;
  margin-bottom: 8px !important;
}

.token-management-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(52, 152, 219, 0.3);
}

.refresh-status-btn {
  padding: 8px 16px !important;
  border-radius: 6px !important;
  margin-top: 12px !important;
  transition: all 0.3s ease !important;
}

.refresh-status-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

/* Scrollbar Styling */
.sidebar::-webkit-scrollbar {
  width: 6px;
}

.sidebar::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.sidebar::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.sidebar::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* Responsive Design */
@media (max-width: 768px) {
  .sidebar {
    width: 100%;
    max-height: 40vh;
  }

  .quick-action-btn,
  .token-management-btn {
    padding: 8px 12px !important;
    font-size: 0.85rem !important;
  }
}
</style>