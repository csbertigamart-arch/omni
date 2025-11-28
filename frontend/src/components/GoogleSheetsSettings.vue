<template>
  <div class="google-sheets-settings">
    <!-- Authentication Status -->
    <Card class="section">
      <template #title>
        <div class="section-title">
          <i class="pi pi-google"></i>
          <span>Google Sheets Authentication</span>
        </div>
      </template>
      <template #content>
        <div v-if="loading" class="loading">
          <ProgressSpinner style="width: 30px; height: 30px" />
          <span>Loading authentication status...</span>
        </div>

        <div v-else class="auth-status">
          <div
            class="status-indicator"
            :class="authStatus.authenticated ? 'connected' : 'disconnected'"
          >
            <i
              :class="authStatus.authenticated ? 'pi pi-check-circle' : 'pi pi-exclamation-circle'"
            ></i>
            <span>{{ authStatus.authenticated ? 'Connected to Google' : 'Not Connected' }}</span>
          </div>

          <div v-if="!authStatus.has_credentials" class="credentials-warning">
            <i class="pi pi-exclamation-triangle"></i>
            <div>
              <p><strong>Google OAuth credentials not configured</strong></p>
              <p>Please download credentials from Google Cloud Console and save as:</p>
              <code>backend/config/google_credentials.json</code>
              <p class="help-text">
                Steps:
                <br />1. Go to
                <a href="https://console.cloud.google.com" target="_blank">Google Cloud Console</a>
                <br />2. Create credentials (OAuth 2.0 Client IDs) <br />3. Set redirect URI to:
                <code>http://localhost:5000/api/google/auth/callback</code>
                <br />4. Download JSON and save as above
              </p>
            </div>
          </div>

          <div class="auth-actions">
            <Button
              v-if="!authStatus.authenticated && authStatus.has_credentials"
              icon="pi pi-google"
              label="Connect Google Account"
              @click="initiateAuth"
              :loading="authLoading"
              class="p-button-success auth-btn"
            />

            <Button
              v-if="authStatus.authenticated"
              icon="pi pi-sign-out"
              label="Disconnect"
              @click="logout"
              :loading="loading"
              class="p-button-danger auth-btn"
            />

            <Button
              icon="pi pi-refresh"
              label="Refresh Status"
              @click="refreshAuthStatus"
              :loading="loading"
              class="p-button-outlined auth-btn"
            />
          </div>
        </div>
      </template>
    </Card>

    <!-- Spreadsheet Configuration -->
    <Card v-if="authStatus.authenticated" class="section">
      <template #title>
        <div class="section-title">
          <i class="pi pi-table"></i>
          <span>Spreadsheet Configuration</span>
        </div>
      </template>
      <template #content>
        <div class="config-form">
          <!-- Wallet Report Spreadsheet -->
          <div class="form-group">
            <label class="form-label">
              <i class="pi pi-wallet"></i>
              Wallet Report Spreadsheet
            </label>
            <div class="spreadsheet-selector">
              <div class="dropdown-container">
                <Dropdown
                  v-model="selectedWalletSpreadsheet"
                  :options="spreadsheets"
                  optionLabel="name"
                  optionValue="id"
                  placeholder="Select spreadsheet for wallet reports"
                  class="w-full spreadsheet-dropdown"
                  :filter="false"
                  :showClear="false"
                  :disabled="spreadsheets.length === 0"
                >
                  <template #value="slotProps">
                    <div v-if="slotProps.value" class="selected-spreadsheet">
                      <i class="pi pi-file-excel"></i>
                      <span>{{ getSpreadsheetName(slotProps.value) }}</span>
                    </div>
                    <span v-else>{{ slotProps.placeholder }}</span>
                  </template>
                  <template #option="slotProps">
                    <div class="spreadsheet-option">
                      <i class="pi pi-file-excel"></i>
                      <div class="option-details">
                        <div class="option-name">
                          {{ slotProps.option.name }}
                        </div>
                        <div class="option-id">{{ slotProps.option.id }}</div>
                      </div>
                    </div>
                  </template>
                </Dropdown>
                <small class="helper-text">
                  Spreadsheet untuk menyimpan laporan wallet transactions dari Shopee
                </small>
              </div>

              <div class="spreadsheet-actions">
                <Button
                  icon="pi pi-refresh"
                  label="Refresh List"
                  @click="refreshSpreadsheets"
                  :loading="loading"
                  class="p-button-outlined p-button-sm refresh-btn"
                  :disabled="loading"
                />
                <Button
                  icon="pi pi-plus"
                  label="Create New"
                  @click="createNewSpreadsheet('wallet')"
                  :loading="creatingSpreadsheet"
                  class="p-button-outlined p-button-sm create-btn"
                />
              </div>
            </div>
          </div>

          <!-- Shipping Fee Spreadsheet -->
          <div class="form-group">
            <label class="form-label">
              <i class="pi pi-truck"></i>
              Shipping Fee Report Spreadsheet
            </label>
            <div class="spreadsheet-selector">
              <div class="dropdown-container">
                <Dropdown
                  v-model="selectedShippingSpreadsheet"
                  :options="spreadsheets"
                  optionLabel="name"
                  optionValue="id"
                  placeholder="Select spreadsheet for shipping fee reports"
                  class="w-full spreadsheet-dropdown"
                  :filter="false"
                  :showClear="false"
                  :disabled="spreadsheets.length === 0"
                >
                  <template #value="slotProps">
                    <div v-if="slotProps.value" class="selected-spreadsheet">
                      <i class="pi pi-file-excel"></i>
                      <span>{{ getSpreadsheetName(slotProps.value) }}</span>
                    </div>
                    <span v-else>{{ slotProps.placeholder }}</span>
                  </template>
                  <template #option="slotProps">
                    <div class="spreadsheet-option">
                      <i class="pi pi-file-excel"></i>
                      <div class="option-details">
                        <div class="option-name">
                          {{ slotProps.option.name }}
                        </div>
                        <div class="option-id">{{ slotProps.option.id }}</div>
                      </div>
                    </div>
                  </template>
                </Dropdown>
                <small class="helper-text">
                  Spreadsheet untuk menyimpan laporan perhitungan shipping fee dari Shopee
                </small>
              </div>

              <div class="spreadsheet-actions">
                <Button
                  icon="pi pi-refresh"
                  label="Refresh List"
                  @click="refreshSpreadsheets"
                  :loading="loading"
                  class="p-button-outlined p-button-sm refresh-btn"
                  :disabled="loading"
                />
                <Button
                  icon="pi pi-plus"
                  label="Create New"
                  @click="createNewSpreadsheet('shipping')"
                  :loading="creatingSpreadsheet"
                  class="p-button-outlined p-button-sm create-btn"
                />
              </div>
            </div>
          </div>

          <!-- Di template, perbaiki bagian Order Spreadsheet -->
          <div class="form-group">
            <label class="form-label">
              <i class="pi pi-shopping-cart"></i>
              Order Export Spreadsheet
              <span class="optional-badge">(Optional)</span>
            </label>
            <div class="spreadsheet-selector">
              <div class="dropdown-container">
                <Dropdown
                  v-model="selectedOrderSpreadsheet"
                  :options="spreadsheets"
                  optionLabel="name"
                  optionValue="id"
                  placeholder="Select spreadsheet for order exports"
                  class="w-full spreadsheet-dropdown"
                  :filter="false"
                  :showClear="true"
                  :disabled="spreadsheets.length === 0"
                >
                  <template #value="slotProps">
                    <div v-if="slotProps.value" class="selected-spreadsheet">
                      <i class="pi pi-file-excel"></i>
                      <span>{{ getSpreadsheetName(slotProps.value) }}</span>
                      <span v-if="slotProps.value === selectedWalletSpreadsheet" class="same-as-wallet-badge">
                        (Same as Wallet)
                      </span>
                    </div>
                    <span v-else>{{ slotProps.placeholder }}</span>
                  </template>
                  <template #option="slotProps">
                    <div class="spreadsheet-option">
                      <i class="pi pi-file-excel"></i>
                      <div class="option-details">
                        <div class="option-name">{{ slotProps.option.name }}</div>
                        <div class="option-id">{{ slotProps.option.id }}</div>
                      </div>
                    </div>
                  </template>
                </Dropdown>
                <small class="helper-text">
                  Spreadsheet untuk menyimpan ekspor order dari semua platform
                  <br /><strong>Kosongkan</strong> jika tidak ingin mengekspor order
                </small>
              </div>

              <div class="spreadsheet-actions">
                <Button
                  icon="pi pi-refresh"
                  label="Refresh List"
                  @click="refreshSpreadsheets"
                  :loading="loading"
                  class="p-button-outlined p-button-sm refresh-btn"
                  :disabled="loading"
                />
                <Button
                  icon="pi pi-copy"
                  label="Use Wallet"
                  @click="selectedOrderSpreadsheet = selectedWalletSpreadsheet"
                  :disabled="!selectedWalletSpreadsheet"
                  class="p-button-outlined p-button-sm copy-btn"
                />
                <Button
                  icon="pi pi-times"
                  label="Clear"
                  @click="selectedOrderSpreadsheet = ''"
                  :disabled="!selectedOrderSpreadsheet"
                  class="p-button-outlined p-button-sm clear-btn"
                />
              </div>
            </div>
          </div>
          <div class="form-actions">
            <Button
              icon="pi pi-save"
              label="Save Configuration"
              @click="saveConfiguration"
              :loading="saving"
              class="p-button-primary save-btn"
            />
            <Button
              icon="pi pi-test-tube"
              label="Test Connections"
              @click="testConnections"
              :loading="testing"
              class="p-button-outlined test-btn"
            />
          </div>

          <div
            v-if="saveResult"
            class="save-result"
            :class="saveResult.success ? 'success' : 'error'"
          >
            <i :class="saveResult.success ? 'pi pi-check-circle' : 'pi pi-exclamation-circle'"></i>
            <span>{{ saveResult.message }}</span>
          </div>
        </div>
      </template>
    </Card>

    <!-- Create Spreadsheet Dialog -->
    <Dialog
      v-model:visible="showCreateDialog"
      header="Create New Spreadsheet"
      :style="{ width: '500px' }"
      :modal="true"
    >
      <div class="create-dialog">
        <div class="dialog-description">
          <i class="pi pi-info-circle"></i>
          <p>
            Create a new Google Spreadsheet for
            {{ createFor === 'wallet' ? 'Wallet Reports' : 'Shipping Fee Reports' }}
          </p>
        </div>

        <div class="form-group">
          <label>Spreadsheet Name</label>
          <InputText
            v-model="newSpreadsheetName"
            placeholder="Enter spreadsheet name"
            class="w-full"
            :class="{ 'p-invalid': !newSpreadsheetName }"
          />
          <small class="helper-text"> Suggested: {{ suggestedName }} </small>
        </div>
      </div>

      <template #footer>
        <Button
          label="Cancel"
          icon="pi pi-times"
          @click="showCreateDialog = false"
          class="p-button-text"
        />
        <Button
          label="Create"
          icon="pi pi-plus"
          @click="confirmCreateSpreadsheet"
          :disabled="!newSpreadsheetName"
          :loading="creatingSpreadsheet"
          class="p-button-primary"
        />
      </template>
    </Dialog>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useGoogleSheetsStore } from '../store/googleSheets';
