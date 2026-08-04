/** Email reminders UI */

let reminderView = 'tasks';

const CATEGORY_ICONS = {
  reorder: '📦', sales_call: '📞', backup_local: '💾', backup_cloud: '☁️',
  accounts_receivable: '💰', quote_followup: '📝', po_followup: '🛒', inventory: '🏪', general: '📋',
};

function recurrenceLabel(r) {
  return { none: 'One-time', daily: 'Daily', weekly: 'Weekly', monthly: 'Monthly' }[r] || r;
}

export async function renderReminders(deps) {
  const { topbarActions, content, api, fmtDate, badge, $, toast } = deps;
  Object.assign(window, { fmtDate, badge, $ });

  topbarActions().innerHTML = `
    <button class="btn btn-secondary" id="run-due-reminders">▶ Run Due Now</button>
    <button class="btn btn-primary" id="add-reminder">+ Add Reminder</button>
  `;

  content().innerHTML = `
    <nav class="report-tabs" id="reminder-views">
      <button class="report-tab active" data-view="tasks">📋 Task Reminders</button>
      <button class="report-tab" data-view="settings">⚙ Email Settings</button>
      <button class="report-tab" data-view="log">📨 Send Log</button>
    </nav>
    <div id="reminder-body"><div class="text-muted">Loading...</div></div>
  `;

  $('#reminder-views').querySelectorAll('.report-tab').forEach(tab => {
    tab.onclick = () => {
      reminderView = tab.dataset.view;
      $('#reminder-views').querySelectorAll('.report-tab').forEach(t =>
        t.classList.toggle('active', t.dataset.view === reminderView));
      renderReminderView(deps);
    };
  });

  $('#add-reminder').onclick = () => showReminderForm(deps);
  $('#run-due-reminders').onclick = async () => {
    try {
      const r = await api('reminders/run-due', { method: 'POST', body: {} });
      toast(`Processed ${r.processed} reminders, ${r.sent} sent`);
      renderReminderView(deps);
    } catch (e) { toast(e.message); }
  };

  await renderReminderView(deps);
}

