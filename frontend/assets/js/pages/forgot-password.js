import { auth } from '../api.js';
import { $, setBusy, clearErrors, showError, esc } from '../ui.js';

const form = $('#forgot-form');
let lastIdentifier = '';

async function send(btn) {
  setBusy(btn, true, 'Sending…');
  try {
    const res = await auth.requestPasswordReset(lastIdentifier);
    $('#step-request').hidden = true;
    $('#step-sent').hidden = false;
    $('#sent-to').textContent = lastIdentifier;
    // Mock mode only: the fake backend returns the link instead of emailing it.
    if (res && res._mock_reset_link) {
      const box = $('#mock-link');
      box.innerHTML = `Demo mode – no email is sent. <a href="${esc(res._mock_reset_link)}">Open the reset link</a>`;
      box.hidden = false;
    }
  } catch (err) {
    showError(form, err);
  } finally {
    setBusy(btn, false);
  }
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  clearErrors(form);
  lastIdentifier = form.identifier.value.trim();
  if (!lastIdentifier) return showError(form, { field: 'identifier', message: 'Please enter your email or username.' });
  send(form.querySelector('[type="submit"]'));
});

$('#resend').addEventListener('click', async (e) => {
  await send(e.currentTarget);
  e.currentTarget.textContent = 'Sent again ✓';
});
