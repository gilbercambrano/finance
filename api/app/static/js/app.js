// ============================================================
// Estado global y utilidades
// ============================================================
const state = {
  accounts: [],
  categoriesIngreso: [],
  categoriasGasto: [],
  editingAccountId: null,
  editingFixedId: null,
  charts: {},
};

const fmtMoney = (n) => "$" + Number(n ?? 0).toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtDate = (d) => new Date(d + "T00:00:00").toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" });
const todayStr = () => new Date().toISOString().slice(0, 10);

const ACCOUNT_TYPE_LABEL = {
  debito: "Débito / Nómina", ahorro: "Ahorro", credito: "Tarjeta de crédito",
  inversion: "Inversión", efectivo: "Efectivo", prestamo: "Préstamo otorgado",
  prestamo_recibido: "Préstamo recibido",
};
const GROUP_LABEL = {
  fijo: "Fijo", variable: "Variable", ahorro_inversion: "Ahorro/Inversión",
  deuda: "Deuda", otros: "Otros",
};
const FREQ_LABEL = {
  semanal: "Semanal", quincenal: "Quincenal", mensual: "Mensual", bimestral: "Bimestral",
  trimestral: "Trimestral", semestral: "Semestral", anual: "Anual",
};
const WEEKDAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const DEBT_TYPES = new Set(["credito", "prestamo_recibido"]);

function toast(msg, isError = false) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.style.background = isError ? "#B3402A" : "#20281F";
  el.style.display = "block";
  clearTimeout(el._timer);
  el._timer = setTimeout(() => (el.style.display = "none"), 3200);
}

function openModal(id) { document.getElementById(id).classList.add("active"); }
function closeModal(id) { document.getElementById(id).classList.remove("active"); }
document.querySelectorAll("[data-close-modal]").forEach((btn) =>
  btn.addEventListener("click", () => btn.closest(".modal-overlay").classList.remove("active"))
);
document.querySelectorAll(".modal-overlay").forEach((ov) =>
  ov.addEventListener("click", (e) => { if (e.target === ov) ov.classList.remove("active"); })
);

// ============================================================
// Sesión
// ============================================================
async function initSession() {
  try {
    const user = await API.me();
    document.getElementById("sidebar-user").textContent = user.full_name || user.email;
  } catch (e) {
    return; // API.me ya redirige a /login si la sesión no es válida
  }
  loadDashboard();
}

document.getElementById("btn-logout").addEventListener("click", async (e) => {
  e.preventDefault();
  await API.logout();
  window.location.href = "/login";
});

// ============================================================
// Navegación
// ============================================================
document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => switchView(item.dataset.view));
});

function switchView(view) {
  document.querySelectorAll(".nav-item").forEach((n) => n.classList.toggle("active", n.dataset.view === view));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + view));
  if (view === "dashboard") loadDashboard();
  if (view === "cuentas") loadAccountsView();
  if (view === "deudas") loadDebtsView();
  if (view === "movimientos") loadTransactionsView();
  if (view === "fijos") loadFixedView();
  if (view === "presupuestos") loadBudgetsView();
  if (view === "categorias") loadCategoriesView();
}

// ============================================================
// Carga base
// ============================================================
async function refreshCache() {
  state.accounts = await API.getAccounts();
  state.categoriesIngreso = await API.getCategories("ingreso");
  state.categoriasGasto = await API.getCategories("gasto");
}

