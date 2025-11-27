<template>
  <div class="status-bar">
    <div class="status-info">
      <span><i class="pi pi-clock"></i> Last updated: {{ lastUpdated }}</span>
      <span :class="['operation-status', loading ? 'running' : 'idle']">
        <i
          :class="loading ? 'pi pi-spin pi-spinner' : 'pi pi-check-circle'"
        ></i>
        {{ loading ? "Running..." : "Ready" }}
      </span>
    </div>
    <div class="status-indicators">
      <span class="indicator">
        <i class="pi pi-exchange"></i> Requests: {{ requestCount }}
      </span>
      <span class="indicator">
        <i class="pi pi-exclamation-triangle"></i> Errors: {{ errorCount }}
      </span>
    </div>
  </div>
</template>

<script>
export default {
  name: "DashboardStatusBar",
  props: {
    lastUpdated: {
      type: String,
      default: "",
    },
    loading: {
      type: Boolean,
      default: false,
    },
    requestCount: {
      type: Number,
      default: 0,
    },
    errorCount: {
      type: Number,
      default: 0,
    },
  },
};
</script>

<style scoped>
.status-bar {
  background: #2c3e50;
  color: white;
  padding: 8px 25px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  border-top: 1px solid #34495e;
}

.status-info {
  display: flex;
  gap: 20px;
  align-items: center;
}

.status-indicators {
  display: flex;
  gap: 15px;
  align-items: center;
}

.indicator {
  display: flex;
  align-items: center;
  gap: 5px;
  opacity: 0.9;
}

.operation-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

.operation-status.running {
  color: #f39c12;
  animation: pulse 1.5s infinite;
}

.operation-status.idle {
  color: #27ae60;
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
  .status-bar {
    padding: 6px 15px;
    font-size: 0.75rem;
  }

  .status-info {
    gap: 12px;
    flex-direction: column;
    align-items: flex-start;
  }

  .status-indicators {
    gap: 10px;
  }
}
</style>