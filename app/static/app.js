// Premium dashboard JavaScript
// Handles navigation, API calls, and UI rendering

// Utility to get JWT token from localStorage
function getToken() {
  return localStorage.getItem('token');
}

function setToken(token) {
  localStorage.setItem('token', token);
}

// Generic API request wrapper
async function apiRequest(path, method = 'GET', data = null) {
  const headers = {
    'Content-Type': 'application/json',
  };
  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const options = { method, headers };
  if (data) {
    options.body = JSON.stringify(data);
  }
  const response = await fetch(path, options);
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || 'API error');
  }
  return response.json();
}

// Navigation handling (single‑page app)
function showSection(id) {
  document.querySelectorAll('section').forEach(sec => {
    sec.style.display = sec.id === id ? 'block' : 'none';
  });
  document.querySelectorAll('nav button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.target === id);
  });
}

// Registration & login forms
async function handleRegister(event) {
  event.preventDefault();
  const form = event.target;
  const data = Object.fromEntries(new FormData(form));
  const result = await apiRequest('/users/register', 'POST', data);
  alert('Registered! Please log in.');
  form.reset();
}

async function handleLogin(event) {
  event.preventDefault();
  const form = event.target;
  const data = Object.fromEntries(new FormData(form));
  const result = await apiRequest('/auth/login', 'POST', data);
  setToken(result.access_token);
  alert('Login successful');
  loadDashboard();
}

// Load wallet overview
async function loadWallet() {
  const wallet = await apiRequest('/wallets/me');
  document.getElementById('wallet-balance').textContent = `$${wallet.balance.toFixed(2)}`;
}

// Internal transfer
async function handleTransfer(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  await apiRequest('/wallets/transfer', 'POST', data);
  alert('Transfer successful');
  loadWallet();
}

// Payment checkout (mock)
async function handleCheckout(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  await apiRequest('/payment/checkout', 'POST', data);
  alert('Payment processed');
  loadWallet();
  loadPayments();
}

// Load payment history
async function loadPayments() {
  const payments = await apiRequest('/payment/history');
  const tbody = document.getElementById('payments-body');
  tbody.innerHTML = '';
  payments.forEach(p => {
    const row = document.createElement('tr');
    row.innerHTML = `<td>${p.id}</td><td>${p.amount}</td><td>${p.status}</td><td>${p.created_at}</td>`;
    tbody.appendChild(row);
  });
}

// Refund interface
async function handleRefund(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  await apiRequest('/refund/create', 'POST', data);
  alert('Refund requested');
  loadPayments();
}

// Ledger view
async function loadLedger() {
  const entries = await apiRequest('/audit/entries');
  const tbody = document.getElementById('ledger-body');
  tbody.innerHTML = '';
  entries.forEach(e => {
    const row = document.createElement('tr');
    row.innerHTML = `<td>${e.id}</td><td>${e.action}</td><td>${e.amount}</td><td>${e.timestamp}</td>`;
    tbody.appendChild(row);
  });
}

function loadDashboard() {
  showSection('wallet-section');
  loadWallet();
  loadPayments();
  loadLedger();
}

// Initial setup
document.addEventListener('DOMContentLoaded', () => {
  // Navigation buttons
  document.querySelectorAll('nav button').forEach(btn => {
    btn.addEventListener('click', () => showSection(btn.dataset.target));
  });

  // Form listeners
  document.getElementById('register-form')?.addEventListener('submit', handleRegister);
  document.getElementById('login-form')?.addEventListener('submit', handleLogin);
  document.getElementById('transfer-form')?.addEventListener('submit', handleTransfer);
  document.getElementById('checkout-form')?.addEventListener('submit', handleCheckout);
  document.getElementById('refund-form')?.addEventListener('submit', handleRefund);

  // Show login by default
  showSection('login-section');
});