// ============================================================
// DASHBOARD
// ============================================================
async function loadDashboard() {
  await refreshCache();
  const [resumen, flujo, gastosCat, tendencia, presupuestos, deudas, gastosFijos] = await Promise.all([
    API.getResumen(), API.getFlujo(), API.getGastosPorCategoria(), API.getTendencia(6),
    API.getPresupuestosActivos(), API.getDeudas(), API.getGastosFijos(),
  ]);

  const kpiRow = document.getElementById("kpi-row");
  const pn = resumen.patrimonio.patrimonio_neto;
  kpiRow.innerHTML = `
    <div class="card kpi-hero">
      <h3>Patrimonio neto</h3>
      <div class="kpi-value">${fmtMoney(pn)}</div>
      <div class="kpi-label">Activos ${fmtMoney(resumen.patrimonio.activos)} · Pasivos ${fmtMoney(resumen.patrimonio.pasivos)}</div>
    </div>
    <div class="card">
      <h3>Ingresos del mes</h3>
      <div class="kpi-value" style="color:var(--primary-dark)">${fmtMoney(flujo.total_ingresos)}</div>
      <div class="kpi-label">Del ${fmtDate(flujo.periodo.desde)} al ${fmtDate(flujo.periodo.hasta)}</div>
    </div>
    <div class="card">
      <h3>Gastos del mes</h3>
      <div class="kpi-value" style="color:var(--terracotta)">${fmtMoney(flujo.total_gastos)}</div>
      <div class="kpi-label ${flujo.ahorro_neto >= 0 ? "kpi-delta-pos" : "kpi-delta-neg"}">
        Ahorro neto: ${fmtMoney(flujo.ahorro_neto)} (${flujo.tasa_ahorro_pct}%)
      </div>
    </div>
  `;

  const kpiRow2 = document.getElementById("kpi-row-2");
  kpiRow2.innerHTML = `
    <div class="card">
      <h3>Gasto fijo mensual (estimado)</h3>
      <div class="kpi-value" style="color:var(--gold)">${fmtMoney(gastosFijos.total_mensualizado_estimado)}</div>
      <div class="kpi-label">${gastosFijos.cantidad_gastos_fijos_activos} gastos fijos activos</div>
    </div>
    <div class="card">
      <h3>Pagado este mes (fijos)</h3>
      <div class="kpi-value" style="color:var(--primary-dark)">${fmtMoney(gastosFijos.mes_actual.pagado)}</div>
      <div class="kpi-label">Pendiente: ${fmtMoney(gastosFijos.mes_actual.pendiente)}</div>
    </div>
    <div class="card">
      <h3>Deuda total (tarjetas y préstamos)</h3>
      <div class="kpi-value" style="color:var(--terracotta)">${fmtMoney(deudas.total_deuda)}</div>
      <div class="kpi-label">${deudas.cuentas.length} cuenta(s) de deuda</div>
    </div>
  `;

  const ledger = document.getElementById("ledger-accounts");
  ledger.innerHTML = resumen.cuentas.map((a) => `
    <div class="ledger-row">
      <div>
        <div class="ledger-name">${a.is_cash ? "💵 " : ""}${a.name}</div>
        <div class="ledger-type">${ACCOUNT_TYPE_LABEL[a.account_type] || a.account_type}</div>
      </div>
      <div class="ledger-amount ${a.nature === "pasivo" ? "liability" : "asset"} mono">
        ${a.nature === "pasivo" ? "-" : ""}${fmtMoney(Math.abs(a.balance))}
      </div>
    </div>
  `).join("") || `<div class="empty-state">Aún no hay cuentas registradas.</div>`;

  renderLineChart("chart-tendencia", tendencia.map((t) => t.mes), [
    { label: "Ingresos", data: tendencia.map((t) => t.ingresos), color: "#2F6F5E" },
    { label: "Gastos", data: tendencia.map((t) => t.gastos), color: "#C4622D" },
  ]);
  renderDoughnutChart("chart-categorias", gastosCat.slice(0, 8).map((g) => g.categoria), gastosCat.slice(0, 8).map((g) => g.total));

  const budgetSummary = document.getElementById("budget-summary");
  if (!presupuestos.length) {
    budgetSummary.innerHTML = `<div class="empty-state">No tienes presupuestos activos.</div>`;
  } else {
    budgetSummary.innerHTML = presupuestos.map((p) => {
      const pct = p.total_planned ? Math.min(100, Math.round((p.total_actual / p.total_planned) * 100)) : 0;
      const over = p.total_actual > p.total_planned;
      const alertItems = p.items.filter((i) => i.status === "alerta");
      return `
        <div style="margin-bottom:16px;">
          <div style="display:flex;justify-content:space-between;font-size:13px;">
            <strong>${p.budget_name}</strong>
            <span class="mono ${over ? "kpi-delta-neg" : ""}">${fmtMoney(p.total_actual)} / ${fmtMoney(p.total_planned)}</span>
          </div>
          <div class="progress-bar"><div class="progress-fill ${over ? "over" : ""}" style="width:${pct}%"></div></div>
          ${alertItems.length ? `<div class="text-sm" style="margin-top:6px;color:var(--danger);">⚠ Desviación en: ${alertItems.map((i) => i.category_name).join(", ")}</div>` : ""}
        </div>
      `;
    }).join("");
  }

  const pendingBox = document.getElementById("dash-fixed-pending");
  const pendientes = gastosFijos.mes_actual.pendientes;
  pendingBox.innerHTML = pendientes.length ? pendientes.map((p) => `
    <div class="ledger-row">
      <div><div class="ledger-name">${p.nombre}</div><div class="ledger-type">Vence ${fmtDate(p.fecha_limite)}</div></div>
      <div class="ledger-amount mono">${fmtMoney(p.monto_estimado)}</div>
    </div>
  `).join("") : `<div class="empty-state">No hay pagos fijos pendientes este mes 🎉</div>`;

  const debtsBox = document.getElementById("dash-debts");
  debtsBox.innerHTML = deudas.cuentas.length ? deudas.cuentas.map((d) => `
    <div style="margin-bottom:14px;">
      <div style="display:flex;justify-content:space-between;font-size:13px;">
        <strong>${d.name}</strong>
        <span class="mono kpi-delta-neg">${fmtMoney(d.balance)}</span>
      </div>
      ${d.credit_limit ? `
        <div class="progress-bar"><div class="progress-fill ${d.utilization_pct > 80 ? "over" : ""}" style="width:${Math.min(100, d.utilization_pct)}%"></div></div>
        <div class="text-sm muted">${d.utilization_pct}% del límite (${fmtMoney(d.credit_limit)})</div>
      ` : ""}
      <div class="text-sm muted">
        ${d.next_payment_due_date ? `Próximo pago: ${fmtDate(d.next_payment_due_date)}` : ""}
        ${d.minimum_payment ? ` · Mínimo: ${fmtMoney(d.minimum_payment)}` : ""}
      </div>
    </div>
  `).join("") : `<div class="empty-state">No tienes tarjetas o préstamos registrados.</div>`;
}

