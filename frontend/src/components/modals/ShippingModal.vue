<template>
  <Dialog
    :visible="visible"
    @update:visible="$emit('update:visible', $event)"
    header="Shopee Shipping Fee Check"
    :style="{ width: '600px' }"
    :modal="true"
    class="custom-modal"
  >
    <div class="modal-content">
      <!-- Shipping Options -->
      <div v-if="!showShippingFileList && !showShippingForm" class="shipping-options">
        <div class="option-card" @click="$emit('select-shipping-option', 1)">
          <div class="option-icon">
            <i class="pi pi-file-export"></i>
          </div>
          <div class="option-content">
            <h4>Get Order Numbers from Wallet</h4>
            <p>Automatically get order numbers from wallet transactions</p>
          </div>
        </div>

        <div class="option-card" @click="$emit('select-shipping-option', 2)">
          <div class="option-icon">
            <i class="pi pi-file-import"></i>
          </div>
          <div class="option-content">
            <h4>Process Existing Files</h4>
            <p>Process existing order number files in the system</p>
          </div>
        </div>
      </div>

      <!-- Option 1: Get from Wallet -->
      <div v-if="showShippingForm" class="form-container">
        <div class="modal-description">
          <i class="pi pi-info-circle"></i>
          <p>
            Select the month and year to extract order numbers from wallet
            transactions.
          </p>
        </div>

        <div class="form-group">
          <label for="shipping-month">Month</label>
          <Dropdown
            v-model="internalShippingParams.month"
            :options="months"
            optionLabel="name"
            optionValue="value"
            placeholder="Select Month"
            class="w-full custom-dropdown"
            @change="updateShippingParams"
          />
        </div>

        <div class="form-group">
          <label for="shipping-year">Year</label>
          <Dropdown
            v-model="internalShippingParams.year"
            :options="years"
            optionLabel="name"
            optionValue="value"
            placeholder="Select Year"
            class="w-full custom-dropdown"
            @change="updateShippingParams"
          />
        </div>
      </div>

      <!-- Option 2: File List -->
      <div v-if="showShippingFileList" class="file-list">
        <div class="modal-description">
          <i class="pi pi-folder-open"></i>
          <p>Select a file to process shipping fee differences.</p>
        </div>

        <div v-if="shippingFiles.length > 0" class="file-list-container">
          <div
            v-for="file in shippingFiles"
            :key="file.filename"
            class="file-item"
          >
            <div class="file-header">
              <i class="pi pi-file"></i>
              <div class="file-info">
                <span class="file-name">{{ file.filename }}</span>
                <span class="file-description">{{ file.description }}</span>
              </div>
            </div>
            <div class="file-details">
              <span class="file-size">{{ formatFileSize(file.size) }}</span>
              <span class="file-modified">{{ file.modified }}</span>
            </div>
            <Button
              icon="pi pi-play"
              label="Process File"
              class="p-button-sm file-process-btn"
              @click="$emit('process-shipping-file', file.filename)"
            />
          </div>
        </div>
        <div v-else class="no-files">
          <i class="pi pi-info-circle"></i>
          <p>No shipping files found in the system</p>
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
        <Button
          v-if="showShippingForm"
          label="Process to Google Sheets"
          icon="pi pi-calculator"
          class="modal-confirm-btn"
          @click="$emit('export-shipping-to-sheets')"
        />
        <Button
          v-if="showShippingFileList"
          label="Refresh Files"
          icon="pi pi-refresh"
          @click="$emit('load-shipping-files')"
          class="p-button-secondary modal-action-btn"
        />
      </div>
    </template>
  </Dialog>
</template>

<script>
import { ref, watch } from "vue";
import Dialog from "primevue/dialog";
import Dropdown from "primevue/dropdown";
import Button from "primevue/button";

