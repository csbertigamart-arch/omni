<template>
  <Dialog
  :visible="visible"
  @update:visible="$emit('update:visible', $event)"
    header="Shopee Wallet Transactions"
    :style="{ width: '500px' }"
    :modal="true"
    class="custom-modal"
  >
    <div class="modal-content">
      <div class="modal-description">
        <i class="pi pi-wallet"></i>
        <p>Download wallet transaction reports for the selected period.</p>
      </div>

      <div class="form-container">
        <div class="form-group">
          <label for="wallet-month">Month</label>
          <Dropdown
            v-model="internalWalletParams.month"
            :options="months"
            optionLabel="name"
            optionValue="value"
            placeholder="Select Month"
            class="w-full custom-dropdown"
            @change="updateWalletParams"
          />
        </div>

        <div class="form-group">
          <label for="wallet-year">Year</label>
          <Dropdown
            v-model="internalWalletParams.year"
            :options="years"
            optionLabel="name"
            optionValue="value"
            placeholder="Select Year"
            class="w-full custom-dropdown"
            @change="updateWalletParams"
          />
        </div>

        <div class="form-group">
          <label for="wallet-type">Transaction Type</label>
          <Dropdown
            v-model="internalWalletParams.transaction_type"
            :options="transactionTypes"
            optionLabel="name"
            optionValue="value"
            placeholder="Select Type"
            class="w-full custom-dropdown"
            @change="updateWalletParams"
          />
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
        <!-- INI HARUS SESUAI -->
        <Button
          label="Export to Google Sheets"
          icon="pi pi-download"
          class="modal-confirm-btn"
          @click="$emit('export-wallet-to-sheets')"
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
  name: "WalletModal",
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
    walletParams: {
      type: Object,
      default: () => ({
        month: new Date().getMonth() + 1,
        year: new Date().getFullYear(),
        transaction_type: "wallet_order_income",
      }),
    },
  },
  emits: ["close", "update-wallet-params", "export-wallet-to-sheet"],
  setup(props, { emit }) {
    const internalWalletParams = ref({ ...props.walletParams });

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

    const transactionTypes = ref([
      { name: "Order Income", value: "wallet_order_income" },
      { name: "Adjustment", value: "wallet_adjustment_filter" },
      { name: "Wallet Payment", value: "wallet_wallet_payment" },
      { name: "Refund from Order", value: "wallet_refund_from_order" },
      { name: "Withdrawals", value: "wallet_withdrawals" },
    ]);

    const updateWalletParams = () => {
      emit("update-wallet-params", internalWalletParams.value);
    };

    // Watch for prop changes
    watch(
      () => props.walletParams,
      (newParams) => {
        internalWalletParams.value = { ...newParams };
      },
      { deep: true }
    );

    return {
      internalWalletParams,
      years,
      months,
      transactionTypes,
      updateWalletParams,
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
}
</style>