function renderLineChart(canvasId, labels, series) {
  const ctx = document.getElementById(canvasId);
  if (state.charts[canvasId]) state.charts[canvasId].destroy();
  state.charts[canvasId] = new Chart(ctx, {
    type: "line",
    data: { labels, datasets: series.map((s) => ({
      label: s.label, data: s.data, borderColor: s.color, backgroundColor: s.color + "22",
      tension: 0.35, fill: true, pointRadius: 3,
    })) },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 11 } } } },
      scales: { y: { ticks: { callback: (v) => "$" + v.toLocaleString("es-MX") } } },
    },
  });
}

function renderDoughnutChart(canvasId, labels, data) {
  const ctx = document.getElementById(canvasId);
  if (state.charts[canvasId]) state.charts[canvasId].destroy();
  const palette = ["#2F6F5E", "#C4622D", "#AD841A", "#3B4F8C", "#5B6358", "#8B9285", "#B3402A", "#7FA391"];
  if (!labels.length) { state.charts[canvasId] = null; return; }
  state.charts[canvasId] = new Chart(ctx, {
    type: "doughnut",
    data: { labels, datasets: [{ data, backgroundColor: palette }] },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: "60%",
      plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 10.5 } } } },
    },
  });
}

document.getElementById("btn-refresh-dashboard").addEventListener("click", loadDashboard);

// ============================================================
// CUENTAS (incluye detalle de deuda)
// ============================================================
function toggleCreditFields() {
  const type = document.getElementById("acc-type").value;
  const isDebt = DEBT_TYPES.has(type);
  document.getElementById("acc-credit-fields").style.display = isDebt ? "block" : "none";
  document.getElementById("acc-limit-field").style.display = type === "credito" ? "block" : "none";
  document.getElementById("acc-original-field").style.display = type === "prestamo_recibido" ? "block" : "none";
  document.getElementById("acc-cutoff-field").style.display = type === "credito" ? "block" : "none";
  document.getElementById("acc-balance-label").textContent = isDebt ? "Saldo actual de la deuda (MXN)" : "Saldo inicial (MXN)";
}
document.getElementById("acc-type").addEventListener("change", toggleCreditFields);

async function loadAccountsView() {
  await refreshCache();
  const tbody = document.querySelector("#table-accounts tbody");
  const nonDebt = state.accounts.filter((a) => !DEBT_TYPES.has(a.account_type));
  tbody.innerHTML = nonDebt.map((a) => `
    <tr>
      <td>${a.is_cash ? "💵 " : ""}<strong>${a.name}</strong>${a.notes ? `<div class="text-sm muted">${a.notes}</div>` : ""}</td>
      <td>${ACCOUNT_TYPE_LABEL[a.account_type] || a.account_type}</td>
      <td>${a.bank_name || "—"}</td>
      <td class="num amount mono" style="color:var(--primary-dark)">${fmtMoney(a.current_balance)}</td>
      <td>
        <div class="row-actions">
          <button class="btn btn-sm" data-edit-account="${a.id}">Editar</button>
          ${a.is_cash ? "" : `<button class="btn btn-sm btn-danger" data-delete-account="${a.id}">Eliminar</button>`}
        </div>
      </td>
    </tr>
  `).join("") || `<tr><td colspan="5" class="empty-state">No hay cuentas registradas.</td></tr>`;

  tbody.querySelectorAll("[data-edit-account]").forEach((btn) => btn.addEventListener("click", () => openAccountModal(Number(btn.dataset.editAccount))));
  tbody.querySelectorAll("[data-delete-account]").forEach((btn) => btn.addEventListener("click", () => deleteAccount(Number(btn.dataset.deleteAccount))));
}

function openAccountModal(id = null, presetType = null) {
  state.editingAccountId = id;
  const form = document.getElementById("form-account");
  form.reset();
  document.getElementById("acc-type").disabled = false;
  document.getElementById("acc-balance").disabled = false;

  if (id) {
    const a = state.accounts.find((x) => x.id === id);
    document.getElementById("modal-account-title").textContent = "Editar cuenta";
    document.getElementById("acc-name").value = a.name;
    document.getElementById("acc-type").value = a.account_type;
    document.getElementById("acc-type").disabled = true;
    document.getElementById("acc-bank").value = a.bank_name || "";
    document.getElementById("acc-balance").value = a.current_balance;
    document.getElementById("acc-balance").disabled = true;
    document.getElementById("acc-notes").value = a.notes || "";
    if (a.credit_detail) {
      const cd = a.credit_detail;
      document.getElementById("acc-credit-limit").value = cd.credit_limit ?? "";
      document.getElementById("acc-original-amount").value = cd.original_amount ?? "";
      document.getElementById("acc-cutoff-day").value = cd.cutoff_day ?? "";
      document.getElementById("acc-due-day").value = cd.payment_due_day ?? "";
      document.getElementById("acc-min-payment").value = cd.minimum_payment ?? "";
      document.getElementById("acc-interest-rate").value = cd.interest_rate_annual ?? "";
    }
  } else {
    document.getElementById("modal-account-title").textContent = "Nueva cuenta";
    if (presetType) document.getElementById("acc-type").value = presetType;
  }
  toggleCreditFields();
  openModal("modal-account");
}