async function renderReminderView(deps) {
  const { api, content } = deps;
  const body = $('#reminder-body');
  if (reminderView === 'settings') return renderEmailSettings(deps);
  if (reminderView === 'log') return renderSendLog(deps);

  body.innerHTML = '<div class="text-muted">Loading...</div>';
  const [reminders, settings] = await Promise.all([
    api('reminders'),
    api('reminders/settings'),
  ]);

  const enabled = settings.enabled;
  body.innerHTML = `
    ${!enabled ? `<div class="card mb-20" style="border-color:var(--color-gold)">
      <div class="card-title">Email not enabled</div>
      <p class="text-muted" style="margin-top:8px;font-size:0.85rem">
        Configure SMTP settings under <strong>Email Settings</strong> to receive automated reminders.
      </p></div>` : ''}

    <div class="metric-grid mb-20" style="grid-template-columns:repeat(4,1fr)">
      <div class="metric-card"><div class="metric-label">Active Reminders</div>
        <div class="metric-value blue">${reminders.filter(r => r.enabled).length}</div></div>
      <div class="metric-card"><div class="metric-label">Auto Tasks</div>
        <div class="metric-value green">${reminders.filter(r => r.task_type === 'auto').length}</div></div>
      <div class="metric-card"><div class="metric-label">Due Today or Earlier</div>
        <div class="metric-value amber">${reminders.filter(r => r.enabled && r.next_due_date <= new Date().toISOString().slice(0,10)).length}</div></div>
      <div class="metric-card"><div class="metric-label">Email Status</div>
        <div class="metric-value ${enabled ? 'green' : 'red'}">${enabled ? 'On' : 'Off'}</div></div>
    </div>

    <div class="card">
      <div class="card-header"><div class="card-title">Scheduled Reminders</div></div>
      <div class="table-wrap"><table>
        <thead><tr>
          <th>Task</th><th>Category</th><th>Schedule</th><th>Next Due</th><th>Last Sent</th><th>Status</th><th>Actions</th>
        </tr></thead>
        <tbody>${reminders.map(r => `
          <tr class="${!r.enabled ? 'text-muted' : ''}">
            <td><strong>${CATEGORY_ICONS[r.category] || ''} ${r.title}</strong>
              ${r.task_type === 'auto' ? '<br><span class="text-muted" style="font-size:0.75rem">Auto-generated content</span>' : ''}
              ${r.description && r.task_type === 'manual' ? `<br><span class="text-muted" style="font-size:0.75rem">${r.description.slice(0,60)}</span>` : ''}
            </td>
            <td>${r.category_label || r.category}</td>
            <td>${recurrenceLabel(r.recurrence)} at ${r.due_time}</td>
            <td>${fmtDate(r.next_due_date)}</td>
            <td>${r.last_sent_at ? r.last_sent_at.slice(0, 16).replace('T', ' ') : '—'}</td>
            <td>${r.enabled ? badge('active') : badge('draft')}</td>
            <td class="gap-8">
              <button class="btn btn-sm btn-primary send-reminder" data-id="${r.id}">Send</button>
              ${r.task_type === 'auto' ? `<button class="btn btn-sm btn-secondary preview-reminder" data-cat="${r.category}">Preview</button>` : ''}
              <button class="btn btn-sm btn-secondary edit-reminder" data-id="${r.id}">Edit</button>
            </td>
          </tr>
        `).join('')}</tbody>
      </table></div>
    </div>

    <div class="tips-card mt-16">
      <h3>Built-in automated reminders</h3>
      <ul>
        <li><strong>Reorder</strong> — emails when SKUs hit reorder level with supplier info</li>
        <li><strong>Sales calls</strong> — weekly contractor/builder contact list</li>
        <li><strong>Local backup</strong> — reminds you to copy the SQLite database</li>
        <li><strong>Cloud backup</strong> — verification checklist for off-site sync</li>
        <li><strong>A/R follow-up</strong> — outstanding and overdue invoices</li>
        <li><strong>Quote follow-up</strong> — pending quotes nearing expiration</li>
        <li><strong>PO follow-up</strong> — open purchase orders awaiting delivery</li>
      </ul>
    </div>
  `;

  body.querySelectorAll('.send-reminder').forEach(btn => {
    btn.onclick = async () => {
      try {
        const r = await api(`reminders/${btn.dataset.id}/send`, { method: 'POST' });
        if (r.skipped) toast(r.reason === 'nothing to report' ? (r.message || 'Nothing to send') : 'Skipped');
        else toast('Reminder sent');
        renderReminderView(deps);
      } catch (e) { toast(e.message); }
    };
  });
  body.querySelectorAll('.preview-reminder').forEach(btn => {
    btn.onclick = async () => {
      const p = await api(`reminders/preview/${btn.dataset.cat}`);
      deps.showModal('Email Preview', `
        ${p.empty ? `<p class="text-muted">${p.body}</p>` : `
          <p><strong>Subject:</strong> ${p.subject}</p>
          <pre class="schema-block" style="margin-top:12px;white-space:pre-wrap">${p.body}</pre>
        `}
      `, '<button class="btn btn-secondary" onclick="document.getElementById(\'modal-overlay\').classList.add(\'hidden\')">Close</button>');
    };
  });
  body.querySelectorAll('.edit-reminder').forEach(btn => {
    btn.onclick = () => showReminderForm(deps, reminders.find(r => r.id == btn.dataset.id));
  });
}

async function renderEmailSettings(deps) {
  const { api } = deps;
  const s = await api('reminders/settings');
  $('#reminder-body').innerHTML = `
    <div class="card">
      <div class="card-header"><div class="card-title">SMTP Email Configuration</div></div>
      <form id="email-settings-form" class="form-grid">
        <div class="form-group full"><label><input type="checkbox" name="enabled" ${s.enabled ? 'checked' : ''}> Enable email reminders</label></div>
        <div class="form-group"><label>SMTP Host</label><input name="smtp_host" value="${s.smtp_host || ''}" placeholder="smtp.gmail.com"></div>
        <div class="form-group"><label>SMTP Port</label><input name="smtp_port" type="number" value="${s.smtp_port || 587}"></div>
        <div class="form-group"><label>SMTP Username</label><input name="smtp_user" value="${s.smtp_user || ''}"></div>
        <div class="form-group"><label>SMTP Password</label><input name="smtp_password" type="password" placeholder="${s.smtp_password ? '(unchanged)' : ''}"></div>
        <div class="form-group"><label>From Email</label><input name="from_email" type="email" value="${s.from_email || ''}"></div>
        <div class="form-group full"><label>To Emails (comma-separated)</label><input name="to_emails" value="${s.to_emails || ''}" placeholder="you@company.com, ops@company.com"></div>
        <div class="form-group"><label><input type="checkbox" name="use_tls" ${s.use_tls ? 'checked' : ''}> Use TLS</label></div>
        <div class="form-group"><label>Check interval (minutes)</label><input name="check_interval_minutes" type="number" min="5" value="${s.check_interval_minutes || 15}"></div>
      </form>
      <div class="gap-8 mt-16">
        <button class="btn btn-primary" id="save-email-settings">Save Settings</button>
        <button class="btn btn-secondary" id="test-email">Send Test Email</button>
      </div>
      <p class="text-muted mt-16" style="font-size:0.8rem">Credentials are stored locally in your SQLite database. For Gmail, use an app password.</p>
    </div>
  `;

  $('#save-email-settings').onclick = async () => {
    const fd = Object.fromEntries(new FormData($('#email-settings-form')));
    fd.enabled = $('#email-settings-form').querySelector('[name=enabled]').checked;
    fd.use_tls = $('#email-settings-form').querySelector('[name=use_tls]').checked;
    fd.smtp_port = parseInt(fd.smtp_port);
    fd.check_interval_minutes = parseInt(fd.check_interval_minutes);
    try {
      await api('reminders/settings', { method: 'PUT', body: fd });
      deps.toast('Email settings saved');
    } catch (e) { deps.toast(e.message); }
  };
  $('#test-email').onclick = async () => {
    try {
      const r = await api('reminders/settings/test', { method: 'POST' });
      deps.toast(r.message);
    } catch (e) { deps.toast(e.message); }
  };
}

