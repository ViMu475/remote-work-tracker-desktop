let trackerState = null;
let editingEntryId = null;
let extractedPdfSessions = [];
let extractedFlexBalance = null;

const MONATS_NUMMERN = {
    "Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6,
    "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11, "Dezember": 12
};

const translations = {
    de: {
        app_title: 'Remote Work Quote Tracker',
        dark_mode: 'Dark Mode',
        switch_language: 'Sprache wechseln',
        export_menu: 'Export und Backup', csv_month: 'CSV (Monat)', pdf_month: 'PDF (Monat)', backup: 'Backup',
        pdf_file: 'PDF-Datei', found_periods: 'Gefundene Zeiträume:', year: 'Jahr',
        remote_placeholder: 'Leer = Vollständig', edit_mode_active: 'Bearbeitungsmodus aktiv',
        soll_per_day: 'Soll-Stunden/Tag', please_confirm: 'Bitte bestätigen', confirm: 'Bestätigen',
        update_entry: 'Eintrag aktualisieren', over_limit: 'über Limit', pdf_import_badge: 'PDF Import',
        empty_entries_hint: 'Tragen Sie oben unter „Tägliches Protokoll“ Ihre erste Arbeitszeit ein oder importieren Sie eine PDF-Datei.',
        empty_history_hint: 'Schließen Sie einen Monat unter „Einstellungen“ ab, dann erscheint er hier.',
        no_history: 'Keine Monate abgeschlossen', no_periods: 'Keine Zeiträume gefunden',
        quarter_word: 'Quartal', month_quote: 'Monat-Quote', actual_short: 'Ist', pause_word: 'Pause', total_word: 'Gesamt',
        quarter_quote: 'Quartals-Quote', quote_word: 'Quote', remote_word: 'Remote',
        toast_close: 'Meldung schließen', backup_running: 'Backup wird erstellt …', working: 'Bitte warten …',
        err_toggle: 'Fehler beim Umschalten', err_pdf_pick: 'Bitte wählen Sie eine PDF-Datei aus', err_pdf_upload: 'Fehler bei PDF-Upload: ',
        err_no_sessions: 'Keine Sessions zum Importieren', err_import: 'Fehler beim Import: ', err_save: 'Fehler beim Speichern',
        err_delete: 'Fehler beim Löschen', err_not_found: 'Eintrag nicht gefunden', editing: 'Eintrag wird bearbeitet', err_generic: 'Fehler',
        err_month_switch: 'Fehler beim Monatswechsel', err_delete_all: 'Fehler beim Löschen: ', err_delete_month: 'Fehler beim Löschen des Monats: ',
        err_clear_history: 'Fehler beim Löschen der Historie: ', err_shutdown: 'Server konnte nicht beendet werden (Status ',
        err_current_month: 'Fehler beim Wechsel zum aktuellen Monat', err_report: 'Fehler beim Laden des Abschlussberichts: ',
        err_view_month: 'Fehler beim Wechsel des Monats: ', err_restore: 'Fehler bei der Wiederherstellung: ',
        server_stopped: 'Server beendet', server_stopped_hint: 'Sie können dieses Fenster schließen.',
        monthly_overview: 'Aktuelle Monatsübersicht',
        rq_progress: 'Remote-Quote Fortschritt',
        soll_arbeitszeit: 'Soll-Arbeitszeit',
        max_remote: 'Max. Remote',
        flex_balance: 'GLZ-Saldo (Nachweis)',
        ist_remote: 'Ist-Remote',
        remaining_remote_hours: 'Verbleibende Remote Stunden',
        current_usage_rate: 'Aktuelle Nutzungsquote:',
        daily_log: 'Tägliches Protokoll',
        date: 'Datum',
        start: 'Start',
        end: 'Ende',
        pause_min: 'Pause (min)',
        remote_h: 'Remote (h)',
        log_worktime: 'Remote Work protokollieren',
        day_history: 'Tageshistorie',
        no_entries: 'Noch keine Einträge',
        settings: 'Einstellungen',
        set: 'Setzen',
        indiv_quote: 'Individuelle Quote (%)',
        month_switch: 'Monat abschließen',
        history: 'Historie',
        delete: 'Löschen',
        edit: 'Ändern',
        confirm_delete: 'Wirklich löschen?',
        confirm_month_switch: 'Monat wirklich abschließen?',
        fill_required: 'Bitte alle Pflichtfelder ausfüllen',
        export_label: 'Export:',
        pdf_import: 'PDF Import',
        pdf_import_desc: 'Laden Sie eine PDF-Datei mit Zeitstempeln hoch. Die Arbeitszeiten werden automatisch extrahiert und zur Tageshistorie hinzugefügt.',
        analyze: 'Analysieren',
        cancel: 'Abbrechen',
        import_sessions: 'Importieren',
        actual_remote_quota: 'Tatsächliche RQ',
        delete_all: 'Alle Einträge löschen',
        confirm_delete_all: 'ACHTUNG: Möchten Sie wirklich ALLE Einträge löschen? Es wird automatisch ein Backup erstellt.',
        backup_created: 'Backup erstellt',
        delete_month: 'Monat löschen',
        confirm_delete_month: 'Möchten Sie diesen Monat wirklich aus der Historie löschen?',
        view_current_month: '→ Aktueller Monat',
        clear_all_history: 'Komplette Historie löschen',
        show_month: 'Monat anzeigen:', restore: 'Wiederherstellen',
        confirm_restore: 'Backup wiederherstellen? Der aktuelle Stand wird ersetzt.',
        final_report: 'Abschlussbericht', print: 'Drucken', close: 'Schließen',
        report_empty: 'Noch keine abgeschlossenen Monate vorhanden.',
        report_overall: 'Gesamt', report_quarter_incomplete: 'unvollständig', report_months: 'Monate',
        report_months_over: 'Monate über Limit', report_limit: 'Limit', report_quota: 'Quote',
        rating_good: 'Gut: Limit eingehalten', rating_tight: 'Knapp eingehalten (über 90 % des Limits)',
        rating_exceeded: 'Überschritten', over_quota_hint: 'Remote-Limit überschritten',
        report_rule: 'Bewertung je Quartal: bis 90 % des Remote-Limits gut, bis 100 % knapp, darüber überschritten.',
        confirm_clear_all_history: 'ACHTUNG: Möchten Sie wirklich die KOMPLETTE Historie löschen? Alle Monate und Einträge werden gelöscht und auf den aktuellen Monat zurückgesetzt.',
        shutdown_server: 'Server beenden',
        confirm_shutdown: 'Möchten Sie den Server wirklich beenden? Die App wird geschlossen.',
        shutdown_success: 'Server wird heruntergefahren...'
    },
    en: {
        app_title: 'Remote Work Quota Tracker',
        dark_mode: 'Dark Mode',
        switch_language: 'Switch language',
        export_menu: 'Export and backup', csv_month: 'CSV (month)', pdf_month: 'PDF (month)', backup: 'Backup',
        pdf_file: 'PDF file', found_periods: 'Periods found:', year: 'Year',
        remote_placeholder: 'Empty = full day', edit_mode_active: 'Edit mode active',
        soll_per_day: 'Target hours/day', please_confirm: 'Please confirm', confirm: 'Confirm',
        update_entry: 'Update entry', over_limit: 'over limit', pdf_import_badge: 'PDF import',
        empty_entries_hint: 'Enter your first working time above under "Daily Log" or import a PDF file.',
        empty_history_hint: 'Close a month under "Settings" and it will appear here.',
        no_history: 'No months closed', no_periods: 'No periods found',
        quarter_word: 'Quarter', month_quote: 'Month quota', actual_short: 'Actual', pause_word: 'Break', total_word: 'Total',
        quarter_quote: 'Quarter quota', quote_word: 'Quota', remote_word: 'Remote',
        toast_close: 'Dismiss message', backup_running: 'Creating backup ...', working: 'Please wait ...',
        err_toggle: 'Could not switch', err_pdf_pick: 'Please choose a PDF file', err_pdf_upload: 'PDF upload failed: ',
        err_no_sessions: 'No sessions to import', err_import: 'Import failed: ', err_save: 'Could not save',
        err_delete: 'Could not delete', err_not_found: 'Entry not found', editing: 'Editing entry', err_generic: 'Error',
        err_month_switch: 'Could not close the month', err_delete_all: 'Could not delete: ', err_delete_month: 'Could not delete the month: ',
        err_clear_history: 'Could not clear the history: ', err_shutdown: 'The server could not be stopped (status ',
        err_current_month: 'Could not switch to the current month', err_report: 'Could not load the final report: ',
        err_view_month: 'Could not change the month: ', err_restore: 'Restore failed: ',
        server_stopped: 'Server stopped', server_stopped_hint: 'You can close this window.',
        monthly_overview: 'Current Month Overview',
        rq_progress: 'Remote Quota Progress',
        soll_arbeitszeit: 'Target Hours',
        max_remote: 'Max Remote',
        flex_balance: 'Flextime balance (statement)',
        ist_remote: 'Actual Remote',
        remaining_remote_hours: 'Remaining Remote Hours',
        current_usage_rate: 'Current usage:',
        daily_log: 'Daily Log',
        date: 'Date',
        start: 'Start',
        end: 'End',
        pause_min: 'Break (min)',
        remote_h: 'Remote (h)',
        log_worktime: 'Log remote work',
        day_history: 'Day History',
        no_entries: 'No entries yet',
        settings: 'Settings',
        set: 'Set',
        indiv_quote: 'Individual Quota (%)',
        month_switch: 'Close Month',
        history: 'History',
        delete: 'Delete',
        edit: 'Edit',
        confirm_delete: 'Really delete?',
        confirm_month_switch: 'Really close month?',
        fill_required: 'Please fill all required fields',
        export_label: 'Export:',
        pdf_import: 'PDF Import',
        pdf_import_desc: 'Upload a PDF file with timestamps. Work hours will be extracted automatically and added to the daily history.',
        analyze: 'Analyze',
        cancel: 'Cancel',
        import_sessions: 'Import',
        actual_remote_quota: 'Actual RQ',
        delete_all: 'Delete All Entries',
        confirm_delete_all: 'WARNING: Do you really want to delete ALL entries? A backup will be created automatically.',
        backup_created: 'Backup created',
        delete_month: 'Delete Month',
        confirm_delete_month: 'Do you really want to delete this month from the history?',
        view_current_month: '→ Current Month',
        clear_all_history: 'Clear All History',
        show_month: 'Show month:', restore: 'Restore',
        confirm_restore: 'Restore backup? The current data will be replaced.',
        final_report: 'Final Report', print: 'Print', close: 'Close',
        report_empty: 'No closed months yet.',
        report_overall: 'Total', report_quarter_incomplete: 'incomplete', report_months: 'months',
        report_months_over: 'months over limit', report_limit: 'Limit', report_quota: 'Quota',
        rating_good: 'Good: within the limit', rating_tight: 'Tight (above 90 % of the limit)',
        rating_exceeded: 'Exceeded', over_quota_hint: 'Remote limit exceeded',
        report_rule: 'Rating per quarter: up to 90 % of the remote limit good, up to 100 % tight, above that exceeded.',
        confirm_clear_all_history: 'WARNING: Do you really want to clear the COMPLETE history? All months and entries will be deleted and reset to the current month.',
        shutdown_server: 'Shutdown Server',
        confirm_shutdown: 'Do you really want to shutdown the server? The app will close.',
        shutdown_success: 'Server is shutting down...'
    }
};

