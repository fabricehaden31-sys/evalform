const defaultQuestions = [
  'Les objectifs de la formation ont été clairement définis.',
  'La participation et les interactions ont été encouragées.',
  'Le contenu était bien organisé et facile à assimiler.',
  'Les supports fournis ont été utiles et adaptés.',
  'Cette formation sera utile dans mon travail.',
];

const formsList = document.querySelector('#formsList');
const dialog = document.querySelector('#formDialog');
const createForm = document.querySelector('#createForm');
const trainersContainer = document.querySelector('#trainersContainer');
const questionsContainer = document.querySelector('#questionsContainer');
const formError = document.querySelector('#formError');
const responseFormSelect = document.querySelector('#responseFormSelect');
const responsesList = document.querySelector('#responsesList');

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function renderForms(forms) {
  if (!forms.length) {
    formsList.innerHTML = '<p class="empty-state">Aucun formulaire pour le moment. Créez-en un pour commencer.</p>';
    return;
  }

  formsList.innerHTML = forms.map((form) => {
    const title = form.titre || 'Sans titre';
    const category = form.categorie || 'Sans catégorie';
    const location = form.lieu || 'Lieu non renseigné';
    const trainers = form.formateurs || 'Formateur non renseigné';
    const responses = form.nombre_evaluations ?? 0;
    const status = form.actif === false ? 'Inactif' : 'Actif';
    return `
      <article class="form-row">
        <div class="form-icon">▤</div>
        <div class="form-details">
          <h3>${escapeHtml(title)}</h3>
          <p>${escapeHtml(category)} · <span class="status">${status}</span></p>
          <p>${escapeHtml(location)} · ${escapeHtml(trainers)}</p>
        </div>
        <div class="form-data">
          <b>${responses}</b>
          <span>réponses</span>
        </div>
        <div class="form-score">
          <b>${(form.questions || []).length}</b>
          <span>questions</span>
        </div>
        <a aria-label="Voir ${escapeHtml(title)}" href="evaluer.html?id=${encodeURIComponent(form.id)}">→</a>
      </article>
    `;
  }).join('');
}

function populateFormSelect(forms) {
  const currentValue = responseFormSelect.value;
  responseFormSelect.innerHTML = '';

  if (!forms.length) {
    const option = document.createElement('option');
    option.value = '';
    option.textContent = 'Aucun formulaire disponible';
    option.disabled = true;
    responseFormSelect.appendChild(option);
    responsesList.innerHTML = '<p class="empty-state">Créez un formulaire pour collecter des réponses.</p>';
    return;
  }

  forms.forEach((form) => {
    const option = document.createElement('option');
    option.value = form.id;
    option.textContent = `${form.titre || 'Sans titre'} (${form.nombre_evaluations ?? 0} réponse${(form.nombre_evaluations ?? 0) > 1 ? 's' : ''})`;
    responseFormSelect.appendChild(option);
  });

  const exists = forms.some((form) => String(form.id) === currentValue);
  if (exists) {
    responseFormSelect.value = currentValue;
  }
  loadResponses(responseFormSelect.value);
}

function formatReponseValue(reponse) {
  if (reponse.question_type === 'echelle_satisfaction') {
    return reponse.valeur_numerique != null ? `${reponse.valeur_numerique} / 5` : '—';
  }
  return reponse.valeur_texte || '—';
}

function formatDate(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString('fr-FR', { dateStyle: 'long', timeStyle: 'short' });
}

const RESPONSES_PER_PAGE = 5;