async function renderSendLog(deps) {
  const log = await deps.api('reminders/log?limit=50');
  $('#reminder-body').innerHTML = `
    <div class="card">
      <div class="card-header"><div class="card-title">Email Send Log</div></div>
      <div class="table-wrap"><table>
        <thead><tr><th>When</th><th>Reminder</th><th>Subject</th><th>Recipients</th><th>Status</th></tr></thead>
        <tbody>${log.length ? log.map(l => `
          <tr>
            <td>${l.sent_at ? l.sent_at.slice(0, 16).replace('T', ' ') : '—'}</td>
            <td>${l.reminder_title || '—'}</td>
            <td>${l.subject}</td>
            <td>${l.recipients}</td>
            <td>${l.status === 'sent' ? badge('active') : l.status === 'failed' ? badge('overdue') : badge('draft')}</td>
          </tr>
        `).join('') : '<tr><td colspan="5" class="text-muted">No emails sent yet</td></tr>'}
        </tbody>
      </table></div>
    </div>
  `;
}

async function showReminderForm(deps, reminder = null) {
  const categories = await deps.api('reminders/categories');
  const isEdit = !!reminder;
  const today = new Date().toISOString().slice(0, 10);
  deps.showModal(isEdit ? 'Edit Reminder' : 'Add Reminder', `
    <form id="reminder-form" class="form-grid">
      <div class="form-group full"><label>Title *</label><input name="title" required value="${reminder?.title || ''}"></div>
      <div class="form-group"><label>Category *</label>
        <select name="category" required>${categories.map(c =>
          `<option value="${c.id}" ${reminder?.category === c.id ? 'selected' : ''}>${c.label}</option>`).join('')}
        </select>
      </div>
      <div class="form-group"><label>Type</label>
        <select name="task_type">
          <option value="manual" ${reminder?.task_type !== 'auto' ? 'selected' : ''}>Manual message</option>
          <option value="auto" ${reminder?.task_type === 'auto' ? 'selected' : ''}>Auto (live data from PowerFlow)</option>
        </select>
      </div>
      <div class="form-group"><label>Recurrence</label>
        <select name="recurrence">
          ${['none','daily','weekly','monthly'].map(r =>
            `<option value="${r}" ${(reminder?.recurrence || 'weekly') === r ? 'selected' : ''}>${recurrenceLabel(r)}</option>`).join('')}
        </select>
      </div>
      <div class="form-group"><label>Due time</label><input name="due_time" type="time" value="${reminder?.due_time || '08:00'}"></div>
      <div class="form-group"><label>Next due date *</label><input name="next_due_date" type="date" required value="${reminder?.next_due_date || today}"></div>
      <div class="form-group full"><label>Override email (optional)</label><input name="email_to" value="${reminder?.email_to || ''}" placeholder="Uses global To list if blank"></div>
      <div class="form-group full"><label>Description (manual tasks)</label><textarea name="description">${reminder?.description || ''}</textarea></div>
      <div class="form-group"><label><input type="checkbox" name="enabled" ${reminder?.enabled !== 0 ? 'checked' : ''}> Enabled</label></div>
    </form>
  `, `<button class="btn btn-secondary" onclick="document.getElementById('modal-overlay').classList.add('hidden')">Cancel</button>
      <button class="btn btn-primary" id="save-reminder">Save</button>`);

  $('#save-reminder').onclick = async () => {
    const form = $('#reminder-form');
    const body = Object.fromEntries(new FormData(form));
    body.enabled = form.querySelector('[name=enabled]').checked;
    try {
      if (isEdit) await deps.api(`reminders/${reminder.id}`, { method: 'PUT', body });
      else await deps.api('reminders', { method: 'POST', body });
      deps.hideModal();
      deps.toast(isEdit ? 'Reminder updated' : 'Reminder added');
      renderReminderView(deps);
    } catch (e) { deps.toast(e.message); }
  };
}
