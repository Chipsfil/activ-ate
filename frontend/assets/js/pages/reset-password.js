import { auth } from '../api.js';
import { $, setBusy, clearErrors, showError } from '../ui.js';
import { wireRevealButtons } from './auth-common.js';

const form = $('#reset-form');
const token = new URLSearchParams(location.search).get('token');
wireRevealButtons();

if (!token) showError(form, { message: 'This link is incomplete. Please request a new reset link.' });

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearErrors(form);
  const pw = form.new_password.value;
  if (pw.length < 8) return showError(form, { field: 'new_password', message: 'The password needs at least 8 characters.' });
  if (pw !== form.confirm_password.value) return showError(form, { field: 'confirm_password', message: 'The passwords do not match.' });
  const btn = form.querySelector('[type="submit"]');
  setBusy(btn, true, 'Saving…');
  try {
    await auth.confirmPasswordReset(token, pw);
    location.href = 'signin.html?reset=1';
  } catch (err) {
    setBusy(btn, false);
    showError(form, err);
  }
});
