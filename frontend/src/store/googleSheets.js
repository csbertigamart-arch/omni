import { defineStore } from "pinia";
import { ref, computed } from "vue";
import apiService from "../services/api";

export const useGoogleSheetsStore = defineStore("googleSheets", () => {
  const authStatus = ref({
    authenticated: false,
    settings: {},
    hasCredentials: false
  });
  
  const spreadsheets = ref([]);
  const worksheets = ref([]);
  const loading = ref(false);
  const editMode = ref(false);
  const tempSettings = ref({});

  const isAuthenticated = computed(() => authStatus.value.authenticated);
  const currentSettings = computed(() => authStatus.value.settings);

  // In frontend/src/store/googleSheets.js
  async function loadAuthStatus() {
    try {
      loading.value = true;
      const response = await apiService.get("/google/auth/status");
      if (response.success) {
        authStatus.value = response.data;
        console.log("🔍 Auth status loaded:", response.data);
        
        // If we're authenticated, automatically load spreadsheets
        if (response.data.authenticated) {
          await loadSpreadsheets();
        }
        
        return response;
      }
      return response;
    } catch (error) {
      console.error("❌ Failed to load auth status:", error);
      throw error;
    } finally {
      loading.value = false;
    }
  }

  async function initiateAuth() {
    try {
      console.log("🔄 Initiating Google authentication...");
      const response = await apiService.get("/google/auth/initiate");
      if (response.success && response.auth_url) {
        console.log("✅ Auth URL received, opening popup...");
        
        const width = 600;
        const height = 700;
        const left = (window.screen.width - width) / 2;
        const top = (window.screen.height - height) / 2;
        
        const popup = window.open(
          response.auth_url,
          'google_auth',
          `width=${width},height=${height},left=${left},top=${top}`
        );
        
        if (!popup || popup.closed) {
          throw new Error('Popup blocked! Please allow popups for this site.');
        }
        
        // Listen for message from popup
        const messageHandler = (event) => {
          console.log("📨 Received message:", event.data);
          if (event.data && event.data.type === 'google_auth_success') {
            console.log("✅ Auth success message received");
            window.removeEventListener('message', messageHandler);
            if (popup && !popup.closed) popup.close();
            loadAuthStatus();
          }
        };
        
        window.addEventListener('message', messageHandler);
        
        // Fallback: check popup closure
        const popupCheck = setInterval(() => {
          if (popup.closed) {
            clearInterval(popupCheck);
            console.log("🔄 Popup closed, checking auth status...");
            setTimeout(() => loadAuthStatus(), 2000);
          }
        }, 1000);
        
        return true;
      } else {
        throw new Error(response.error || 'Failed to get auth URL');
      }
    } catch (error) {
      console.error("❌ Failed to initiate auth:", error);
      throw error;
    }
  }
  async function loadSpreadsheets() {
    try {
      loading.value = true;
      const response = await apiService.get("/google/sheets/list");
      if (response.success) {
        spreadsheets.value = response.data;
        console.log(`📊 Loaded ${response.data.length} spreadsheets`);
        return response;
      }
      return response;
    } catch (error) {
      console.error("❌ Failed to load spreadsheets:", error);
      throw error;
    } finally {
      loading.value = false;
    }
  }

  async function loadWorksheets(spreadsheetId) {
    try {
      loading.value = true;
      const response = await apiService.get(`/google/worksheets/${spreadsheetId}`);
      if (response.success) {
        worksheets.value = response.data;
        console.log(`📑 Loaded ${response.data.length} worksheets`);
        return response;
      }
      return response;
    } catch (error) {
      console.error("❌ Failed to load worksheets:", error);
      throw error;
    } finally {
      loading.value = false;
    }
  }

  async function updateSettings(settings) {
    try {
      loading.value = true;
      const response = await apiService.post("/google/settings/update", settings);
      if (response.success) {
        console.log("✅ Settings updated successfully");
        await loadAuthStatus(); // Reload status
        editMode.value = false;
        return response;
      }
      return response;
    } catch (error) {
      console.error("❌ Failed to update settings:", error);
      throw error;
    } finally {
      loading.value = false;
    }
  }

  async function testConnection() {
    try {
      const response = await apiService.get("/google/settings/test");
      console.log("🔌 Connection test result:", response);
      return response;
    } catch (error) {
      console.error("❌ Failed to test connection:", error);
      throw error;
    }
  }

  async function logout() {
    try {
      const response = await apiService.get("/google/auth/logout");
      if (response.success) {
        console.log("✅ Logged out successfully");
        await loadAuthStatus(); // Reload status
        return response;
      }
      return response;
    } catch (error) {
      console.error("❌ Failed to logout:", error);
      throw error;
    }
  }

  function startEdit() {
    editMode.value = true;
    tempSettings.value = { ...currentSettings.value };
    console.log("✏️ Entering edit mode");
  }

  function cancelEdit() {
    editMode.value = false;
    tempSettings.value = {};
    console.log("❌ Cancelled edit mode");
  }

  return {
    // State
    authStatus,
    spreadsheets,
    worksheets,
    loading,
    editMode,
    tempSettings,
    
    // Getters
    isAuthenticated,
    currentSettings,
    
    // Actions
    loadAuthStatus,
    initiateAuth,
    loadSpreadsheets,
    loadWorksheets,
    updateSettings,
    testConnection,
    logout,
    startEdit,
    cancelEdit
  };
});