document.getElementById("btn-new-account").addEventListener("click", () => openAccountModal(null));
document.getElementById("btn-new-debt").addEventListener("click", () => openAccountModal(null, "credito"));

document.getElementById("form-account").addEventListener("submit", async (e) => {
  e.preventDefault();
  const type = document.getElementById("acc-type").value;
  const nature = DEBT_TYPES.has(type) ? "pasivo" : "activo";
  const isDebt = DEBT_TYPES.has(type);

  const creditDetail = isDebt ? {
    credit_limit: parseFloat(document.getElementById("acc-credit-limit").value) || null,
    original_amount: parseFloat(document.getElementById("acc-original-amount").value) || null,
    cutoff_day: parseInt(document.getElementById("acc-cutoff-day").value) || null,
    payment_due_day: parseInt(document.getElementById("acc-due-day").value) || null,
    minimum_payment: parseFloat(document.getElementById("acc-min-payment").value) || null,
    interest_rate_annual: parseFloat(document.getElementById("acc-interest-rate").value) || null,
  } : null;

  try {
    if (state.editingAccountId) {
      await API.updateAccount(state.editingAccountId, {
        name: document.getElementById("acc-name").value,
        bank_name: document.getElementById("acc-bank").value || null,
        notes: document.getElementById("acc-notes").value || null,
        credit_detail: creditDetail,
      });
      toast("Cuenta actualizada");
    } else {
      await API.createAccount({
        name: document.getElementById("acc-name").value, account_type: type, nature,
        bank_name: document.getElementById("acc-bank").value || null,
        initial_balance: parseFloat(document.getElementById("acc-balance").value),
        notes: document.getElementById("acc-notes").value || null,
        credit_detail: creditDetail,
      });
      toast("Cuenta creada");
    }
    closeModal("modal-account");
    loadAccountsView();
    loadDebtsView();
  } catch (err) { toast(err.message, true); }
});

async function deleteAccount(id) {
  if (!confirm("¿Eliminar o desactivar esta cuenta?")) return;
  try {
    const res = await API.deleteAccount(id);
    toast(res.detail);
    loadAccountsView();
  } catch (err) { toast(err.message, true); }
}

// ============================================================
// TARJETAS Y DEUDAS
// ============================================================
async function loadDebtsView() {
  await refreshCache();
  const deudas = await API.getDeudas();
  const container = document.getElementById("debts-container");
  if (!deudas.cuentas.length) {
    container.innerHTML = `<div class="card"><div class="empty-state">No tienes tarjetas de crédito ni préstamos registrados. Usa "+ Nueva tarjeta / deuda".</div></div>`;
    return;
  }
  container.innerHTML = `
    <div class="card" style="margin-bottom:16px;">
      <h3>Deuda total</h3>
      <div class="kpi-value" style="color:var(--terracotta)">${fmtMoney(deudas.total_deuda)}</div>
    </div>
    <div class="grid grid-2">
    ${deudas.cuentas.map((d) => `
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:baseline;">
          <h2 style="font-size:17px;">${d.name}</h2>
          <button class="btn btn-sm" data-edit-account="${d.account_id}">Editar</button>
        </div>
        <div class="ledger-type" style="margin-bottom:10px;">${ACCOUNT_TYPE_LABEL[d.account_type]}</div>
        <div class="kpi-value" style="color:var(--terracotta);font-size:26px;">${fmtMoney(d.balance)}</div>
        ${d.credit_limit ? `
          <div class="progress-bar"><div class="progress-fill ${d.utilization_pct > 80 ? "over" : ""}" style="width:${Math.min(100, d.utilization_pct)}%"></div></div>
          <div class="text-sm muted" style="margin-top:4px;">${d.utilization_pct}% usado de ${fmtMoney(d.credit_limit)}</div>
        ` : ""}
        <table style="margin-top:14px;">
          <tbody>
            ${d.next_cutoff_date ? `<tr><td>Próximo corte</td><td class="num mono">${fmtDate(d.next_cutoff_date)}</td></tr>` : ""}
            ${d.next_payment_due_date ? `<tr><td>Fecha límite de pago</td><td class="num mono">${fmtDate(d.next_payment_due_date)}</td></tr>` : ""}
            ${d.minimum_payment ? `<tr><td>Pago mínimo</td><td class="num mono">${fmtMoney(d.minimum_payment)}</td></tr>` : ""}
            ${d.interest_rate_annual ? `<tr><td>Tasa de interés anual</td><td class="num mono">${d.interest_rate_annual}%</td></tr>` : ""}
          </tbody>
        </table>
      </div>
    `).join("")}
    </div>
  `;
  container.querySelectorAll("[data-edit-account]").forEach((btn) =>
    btn.addEventListener("click", () => openAccountModal(Number(btn.dataset.editAccount)))
  );
}

// ============================================================
// MOVIMIENTOS
// ============================================================
function populateAccountSelect(select, { excludeId = null, placeholder = null } = {}) {
  select.innerHTML = (placeholder ? `<option value="">${placeholder}</option>` : "") +
    state.accounts.filter((a) => a.id !== excludeId).map((a) =>
      `<option value="${a.id}">${a.is_cash ? "💵 " : ""}${a.name}${DEBT_TYPES.has(a.account_type) ? " 💳" : ""}</option>`
    ).join("");
}

