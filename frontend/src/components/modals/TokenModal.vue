<template>
  <Dialog
    :visible="visible"
    @update:visible="$emit('update:visible', $event)"
    :header="`${
      platform ? platform.charAt(0).toUpperCase() + platform.slice(1) : ''
    } Token Management`"
    :style="{ width: '500px' }"
    :modal="true"
    class="custom-modal"
  >
    <div class="modal-content">
      <div class="modal-description">
        <i class="pi pi-info-circle"></i>
        <p>
          Manage your {{ platform }} API tokens and authorization codes.
        </p>
      </div>

      <div class="modal-actions">
        <Button
          icon="pi pi-code"
          label="Update Authorization Code"
          class="p-button-secondary modal-action-btn"
          @click="$emit('handle-token-operation', 'update_code')"
        />
        <Button
          icon="pi pi-key"
          label="Get Access Token"
          class="p-button-secondary modal-action-btn"
          @click="$emit('handle-token-operation', 'get_token')"
        />
        <Button
          icon="pi pi-refresh"
          label="Refresh Token"
          class="p-button-secondary modal-action-btn"
          @click="$emit('handle-token-operation', 'refresh_token')"
        />
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
import Dialog from "primevue/dialog";
import Button from "primevue/button";

export default {
  name: "TokenModal",
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
  emits: ["close", "handle-token-operation"],
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

.modal-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.modal-action-btn {
  padding: 12px 16px !important;
  border-radius: 6px !important;
  transition: all 0.3s ease !important;
  font-weight: 500 !important;
  text-align: left !important;
  justify-content: flex-start !important;
}

.modal-action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
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