function currentLang(){ return (trackerState && trackerState.language) || 'de'; }
function t(key){ const lang=currentLang(); return (translations[lang] && translations[lang][key]) || key; }

function locale(){ return currentLang()==='de' ? 'de-DE' : 'en-GB'; }

function updateUILanguage(){
    document.documentElement.lang = currentLang();
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (key) el.textContent = t(key);
    });
    document.querySelectorAll('[data-i18n-aria]').forEach(el => el.setAttribute('aria-label', t(el.getAttribute('data-i18n-aria'))));
    document.querySelectorAll('[data-i18n-title]').forEach(el => el.setAttribute('title', t(el.getAttribute('data-i18n-title'))));
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => el.setAttribute('placeholder', t(el.getAttribute('data-i18n-placeholder'))));
    const btn = document.getElementById('lang-toggle');
    if (btn) btn.textContent = currentLang()==='de' ? '🇬🇧' : '🇩🇪';
    if (!editingEntryId) { const sb = document.getElementById('submit-btn'); if (sb) sb.textContent = t('log_worktime'); }
    syncViewSelectors(true);
}

// Month names are stored in German; show them in the language of the UI.
function monthLabel(name){
    const n = MONTH_NUMBERS[name];
    return n ? new Intl.DateTimeFormat(locale(), {month: 'long'}).format(new Date(2000, n - 1, 1)) : name;
}
function dateLabel(iso){
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
    if (!m) return iso || '';
    return new Intl.DateTimeFormat(locale(), {weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric'}).format(new Date(+m[1], +m[2] - 1, +m[3]));
}

async function toggleLanguage(){
    const newLang = currentLang()==='de' ? 'en' : 'de';
    try{
        const res = await fetch('/api/language', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({language:newLang})});
        const result = await res.json();
        if(result.success){
            trackerState = result.state;
            updateUILanguage();
            updateUI();
        }
    }catch(e){ showMessage(t('err_toggle'), 'error'); }
}

async function loadState() {
    const res = await fetch('/api/state');
    trackerState = await res.json();
    applyDarkMode();
    updateUILanguage();
    updateUI();
}

// Theme: the stored setting wins (dark_mode=true, or light chosen explicitly by this user);
// without any choice the system setting (prefers-color-scheme) decides.
function themeChosen(){ try { return localStorage.getItem('rw-theme-chosen') === '1'; } catch (e) { return false; } }
function isDarkTheme(){
    if (trackerState && trackerState.dark_mode) return true;
    if (themeChosen()) return false;
    return !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
}
function applyDarkMode() {
    const dark = isDarkTheme();
    const root = document.documentElement;
    root.classList.toggle('dark-mode', dark);
    root.classList.toggle('light-mode', !dark);
    const btn = document.getElementById('dark-toggle');
    if (btn) btn.setAttribute('aria-pressed', dark ? 'true' : 'false');
    const icon = document.getElementById('dark-icon');
    if (icon) icon.textContent = dark ? '☀️' : '🌙';
}

async function toggleDarkMode() {
    const newDarkMode = !isDarkTheme();
    try { localStorage.setItem('rw-theme-chosen', '1'); } catch (e) { }
    try {
        const res = await fetch('/api/darkmode', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({darkMode: newDarkMode})});
        const result = await res.json();
        if (result.success) {
            trackerState = result.state;
            applyDarkMode();
            showMessage(result.message, 'info');
        }
    } catch (e) {
        showMessage(t('err_toggle'), 'error');
    }
}