function renderResponses(data, page) {
  const evaluations = data.results || [];
  const total = data.count ?? 0;

  if (!total) {
    responsesList.innerHTML = '<p class="empty-state">Aucune réponse pour ce formulaire pour le moment.</p>';
    return;
  }

  const totalPages = Math.max(1, Math.ceil(total / RESPONSES_PER_PAGE));
  const cards = evaluations.map((evaluation, index) => {
    const reponses = [...(evaluation.reponses || [])].sort((a, b) => (a.question_ordre ?? 0) - (b.question_ordre ?? 0));
    const rows = reponses.map((reponse) => `
      <li>
        <span class="response-question">${escapeHtml(reponse.question_libelle || 'Question sans intitulé')}</span>
        <span class="response-value">${escapeHtml(formatReponseValue(reponse))}</span>
      </li>
    `).join('');
    const score = evaluation.score_global != null ? `${Math.round(evaluation.score_global)}%` : '—';
    const numero = total - ((page - 1) * RESPONSES_PER_PAGE + index);
    return `
      <article class="response-card">
        <header>
          <b>Réponse n°${numero}</b>
          <span>Soumise le ${escapeHtml(formatDate(evaluation.date_soumission))} · Satisfaction : ${score}</span>
        </header>
        <ul>${rows}</ul>
      </article>
    `;
  }).join('');

  const pagination = totalPages > 1 ? `
    <nav class="responses-pagination" aria-label="Pagination des réponses">
      <button type="button" data-page="${page - 1}" ${page <= 1 ? 'disabled' : ''}>← Précédent</button>
      <span>Page ${page} sur ${totalPages} · ${total} réponse${total > 1 ? 's' : ''}</span>
      <button type="button" data-page="${page + 1}" ${page >= totalPages ? 'disabled' : ''}>Suivant →</button>
    </nav>
  ` : '';

  responsesList.innerHTML = cards + pagination;
}

async function loadResponses(formId, page = 1) {
  if (!formId) {
    responsesList.innerHTML = '<p class="empty-state">Sélectionnez un formulaire pour afficher les réponses.</p>';
    return;
  }
  responsesList.innerHTML = '<p class="empty-state">Chargement des réponses…</p>';
  try {
    const data = await apiRequest(
      `/administration/formulaires/${encodeURIComponent(formId)}/reponses/?page=${page}&page_size=${RESPONSES_PER_PAGE}`,
    );
    renderResponses(data, page);
  } catch (error) {
    responsesList.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
  }
}

responsesList.addEventListener('click', (event) => {
  const button = event.target.closest('.responses-pagination button');
  if (!button || button.disabled) return;
  loadResponses(responseFormSelect.value, Number(button.dataset.page));
});

function addTrainerRow(value = '') {
  const row = document.createElement('div');
  row.className = 'dynamic-row';
  row.innerHTML = `
    <input type="text" class="trainer-name" required placeholder="Nom du formateur" value="${escapeHtml(value)}">
    <button type="button" class="button button-ghost button-tiny remove-row">Supprimer</button>
  `;
  row.querySelector('.remove-row').addEventListener('click', () => {
    if (trainersContainer.children.length === 1) {
      row.querySelector('input').value = '';
      return;
    }
    row.remove();
  });
  trainersContainer.appendChild(row);
}

function addQuestionRow(question = {}) {
  const type = question.type_reponse || 'echelle_satisfaction';
  const row = document.createElement('article');
  row.className = 'question-item';
  row.innerHTML = `
    <div class="dynamic-row">
      <label class="grow">Intitulé
        <input type="text" class="question-label" required placeholder="Ex. Le contenu était clair et utile." value="${escapeHtml(question.libelle || '')}">
      </label>
      <button type="button" class="button button-ghost button-tiny remove-row">Supprimer</button>
    </div>
    <div class="question-meta">
      <label>Type de réponse
        <select class="question-type">
          <option value="echelle_satisfaction">Échelle de satisfaction</option>
          <option value="commentaire_libre">Commentaire libre</option>
          <option value="choix_multiple">Choix multiple</option>
        </select>
      </label>
      <label class="checkbox-inline">
        <input type="checkbox" class="question-required" ${question.obligatoire === false ? '' : 'checked'}>
        Obligatoire
      </label>
    </div>
    <label class="options-field" hidden>Options (séparées par une virgule)
      <input type="text" class="question-options" placeholder="Ex. ISO 27001, PMP, ITIL">
    </label>
  `;

  const typeSelect = row.querySelector('.question-type');
  const optionsField = row.querySelector('.options-field');
  const optionsInput = row.querySelector('.question-options');
  typeSelect.value = type;
  optionsInput.value = (question.options || []).join(', ');
  optionsField.hidden = type !== 'choix_multiple';
  typeSelect.addEventListener('change', () => {
    optionsField.hidden = typeSelect.value !== 'choix_multiple';
  });
  row.querySelector('.remove-row').addEventListener('click', () => {
    if (questionsContainer.children.length === 1) {
      formError.textContent = 'Le formulaire doit contenir au moins une question.';
      return;
    }
    row.remove();
  });
  questionsContainer.appendChild(row);
}

