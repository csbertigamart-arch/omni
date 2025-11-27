import { defineStore } from "pinia";
import { ref, computed } from "vue";
import apiService from "../services/api";

export const useGoogleSheetsStore = defineStore("googleSheets", () => {
  const authStatus = ref({
    authenticated: false,
    settings: {},
    hasCredentials: false,
  });

  const spreadsheets = ref([]);
  const worksheets = ref([]);
  const loading = ref(false);
  const editMode = ref(false);
  const tempSettings = ref({});

  const isAuthenticated = computed(() => authStatus.value.authenticated);
  const currentSettings = computed(() => authStatus.value.settings);

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

  // PERBAIKAN: Tambahkan method refreshSpreadsheets
  async function refreshSpreadsheets() {
    try {
      loading.value = true;
      console.log("🔄 Refreshing spreadsheets...");

      // Panggil endpoint refresh yang sudah ada di backend
      const response = await apiService.get("/google/sheets/refresh");

      if (response.success) {
        spreadsheets.value = response.data;
        console.log(`✅ Refreshed ${response.data.length} spreadsheets`);
        return response;
      } else {
        throw new Error(response.error || "Failed to refresh spreadsheets");
      }
    } catch (error) {
      console.error("❌ Failed to refresh spreadsheets:", error);
      throw error;
    } finally {
      loading.value = false;
    }
  }

  async function loadWorksheets(spreadsheetId) {
    try {
      loading.value = true;
      const response = await apiService.get(
        `/google/worksheets/${spreadsheetId}`
      );
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
      const response = await apiService.post(
        "/google/settings/update",
        settings
      );
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
    loadSpreadsheets,
    refreshSpreadsheets, // EKSPOR METHOD INI
    loadWorksheets,
    updateSettings,
    testConnection,
    logout,
    startEdit,
    cancelEdit,
  };
});