export default {
  name: "ShippingModal",
  components: {
    Dialog,
    Dropdown,
    Button,
  },
  props: {
    visible: {
      type: Boolean,
      default: false,
    },
    shippingParams: {
      type: Object,
      default: () => ({
        month: new Date().getMonth() + 1,
        year: new Date().getFullYear(),
        option: 1,
      }),
    },
    shippingFiles: {
      type: Array,
      default: () => [],
    },
    showShippingForm: {
      type: Boolean,
      default: false,
    },
    showShippingFileList: {
      type: Boolean,
      default: false,
    },
  },
  emits: [
    "close",
    "select-shipping-option",
    "load-shipping-files",
    "process-shipping-file",
    "process-shipping-fee",
    "update-shipping-params",
  ],
  setup(props, { emit }) {
    const internalShippingParams = ref({ ...props.shippingParams });

    // Generate years from 2020 to 2030
    const years = ref(
      Array.from({ length: 11 }, (_, i) => ({
        name: (2020 + i).toString(),
        value: 2020 + i,
      }))
    );

    const months = ref([
      { name: "January", value: 1 },
      { name: "February", value: 2 },
      { name: "March", value: 3 },
      { name: "April", value: 4 },
      { name: "May", value: 5 },
      { name: "June", value: 6 },
      { name: "July", value: 7 },
      { name: "August", value: 8 },
      { name: "September", value: 9 },
      { name: "October", value: 10 },
      { name: "November", value: 11 },
      { name: "December", value: 12 },
    ]);

    const formatFileSize = (bytes) => {
      if (bytes === 0) return "0 Bytes";
      const k = 1024;
      const sizes = ["Bytes", "KB", "MB", "GB"];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
    };

    const updateShippingParams = () => {
      emit("update-shipping-params", internalShippingParams.value);
    };

    // Watch for prop changes
    watch(
      () => props.shippingParams,
      (newParams) => {
        internalShippingParams.value = { ...newParams };
      },
      { deep: true }
    );

    return {
      internalShippingParams,
      years,
      months,
      formatFileSize,
      updateShippingParams,
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

.shipping-options {
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

.form-container {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-group {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #2c3e50;
  font-size: 0.9rem;
}

.w-full {
  width: 100%;
}

.custom-dropdown {
  border-radius: 6px !important;
}

.custom-dropdown :deep(.p-dropdown) {
  width: 100%;
  border-radius: 6px !important;
}

.custom-dropdown :deep(.p-dropdown-label) {
  padding: 0.75rem !important;
}

.file-list-container {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #e1e5e9;
  border-radius: 6px;
  padding: 8px;
}

.file-item {
  padding: 12px;
  border: 1px solid #e1e5e9;
  border-radius: 6px;
  margin-bottom: 8px;
  background: white;
  transition: all 0.2s ease;
}

.file-item:hover {
  border-color: #3498db;
  background: #f8fafc;
  transform: translateY(-1px);
}

.file-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.file-header i {
  color: #3498db;
  font-size: 1.2rem;
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-name {
  font-weight: 600;
  color: #2c3e50;
  font-size: 0.9rem;
}

.file-description {
  color: #6c757d;
  font-size: 0.8rem;
}

.file-details {
  display: flex;
  gap: 12px;
  font-size: 0.8rem;
  color: #6c757d;
  margin-bottom: 8px;
}

.file-process-btn {
  padding: 6px 12px !important;
  border-radius: 4px !important;
  transition: all 0.3s ease !important;
  margin-top: 8px !important;
}

.file-process-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.no-files {
  text-align: center;
  padding: 2rem;
  color: #6c757d;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px dashed #dee2e6;
}

.no-files i {
  font-size: 2rem;
  margin-bottom: 1rem;
  display: block;
  color: #adb5bd;
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

.modal-action-btn {
  padding: 8px 16px !important;
  border-radius: 6px !important;
  transition: all 0.3s ease !important;
}

.modal-cancel-btn:hover,
.modal-confirm-btn:hover,
.modal-action-btn:hover {
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
.file-list-container::-webkit-scrollbar {
  width: 6px;
}

.file-list-container::-webkit-scrollbar-track {
  background: #f1f1f1;
}

.file-list-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.file-list-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
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
}
</style>