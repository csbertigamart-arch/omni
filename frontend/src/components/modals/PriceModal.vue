<template>
  <Dialog
    :visible="visible"
    @update:visible="$emit('update:visible', $event)"
    :header="`Update Prices - ${
      platform ? platform.charAt(0).toUpperCase() + platform.slice(1) : ''
    }`"
    :style="{ width: '500px' }"
    :modal="true"
    class="custom-modal"
  >
    <div class="modal-content">
      <div class="modal-description">
        <i class="pi pi-tag"></i>
        <p>Select the type of price update you want to perform.</p>
      </div>

      <div class="price-options">
        <div
          class="option-card"
          :class="{ active: currentPriceOption === 'regular' }"
          @click="$emit('select-price-option', 'regular')"
        >
          <div class="option-icon">
            <i class="pi pi-tag"></i>
          </div>
          <div class="option-content">
            <h4>Regular Price</h4>
            <p>Update regular product prices</p>
          </div>
          <i
            v-if="currentPriceOption === 'regular'"
            class="pi pi-check active-check"
          ></i>
        </div>

        <div
          class="option-card"
          :class="{ active: currentPriceOption === 'wholesale' }"
          @click="$emit('select-price-option', 'wholesale')"
        >
          <div class="option-icon">
            <i class="pi pi-layer-group"></i>
          </div>
          <div class="option-content">
            <h4>Wholesale Price</h4>
            <p>Update wholesale price tiers</p>
          </div>
          <i
            v-if="currentPriceOption === 'wholesale'"
            class="pi pi-check active-check"
          ></i>
        </div>

        <div
          class="option-card"
          :class="{ active: currentPriceOption === 'delete_wholesale' }"
          @click="$emit('select-price-option', 'delete_wholesale')"
        >
          <div class="option-icon">
            <i class="pi pi-trash"></i>
          </div>
          <div class="option-content">
            <h4>Delete Wholesale</h4>
            <p>Delete all wholesale tiers</p>
          </div>
          <i
            v-if="currentPriceOption === 'delete_wholesale'"
            class="pi pi-check active-check"
          ></i>
        </div>
      </div>

      <div v-if="currentPriceOption" class="price-instructions">
        <div class="instructions-header">
          <i class="pi pi-info-circle"></i>
          <h4>Instructions:</h4>
        </div>
        <p>{{ priceInstructions }}</p>
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
          label="Execute Update"
          icon="pi pi-play"
          class="modal-confirm-btn"
          @click="$emit('execute-price-update')"
          :disabled="!currentPriceOption"
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
  name: "PriceModal",
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
    currentPriceOption: {
      type: String,
      default: null,
    },
  },
  emits: ["close", "select-price-option", "execute-price-update"],
  setup(props) {
    const priceInstructions = computed(() => {
      const instructions = {
        regular:
          "Update regular prices for all checked products in the sheet. Make sure the Google Sheet is prepared correctly with product IDs and new prices.",
        wholesale:
          "Update wholesale price tiers. Ensure Min_Order1, Price_Order1, Max_Order1 columns are filled. The system will automatically delete old tiers before adding new ones.",
        delete_wholesale:
          "Delete all wholesale tiers for checked products. This action cannot be undone. Make sure you have backups if needed.",
      };
      return instructions[props.currentPriceOption] || "";
    });

    return {
      priceInstructions,
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

.price-options {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
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

.option-card.active {
  border-color: #3498db;
  background: #f0f8ff;
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

.option-card.active .option-icon {
  background: #3498db;
}

.option-card.active .option-icon i {
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

.active-check {
  color: #3498db;
  font-size: 1.2rem;
}

.price-instructions {
  margin-top: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #3498db;
}

.instructions-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.instructions-header h4 {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
  color: #2c3e50;
}

.instructions-header i {
  color: #3498db;
}

.price-instructions p {
  margin: 0;
  color: #6c757d;
  font-size: 0.85rem;
  line-height: 1.5;
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