const API_BASE_URL = `${window.location.origin}/api`;

const AUTH_STORAGE_KEY = 'evalform_role';
const USER_STORAGE_KEY = 'evalform_username';

function getCsrfToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : '';
}

function apiErrorMessage(data) {
  if (!data || typeof data !== 'object') return 'La requête n'a pas pu aboutir.';
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.non_field_errors)) return data.non_field_errors[0];
  const first = Object.values(data).find((value) => Array.isArray(value) && value.length);
  if (first) return first[0];
  return 'La requête n'a pas pu aboutir.';
}

async function apiRequest(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    'X-CSRFToken': getCsrfToken(),
    ...options.headers,
  };
  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    ...options,
    headers,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(apiErrorMessage(data));
  }
  return response.status === 204 ? null : response.json();
}

function setAdminSession(username) {
  sessionStorage.setItem(AUTH_STORAGE_KEY, 'administrateur');
  sessionStorage.setItem(USER_STORAGE_KEY, username || 'Admin');
}

function clearAdminSession() {
  sessionStorage.removeItem(AUTH_STORAGE_KEY);
  sessionStorage.removeItem(USER_STORAGE_KEY);
}

function isLocalAdmin() {
  return sessionStorage.getItem(AUTH_STORAGE_KEY) === 'administrateur';
}