import Card from 'primevue/card';
import Button from 'primevue/button';
import Dropdown from 'primevue/dropdown';
import InputText from 'primevue/inputtext';
import Dialog from 'primevue/dialog';
import ProgressSpinner from 'primevue/progressspinner';

export default {
  name: 'GoogleSheetsSettings',
  components: {
    Card,
    Button,
    Dropdown,
    InputText,
    Dialog,
    ProgressSpinner,
  },
  setup() {
    const toast = useToast();
    const googleSheetsStore = useGoogleSheetsStore();
    const selectedOrderSpreadsheet = ref('');
    const authStatus = ref({
      authenticated: false,
      settings: {},
      has_credentials: false,
    });
    const spreadsheets = ref([]);
    const loading = ref(false);
    const authLoading = ref(false);
    const saving = ref(false);
    const testing = ref(false);
    const creatingSpreadsheet = ref(false);

    const selectedWalletSpreadsheet = ref('');
    const selectedShippingSpreadsheet = ref('');
    const saveResult = ref(null);

    const showCreateDialog = ref(false);
    const createFor = ref('wallet');
    const newSpreadsheetName = ref('');

    const suggestedName = computed(() => {
      const baseName = createFor.value === 'wallet' ? 'Wallet_Reports' : 'Shipping_Fee_Reports';
      const timestamp = new Date().toISOString().split('T')[0];
      return `${baseName}_${timestamp}`;
    });

    // Dalam setup() di GoogleSheetsSettings.vue

    const refreshSpreadsheets = async () => {
      try {
        // Gunakan store Google Sheets untuk refresh
        await googleSheetsStore.refreshSpreadsheets();

        // Update local spreadsheets data
        spreadsheets.value = googleSheetsStore.spreadsheets;

        toast.add({
          severity: 'success',
          summary: 'Success',
          detail: `Refreshed ${spreadsheets.value.length} spreadsheets`,
          life: 3000,
        });
      } catch (error) {
        console.error('❌ Failed to refresh spreadsheets:', error);
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: error.message,
          life: 5000,
        });
      }
    };

    const loadAuthStatus = async () => {
      try {
        loading.value = true;
        const response = await fetch('/api/google/auth/status');
        const data = await response.json();

        if (data.success) {
          authStatus.value = data.data;
          // Load existing configuration untuk semua spreadsheet
          if (data.data.settings.wallet_spreadsheet_id) {
            selectedWalletSpreadsheet.value = data.data.settings.wallet_spreadsheet_id;
          }
          if (data.data.settings.shipping_spreadsheet_id) {
            selectedShippingSpreadsheet.value = data.data.settings.shipping_spreadsheet_id;
          }
          if (data.data.settings.order_spreadsheet_id) {
            selectedOrderSpreadsheet.value = data.data.settings.order_spreadsheet_id;

          }
        }
      } catch (error) {
        console.error('Failed to load auth status:', error);
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Failed to load authentication status',
          life: 5000,
        });
      } finally {
        loading.value = false;
      }
    };
    const loadSpreadsheets = async () => {
      try {
        loading.value = true;
        const response = await fetch('/api/google/sheets/list');
        const data = await response.json();

        if (data.success) {
          spreadsheets.value = data.data;
          toast.add({
            severity: 'success',
            summary: 'Success',
            detail: `Loaded ${data.data.length} spreadsheets`,
            life: 3000,
          });
        }
      } catch (error) {
        console.error('Failed to load spreadsheets:', error);
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Failed to load spreadsheets',
          life: 5000,
        });
      } finally {
        loading.value = false;
      }
    };

    const getSpreadsheetName = (spreadsheetId) => {
      const spreadsheet = spreadsheets.value.find((s) => s.id === spreadsheetId);
      return spreadsheet ? spreadsheet.name : 'Unknown Spreadsheet';
    };

    const createNewSpreadsheet = (type) => {
      createFor.value = type;
      newSpreadsheetName.value = suggestedName.value;
      showCreateDialog.value = true;
    };

    const confirmCreateSpreadsheet = async () => {
      try {
        creatingSpreadsheet.value = true;
        const response = await fetch('/api/google/spreadsheets/create', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            title: newSpreadsheetName.value,
          }),
        });

        const data = await response.json();

        if (data.success) {
          toast.add({
            severity: 'success',
            summary: 'Success',
            detail: data.message,
            life: 5000,
          });

          // Add to spreadsheets list
          spreadsheets.value.push(data.data);

          // Auto-select the new spreadsheet
          if (createFor.value === 'wallet') {
            selectedWalletSpreadsheet.value = data.data.id;
          } else {
            selectedShippingSpreadsheet.value = data.data.id;
          }

          showCreateDialog.value = false;
          newSpreadsheetName.value = '';
        } else {
          throw new Error(data.error || 'Failed to create spreadsheet');
        }
      } catch (error) {
        console.error('Failed to create spreadsheet:', error);
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: error.message,
          life: 5000,
        });
      } finally {
        creatingSpreadsheet.value = false;
      }
    };

    const saveConfiguration = async () => {
      try {
        saving.value = true;

        // Validasi: pastikan setidaknya satu spreadsheet dipilih
        if (
          !selectedWalletSpreadsheet.value &&
          !selectedShippingSpreadsheet.value &&
          !selectedOrderSpreadsheet.value
        ) {
          throw new Error('Please select at least one spreadsheet');
        }

        const response = await fetch('/api/google/settings/update-detailed', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            wallet_spreadsheet_id: selectedWalletSpreadsheet.value,
            shipping_spreadsheet_id: selectedShippingSpreadsheet.value,
            order_spreadsheet_id: selectedOrderSpreadsheet.value,
          }),
        });

        const data = await response.json();

        if (data.success) {
          saveResult.value = {
            success: true,
            message: data.message,
          };
          toast.add({
            severity: 'success',
            summary: 'Success',
            detail: data.message,
            life: 5000,
          });

          // Refresh status untuk mendapatkan settings terbaru
          await loadAuthStatus();
        } else {
          throw new Error(data.error || 'Failed to save configuration');
        }
      } catch (error) {
        console.error('Failed to save configuration:', error);
        saveResult.value = {
          success: false,
          message: error.message,
        };
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: error.message,
          life: 5000,
        });
      } finally {
        saving.value = false;
      }
    };

    const testConnections = async () => {
      try {
        testing.value = true;

        // Test wallet spreadsheet
        if (selectedWalletSpreadsheet.value) {
          const walletResponse = await fetch('/api/google/settings/test');
          const walletData = await walletResponse.json();

          if (walletData.success) {
            toast.add({
              severity: 'success',
              summary: 'Wallet Spreadsheet',
              detail: 'Connection test successful',
              life: 5000,
            });
          } else {
            toast.add({
              severity: 'error',
              summary: 'Wallet Spreadsheet',
              detail: walletData.error || 'Connection test failed',
              life: 5000,
            });
          }
        }

        // Test shipping spreadsheet
        if (selectedShippingSpreadsheet.value) {
          const shippingResponse = await fetch('/api/google/settings/test');
          const shippingData = await shippingResponse.json();

          if (shippingData.success) {
            toast.add({
              severity: 'success',
              summary: 'Shipping Spreadsheet',
              detail: 'Connection test successful',
              life: 5000,
            });
          } else {
            toast.add({
              severity: 'error',
              summary: 'Shipping Spreadsheet',
              detail: shippingData.error || 'Connection test failed',
              life: 5000,
            });
          }
        }

        if (!selectedWalletSpreadsheet.value && !selectedShippingSpreadsheet.value) {
          toast.add({
            severity: 'warn',
            summary: 'No Spreadsheets',
            detail: 'Please select at least one spreadsheet to test',
            life: 5000,
          });
        }
      } catch (error) {
        console.error('Failed to test connections:', error);
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: error.message,
          life: 5000,
        });
      } finally {
        testing.value = false;
      }
    };

    const initiateAuth = async () => {
      try {
        authLoading.value = true;
        const response = await fetch('/api/google/auth/initiate');
        const data = await response.json();

        if (data.success && data.auth_url) {
          const width = 600;
          const height = 700;
          const left = (window.screen.width - width) / 2;
          const top = (window.screen.height - height) / 2;

          const authWindow = window.open(
            data.auth_url,
            'google_auth',
            `width=${width},height=${height},left=${left},top=${top}`
          );

          const checkAuth = setInterval(() => {
            if (authWindow.closed) {
              clearInterval(checkAuth);
              loadAuthStatus();
            }
          }, 1000);
        } else {
          throw new Error(data.error || 'Failed to generate auth URL');
        }
      } catch (error) {
        console.error('Failed to initiate auth:', error);
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: error.message,
          life: 5000,
        });
      } finally {
        authLoading.value = false;
      }
    };

    const logout = async () => {
      try {
        loading.value = true;
        const response = await fetch('/api/google/auth/logout');
        const data = await response.json();

        if (data.success) {
          toast.add({
            severity: 'success',
            summary: 'Success',
            detail: 'Successfully disconnected from Google',
            life: 3000,
          });
          await loadAuthStatus();
          // Reset selections
          selectedWalletSpreadsheet.value = '';
          selectedShippingSpreadsheet.value = '';
          spreadsheets.value = [];
        } else {
          throw new Error(data.error || 'Failed to logout');
        }
      } catch (error) {
        console.error('Failed to logout:', error);
        toast.add({
          severity: 'error',
          summary: 'Error',
          detail: error.message,
          life: 5000,
        });
      } finally {
        loading.value = false;
      }
    };

    const refreshAuthStatus = async () => {
      await loadAuthStatus();
      await loadSpreadsheets();
      toast.add({
        severity: 'info',
        summary: 'Info',
        detail: 'Authentication status refreshed',
        life: 3000,
      });
    };

    onMounted(() => {
      loadAuthStatus();
      loadSpreadsheets();

      window.addEventListener('message', (event) => {
        if (event.data && event.data.type === 'google_auth_success') {
          loadAuthStatus();
          loadSpreadsheets();
          toast.add({
            severity: 'success',
            summary: 'Success',
            detail: 'Google authentication successful!',
            life: 5000,
          });
        } else if (event.data && event.data.type === 'google_auth_error') {
          toast.add({
            severity: 'error',
            summary: 'Authentication Failed',
            detail: event.data.error || 'Google authentication failed',
            life: 5000,
          });
        }
      });
    });

    watch(selectedOrderSpreadsheet, (newValue) => {
      console.log('Order spreadsheet changed to:', newValue);
      saveResult.value = null;
    });

    // Juga perbaiki watch yang existing
    watch([selectedWalletSpreadsheet, selectedShippingSpreadsheet], () => {
      saveResult.value = null;
    });

    return {
      authStatus,
      spreadsheets,
      loading,
      authLoading,
      saving,
      testing,
      creatingSpreadsheet,
      selectedWalletSpreadsheet,
      selectedShippingSpreadsheet,
      saveResult,
      showCreateDialog,
      createFor,
      newSpreadsheetName,
      refreshSpreadsheets,
      suggestedName,
      getSpreadsheetName,
      createNewSpreadsheet,
      confirmCreateSpreadsheet,
      saveConfiguration,
      testConnections,
      initiateAuth,
      logout,
      refreshAuthStatus,
    };
  },
};
</script>