// Toasts: fixed at the bottom, announced to screen readers, with a close button.
// Errors stay for 10 s (others 5 s). While a dialog is open the toast is shown inside it (the page behind is inert).
function showMessage(message, type = 'success') {
    const open = document.querySelector('dialog[open] .toast-region');
    const region = open || document.getElementById('toast-region');
    if (!region) return;
    const toast = document.createElement('div');
    const isError = type === 'error';
    toast.className = `toast toast-${colorFor(type)}`;
    toast.setAttribute('role', isError ? 'alert' : 'status');
    toast.setAttribute('aria-live', isError ? 'assertive' : 'polite');
    const text = document.createElement('span');
    text.className = 'flex-1';
    text.textContent = message;
    const close = document.createElement('button');
    close.type = 'button';
    close.setAttribute('aria-label', t('toast_close'));
    close.textContent = '×';
    toast.append(text, close);
    const remove = () => { if (toast.parentNode) toast.parentNode.removeChild(toast); };
    close.addEventListener('click', remove);
    while (region.children.length >= 3) region.removeChild(region.firstChild);
    region.appendChild(toast);
    setTimeout(remove, isError ? 10000 : 5000);
}
function colorFor(type){ return ({success: 'success', error: 'error', warning: 'warning', info: 'info'})[type] || 'info'; }

// Native <dialog> helpers: showModal() gives Escape, a focus trap and an inert page; the focus goes back to the opener.
const dialogOpeners = new WeakMap();
function openDialog(id){
    const d = document.getElementById(id);
    if (!d || d.open) return;
    dialogOpeners.set(d, document.activeElement);
    d.showModal();
}
function restoreFocus(d){
    const el = dialogOpeners.get(d);
    if (el && el.isConnected && typeof el.focus === 'function') el.focus();
}
document.addEventListener('close', ev => { if (ev.target && ev.target.tagName === 'DIALOG') restoreFocus(ev.target); }, true);

// Replacement for window.confirm(): resolves to true (confirm) or false (cancel, Escape).
function confirmDialog(message, danger = true){
    return new Promise(resolve => {
        const d = document.getElementById('confirm-dialog');
        document.getElementById('confirm-text').textContent = message;
        const ok = document.getElementById('confirm-ok');
        const cancel = document.getElementById('confirm-cancel');
        ok.className = 'btn ' + (danger ? 'btn-error' : 'btn-primary');
        let result = false;
        const finish = () => { ok.onclick = cancel.onclick = null; d.removeEventListener('close', finish); resolve(result); };
        ok.onclick = () => { result = true; d.close(); };
        cancel.onclick = () => { result = false; d.close(); };
        d.addEventListener('close', finish);
        dialogOpeners.set(d, document.activeElement);
        d.showModal();
        cancel.focus();
    });
}

