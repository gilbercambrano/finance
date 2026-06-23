const API = (() => {
  const base = "/api";

  async function request(path, options = {}) {
    const res = await fetch(base + path, {
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      ...options,
    });
    if (res.status === 401) {
      window.location.href = "/login";
      throw new Error("Sesión expirada");
    }
    if (!res.ok) {
      let detail = "Error desconocido";
      try { detail = (await res.json()).detail; } catch (e) {}
      throw new Error(detail || `Error ${res.status}`);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  const qs = (params = {}) => {
    const s = new URLSearchParams(Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null))).toString();
    return s ? `?${s}` : "";
  };

  return {
    // Auth
    me: () => request("/auth/me"),
    login: (data) => request("/auth/login", { method: "POST", body: JSON.stringify(data) }),
    register: (data) => request("/auth/register", { method: "POST", body: JSON.stringify(data) }),
    logout: () => request("/auth/logout", { method: "POST" }),

    // Accounts
    getAccounts: (includeInactive = false) => request(`/accounts${qs({ include_inactive: includeInactive || "" })}`),
    createAccount: (data) => request("/accounts", { method: "POST", body: JSON.stringify(data) }),
    updateAccount: (id, data) => request(`/accounts/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    deleteAccount: (id) => request(`/accounts/${id}`, { method: "DELETE" }),

    // Categories
    getCategories: (kind) => request(`/categories${qs({ kind })}`),
    createCategory: (data) => request("/categories", { method: "POST", body: JSON.stringify(data) }),
    deleteCategory: (id) => request(`/categories/${id}`, { method: "DELETE" }),

    // Transactions
    getTransactions: (params = {}) => request(`/transactions${qs(params)}`),
    createTransaction: (data) => request("/transactions", { method: "POST", body: JSON.stringify(data) }),
    updateTransaction: (id, data) => request(`/transactions/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    deleteTransaction: (id) => request(`/transactions/${id}`, { method: "DELETE" }),

    // Budgets
    getBudgets: () => request("/budgets"),
    createBudget: (data) => request("/budgets", { method: "POST", body: JSON.stringify(data) }),
    deleteBudget: (id) => request(`/budgets/${id}`, { method: "DELETE" }),
    getBudgetStatus: (id) => request(`/budgets/${id}/status`),

    // Fixed expenses
    getFixedExpenses: (includeInactive = false) => request(`/fixed-expenses${qs({ include_inactive: includeInactive || "" })}`),
    createFixedExpense: (data) => request("/fixed-expenses", { method: "POST", body: JSON.stringify(data) }),
    updateFixedExpense: (id, data) => request(`/fixed-expenses/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    deleteFixedExpense: (id) => request(`/fixed-expenses/${id}`, { method: "DELETE" }),
    getPendingOccurrences: () => request("/fixed-expenses/occurrences/pending"),
    confirmOccurrence: (id, data) => request(`/fixed-expenses/occurrences/${id}/confirm`, { method: "POST", body: JSON.stringify(data) }),
    skipOccurrence: (id) => request(`/fixed-expenses/occurrences/${id}/skip`, { method: "POST" }),

    // Dashboard
    getResumen: () => request("/dashboard/resumen"),
    getFlujo: (params = {}) => request(`/dashboard/flujo${qs(params)}`),
    getGastosPorCategoria: (params = {}) => request(`/dashboard/gastos-por-categoria${qs(params)}`),
    getTendencia: (meses = 6) => request(`/dashboard/tendencia?meses=${meses}`),
    getPresupuestosActivos: () => request("/dashboard/presupuestos-activos"),
    getDeudas: () => request("/dashboard/deudas"),
    getGastosFijos: () => request("/dashboard/gastos-fijos"),
  };
})();
