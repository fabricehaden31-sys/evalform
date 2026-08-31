const SCALE_OPTIONS = [
  { value: 5, key: 'tres_satisfait', label: 'Très satisfait', icon: '☺' },
  { value: 4, key: 'satisfait', label: 'Satisfait', icon: '🙂' },
  { value: 3, key: 'neutre', label: 'Neutre', icon: '😐' },
  { value: 2, key: 'insatisfait', label: 'Insatisfait', icon: '☹' },
  { value: 1, key: 'tres_insatisfait', label: 'Très insatisfait', icon: '☹' },
];

const picker = document.querySelector('#formPicker');
const pickerList = document.querySelector('#pickerList');
const form = document.querySelector('#evaluationForm');
const container = document.querySelector('#questionContainer');
const validation = document.querySelector('#validation');

let currentForm = null;

function escapeHtml(value) {
  return String(value || '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function formIdFromUrl() {
  return new URLSearchParams(window.location.search).get('id');
}

async function loadForms() {
  return apiRequest('/formulaires/');
}

function showPicker(forms, message) {
  picker.hidden = false;
  form.hidden = true;
  if (message) {
    pickerList.innerHTML = `<p>${escapeHtml(message)}</p>`;
    return;
  }
  if (!forms.length) {
    pickerList.innerHTML = '<p>Aucun formulaire actif n’est disponible pour le moment.</p>';
    return;
  }
  pickerList.innerHTML = forms.map((item) => `
    <a class="picker-item" href="evaluer.html?id=${encodeURIComponent(item.id)}">
      <h3>${escapeHtml(item.titre)}</h3>
      <p>${escapeHtml(item.lieu || 'Lieu non renseigné')} · ${escapeHtml(item.formateurs || 'Formateur non renseigné')}</p>
    </a>
  `).join('');
}

function renderScaleQuestions(questions) {
  return `<div class="evaluation-table" role="table">
    <div class="table-header" role="row">
      <span>Points à évaluer</span>
      ${SCALE_OPTIONS.map((option) => `<span title="${option.label}"><i>${option.icon}</i>${option.label}</span>`).join('')}
    </div>
    ${questions.map((question, index) => `
      <fieldset class="table-row" role="row">
        <legend>${index + 1}. ${escapeHtml(question.libelle)}</legend>
        ${SCALE_OPTIONS.map((option) => `
          <label title="${option.label}">
            <b>${option.label}</b>
            <input type="radio" name="question-${question.id}" value="${option.value}" ${question.obligatoire ? 'required' : ''}>
            <span aria-hidden="true"></span>
          </label>
        `).join('')}
      </fieldset>
    `).join('')}
  </div>`;
}

function renderOpenQuestion(question, index) {
  return `
    <div class="open-question">
      <label for="question-${question.id}">${index + 1}. ${escapeHtml(question.libelle)} ${question.obligatoire ? '' : '<span>Facultatif</span>'}</label>
      <textarea id="question-${question.id}" name="question-${question.id}" rows="4" placeholder="Écrivez votre réponse ici…" ${question.obligatoire ? 'required' : ''}></textarea>
    </div>
  `;
}

function renderChoiceQuestion(question, index) {
  const options = question.options || [];
  return `
    <fieldset class="multiple-question">
      <legend>${index + 1}. ${escapeHtml(question.libelle)} <span>Plusieurs réponses possibles</span></legend>
      <div class="checkbox-list">
        ${options.map((option) => `
          <label>
            <input type="checkbox" name="question-${question.id}" value="${escapeHtml(option)}">
            <span></span> ${escapeHtml(option)}
          </label>
        `).join('') || '<p>Aucune option n’a été définie pour cette question.</p>'}
      </div>
    </fieldset>
  `;
}

function renderForm(formulaire) {
  currentForm = formulaire;
  picker.hidden = true;
  form.hidden = false;

  document.querySelector('#surveyTitle').textContent = formulaire.titre || 'Votre avis compte pour nous.';
  document.querySelector('#surveyCategory').textContent = formulaire.categorie || 'Évaluation de formation';
  document.querySelector('#surveyLocation').textContent = formulaire.lieu || '—';
  document.querySelector('#surveyTrainers').textContent = formulaire.formateurs || '—';
  document.querySelector('#surveyDate').textContent = new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date());
  document.querySelector('#surveyDescription').textContent = formulaire.description
    || 'Veuillez indiquer votre degré de satisfaction pour chacun des points ci-dessous.';

  const questions = formulaire.questions || [];
  const scale = questions.filter((question) => question.type_reponse === 'echelle_satisfaction');
  const others = questions.filter((question) => question.type_reponse !== 'echelle_satisfaction');
  const offset = scale.length;

  container.innerHTML = [
    scale.length ? renderScaleQuestions(scale) : '',
    others.length ? `<section class="open-questions">${others.map((question, index) => (
      question.type_reponse === 'choix_multiple'
        ? renderChoiceQuestion(question, offset + index)
        : renderOpenQuestion(question, offset + index)
    )).join('')}</section>` : '',
  ].join('');
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  validation.textContent = '';
  if (!currentForm) return;

  const reponses = [];
  for (const question of currentForm.questions || []) {
    if (question.type_reponse === 'echelle_satisfaction') {
      const selected = form.querySelector(`input[name="question-${question.id}"]:checked`);
      if (!selected) {
        if (question.obligatoire) {
          validation.textContent = `Veuillez répondre à la question : ${question.libelle}`;
          return;
        }
        continue;
      }
      reponses.push({ question_id: question.id, valeur_numerique: Number(selected.value) });
    } else if (question.type_reponse === 'choix_multiple') {
      const selected = [...form.querySelectorAll(`input[name="question-${question.id}"]:checked`)].map((input) => input.value);
      if (!selected.length && question.obligatoire) {
        validation.textContent = `Veuillez répondre à la question : ${question.libelle}`;
        return;
      }
      reponses.push({ question_id: question.id, valeur_texte: selected.join(', ') });
    } else {
      const text = form.querySelector(`[name="question-${question.id}"]`)?.value.trim() || '';
      if (!text && question.obligatoire) {
        validation.textContent = `Veuillez répondre à la question : ${question.libelle}`;
        return;
      }
      if (text) reponses.push({ question_id: question.id, valeur_texte: text });
    }
  }

  try {
    await apiRequest(`/formulaires/${currentForm.id}/evaluations/`, {
      method: 'POST',
      body: JSON.stringify({ reponses }),
    });
  } catch (error) {
    validation.textContent = error.message;
    return;
  }

  form.innerHTML = `
    <div class="success-state">
      <span>✓</span>
      <h2>Merci pour votre avis !</h2>
      <p>Votre évaluation a bien été enregistrée. Elle nous aide à améliorer nos formations.</p>
      <a class="button" href="index.html">Retour à l’accueil</a>
    </div>
  `;
});

(async function init() {
  let forms = [];
  try {
    forms = await loadForms();
  } catch (error) {
    showPicker([], `${error.message} Lancez le serveur Django (port 8000) pour charger les formulaires.`);
    return;
  }

  const requestedId = formIdFromUrl();
  if (!requestedId) {
    showPicker(forms);
    return;
  }
  const selected = forms.find((item) => String(item.id) === String(requestedId));
  if (!selected) {
    showPicker(forms);
    return;
  }
  renderForm(selected);
})();