function populateCategorySelect(select, kind) {
  const cats = kind === "ingreso" ? state.categoriesIngreso : state.categoriasGasto;
  select.innerHTML = cats.map((c) => `<option value="${c.id}">${c.icon || ""} ${c.name}</option>`).join("");
}

function updateTransactionFormFields() {
  const kind = document.getElementById("txn-kind").value;
  const toField = document.getElementById("txn-to-account-field");
  const catField = document.getElementById("txn-category-field");
  const accountLabel = document.getElementById("txn-account-label");
  if (kind === "transferencia") {
    toField.style.display = "block";
    catField.style.display = "none";
    accountLabel.textContent = "Cuenta / Efectivo origen";
    populateAccountSelect(document.getElementById("txn-to-account"), { placeholder: "Selecciona destino" });
  } else {
    toField.style.display = "none";
    catField.style.display = "block";
    accountLabel.textContent = "Cuenta / Efectivo / Tarjeta";
    populateCategorySelect(document.getElementById("txn-category"), kind);
  }
}
document.getElementById("txn-kind").addEventListener("change", updateTransactionFormFields);

function openTransactionModal() {
  const form = document.getElementById("form-transaction");
  form.reset();
  populateAccountSelect(document.getElementById("txn-account"));
  document.getElementById("txn-date").value = todayStr();
  document.getElementById("txn-kind").value = "gasto";
  updateTransactionFormFields();
  document.getElementById("modal-transaction-title").textContent = "Nuevo movimiento";
  openModal("modal-transaction");
}
document.getElementById("btn-new-transaction").addEventListener("click", openTransactionModal);

document.getElementById("form-transaction").addEventListener("submit", async (e) => {
  e.preventDefault();
  const kind = document.getElementById("txn-kind").value;
  const payload = {
    date: document.getElementById("txn-date").value, kind,
    amount: parseFloat(document.getElementById("txn-amount").value),
    description: document.getElementById("txn-description").value || null,
    account_id: Number(document.getElementById("txn-account").value),
    to_account_id: kind === "transferencia" ? Number(document.getElementById("txn-to-account").value) : null,
    category_id: kind !== "transferencia" ? Number(document.getElementById("txn-category").value) : null,
  };
  try {
    await API.createTransaction(payload);
    toast("Movimiento registrado");
    closeModal("modal-transaction");
    loadTransactionsView();
  } catch (err) { toast(err.message, true); }
});

async function loadTransactionsView() {
  await refreshCache();
  const accSelect = document.getElementById("filter-account");
  accSelect.innerHTML = `<option value="">Todas las cuentas</option>` + state.accounts.map((a) => `<option value="${a.id}">${a.name}</option>`).join("");

  const params = {
    kind: document.getElementById("filter-kind").value,
    account_id: document.getElementById("filter-account").value,
    date_from: document.getElementById("filter-from").value,
    date_to: document.getElementById("filter-to").value,
  };
  const txns = await API.getTransactions(params);
  const tbody = document.querySelector("#table-transactions tbody");
  tbody.innerHTML = txns.map((t) => `
    <tr class="${t.kind === "ingreso" ? "income" : t.kind === "gasto" ? "expense" : "transfer"}">
      <td>${fmtDate(t.date)}</td>
      <td><span class="badge badge-${t.kind === "ingreso" ? "ok" : t.kind === "gasto" ? "alerta" : "otros"}">${t.kind}</span></td>
      <td>${t.account_name}${t.to_account_name ? ` → ${t.to_account_name}` : ""}</td>
      <td>${t.category_name || "—"}</td>
      <td>${t.description || "—"}</td>
      <td class="num amount mono">${t.kind === "gasto" ? "-" : t.kind === "ingreso" ? "+" : ""}${fmtMoney(t.amount)}</td>
      <td><div class="row-actions"><button class="btn btn-sm btn-danger" data-delete-txn="${t.id}">Eliminar</button></div></td>
    </tr>
  `).join("") || `<tr><td colspan="7" class="empty-state">No hay movimientos con estos filtros.</td></tr>`;

  tbody.querySelectorAll("[data-delete-txn]").forEach((btn) => btn.addEventListener("click", () => deleteTransaction(Number(btn.dataset.deleteTxn))));
}

async function deleteTransaction(id) {
  if (!confirm("¿Eliminar este movimiento? Se ajustarán los saldos correspondientes.")) return;
  try {
    await API.deleteTransaction(id);
    toast("Movimiento eliminado");
    loadTransactionsView();
  } catch (err) { toast(err.message, true); }
}

["filter-kind", "filter-account", "filter-from", "filter-to"].forEach((id) =>
  document.getElementById(id).addEventListener("change", loadTransactionsView)
);
document.getElementById("btn-filter-clear").addEventListener("click", () => {
  ["filter-kind", "filter-account", "filter-from", "filter-to"].forEach((id) => (document.getElementById(id).value = ""));
  loadTransactionsView();
});