// Loading state for a button: disabled, aria-busy and a spinner while the work runs.
async function withBusy(btn, work){
    if (!btn) return work();
    const html = btn.innerHTML;
    btn.disabled = true;
    btn.setAttribute('aria-busy', 'true');
    const sp = document.createElement('span');
    sp.className = 'spinner';
    sp.setAttribute('aria-hidden', 'true');
    btn.prepend(sp);
    try { return await work(); }
    finally { btn.disabled = false; btn.removeAttribute('aria-busy'); btn.innerHTML = html; }
}

function handleBackupClick(link){
    showMessage(t('backup_running'), 'info');
    link.setAttribute('aria-busy', 'true');
    setTimeout(() => link.removeAttribute('aria-busy'), 1500);
    const menu = document.getElementById('export-menu');
    if (menu) menu.open = false;
}
document.addEventListener('click', ev => {
    const menu = document.getElementById('export-menu');
    if (menu && menu.open && !menu.contains(ev.target)) menu.open = false;
});
document.addEventListener('keydown', ev => {
    const menu = document.getElementById('export-menu');
    if (ev.key === 'Escape' && menu && menu.open) { menu.open = false; menu.querySelector('summary').focus(); }
});

async function handlePdfUpload() {
    const fileInput = document.getElementById('pdf-file-input');
    if (!fileInput.files.length) {
        showMessage(t('err_pdf_pick'), 'error');
        return;
    }

    // Start every analysis from a clean slate. Otherwise a failed analysis would leave the
    // sessions of the PREVIOUS statement (and the import button) in place, and clicking
    // "Importieren" would load the old statement again instead of the new one.
    extractedPdfSessions = [];
    extractedFlexBalance = null;
    document.getElementById('pdf-import-btn').style.display = 'none';
    document.getElementById('pdf-analysis-result').style.display = 'none';

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    const analyzeBtn = document.getElementById('pdf-analyze-btn');
    try {
      await withBusy(analyzeBtn, async () => {
        const res = await fetch('/api/pdf/analyze', {method: 'POST', body: formData});
        const result = await res.json();

        if (result.success) {
            extractedPdfSessions = result.sessions;
            extractedFlexBalance = result.flex_balance || null;
            displayPdfSessions(result.sessions);
            document.getElementById('pdf-import-btn').style.display = 'block';
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message, 'error');
        }
      });
    } catch (e) {
        showMessage(t('err_pdf_upload') + e, 'error');
    }
}

function displayPdfSessions(sessions) {
    const list = document.getElementById('pdf-sessions-list');
    document.getElementById('pdf-analysis-result').style.display = 'block';

    if (sessions.length === 0) {
        list.innerHTML = '<li>' + escapeHtml(t('no_periods')) + '</li>';
        return;
    }

    list.innerHTML = sessions.map(s => `
        <li class="pl-3" style="border-left: 4px solid var(--primary)">
            <strong>${escapeHtml(s.date)}</strong>: ${escapeHtml(s.start_time)} - ${escapeHtml(s.end_time)}
            ${s.is_remote ? ' <span class="badge badge-remote">Remote</span>' : ''}
        </li>
    `).join('');
}

async function handlePdfImport() {
    if (!extractedPdfSessions.length) {
        showMessage(t('err_no_sessions'), 'error');
        return;
    }

    try {
      await withBusy(document.getElementById('pdf-import-btn'), async () => {
        const res = await fetch('/api/pdf/import', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({sessions: extractedPdfSessions, flex_balance: extractedFlexBalance})
        });
        const result = await res.json();

        if (result.success) {
            trackerState = result.state;
            updateUI();
            closePdfModal();
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message, 'error');
        }
      });
    } catch (e) {
        showMessage(t('err_import') + e, 'error');
    }
}

function closePdfModal() {
    { const dlg = document.getElementById('pdf-import-modal'); if (dlg.open) dlg.close(); }
    document.getElementById('pdf-file-input').value = '';
    document.getElementById('pdf-analysis-result').style.display = 'none';
    document.getElementById('pdf-import-btn').style.display = 'none';
    extractedPdfSessions = [];
    extractedFlexBalance = null;
}

