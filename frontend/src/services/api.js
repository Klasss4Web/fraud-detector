import axios from "axios";

// const API_BASE_URL = "http://localhost:8000/api/v1"; Uncomment for local development
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Health check
export const checkHealth = async () => {
  const response = await api.get("/health");
  return response.data;
};

// Transaction analysis
export const analyzeTransaction = async (
  transactionData,
  autoInvestigate = true,
) => {
  const response = await api.post(
    `/analyze/transaction?auto_investigate=${autoInvestigate}`,
    transactionData,
  );
  return response.data;
};

// Insurance claim analysis
export const analyzeInsuranceClaim = async (
  claimData,
  autoInvestigate = true,
) => {
  const response = await api.post(
    `/analyze/insurance-claim?auto_investigate=${autoInvestigate}`,
    claimData,
  );
  return response.data;
};

// User profile analysis
export const analyzeUserProfile = async (
  profileData,
  autoInvestigate = true,
) => {
  const response = await api.post(
    `/analyze/user-profile?auto_investigate=${autoInvestigate}`,
    profileData,
  );
  return response.data;
};

// E-commerce order analysis
export const analyzeEcommerceOrder = async (
  orderData,
  autoInvestigate = true,
) => {
  const response = await api.post(
    `/analyze/ecommerce-order?auto_investigate=${autoInvestigate}`,
    orderData,
  );
  return response.data;
};

// Comprehensive analysis
export const analyzeComprehensive = async (data) => {
  const response = await api.post("/analyze/comprehensive", data);
  return response.data;
};

// Batch analysis
export const analyzeBatch = async (
  items,
  entityType,
  autoInvestigate = false,
) => {
  const response = await api.post("/analyze/batch", {
    items,
    entity_type: entityType,
    auto_investigate: autoInvestigate,
  });
  return response.data;
};

// Simulate fraud attack
export const simulateFraudAttack = async (attackType = null) => {
  const url = attackType
    ? `/simulate-attack?attack_type=${encodeURIComponent(attackType)}`
    : "/simulate-attack";
  const response = await api.get(url);
  return response.data;
};

// Detection score analysis
export const runDetectionScoreAnalysis = async (options = {}) => {
  const {
    attackTypes = null,
    simulationsPerType = 1,
    detectionThreshold = null,
  } = options;
  const response = await api.post("/detection-score", {
    attack_types: attackTypes,
    simulations_per_type: simulationsPerType,
    detection_threshold: detectionThreshold,
  });
  return response.data;
};

// Quick detection score analysis (GET)
export const getDetectionScoreAnalysis = async (
  simulationsPerType = 1,
  detectionThreshold = null,
) => {
  let url = `/detection-score?simulations_per_type=${simulationsPerType}`;
  if (detectionThreshold !== null) {
    url += `&detection_threshold=${detectionThreshold}`;
  }
  const response = await api.get(url);
  return response.data;
};

// ============== Observability API ==============

// Get all metrics
export const getMetrics = async () => {
  const response = await api.get("/observability/metrics");
  return response.data;
};

// Get fraud-specific metrics
export const getFraudMetrics = async () => {
  const response = await api.get("/observability/metrics/fraud");
  return response.data;
};

// Get evaluation summary
export const getEvaluationSummary = async () => {
  const response = await api.get("/observability/evaluation/summary");
  return response.data;
};

// Get confusion matrix
export const getConfusionMatrix = async (entityType = null) => {
  const url = entityType
    ? `/observability/evaluation/confusion-matrix?entity_type=${entityType}`
    : "/observability/evaluation/confusion-matrix";
  const response = await api.get(url);
  return response.data;
};

// Get agent performance
export const getAgentPerformance = async (agentName = null) => {
  const url = agentName
    ? `/observability/evaluation/agent-performance?agent_name=${agentName}`
    : "/observability/evaluation/agent-performance";
  const response = await api.get(url);
  return response.data;
};

// Record human override feedback
export const recordHumanOverride = async (data) => {
  const response = await api.post(
    "/observability/feedback/human-override",
    data,
  );
  return response.data;
};

// Record chargeback feedback
export const recordChargeback = async (data) => {
  const response = await api.post("/observability/feedback/chargeback", data);
  return response.data;
};

// Get improvement suggestions
export const getImprovementSuggestions = async () => {
  const response = await api.get(
    "/observability/feedback/improvement-suggestions",
  );
  return response.data;
};

// Get negative exemplars
export const getNegativeExemplars = async (limit = 100) => {
  const response = await api.get(
    `/observability/feedback/negative-exemplars?limit=${limit}`,
  );
  return response.data;
};

// ============== LLM Usage API ==============

// Get LLM usage summary
export const getLLMUsage = async (hours = 24) => {
  const response = await api.get(`/observability/llm/usage?hours=${hours}`);
  return response.data;
};

