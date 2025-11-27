import axios from "axios";

// Fungsi untuk mendapatkan URL backend otomatis
function getBackendUrl() {
  // Jika dalam development, gunakan host yang sama dengan frontend
  if (import.meta.env.DEV) {
    const currentUrl = window.location.origin;
    return `${currentUrl.replace(/:\d+$/, "")}:5000/api`;
  }

  // Untuk production, gunakan environment variable atau relative path
  return import.meta.env.VITE_API_URL || "/api";
}

const API_BASE_URL = getBackendUrl();

class ApiService {
  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 45000,
      headers: {
        "Content-Type": "application/json",
      },
    });

    console.log(`🌐 API Base URL: ${API_BASE_URL}`);

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        console.log(`🔄 Making API request to: ${config.url}`);
        return config;
      },
      (error) => {
        console.error("❌ API Request Error:", error);
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        console.log("✅ API Response:", response.status);
        return response;
      },
      (error) => {
        console.error(
          "❌ API Response Error:",
          error.response?.status,
          error.response?.data
        );

        if (error.code === "ECONNABORTED") {
          return Promise.reject(
            new Error("Request timeout - server is taking too long to respond")
          );
        }

        if (!error.response) {
          const currentUrl = window.location.origin;
          const backendUrl = currentUrl.replace(/:\d+$/, "") + ":5000";
          return Promise.reject(
            new Error(
              `Network error - cannot connect to server. Make sure backend is running on ${backendUrl}`
            )
          );
        }

        return Promise.reject(error);
      }
    );
  }

  async healthCheck() {
    try {
      const response = await this.client.get("/health", { timeout: 10000 });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }



  async getStatus() {
    try {
      const response = await this.client.get("/status", { timeout: 15000 });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async executeOperation(operation, params = {}) {
    try {
      const response = await this.client.post(
        "/execute",
        {
          operation,
          params,
        },
        { timeout: 60000 }
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }
  async executeSheetsOperation(operation, params = {}) {
    try {
      console.log(`🔄 [API] Executing sheets operation: ${operation}`, params);
      
      const response = await this.client.post(
        "/execute-sheets",
        {
          operation,
          params,
        },
        { timeout: 60000 }
      );
      
      console.log(`✅ [API] Sheets operation ${operation} response:`, response.data);
      return response.data;
    } catch (error) {
      console.error(`❌ [API] Sheets operation ${operation} failed:`, error);
      throw this.handleError(error);
    }
  }
  async getShippingFiles() {
    try {
      const response = await this.client.get("/shipping/files", {
        timeout: 15000,
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async processShippingFile(filename) {
    try {
      const response = await this.client.post(
        "/shipping/process-file",
        {
          filename,
        },
        { timeout: 30000 }
      );
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  async debugCheckFunctions() {
    try {
      const response = await this.client.get("/debug/check-functions", {
        timeout: 15000,
      });
      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  handleError(error) {
    if (error.response) {
      const message =
        error.response.data.error || `Server error: ${error.response.status}`;
      console.error("API Error Response:", error.response);
      return new Error(message);
    } else if (error.request) {
      console.error("API No Response:", error.request);
      const currentUrl = window.location.origin;
      const backendUrl = currentUrl.replace(/:\d+$/, "") + ":5000";
      return new Error(
        `Network error - cannot connect to server. Make sure backend is running on ${backendUrl}`
      );
    } else {
      console.error("API Error:", error.message);
      return new Error(error.message);
    }
  }
}

export default new ApiService();