async function handleProtokoll() {
    const remoteInput = document.getElementById('input-remote').value.trim();
    const data = {
        datum: document.getElementById('input-date').value,
        start: document.getElementById('input-start').value,
        end: document.getElementById('input-end').value,
        pause: document.getElementById('input-pause').value,
        remote: remoteInput === '' ? '' : remoteInput
    };

    if (!data.datum || !data.start || !data.end) {
        showMessage(t('fill_required'), 'error');
        return;
    }

    try {
        const isEditing = !!editingEntryId;
        const url = isEditing ? `/api/update/${editingEntryId}` : '/api/protokoll';
        const method = isEditing ? 'PUT' : 'POST';
        const res = await fetch(url, {method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
        const result = await res.json();

        if (result.success) {
            trackerState = result.state;
            updateUI();
            if (isEditing) cancelEdit();
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (e) {
        showMessage(t('err_save'), 'error');
    }
}

async function handleDelete(entryId) {
    if (!(await confirmDialog(t('confirm_delete')))) return;
    try {
        const res = await fetch(`/api/delete/${entryId}`, {method: 'DELETE'});
        const result = await res.json();
        if (result.success) {
            trackerState = result.state;
            updateUI();
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (e) {
        showMessage(t('err_delete'), 'error');
    }
}

function setEditMode(rec){
    editingEntryId = rec.id;
    document.getElementById('input-date').value = rec.datum || '';
    document.getElementById('input-start').value = rec.startTime || '';
    document.getElementById('input-end').value = rec.endTime || '';
    document.getElementById('input-pause').value = rec.pauseMinutes ?? 0;

    const remoteValue = rec.remoteStundenHeute;
    const totalValue = rec.totalStundenHeute;

    if (remoteValue !== undefined && totalValue !== undefined && 
        Math.abs(remoteValue - totalValue) < 0.01) {
        document.getElementById('input-remote').value = '';
    } else if (remoteValue !== undefined) {
        document.getElementById('input-remote').value = remoteValue;
    } else {
        document.getElementById('input-remote').value = '';
    }

    document.getElementById('submit-btn').textContent = t('update_entry');
    document.getElementById('cancel-edit-btn').classList.remove('hidden');
    document.getElementById('edit-mode-hint').classList.remove('hidden');
}

function cancelEdit(){
    editingEntryId = null;
    document.getElementById('submit-btn').textContent = t('log_worktime');
    document.getElementById('cancel-edit-btn').classList.add('hidden');
    document.getElementById('edit-mode-hint').classList.add('hidden');
    document.getElementById('input-remote').value = '';
}

function findRecordById(id){
    const dr = (trackerState && trackerState.daily_records) || {};
    for (const v of Object.values(dr)){
        const arr = Array.isArray(v) ? v : (v && typeof v==='object' ? [v] : []);
        for (const r of arr){ if (r && r.id === id) return r; }
    }
    return null;
}

function handleEdit(id){
    const rec = findRecordById(id);
    if (!rec){ showMessage(t('err_not_found'), 'error'); return; }
    setEditMode(rec);
    showMessage(t('editing'), 'info');
}

async function handleQuoteUpdate() {
    const quote = document.getElementById('input-quote').value;
    try {
        const res = await fetch('/api/quote', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({quote: quote})});
        const result = await res.json();
        if (result.success) {
            trackerState = result.state;
            updateUI();
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (e) {
        showMessage(t('err_generic'), 'error');
    }
}

async function handleSollstundenUpdate() {
    const sollStunden = document.getElementById('input-sollstunden').value;
    try {
        const res = await fetch('/api/sollstunden', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({sollStunden: sollStunden})});
        const result = await res.json();
        if (result.success) {
            trackerState = result.state;
            updateUI();
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (e) {
        showMessage(t('err_generic'), 'error');
    }
}

async function handleMonthSwitch() {
    if (!(await confirmDialog(t('confirm_month_switch'), false))) return;
    try {
        const res = await fetch('/api/month/switch', {method: 'POST', headers: {'Content-Type': 'application/json'}});
        const result = await res.json();
        if (result.success) {
            trackerState = result.state;
            updateUI();
            showMessage(result.message, result.quartal_msg ? 'warning' : 'success');
        } else {
            showMessage(result.message || t('err_generic'), 'error');
        }
    } catch (e) {
        showMessage(t('err_month_switch'), 'error');
    }
}

async function handleDeleteAllEntries() {
    if (!(await confirmDialog(t('confirm_delete_all')))) return;

    try {
        // Erst Backup erstellen
        const backupRes = await fetch('/api/backup');
        const backupData = await backupRes.json();

        // Backup als JSON-Datei herunterladen
        const backupBlob = new Blob([JSON.stringify(backupData, null, 2)], {type: 'application/json'});
        const backupUrl = window.URL.createObjectURL(backupBlob);
        const backupLink = document.createElement('a');
        backupLink.href = backupUrl;
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        backupLink.download = `backup_before_delete_${timestamp}.json`;
        document.body.appendChild(backupLink);
        backupLink.click();
        document.body.removeChild(backupLink);
        window.URL.revokeObjectURL(backupUrl);

        showMessage(t('backup_created') + ': backup_before_delete_' + timestamp + '.json', 'success');

        // Kurz warten damit Benutzer Backup-Bestätigung sieht
        await new Promise(resolve => setTimeout(resolve, 1500));

        // Jetzt alle Einträge löschen
        const deleteRes = await fetch('/api/delete_all_entries', {method: 'POST', headers: {'Content-Type': 'application/json'}});
        const result = await deleteRes.json();

        if (result.success) {
            trackerState = result.state;
            updateUI();
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (e) {
        showMessage(t('err_delete_all') + e, 'error');
    }
}

async function handleDeleteMonth(monthName, year) {
    if (!(await confirmDialog(t('confirm_delete_month')))) return;

    try {
        const res = await fetch(`/api/delete_month/${encodeURIComponent(monthName)}/${year}`, {method: 'DELETE'});
        const result = await res.json();

        if (result.success) {
            trackerState = result.state;
            updateUI();
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (e) {
        showMessage(t('err_delete_month') + e, 'error');
    }
}

async function handleClearAllHistory() {
    if (!(await confirmDialog(t('confirm_clear_all_history')))) return;

    try {
        // Create backup first
        const backupRes = await fetch('/api/backup');
        const backupData = await backupRes.json();

        // Download backup as JSON file
        const backupBlob = new Blob([JSON.stringify(backupData, null, 2)], {type: 'application/json'});
        const backupUrl = window.URL.createObjectURL(backupBlob);
        const backupLink = document.createElement('a');
        backupLink.href = backupUrl;
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        backupLink.download = `backup_before_clear_all_${timestamp}.json`;
        document.body.appendChild(backupLink);
        backupLink.click();
        document.body.removeChild(backupLink);
        window.URL.revokeObjectURL(backupUrl);

        showMessage(t('backup_created') + ': backup_before_clear_all_' + timestamp + '.json', 'success');

        // Wait briefly so user sees backup confirmation
        await new Promise(resolve => setTimeout(resolve, 1500));

        // Now clear all history
        const clearRes = await fetch('/api/clear_all_history', {method: 'POST', headers: {'Content-Type': 'application/json'}});
        const result = await clearRes.json();

        if (result.success) {
            trackerState = result.state;
            updateUI();
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (e) {
        showMessage(t('err_clear_history') + e, 'error');
    }
}

async function handleShutdown() {
    if (!(await confirmDialog(t('confirm_shutdown'), false))) return;
    try {
        const tokenMeta = document.querySelector('meta[name="rw-shutdown-token"]');
        const res = await fetch('/api/shutdown', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-RW-Token': tokenMeta ? tokenMeta.content : ''
            }
        });
        if (!res.ok) {
            // The server refused (wrong token, not a local request, ...): it is still running.
            showMessage(t('err_shutdown') + res.status + ').', 'error');
            return;
        }
        showMessage(t('shutdown_success'), 'success');
        setTimeout(() => {
            showServerStopped();
        }, 500);
    } catch (e) {
        // No answer at all: the server went away while we were waiting.
        showMessage(t('shutdown_success'), 'success');
        setTimeout(() => {
            showServerStopped();
        }, 500);
    }
}

function showServerStopped() {
    document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;background:#111827;color:#E6E9EF;"><div style="text-align:center;"><h1></h1><p></p></div></div>';
    document.querySelector('body h1').textContent = t('server_stopped');
    document.querySelector('body p').textContent = t('server_stopped_hint');
}

async function handleViewCurrentMonth() {
    try {
        const response = await fetch('/api/view/current_month', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });

        const result = await response.json();
        if (result.success) {
            trackerState = result.state;
            updateUI();
            showMessage(result.message);
        } else {
            showMessage(result.message || t('err_generic'), 'error');
        }
    } catch (error) {
        showMessage(t('err_current_month'), 'error');
    }
}

// Progress bar (div role=progressbar): no canvas, so it always fits the width; the label sits OUTSIDE the bar.
function drawRemoteChart() {
    const bar = document.getElementById('remote-chart');
    const fill = document.getElementById('remote-chart-fill');
    const label = document.getElementById('remote-chart-label');
    if (!bar || !fill) return;
    if (!trackerState || !trackerState.current_month_data) return;

    const data = trackerState.current_month_data;
    const maxRemote = parseFloat(data.max_remote_stunden) || 1;
    const istRemote = parseFloat(data.ist_remote_stunden_laufend) || 0;
    const usedRaw = (istRemote / maxRemote) * 100;
    const usedPercentage = Math.min(usedRaw, 100);
    const over = usedRaw > 100;
    const status = over ? 'err' : (maxRemote - istRemote < 10 ? 'warn' : 'ok');

    fill.style.width = usedPercentage.toFixed(2) + '%';
    fill.className = 'bar-fill bar-' + status;
    bar.setAttribute('aria-valuenow', usedPercentage.toFixed(2));
    const text = `${istRemote.toFixed(2)}h / ${maxRemote.toFixed(2)}h (${usedRaw.toFixed(2)}%)`;
    bar.setAttribute('aria-valuetext', text);
    if (label) label.textContent = over ? `${text} · ⚠ ${t('over_limit')}` : text;
}

function renderFlexBalance(flex) {
    const box = document.getElementById('flex-balance-box');
    if (!box) return;
    const fmt = v => (v > 0 ? '+' : '') + v.toFixed(2) + 'h';
    const parts = [];
    if (flex && typeof flex.current === 'number') parts.push(`${fmt(flex.current)}`);
    if (flex && typeof flex.total === 'number') parts.push(`Σ ${fmt(flex.total)}`);
    box.classList.toggle('hidden', parts.length === 0);
    const out = document.getElementById('display-flex-balance');
    if (out) out.textContent = parts.join('  ');
}

function updateUI() {
    if (!trackerState) {
        return;
    }

    const data = trackerState.current_month_data;

    // Berechne tatsächliche Remote-Quote (Monat)
    const actualRemoteQuota = data.soll_stunden_gesamt > 0
        ? (data.ist_remote_stunden_laufend / data.soll_stunden_gesamt * 100)
        : 0;

    // Use view_month and view_year from state
    const displayMonth = trackerState.view_month || trackerState.aktueller_monat;
    const displayYear = trackerState.view_year || trackerState.aktuelles_jahr;

    // Quarter of the month being viewed (current_quartal belongs to the open month)
    const displayMonthNum = MONATS_NUMMERN[displayMonth] || 1;
    const displayQuartal = `Q${Math.ceil(displayMonthNum / 3)}/${displayYear}`;

    document.getElementById('display-month').textContent =
        `${monthLabel(displayMonth)} ${displayYear} | ${t('quarter_word')}: ${displayQuartal} | ${t('month_quote')}: ${Number(data.individuelle_quote).toFixed(2)}% (${t('actual_short')}: ${actualRemoteQuota.toFixed(2)}%)`;

    syncViewSelectors();

    // Show/hide "Current Month" button
    const isCurrentMonth = (trackerState.view_month === trackerState.aktueller_monat &&
                            trackerState.view_year === trackerState.aktuelles_jahr);
    const currentMonthBtn = document.getElementById('btn-current-month');
    if (currentMonthBtn) {
        if (isCurrentMonth) {
            currentMonthBtn.classList.add('hidden');
        } else {
            currentMonthBtn.classList.remove('hidden');
        }
    }

    document.getElementById('display-soll').textContent = `${data.soll_stunden_gesamt.toFixed(2)}h`;
    document.getElementById('display-max-remote').textContent = `${data.max_remote_stunden.toFixed(2)}h`;
    document.getElementById('display-ist-remote').textContent = `${data.ist_remote_stunden_laufend.toFixed(2)}h`;
    renderFlexBalance(trackerState && trackerState.gleitzeit_saldo);

    const rawVerbleibend = (data.max_remote_stunden || 0) - (data.ist_remote_stunden_laufend || 0);
    const verbleibendEl = document.getElementById('display-verbleibend');
    const displayVerbleibend = Math.max(0, rawVerbleibend);
    verbleibendEl.textContent = `${displayVerbleibend.toFixed(2)}h`;

    if (rawVerbleibend < 0) {
        verbleibendEl.className = 'kpi kpi-err';
    } else if (rawVerbleibend < 10) {
        verbleibendEl.className = 'kpi kpi-warn';
    } else {
        verbleibendEl.className = 'kpi kpi-ok';
    }

    const aktuelleQuote = data.max_remote_stunden > 0 ? (data.ist_remote_stunden_laufend / data.max_remote_stunden * 100) : 0;
    document.getElementById('display-aktuelle-quote').textContent = `${aktuelleQuote.toFixed(2)}%`;

    document.getElementById('input-sollstunden').value = trackerState.soll_stunden_pro_tag;
    document.getElementById('input-quote').value = trackerState.individuelle_quote_prozent;

    const recordList = document.getElementById('daily-record-list');
    const dr = trackerState.daily_records || {};
    let records = [];
    Object.values(dr).forEach(v => {
        if (Array.isArray(v)) records.push(...v);
        else if (v && typeof v === 'object') records.push(v);
    });

    // Filter records by view_month and view_year
    const viewMonthNum = MONATS_NUMMERN[trackerState.view_month] || 1;
    const viewYear = trackerState.view_year || trackerState.aktuelles_jahr;
    records = records.filter(r => {
        if (!r.datum) return false;
        const d = new Date(r.datum);
        return d.getFullYear() === viewYear && (d.getMonth() + 1) === viewMonthNum;
    });

    if (records.length === 0) {
        recordList.innerHTML = '<li class="p-4 text-center"><p class="font-semibold">' + escapeHtml(t('no_entries')) + '</p><p class="text-sm muted mt-1">' + escapeHtml(t('empty_entries_hint')) + '</p></li>';
    } else {
        records.sort((a, b) => {
            const d = b.datum.localeCompare(a.datum);
            if (d !== 0) return d;
            return (a.startTime||'').localeCompare(b.startTime||'');
        });
        recordList.innerHTML = records.map(r => {
            const rid = escapeHtml(r.id || (r.datum + '|' + (r.startTime||'') + '|' + (r.endTime||'')));
            return `
            <li class="p-3">
                <div class="flex flex-wrap justify-between items-start gap-3">
                    <div class="min-w-0">
                        <p class="font-bold">${escapeHtml(dateLabel(r.datum))}</p>
                        <p class="text-sm muted">
                            ${escapeHtml(r.startTime)} - ${escapeHtml(r.endTime)} (${t('pause_word')}: ${Number(r.pauseMinutes).toFixed(0)}min)
                        </p>
                        <p class="text-sm font-medium">
                            ${t('remote_word')}: ${Number(r.remoteStundenHeute).toFixed(2)}h | ${t('total_word')}: ${Number(r.totalStundenHeute).toFixed(2)}h
                        </p>
                        ${r.source === 'pdf_import' ? `<p class="mt-1"><span class="badge badge-info">📄 ${t('pdf_import_badge')}</span></p>` : ''}
                        ${r.pauseWarning && r.source !== 'pdf_import' ? `<p class="text-xs warn-text mt-1">⚠ ${escapeHtml(r.pauseWarning)}</p>` : ''}
                    </div>
                    <div class="flex items-center gap-3">
                        <button type="button" onclick="handleEdit('${rid}')" class="btn btn-warning btn-sm">${t('edit')}</button>
                        <button type="button" onclick="handleDelete('${rid}')" class="btn btn-outline-danger btn-sm ml-2">${t('delete')}</button>
                    </div>
                </div>
            </li>`;
        }).join('');
    }

    const historyList = document.getElementById('history-list');
    const history = trackerState.monatliche_historie || [];

    if (history.length === 0) {
        historyList.innerHTML = '<li class="p-4 text-center"><p class="font-semibold">' + escapeHtml(t('no_history')) + '</p><p class="text-sm muted mt-1">' + escapeHtml(t('empty_history_hint')) + '</p></li>';
    } else {
        historyList.innerHTML = sortedHistory(history).map(m => {
            // Berechne tatsächliche Remote-Quote falls nicht vorhanden
            const tatsaechlicheQuote = m.tatsaechliche_remote_quote ||
                (m.soll_stunden_gesamt > 0 ? (m.ist_remote_stunden_laufend / m.soll_stunden_gesamt * 100) : 0);

            // Zeige Quartals-Quote nur wenn vorhanden
            const quartalQuoteHtml = m.quartal_quote !== undefined ? `
                <p class="text-sm font-semibold accent mt-2 pt-2" style="border-top: 1px solid var(--border)">
                    ${escapeHtml(m.quartal)}: ${t('quarter_quote')}: ${Number(m.quartal_quote).toFixed(2)}%
                    (${Number(m.quartal_remote).toFixed(2)}h / ${Number(m.quartal_soll).toFixed(2)}h)
                </p>
            ` : '';

            const over = isOverQuota(m);
            return `
            <li class="p-3${over ? ' over-quota' : ''}"${over ? ` data-over-quota="true" title="${t('over_quota_hint')}"` : ''}>
                <div class="flex flex-wrap items-center gap-2">
                    <p class="font-bold">${escapeHtml(monthLabel(m.monat))} ${m.jahr} <span class="text-sm font-semibold accent">(${escapeHtml(m.quartal || 'Q?')})</span></p>
                    ${over ? `<span class="badge badge-over"><span aria-hidden="true">⚠</span> ${t('over_limit')}</span>` : ''}
                </div>
                <p class="text-sm muted">
                    ${t('quote_word')}: ${Number(m.individuelle_quote).toFixed(2)}% |
                    ${t('actual_remote_quota')}: ${Number(tatsaechlicheQuote).toFixed(2)}%
                </p>
                <p class="text-sm">
                    ${t('remote_word')}: ${Number(m.ist_remote_stunden_laufend).toFixed(2)}h / ${Number(m.max_remote_stunden).toFixed(2)}h
                </p>
                <p class="text-sm">
                    ${t('total_word')}: ${Number(m.ist_arbeitszeit_laufend).toFixed(2)}h / ${Number(m.soll_stunden_gesamt).toFixed(2)}h
                </p>
                ${quartalQuoteHtml}
                <div class="mt-3">
                    <button type="button" onclick="handleDeleteMonth('${escapeHtml(m.monat)}', ${m.jahr})" class="btn btn-outline-danger btn-sm" data-i18n="delete_month">${t('delete_month')}</button>
                </div>
            </li>
        `}).join('');
    }

    drawRemoteChart();
}

const MONTH_NUMBERS = {Januar:1, Februar:2, 'März':3, April:4, Mai:5, Juni:6, Juli:7, August:8, September:9, Oktober:10, November:11, Dezember:12};

// Same rules as services/final_report.py: newest month first, over quota when remote > limit (2 decimals).
function sortedHistory(history) {
    return history.slice().sort((a, b) =>
        (b.jahr - a.jahr) || ((MONTH_NUMBERS[b.monat] || 0) - (MONTH_NUMBERS[a.monat] || 0)));
}

function isOverQuota(m) {
    return Number(m.ist_remote_stunden_laufend || 0).toFixed(2) * 1 > Number(m.max_remote_stunden || 0).toFixed(2) * 1;
}

function escapeHtml(v) {
    return String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function renderFinalReport(report) {
    const f = v => Number(v).toFixed(2);
    if (!report.quarters.length) return `<p class="text-sm muted">${t('report_empty')}</p>`;
    const o = report.overall;
    const quarters = report.quarters.map(q => `
        <section class="mb-4 rounded-xl overflow-hidden" style="border: 1px solid var(--border)" data-quartal="${escapeHtml(q.quartal)}" data-rating="${q.rating}">
            <div class="flex flex-wrap justify-between items-center p-3 rating-${q.rating}">
                <h3 class="font-extrabold">${escapeHtml(q.quartal)}${q.complete ? '' : ` <span class="text-xs font-semibold">(${t('report_quarter_incomplete')}: ${q.month_count}/3)</span>`}</h3>
                <span class="font-bold">${t('rating_' + q.rating)}</span>
            </div>
            <p class="px-3 pt-2 text-sm">
                Remote ${f(q.remote)}h / ${t('report_limit')} ${f(q.max_remote)}h (${Math.round(q.usage * 100)} %) |
                ${t('report_quota')} ${f(q.actual_quote)}% | ${q.months_over} ${t('report_months_over')}
            </p>
            <ul class="p-3 text-sm">
                ${q.months.map(m => `<li class="flex flex-wrap justify-between gap-x-3 py-1 px-2 rounded${m.over ? ' over-quota' : ''}">
                    <span>${escapeHtml(monthLabel(m.monat))} ${m.jahr}${m.over ? ` <span class="badge badge-over"><span aria-hidden="true">⚠</span> ${t('over_limit')}</span>` : ''}</span>
                    <span>Remote ${f(m.remote)}h / ${f(m.max_remote)}h | ${f(m.actual_quote)}%</span></li>`).join('')}
            </ul>
        </section>`).join('');
    return `
        <div class="mb-4 p-3 rounded-xl rating-${o.rating}" data-overall-rating="${o.rating}">
            <p class="font-extrabold">${t('report_overall')}: ${t('rating_' + o.rating)}</p>
            <p class="text-sm">${o.months} ${t('report_months')}, ${o.quarters} Q | Remote ${f(o.remote)}h / ${t('report_limit')} ${f(o.max_remote)}h | ${t('report_quota')} ${f(o.actual_quote)}% | ${o.months_over} ${t('report_months_over')}</p>
        </div>
        ${quarters}
        <p class="text-xs muted">${t('report_rule')}</p>`;
}

async function handleFinalReport() {
    try {
        const res = await fetch('/api/report/final');
        const data = await res.json();
        document.getElementById('final-report-body').innerHTML = renderFinalReport(data.report);
        openDialog('final-report-modal');
    } catch (e) {
        showMessage(t('err_report') + e, 'error');
    }
}

function closeFinalReport() {
    { const dlg = document.getElementById('final-report-modal'); if (dlg.open) dlg.close(); }
}

// Local calendar date (YYYY-MM-DD). toISOString() would give the UTC date: yesterday shortly after midnight.
function localToday() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// B4: choose any month to look at (entries and totals of that month)
function syncViewSelectors(relabel) {
    const monthSel = document.getElementById('view-month-select');
    const yearSel = document.getElementById('view-year-select');
    if (!monthSel || !yearSel || !trackerState) return;
    if (!monthSel.options.length) {
        Object.keys(MONTH_NUMBERS).forEach(m => monthSel.add(new Option(monthLabel(m), m)));
    } else if (relabel) {
        Array.from(monthSel.options).forEach(o => { o.textContent = monthLabel(o.value); });
    }
    const years = new Set([2025, 2026, 2027, 2028, 2029, 2030, trackerState.view_year, trackerState.aktuelles_jahr]);
    (trackerState.monatliche_historie || []).forEach(h => years.add(h.jahr));
    const sorted = [...years].sort((a, b) => a - b);
    if (yearSel.options.length !== sorted.length) {
        yearSel.innerHTML = '';
        sorted.forEach(y => yearSel.add(new Option(String(y), String(y))));
    }
    if (trackerState.view_month) monthSel.value = trackerState.view_month;
    yearSel.value = String(trackerState.view_year);
}

async function handleViewMonthChange() {
    const month = document.getElementById('view-month-select').value;
    const year = parseInt(document.getElementById('view-year-select').value, 10);
    try {
        const res = await fetch('/api/view/month', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({month, year})});
        const result = await res.json();
        if (result.success) {
            trackerState = result.state;
            updateUI();
        } else {
            showMessage(result.message || t('err_generic'), 'error');
        }
    } catch (e) {
        showMessage(t('err_view_month') + e, 'error');
    }
}

// B3: restore a JSON backup from the UI (the API existed, the button did not)
async function handleRestoreFile(input) {
    const file = input.files && input.files[0];
    input.value = '';
    if (!file || !(await confirmDialog(t('confirm_restore'), false))) return;
    try {
      await withBusy(document.getElementById('restore-btn'), async () => {
        const fd = new FormData();
        fd.append('file', file);
        const res = await fetch('/api/restore', {method: 'POST', body: fd});
        const result = await res.json();
        if (result.success) {
            trackerState = result.state;
            updateUI();
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message || t('err_generic'), 'error');
        }
      });
    } catch (e) {
        showMessage(t('err_restore') + e, 'error');
    }
}

applyDarkMode();   // before the state arrives: stored choice or system setting
if (window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onSchemeChange = () => { applyDarkMode(); };
    if (mq.addEventListener) mq.addEventListener('change', onSchemeChange);
}

window.addEventListener('DOMContentLoaded', () => {
    loadState();
    const today = localToday();
    document.getElementById('input-date').value = today;
});