// ============================================================
// GASTOS FIJOS
// ============================================================
function toggleFixedDueDayField() {
  const freq = document.getElementById("fix-frequency").value;
  const label = document.getElementById("fix-dueday-label");
  const input = document.getElementById("fix-dueday");
  if (freq === "semanal") {
    label.textContent = "Día de la semana";
    input.setAttribute("max", "6");
    input.setAttribute("min", "0");
    input.placeholder = "0=Lunes ... 6=Domingo";
  } else if (freq === "quincenal") {
    label.textContent = "Quincenal (vence días 1 y 16, no requiere día)";
    input.value = 1;
  } else {
    label.textContent = "Día del mes de vencimiento";
    input.setAttribute("max", "31");
    input.setAttribute("min", "1");
    input.placeholder = "1-31";
  }
}
document.getElementById("fix-frequency").addEventListener("change", toggleFixedDueDayField);
document.getElementById("fix-variable").addEventListener("change", (e) => {
  document.getElementById("fix-autopost-field").style.display = e.target.checked ? "none" : "block";
  if (e.target.checked) document.getElementById("fix-autopost").checked = false;
});

function openFixedModal(id = null) {
  state.editingFixedId = id;
  populateCategorySelect(document.getElementById("fix-category"), "gasto");
  populateAccountSelect(document.getElementById("fix-account"));
  document.getElementById("form-fixed").reset();
  document.getElementById("fix-startdate").value = todayStr();
  document.getElementById("fix-startdate-field").style.display = id ? "none" : "block";
  document.getElementById("fix-frequency").disabled = !!id;
  document.getElementById("fix-dueday").disabled = !!id;
  document.getElementById("modal-fixed-title").textContent = id ? "Editar gasto fijo" : "Nuevo gasto fijo";

  if (id) {
    // (edición simplificada: usamos los datos ya cargados en la tabla)
    const fe = state._fixedCache.find((f) => f.id === id);
    document.getElementById("fix-name").value = fe.name;
    document.getElementById("fix-category").value = fe.category_id;
    document.getElementById("fix-account").value = fe.account_id;
    document.getElementById("fix-amount").value = fe.estimated_amount;
    document.getElementById("fix-frequency").value = fe.frequency;
    document.getElementById("fix-dueday").value = fe.due_day;
    document.getElementById("fix-variable").checked = fe.is_variable_amount;
    document.getElementById("fix-autopost").checked = fe.auto_post;
    document.getElementById("fix-autopost-field").style.display = fe.is_variable_amount ? "none" : "block";
    document.getElementById("fix-notes").value = fe.notes || "";
  }
  toggleFixedDueDayField();
  openModal("modal-fixed");
}
document.getElementById("btn-new-fixed").addEventListener("click", () => openFixedModal(null));

document.getElementById("form-fixed").addEventListener("submit", async (e) => {
  e.preventDefault();
  const isVariable = document.getElementById("fix-variable").checked;
  try {
    if (state.editingFixedId) {
      await API.updateFixedExpense(state.editingFixedId, {
        name: document.getElementById("fix-name").value,
        category_id: Number(document.getElementById("fix-category").value),
        account_id: Number(document.getElementById("fix-account").value),
        estimated_amount: parseFloat(document.getElementById("fix-amount").value),
        is_variable_amount: isVariable,
        auto_post: isVariable ? false : document.getElementById("fix-autopost").checked,
        notes: document.getElementById("fix-notes").value || null,
      });
      toast("Gasto fijo actualizado");
    } else {
      await API.createFixedExpense({
        name: document.getElementById("fix-name").value,
        category_id: Number(document.getElementById("fix-category").value),
        account_id: Number(document.getElementById("fix-account").value),
        estimated_amount: parseFloat(document.getElementById("fix-amount").value),
        is_variable_amount: isVariable,
        frequency: document.getElementById("fix-frequency").value,
        due_day: parseInt(document.getElementById("fix-dueday").value),
        auto_post: isVariable ? false : document.getElementById("fix-autopost").checked,
        notes: document.getElementById("fix-notes").value || null,
        start_date: document.getElementById("fix-startdate").value || null,
      });
      toast("Gasto fijo creado");
    }
    closeModal("modal-fixed");
    loadFixedView();
  } catch (err) { toast(err.message, true); }
});

function openConfirmOccModal(occ) {
  document.getElementById("occ-id").value = occ.id;
  document.getElementById("occ-name-label").textContent = `${occ.fixed_expense_name} — vence ${fmtDate(occ.due_date)}`;
  document.getElementById("occ-amount").value = occ.expected_amount;
  populateAccountSelect(document.getElementById("occ-account"));
  document.getElementById("occ-date").value = todayStr();
  openModal("modal-confirm-occ");
}

document.getElementById("form-confirm-occ").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = Number(document.getElementById("occ-id").value);
  try {
    await API.confirmOccurrence(id, {
      amount: parseFloat(document.getElementById("occ-amount").value),
      account_id: Number(document.getElementById("occ-account").value),
      date: document.getElementById("occ-date").value,
    });
    toast("Pago confirmado");
    closeModal("modal-confirm-occ");
    loadFixedView();
    if (document.getElementById("view-dashboard").classList.contains("active")) loadDashboard();
  } catch (err) { toast(err.message, true); }
});

