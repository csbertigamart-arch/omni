<template>
  <Dialog
    :visible="visible"
    @update:visible="$emit('update:visible', $event)"
    :header="`Export Orders - ${
      platform ? platform.charAt(0).toUpperCase() + platform.slice(1) : ''
    }`"
    :style="{ width: '650px' }"
    :modal="true"
    class="custom-modal"
  >
    <div class="modal-content">
      <div class="modal-description">
        <i class="pi pi-file-export"></i>
        <p>Select the type of orders you want to export.</p>
      </div>

      <div class="export-options-container">
        <div class="export-options">
          <div
            v-for="option in exportOptions"
            :key="option.value"
            class="option-card"
            @click="$emit('execute-export-order', option.value)"
          >
            <div class="option-icon">
              <i :class="option.icon"></i>
            </div>
            <div class="option-content">
              <h4>{{ option.label }}</h4>
              <p>{{ option.description }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="modal-footer">
        <Button
          label="Cancel"
          icon="pi pi-times"
          @click="$emit('close')"
          class="p-button-text modal-cancel-btn"
        />
      </div>
    </template>
  </Dialog>
</template>

<script>
import { computed } from "vue";
import Dialog from "primevue/dialog";
import Button from "primevue/button";

export default {
  name: "ExportOrdersModal",
  components: {
    Dialog,
    Button,
  },
  props: {
    visible: {
      type: Boolean,
      default: false,
    },
    platform: {
      type: String,
      default: null,
    },
  },
  emits: ["close", "execute-export-order"],
  setup(props) {
    const exportOptions = computed(() => {
      const options = {
        shopee: [
          {
            value: "UNPAID",
            icon: "pi pi-clock",
            label: "UNPAID Orders",
            description: "Export orders waiting for payment",
          },
          {
            value: "READY_TO_SHIP",
            icon: "pi pi-shipping-fast",
            label: "READY TO SHIP Orders",
            description: "Export orders ready for shipping",
          },
          {
            value: "PROCESSED",
            icon: "pi pi-cog",
            label: "PROCESSED Orders",
            description: "Export orders being processed",
          },
          {
            value: "COMPLETED",
            icon: "pi pi-check-circle",
            label: "COMPLETED Orders",
            description: "Export completed orders",
          },
          {
            value: "ALL",
            icon: "pi pi-layer-group",
            label: "ALL Orders",
            description: "Export all order types combined",
          },
        ],
        lazada: [
          {
            value: "unpaid",
            icon: "pi pi-clock",
            label: "UNPAID Orders",
            description: "Export unpaid orders",
          },
          {
            value: "pending",
            icon: "pi pi-hourglass",
            label: "PENDING Orders",
            description: "Export pending orders",
          },
          {
            value: "topack",
            icon: "pi pi-box",
            label: "TOPACK Orders",
            description: "Export orders to pack",
          },
          {
            value: "toship",
            icon: "pi pi-shipping-fast",
            label: "TOSHIP Orders",
            description: "Export orders to ship",
          },
          {
            value: "ALL",
            icon: "pi pi-layer-group",
            label: "ALL Orders",
            description: "Export all order types combined",
          },
        ],
        tiktok: [
          {
            value: "UNPAID",
            icon: "pi pi-clock",
            label: "UNPAID Orders",
            description: "Export unpaid orders",
          },
          {
            value: "AWAITING_SHIPMENT",
            icon: "pi pi-shipping-fast",
            label: "AWAITING SHIPMENT",
            description: "Export orders awaiting shipment",
          },
          {
            value: "AWAITING_COLLECTION",
            icon: "pi pi-inbox",
            label: "AWAITING COLLECTION",
            description: "Export orders awaiting collection",
          },
          {
            value: "COMPLETED",
            icon: "pi pi-check-circle",
            label: "COMPLETED Orders",
            description: "Export completed orders",
          },
          {
            value: "ALL",
            icon: "pi pi-layer-group",
            label: "ALL Orders",
            description: "Export all order types combined",
          },
        ],
      };
      return options[props.platform] || [];
    });

    return {
      exportOptions,
    };
  },
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

/* Container dengan scroll */
.export-options-container {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  padding: 8px;
}

.export-options {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.option-card {
  padding: 1.25rem;
  border: 2px solid #e1e5e9;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: white;
  display: flex;
  align-items: center;
  gap: 1rem;
  position: relative;
}

.option-card:hover {
  border-color: #3498db;
  background: #f8fafc;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(52, 152, 219, 0.15);
}

.option-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  background: #f8f9fa;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.option-card:hover .option-icon {
  background: #3498db;
  transform: scale(1.05);
}

.option-card:hover .option-icon i {
  color: white !important;
}

.option-icon i {
  font-size: 1.5rem;
  color: #3498db;
  transition: all 0.3s ease;
}

.option-content {
  flex: 1;
}

.option-content h4 {
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
}

.option-content p {
  margin: 0;
  color: #6c757d;
  font-size: 0.85rem;
  line-height: 1.4;
}

.modal-cancel-btn {
  padding: 8px 16px !important;
  border-radius: 6px !important;
  transition: all 0.3s ease !important;
}

.modal-cancel-btn:hover {
  transform: translateY(-1px);
}

.modal-footer {
  display: flex;
  gap: 0.5rem;
  width: 100%;
  justify-content: flex-end;
}

/* Scrollbar Styling */
.export-options-container::-webkit-scrollbar {
  width: 6px;
}

.export-options-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.export-options-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.export-options-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
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

/* Responsive Design */
@media (max-width: 768px) {
  .custom-modal :deep(.p-dialog) {
    width: 95% !important;
    margin: 1rem auto !important;
  }

  .option-card {
    padding: 1rem;
    gap: 0.75rem;
  }

  .option-icon {
    width: 40px;
    height: 40px;
  }

  .option-icon i {
    font-size: 1.2rem;
  }

  .export-options-container {
    max-height: 300px;
  }
}
</style>
