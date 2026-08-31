(async function protectAdminPage() {
  if (sessionStorage.getItem('evalform_role') !== 'administrateur') {
    window.location.replace('connexion.html');
    return;
  }

  try {
    const data = await apiRequest('/auth/moi/');
    if (data.authentifie && data.is_administrateur) {
      setAdminSession(data.username);
      return;
    }
  } catch {
    clearAdminSession();
  }

  window.location.replace('connexion.html');
})();