async function loadFixedView() {
  await refreshCache();
  const [fixedList, pending] = await Promise.all([API.getFixedExpenses(), API.getPendingOccurrences()]);
  state._fixedCache = fixedList;

  const pendingBox = document.getElementById("fixed-pending-list");
  pendingBox.innerHTML = pending.length ? pending.map((o) => `
    <div class="ledger-row">
      <div>
        <div class="ledger-name">${o.fixed_expense_name}</div>
        <div class="ledger-type">${o.category_name} · vence ${fmtDate(o.due_date)}</div>
      </div>
      <div style="display:flex;align-items:center;gap:10px;">
        <span class="mono">${fmtMoney(o.expected_amount)}</span>
        <button class="btn btn-sm btn-primary" data-confirm-occ='${JSON.stringify(o).replace(/'/g, "&apos;")}'>Confirmar pago</button>
        <button class="btn btn-sm" data-skip-occ="${o.id}">Omitir</button>
      </div>
    </div>
  `).join("") : `<div class="empty-state">No hay pagos fijos pendientes por confirmar 🎉</div>`;

  pendingBox.querySelectorAll("[data-confirm-occ]").forEach((btn) =>
    btn.addEventListener("click", () => openConfirmOccModal(JSON.parse(btn.dataset.confirmOcc.replace(/&apos;/g, "'"))))
  );
  pendingBox.querySelectorAll("[data-skip-occ]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      if (!confirm("¿Omitir este pago fijo de este periodo?")) return;
      await API.skipOccurrence(Number(btn.dataset.skipOcc));
      toast("Ocurrencia omitida");
      loadFixedView();
    })
  );

  const tbody = document.querySelector("#table-fixed tbody");
  tbody.innerHTML = fixedList.map((fe) => `
    <tr>
      <td><strong>${fe.name}</strong>${fe.is_variable_amount ? ' <span class="badge badge-variable">monto variable</span>' : ""}</td>
      <td>${fe.category_name}</td>
      <td>${fe.account_name}</td>
      <td>${FREQ_LABEL[fe.frequency] || fe.frequency}</td>
      <td class="num mono">${fmtMoney(fe.estimated_amount)}</td>
      <td>${fmtDate(fe.next_due_date)}</td>
      <td>${fe.auto_post ? '<span class="badge badge-ok">Automático</span>' : '<span class="badge badge-otros">Manual</span>'}</td>
      <td>
        <div class="row-actions">
          <button class="btn btn-sm" data-edit-fixed="${fe.id}">Editar</button>
          <button class="btn btn-sm btn-danger" data-delete-fixed="${fe.id}">Desactivar</button>
        </div>
      </td>
    </tr>
  `).join("") || `<tr><td colspan="8" class="empty-state">No tienes gastos fijos registrados.</td></tr>`;

  tbody.querySelectorAll("[data-edit-fixed]").forEach((btn) => btn.addEventListener("click", () => openFixedModal(Number(btn.dataset.editFixed))));
  tbody.querySelectorAll("[data-delete-fixed]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      if (!confirm("¿Desactivar este gasto fijo? Ya no generará nuevos pagos.")) return;
      await API.deleteFixedExpense(Number(btn.dataset.deleteFixed));
      toast("Gasto fijo desactivado");
      loadFixedView();
    })
  );
}

// ============================================================
// PRESUPUESTOS
// ============================================================
function addBudgetItemRow(categoryId = "", amount = "") {
  const container = document.getElementById("bud-items");
  const row = document.createElement("div");
  row.className = "field-row bud-item-row";
  row.style.alignItems = "flex-end";
  row.innerHTML = `
    <div class="field">
      <label>Categoría</label>
      <select class="bud-item-category">
        ${state.categoriasGasto.map((c) => `<option value="${c.id}" ${c.id == categoryId ? "selected" : ""}>${c.icon || ""} ${c.name}</option>`).join("")}
      </select>
    </div>
    <div class="field" style="max-width:140px;"><label>Monto planeado</label><input type="number" class="bud-item-amount" step="0.01" min="0.01" value="${amount}" required></div>
    <button type="button" class="btn btn-sm btn-danger" style="margin-bottom:14px;" data-remove-row>✕</button>
  `;
  row.querySelector("[data-remove-row]").addEventListener("click", () => row.remove());
  container.appendChild(row);
}
document.getElementById("btn-add-bud-item").addEventListener("click", () => addBudgetItemRow());
document.getElementById("bud-period").addEventListener("change", (e) => {
  document.getElementById("bud-end-field").style.display = e.target.value === "personalizado" ? "block" : "none";
});
document.getElementById("btn-new-budget").addEventListener("click", async () => {
  await refreshCache();
  document.getElementById("form-budget").reset();
  document.getElementById("bud-items").innerHTML = "";
  document.getElementById("bud-start").value = todayStr();
  document.getElementById("bud-end-field").style.display = "none";
  addBudgetItemRow();
  openModal("modal-budget");
});
document.getElementById("form-budget").addEventListener("submit", async (e) => {
  e.preventDefault();
  const rows = document.querySelectorAll(".bud-item-row");
  const items = Array.from(rows).map((r) => ({
    category_id: Number(r.querySelector(".bud-item-category").value),
    planned_amount: parseFloat(r.querySelector(".bud-item-amount").value),
  }));
  if (!items.length) { toast("Agrega al menos una categoría", true); return; }
  const periodType = document.getElementById("bud-period").value;
  try {
    await API.createBudget({
      name: document.getElementById("bud-name").value, period_type: periodType,
      start_date: document.getElementById("bud-start").value,
      end_date: periodType === "personalizado" ? (document.getElementById("bud-end").value || null) : null,
      items,
    });
    toast("Presupuesto creado");
    closeModal("modal-budget");
    loadBudgetsView();
  } catch (err) { toast(err.message, true); }
});

