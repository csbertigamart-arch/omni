<template>
  <Dialog
    :visible="visible"
    @update:visible="$emit('update:visible', $event)"
    header="Debug Information"
    :style="{ width: '700px' }"
    :modal="true"
    class="custom-modal"
  >
    <div class="modal-content">
      <div class="modal-description">
        <i class="pi pi-bug"></i>
        <p>System debug information and connection status.</p>
      </div>

      <div v-if="debugInfo" class="debug-info">
        <div class="debug-section">
          <h4>System Status</h4>
          <pre>{{ JSON.stringify(debugInfo, null, 2) }}</pre>
        </div>
      </div>
      <div v-else class="debug-loading">
        <ProgressSpinner style="width: 50px; height: 50px" strokeWidth="4" />
        <p>Loading debug information...</p>
      </div>
    </div>

    <template #footer>
      <div class="modal-footer">
        <Button
          label="Close"
          icon="pi pi-times"
          @click="$emit('close')"
          class="p-button-text modal-cancel-btn"
        />
        <Button
          label="Refresh Debug"
          icon="pi pi-refresh"
          class="modal-confirm-btn"
          @click="$emit('load-debug-info')"
        />
      </div>
    </template>
  </Dialog>
</template>

<script>
import Dialog from "primevue/dialog";
import Button from "primevue/button";
import ProgressSpinner from "primevue/progressspinner";

export default {
  name: "DebugModal",
  components: {
    Dialog,
    Button,
    ProgressSpinner,
  },
  props: {
    visible: {
      type: Boolean,
      default: false,
    },
    debugInfo: {
      type: Object,
      default: null,
    },
  },
  emits: ["close", "load-debug-info"],
};
</script>

<style scoped>
.custom-modal :deep(.p-dialog-header) {
  padding: 1.5rem 1.5rem 0.5rem 1.5rem !important;
  border-bottom: 1px solid #e1e5e9 !important;
}

.custom-modal :deep(.p-dialog-content) {
  padding: 0 1.5rem !important;
}

.custom-modal :deep(.p-dialog-footer) {
  padding: 1rem 1.5rem !important;
  border-top: 1px solid #e1e5e9 !important;
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

.modal-content {
  padding: 1rem 0;
}

.modal-description {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #3498db;
}

.modal-description i {
  color: #3498db;
  font-size: 1.1rem;
  margin-top: 0.1rem;
}

.modal-description p {
  margin: 0;
  color: #495057;
  font-size: 0.9rem;
  line-height: 1.5;
}

.debug-info {
  font-family: "Courier New", monospace;
  font-size: 0.8rem;
  max-height: 60vh;
  overflow-y: auto;
}

.debug-section {
  margin-bottom: 1.5rem;
}

.debug-section h4 {
  margin: 0 0 0.8rem 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: #2c3e50;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #e1e5e9;
}

.debug-section pre {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 6px;
  border: 1px solid #e1e5e9;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 0.75rem;
  line-height: 1.4;
  max-height: 300px;
  overflow-y: auto;
}

.debug-loading {
  text-align: center;
  padding: 3rem;
  color: #6c757d;
}

.debug-loading p {
  margin-top: 1rem;
  font-size: 0.9rem;
}

.modal-cancel-btn {
  padding: 8px 16px !important;
  border-radius: 6px !important;
  transition: all 0.3s ease !important;
}

.modal-confirm-btn {
  padding: 8px 16px !important;
  border-radius: 6px !important;
  transition: all 0.3s ease !important;
}

.modal-cancel-btn:hover,
.modal-confirm-btn:hover {
  transform: translateY(-1px);
}

.modal-footer {
  display: flex;
  gap: 0.5rem;
  width: 100%;
  justify-content: flex-end;
}

/* Animation for modal appearance */
.custom-modal :deep(.p-dialog) {
  animation: modalAppear 0.3s ease-out;
}

@keyframes modalAppear {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

/* Scrollbar Styling */
.debug-info::-webkit-scrollbar,
.debug-section pre::-webkit-scrollbar {
  width: 6px;
}

.debug-info::-webkit-scrollbar-track,
.debug-section pre::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.debug-info::-webkit-scrollbar-thumb,
.debug-section pre::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.debug-info::-webkit-scrollbar-thumb:hover,
.debug-section pre::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* Responsive Design */
@media (max-width: 768px) {
  .custom-modal :deep(.p-dialog) {
    width: 95% !important;
    margin: 1rem auto !important;
  }

  .debug-section pre {
    font-size: 0.7rem;
    padding: 0.75rem;
  }
}
</style>