<style scoped>
.google-sheets-settings {
  padding: 20px;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.section {
  margin-bottom: 20px;
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  overflow: hidden;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
}

.loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px;
  justify-content: center;
  color: #6c757d;
}

.auth-status {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 6px;
  font-weight: 500;
}

.status-indicator.connected {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.status-indicator.disconnected {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.credentials-warning {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 15px;
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 6px;
  color: #856404;
}

.credentials-warning i {
  margin-top: 2px;
  color: #ffc107;
}

.help-text {
  font-size: 0.85rem;
  margin-top: 8px;
  line-height: 1.4;
}

.help-text code {
  background: #f8f9fa;
  padding: 2px 4px;
  border-radius: 3px;
  font-family: monospace;
}

.auth-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.auth-btn {
  padding: 10px 16px !important;
  border-radius: 6px !important;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #495057;
  font-size: 0.95rem;
}

.form-label i {
  color: #3498db;
}

.spreadsheet-selector {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dropdown-container {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.w-full {
  width: 100%;
}

.spreadsheet-dropdown {
  border-radius: 6px !important;
}

.spreadsheet-dropdown :deep(.p-dropdown) {
  width: 100%;
  border-radius: 6px !important;
}

.spreadsheet-dropdown :deep(.p-dropdown-label) {
  padding: 0.75rem !important;
}

.selected-spreadsheet {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selected-spreadsheet i {
  color: #27ae60;
}

.spreadsheet-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 4px;
}

.spreadsheet-option i {
  color: #27ae60;
  flex-shrink: 0;
}

.option-details {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.option-name {
  font-weight: 500;
  color: #2c3e50;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.option-id {
  font-size: 0.75rem;
  color: #6c757d;
  font-family: monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.helper-text {
  color: #6c757d;
  font-size: 0.8rem;
  line-height: 1.3;
}

.spreadsheet-actions {
  display: flex;
  gap: 8px;
  align-self: flex-start;
}

.refresh-btn,
.create-btn {
  padding: 8px 16px !important;
  border-radius: 6px !important;
  white-space: nowrap;
  min-width: 120px;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 10px;
  padding-top: 15px;
  border-top: 1px solid #e9ecef;
}

.save-btn,
.test-btn {
  padding: 10px 20px !important;
  border-radius: 6px !important;
  min-width: 160px;
}

.save-result {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-radius: 6px;
  font-weight: 500;
  margin-top: 10px;
}

.save-result.success {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.save-result.error {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.create-dialog {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.dialog-description {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
  border-left: 4px solid #3498db;
}

.dialog-description i {
  color: #3498db;
  margin-top: 2px;
}

.dialog-description p {
  margin: 0;
  color: #495057;
  font-size: 0.9rem;
}

/* Scrollbar Styling */
.google-sheets-settings::-webkit-scrollbar {
  width: 8px;
}

.google-sheets-settings::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.google-sheets-settings::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.google-sheets-settings::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* Hover effects */
.create-btn:hover,
.save-btn:hover,
.test-btn:hover,
.refresh-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  transition: all 0.2s ease;
}

/* Animation for refresh */
.refresh-btn .pi-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Responsive design */
@media (max-width: 768px) {
  .google-sheets-settings {
    padding: 15px;
  }

  .spreadsheet-actions {
    flex-direction: column;
    width: 100%;
  }

  .refresh-btn,
  .create-btn {
    width: 100%;
    justify-content: center;
  }

  .form-actions {
    flex-direction: column;
  }

  .save-btn,
  .test-btn {
    width: 100%;
    justify-content: center;
  }

  .auth-actions {
    flex-direction: column;
  }

  .auth-btn {
    width: 100%;
    justify-content: center;
  }
}

@media (min-width: 769px) {
  .spreadsheet-selector {
    flex-direction: row;
    align-items: flex-end;
    gap: 15px;
  }

  .dropdown-container {
    flex: 1;
  }

  .spreadsheet-actions {
    flex-shrink: 0;
  }
}


.optional-badge {
  background: #6c757d;
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.7rem;
  margin-left: 8px;
}

.same-as-wallet-badge {
  background: #e3f2fd;
  color: #1976d2;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.7rem;
  margin-left: 8px;
}

.clear-btn {
  color: #dc3545 !important;
  border-color: #dc3545 !important;
}

.clear-btn:hover {
  background: #dc3545 !important;
  color: white !important;
}
</style>