async function loadBudgetsView() {
  await refreshCache();
  const budgets = await API.getBudgets();
  const container = document.getElementById("budgets-container");
  if (!budgets.length) {
    container.innerHTML = `<div class="card"><div class="empty-state">No tienes presupuestos creados todavía.</div></div>`;
    return;
  }
  const statuses = await Promise.all(budgets.map((b) => API.getBudgetStatus(b.id)));
  container.innerHTML = statuses.map((s) => {
    const pct = s.total_planned ? Math.min(100, Math.round((s.total_actual / s.total_planned) * 100)) : 0;
    const over = s.total_actual > s.total_planned;
    return `
    <div class="card" style="margin-bottom:16px;">
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px;">
        <h2 style="font-size:17px;">${s.budget_name}</h2>
        <button class="btn btn-sm btn-danger" data-delete-budget="${s.budget_id}">Eliminar</button>
      </div>
      <div class="text-sm muted" style="margin-bottom:10px;">Periodo ${s.period_type} vigente: ${fmtDate(s.period_start)} – ${fmtDate(s.period_end)}</div>
      <div style="display:flex;justify-content:space-between;font-size:14px;margin-bottom:2px;">
        <strong>Total</strong><span class="mono ${over ? "kpi-delta-neg" : "kpi-delta-pos"}">${fmtMoney(s.total_actual)} / ${fmtMoney(s.total_planned)}</span>
      </div>
      <div class="progress-bar" style="margin-bottom:14px;"><div class="progress-fill ${over ? "over" : ""}" style="width:${pct}%"></div></div>
      <table>
        <thead><tr><th>Categoría</th><th class="num">Planeado</th><th class="num">Real</th><th class="num">Desviación</th><th>Estado</th></tr></thead>
        <tbody>
          ${s.items.map((i) => `
            <tr>
              <td>${i.category_name}</td>
              <td class="num mono">${fmtMoney(i.planned_amount)}</td>
              <td class="num mono">${fmtMoney(i.actual_amount)}</td>
              <td class="num mono" style="color:${i.deviation > 0 ? "var(--danger)" : "var(--primary-dark)"}">${i.deviation > 0 ? "+" : ""}${fmtMoney(i.deviation)} (${i.deviation_pct}%)</td>
              <td><span class="badge badge-${i.status === "alerta" ? "alerta" : "ok"}">${i.status === "alerta" ? "Desviado" : "En línea"}</span></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>`;
  }).join("");

  container.querySelectorAll("[data-delete-budget]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      if (!confirm("¿Eliminar este presupuesto?")) return;
      await API.deleteBudget(Number(btn.dataset.deleteBudget));
      toast("Presupuesto eliminado");
      loadBudgetsView();
    })
  );
}

// ============================================================
// CATEGORIAS
// ============================================================
async function loadCategoriesView() {
  const [ingresos, gastos] = await Promise.all([API.getCategories("ingreso"), API.getCategories("gasto")]);
  const renderList = (cats) => cats.map((c) => `
    <div class="ledger-row">
      <div>
        <span style="margin-right:6px;">${c.icon || ""}</span>
        <span class="ledger-name">${c.name}</span>
        <span class="badge badge-${c.group}" style="margin-left:8px;">${GROUP_LABEL[c.group] || c.group}</span>
      </div>
      <button class="btn btn-sm btn-danger" data-delete-cat="${c.id}">✕</button>
    </div>
  `).join("") || `<div class="empty-state">Sin categorías.</div>`;

  document.getElementById("list-cat-ingreso").innerHTML = renderList(ingresos);
  document.getElementById("list-cat-gasto").innerHTML = renderList(gastos);

  document.querySelectorAll("[data-delete-cat]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      if (!confirm("¿Eliminar esta categoría?")) return;
      try {
        await API.deleteCategory(Number(btn.dataset.deleteCat));
        toast("Categoría eliminada");
        loadCategoriesView();
      } catch (err) { toast(err.message, true); }
    })
  );
}

document.getElementById("btn-new-category").addEventListener("click", () => {
  document.getElementById("form-category").reset();
  openModal("modal-category");
});
document.getElementById("form-category").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await API.createCategory({
      name: document.getElementById("cat-name").value,
      kind: document.getElementById("cat-kind").value,
      group: document.getElementById("cat-group").value,
    });
    toast("Categoría creada");
    closeModal("modal-category");
    loadCategoriesView();
  } catch (err) { toast(err.message, true); }
});

// ============================================================
// Init
// ============================================================
initSession();
