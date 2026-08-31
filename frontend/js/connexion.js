document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.getElementById('loginForm');
  const loginError = document.getElementById('loginError');
  const submitButton = document.getElementById('loginSubmit');

  if (!loginForm) return;

  loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    loginError.textContent = '';
    submitButton.disabled = true;

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    try {
      const data = await apiRequest('/auth/connexion/', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });

      if (!data.is_administrateur) {
        loginError.textContent = 'Cet espace est réservé aux administrateurs.';
        return;
      }

      setAdminSession(data.username);
      window.location.href = 'admin.html';
    } catch (error) {
      loginError.textContent = error.message || 'Identifiants incorrects.';
    } finally {
      submitButton.disabled = false;
    }
  });
});