function resetBuilder() {
  createForm.reset();
  formError.textContent = '';
  trainersContainer.innerHTML = '';
  questionsContainer.innerHTML = '';
  addTrainerRow();
  defaultQuestions.forEach((libelle) => addQuestionRow({ libelle, type_reponse: 'echelle_satisfaction', obligatoire: true }));
}

function collectTrainers() {
  return [...document.querySelectorAll('.trainer-name')]
    .map((input) => input.value.trim())
    .filter(Boolean)
    .join(', ');
}

function collectQuestions() {
  return [...questionsContainer.querySelectorAll('.question-item')].map((row, index) => {
    const type = row.querySelector('.question-type').value;
    const options = type === 'choix_multiple'
      ? row.querySelector('.question-options').value.split(',').map((item) => item.trim()).filter(Boolean)
      : [];
    return {
      libelle: row.querySelector('.question-label').value.trim(),
      type_reponse: type,
      obligatoire: row.querySelector('.question-required').checked,
      ordre: index + 1,
      options,
    };
  });
}

function updateMetrics(dashboard) {
  const evaluations = dashboard?.nombre_evaluations ?? 0;
  const satisfaction = dashboard?.satisfaction_moyenne;
  const active = dashboard?.formulaires_actifs ?? 0;
  document.querySelector('#metricEvaluations').textContent = evaluations;
  document.querySelector('#metricSatisfaction').textContent = satisfaction == null ? '—' : `${Math.round(satisfaction)}%`;
  document.querySelector('#metricForms').textContent = active;
}

async function refreshDashboard() {
  try {
    const [forms, dashboard] = await Promise.all([
      apiRequest('/administration/formulaires/'),
      apiRequest('/administration/tableau-de-bord/'),
    ]);
    renderForms(forms);
    updateMetrics(dashboard);
    populateFormSelect(forms);
  } catch (error) {
    formsList.innerHTML = `<p class="empty-state">${escapeHtml(error.message)} Lancez le serveur Django pour charger les formulaires.</p>`;
  }
}

document.querySelector('#newFormButton').addEventListener('click', () => {
  resetBuilder();
  dialog.showModal();
});

responseFormSelect.addEventListener('change', () => {
  loadResponses(responseFormSelect.value);
});

document.querySelector('#addTrainerButton').addEventListener('click', () => addTrainerRow());
document.querySelector('#addQuestionButton').addEventListener('click', () => {
  formError.textContent = '';
  addQuestionRow();
});

function closeDialog() {
  dialog.close();
}

document.querySelector('#closeDialog').addEventListener('click', closeDialog);
document.querySelector('#cancelDialog').addEventListener('click', closeDialog);

createForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  formError.textContent = '';

  const payload = {
    titre: document.querySelector('#formTitle').value.trim(),
    categorie: document.querySelector('#formCategory').value.trim() || 'Formation',
    lieu: document.querySelector('#formLocation').value.trim(),
    formateurs: collectTrainers(),
    actif: true,
    questions: collectQuestions(),
  };

  if (!payload.formateurs) {
    formError.textContent = 'Ajoutez au moins un formateur.';
    return;
  }
  if (!payload.questions.length || payload.questions.some((question) => !question.libelle)) {
    formError.textContent = 'Chaque question doit avoir un intitulé.';
    return;
  }

  try {
    await apiRequest('/administration/formulaires/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    dialog.close();
    await refreshDashboard();
  } catch (error) {
    formError.textContent = error.message;
  }
});

document.querySelector('#logoutButton').addEventListener('click', async () => {
  try {
    await apiRequest('/auth/deconnexion/', { method: 'POST' });
  } catch {
    // La session locale est tout de même effacée.
  }
  clearAdminSession();
  window.location.href = 'connexion.html';
});

const storedName = sessionStorage.getItem(USER_STORAGE_KEY);
if (storedName) {
  document.querySelector('#adminName').textContent = storedName;
  document.querySelector('#adminGreeting').textContent = storedName;
}

refreshDashboard();