// Get LLM usage by operation (detailed breakdown)
export const getLLMUsageByOperation = async (hours = 24, operation = null) => {
  let url = `/observability/llm/usage/by-operation?hours=${hours}`;
  if (operation) {
    url += `&operation=${encodeURIComponent(operation)}`;
  }
  const response = await api.get(url);
  return response.data;
};

// Get recent LLM calls
export const getRecentLLMCalls = async (limit = 50, filters = {}) => {
  let url = `/observability/llm/usage/recent?limit=${limit}`;
  if (filters.operation)
    url += `&operation=${encodeURIComponent(filters.operation)}`;
  if (filters.agent) url += `&agent=${encodeURIComponent(filters.agent)}`;
  if (filters.model) url += `&model=${encodeURIComponent(filters.model)}`;
  if (filters.successOnly) url += `&success_only=true`;
  const response = await api.get(url);
  return response.data;
};

// Get hourly LLM stats
export const getLLMHourlyStats = async (hours = 24) => {
  const response = await api.get(
    `/observability/llm/usage/hourly?hours=${hours}`,
  );
  return response.data;
};

// Get LLM cost breakdown
export const getLLMCostBreakdown = async (hours = 24) => {
  const response = await api.get(
    `/observability/llm/usage/cost-breakdown?hours=${hours}`,
  );
  return response.data;
};

// Get list of LLM operations
export const getLLMOperations = async () => {
  const response = await api.get("/observability/llm/operations");
  return response.data;
};

// ============== Mixed Detection Analysis API ==============

// Run mixed detection analysis (legitimate + fraudulent transactions)
export const runMixedDetectionAnalysis = async (options = {}) => {
  const {
    numLegitimate = 10,
    numFraudulent = 10,
    detectionThreshold = null,
    useLlm = false,
  } = options;

  const response = await api.post("/detection-score-mixed", {
    num_legitimate: numLegitimate,
    num_fraudulent: numFraudulent,
    detection_threshold: detectionThreshold,
    use_llm: useLlm,
  });
  return response.data;
};

// Quick mixed detection analysis (GET)
export const getMixedDetectionAnalysis = async (
  numLegitimate = 10,
  numFraudulent = 10,
  detectionThreshold = null,
) => {
  let url = `/detection-score-mixed?num_legitimate=${numLegitimate}&num_fraudulent=${numFraudulent}`;
  if (detectionThreshold !== null) {
    url += `&detection_threshold=${detectionThreshold}`;
  }
  const response = await api.get(url);
  return response.data;
};

// ============== Authentication API ==============

// Store token in localStorage
const setAuthToken = (token) => {
  if (token) {
    localStorage.setItem("access_token", token);
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    localStorage.removeItem("access_token");
    delete api.defaults.headers.common["Authorization"];
  }
};

// Initialize auth header from localStorage on load
const storedToken = localStorage.getItem("access_token");
if (storedToken) {
  api.defaults.headers.common["Authorization"] = `Bearer ${storedToken}`;
}

// Login
export const login = async (email, password) => {
  const response = await api.post("/auth/login", { email, password });
  const { access_token, refresh_token } = response.data;
  setAuthToken(access_token);
  localStorage.setItem("refresh_token", refresh_token);
  return response.data;
};

// Register
export const register = async (email, password, fullName) => {
  const response = await api.post("/auth/register", {
    email,
    password,
    full_name: fullName,
  });
  return response.data;
};

// Logout
export const logout = () => {
  setAuthToken(null);
  localStorage.removeItem("refresh_token");
};

// Get current user
export const getCurrentUser = async () => {
  const response = await api.get("/auth/me");
  return response.data;
};

// Refresh token
export const refreshToken = async () => {
  const refresh = localStorage.getItem("refresh_token");
  if (!refresh) throw new Error("No refresh token");

  const response = await api.post("/auth/refresh", { refresh_token: refresh });
  const { access_token, refresh_token: newRefresh } = response.data;
  setAuthToken(access_token);
  localStorage.setItem("refresh_token", newRefresh);
  return response.data;
};

// Change password
export const changePassword = async (currentPassword, newPassword) => {
  const response = await api.post("/auth/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return response.data;
};

// API Keys
export const createApiKey = async (name, scopes = [], expiresInDays = null) => {
  const response = await api.post("/auth/api-keys", {
    name,
    scopes,
    expires_in_days: expiresInDays,
  });
  return response.data;
};

export const listApiKeys = async () => {
  const response = await api.get("/auth/api-keys");
  return response.data;
};

export const revokeApiKey = async (keyId) => {
  const response = await api.delete(`/auth/api-keys/${keyId}`);
  return response.data;
};

export const getAvailableScopes = async () => {
  const response = await api.get("/auth/scopes");
  return response.data;
};

// Check if user is authenticated
export const isAuthenticated = () => {
  return !!localStorage.getItem("access_token");
};

// ============== Webhooks Status ==============

export const getWebhookStatus = async () => {
  const response = await api.get("/webhooks/status");
  return response.data;
};

export default api;
