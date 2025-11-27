<template>
  <div class="header">
    <h1>
      <i class="pi pi-shopping-cart"></i> Ecommerce Integration Platform
    </h1>
    <div class="header-controls">
      <div class="connection-status" :class="connectionStatus">
        <span class="status-dot"></span>
        <span class="status-text">{{ connectionStatusText }}</span>
      </div>
      <Button
        icon="pi pi-refresh"
        label="Refresh All"
        @click="$emit('refresh-all')"
        :loading="loading"
        class="p-button-sm refresh-btn"
      />
      <Button
        icon="pi pi-bug"
        label="Debug"
        @click="$emit('show-debug-modal')"
        class="p-button-outlined p-button-sm debug-btn"
      />
    </div>
  </div>
</template>

<script>
import { computed } from "vue";
import Button from "primevue/button";

export default {
  name: "DashboardHeader",
  components: {
    Button,
  },
  props: {
    connectionStatus: {
      type: String,
      default: "connecting",
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },
  emits: ["refresh-all", "show-debug-modal"],
  setup(props) {
    const connectionStatusText = computed(() => {
      const statusMap = {
        connecting: "Connecting...",
        connected: "Connected",
        error: "Disconnected",
      };
      return statusMap[props.connectionStatus] || "Unknown";
    });

    return {
      connectionStatusText,
    };
  },
};
</script>

<style scoped>
.header {
  background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
  color: white;
  padding: 12px 25px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  border-bottom: 1px solid #34495e;
}

.header h1 {
  margin: 0;
  font-size: 1.4rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.15);
  font-size: 0.85rem;
  font-weight: 500;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f39c12;
  display: inline-block;
}

.connection-status.connected .status-dot {
  background: #27ae60;
  box-shadow: 0 0 8px rgba(39, 174, 96, 0.4);
}

.connection-status.error .status-dot {
  background: #e74c3c;
  box-shadow: 0 0 8px rgba(231, 76, 60, 0.4);
  animation: pulse 2s infinite;
}

.connection-status.connecting .status-dot {
  background: #f39c12;
  box-shadow: 0 0 8px rgba(243, 156, 18, 0.4);
  animation: pulse 1s infinite;
}

.refresh-btn,
.debug-btn {
  padding: 8px 16px !important;
  border-radius: 6px !important;
  transition: all 0.3s ease !important;
}

.refresh-btn:hover,
.debug-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
  100% {
    opacity: 1;
  }
}

/* Responsive Design */
@media (max-width: 768px) {
  .header {
    padding: 10px 15px;
  }

  .header h1 {
    font-size: 1.2rem;
  }

  .header-controls {
    gap: 8px;
  }

  .connection-status {
    font-size: 0.8rem;
    padding: 4px 8px;
  }
}
</style>