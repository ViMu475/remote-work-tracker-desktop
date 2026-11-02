let trackerState = null;
let editingEntryId = null;
let extractedPdfSessions = [];

const MONATS_NUMMERN = {
    "Januar": 1, "Februar": 2, "März": 3, "April": 4, "Mai": 5, "Juni": 6,
    "Juli": 7, "August": 8, "September": 9, "Oktober": 10, "November": 11, "Dezember": 12
};

const translations = {
    de: {
        app_title: 'Remote Work Quote Tracker',
        dark_mode: '🌙 Dark Mode',
        monthly_overview: 'Aktuelle Monatsübersicht',
        rq_progress: 'Remote-Quote Fortschritt',
        soll_arbeitszeit: 'Soll-Arbeitszeit',
        max_remote: 'Max. Remote',
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
        show_month: 'Monat anzeigen:', restore: '♻️ Wiederherstellen',
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
        dark_mode: '🌙 Dark Mode',
        monthly_overview: 'Current Month Overview',
        rq_progress: 'Remote Quota Progress',
        soll_arbeitszeit: 'Target Hours',
        max_remote: 'Max Remote',
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
        show_month: 'Show month:', restore: '♻️ Restore',
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

function updateUILanguage(){
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (key) el.textContent = t(key);
    });
    const btn = document.getElementById('lang-toggle');
    if (btn) btn.textContent = currentLang()==='de' ? '🇬🇧' : '🇩🇪';
}

async function toggleLanguage(){
    const newLang = currentLang()==='de' ? 'en' : 'de';
    try{
        const res = await fetch('/api/language', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({language:newLang})});
        const result = await res.json();
        if(result.success){
            trackerState = result.state;
            updateUI();
            updateUILanguage();
        }
    }catch(e){ }
}

async function loadState() {
    const res = await fetch('/api/state');
    trackerState = await res.json();
    updateUI();
    applyDarkMode();
    updateUILanguage();
}

function applyDarkMode() {
    if (trackerState && trackerState.dark_mode) {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }
}

async function toggleDarkMode() {
    const newDarkMode = !(trackerState && trackerState.dark_mode);
    try {
        const res = await fetch('/api/darkmode', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({darkMode: newDarkMode})});
        const result = await res.json();
        if (result.success) {
            trackerState = result.state;
            applyDarkMode();
            showMessage(result.message, 'info');
        }
    } catch (e) {
        showMessage('Fehler beim Umschalten', 'error');
    }
}

function showMessage(message, type = 'success') {
    const msgBox = document.getElementById('message-box');
    const colors = { success: 'bg-green-500', error: 'bg-red-500', warning: 'bg-yellow-600', info: 'bg-blue-500' };
    msgBox.className = `p-3 mb-6 rounded-xl text-white font-bold transition-opacity duration-300 ${colors[type]}`;
    msgBox.textContent = message;
    msgBox.style.opacity = '1';
    setTimeout(() => { msgBox.style.opacity = '0'; }, 5000);
}

async function handlePdfUpload() {
    const fileInput = document.getElementById('pdf-file-input');
    if (!fileInput.files.length) {
        showMessage('Bitte wählen Sie eine PDF-Datei aus', 'error');
        return;
    }

    // Start every analysis from a clean slate. Otherwise a failed analysis would leave the
    // sessions of the PREVIOUS statement (and the import button) in place, and clicking
    // "Importieren" would load the old statement again instead of the new one.
    extractedPdfSessions = [];
    document.getElementById('pdf-import-btn').style.display = 'none';
    document.getElementById('pdf-analysis-result').style.display = 'none';

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const res = await fetch('/api/pdf/analyze', {method: 'POST', body: formData});
        const result = await res.json();

        if (result.success) {
            extractedPdfSessions = result.sessions;
            displayPdfSessions(result.sessions);
            document.getElementById('pdf-import-btn').style.display = 'block';
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (e) {
        showMessage('Fehler bei PDF-Upload: ' + e, 'error');
    }
}

function displayPdfSessions(sessions) {
    const list = document.getElementById('pdf-sessions-list');
    document.getElementById('pdf-analysis-result').style.display = 'block';

    if (sessions.length === 0) {
        list.innerHTML = '<li>Keine Zeiträume gefunden</li>';
        return;
    }

    list.innerHTML = sessions.map(s => `
        <li class="border-l-4 border-indigo-500 pl-3">
            <strong>${s.date}</strong>: ${s.start_time} - ${s.end_time}
            ${s.is_remote ? ' <span class="text-xs bg-green-200 text-green-800 px-2 py-1 rounded">Remote</span>' : ''}
        </li>
    `).join('');
}

async function handlePdfImport() {
    if (!extractedPdfSessions.length) {
        showMessage('Keine Sessions zum Importieren', 'error');
        return;
    }

    try {
        const res = await fetch('/api/pdf/import', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({sessions: extractedPdfSessions})
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
    } catch (e) {
        showMessage('Fehler beim Import: ' + e, 'error');
    }
}

function closePdfModal() {
    document.getElementById('pdf-import-modal').classList.remove('active');
    document.getElementById('pdf-file-input').value = '';
    document.getElementById('pdf-analysis-result').style.display = 'none';
    document.getElementById('pdf-import-btn').style.display = 'none';
    extractedPdfSessions = [];
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
        showMessage('Fehler beim Speichern', 'error');
    }
}

async function handleDelete(entryId) {
    if (!confirm(t('confirm_delete'))) return;
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
        showMessage('Fehler beim Löschen', 'error');
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

    document.getElementById('submit-btn').textContent = 'Eintrag aktualisieren';
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
    if (!rec){ showMessage('Eintrag nicht gefunden', 'error'); return; }
    setEditMode(rec);
    showMessage('Eintrag wird bearbeitet', 'info');
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
        showMessage('Fehler', 'error');
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
        showMessage('Fehler', 'error');
    }
}

async function handleMonthSwitch() {
    if (!confirm(t('confirm_month_switch'))) return;
    try {
        const res = await fetch('/api/month/switch', {method: 'POST', headers: {'Content-Type': 'application/json'}});
        const result = await res.json();
        if (result.success) {
            trackerState = result.state;
            updateUI();
            showMessage(result.message, result.quartal_msg ? 'warning' : 'success');
        } else {
            showMessage(result.message || 'Fehler', 'error');
        }
    } catch (e) {
        showMessage('Fehler beim Monatswechsel', 'error');
    }
}

async function handleDeleteAllEntries() {
    if (!confirm(t('confirm_delete_all'))) return;

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
        showMessage('Fehler beim Löschen: ' + e, 'error');
    }
}

async function handleDeleteMonth(monthName, year) {
    if (!confirm(t('confirm_delete_month'))) return;

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
        showMessage('Fehler beim Löschen des Monats: ' + e, 'error');
    }
}

async function handleClearAllHistory() {
    if (!confirm(t('confirm_clear_all_history'))) return;

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
        showMessage('Fehler beim Löschen der Historie: ' + e, 'error');
    }
}

async function handleShutdown() {
    if (!confirm(t('confirm_shutdown'))) return;
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
            showMessage('Server konnte nicht beendet werden (Status ' + res.status + ').', 'error');
            return;
        }
        showMessage(t('shutdown_success'), 'success');
        setTimeout(() => {
            document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;background:#1a1a2e;color:white;"><div style="text-align:center;"><h1>Server beendet</h1><p>Sie können dieses Fenster schließen.</p></div></div>';
        }, 500);
    } catch (e) {
        // No answer at all: the server went away while we were waiting.
        showMessage(t('shutdown_success'), 'success');
        setTimeout(() => {
            document.body.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;background:#1a1a2e;color:white;"><div style="text-align:center;"><h1>Server beendet</h1><p>Sie können dieses Fenster schließen.</p></div></div>';
        }, 500);
    }
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
            showMessage(result.message || 'Fehler', 'error');
        }
    } catch (error) {
        showMessage('Fehler beim Wechsel zum aktuellen Monat', 'error');
    }
}

function drawRemoteChart() {
    const canvas = document.getElementById('remote-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    if (!trackerState || !trackerState.current_month_data) {
        return;
    }

    const data = trackerState.current_month_data;
    const maxRemote = parseFloat(data.max_remote_stunden) || 1;
    const istRemote = parseFloat(data.ist_remote_stunden_laufend) || 0;

    const usedPercentage = Math.min((istRemote / maxRemote) * 100, 100);
    const remainingPercentage = Math.max(0, 100 - usedPercentage);

    const isDark = !!(trackerState && trackerState.dark_mode);
    const colorBg = isDark ? '#1b2030' : '#e0e7ff';
    const colorUsed = isDark ? '#d46a6a' : '#ef4444';
    const colorRemaining = isDark ? '#22b07f' : '#10b981';
    const colorOverOverlay = isDark ? 'rgba(139, 0, 0, 0.35)' : 'rgba(153, 27, 27, 0.3)';

    ctx.fillStyle = colorBg;
    ctx.fillRect(0, 0, width, height);

    const usedWidth = (width * usedPercentage) / 100;
    ctx.fillStyle = colorUsed;
    ctx.fillRect(0, 0, usedWidth, height);

    if (usedPercentage < 100) {
        const remainingWidth = (width * remainingPercentage) / 100;
        ctx.fillStyle = colorRemaining;
        ctx.fillRect(usedWidth, 0, remainingWidth, height);
    }

    if (usedPercentage > 100) {
        ctx.fillStyle = colorOverOverlay;
        ctx.fillRect(0, 0, width, height);
    }

    ctx.strokeStyle = '#6366f1';
    ctx.lineWidth = 2;
    ctx.strokeRect(0, 0, width, height);

    const textColor = isDark ? '#e6e9ef' : '#000000';
    ctx.fillStyle = textColor;
    ctx.font = 'bold 18px sans-serif';
    ctx.textAlign = 'center';
    ctx.shadowColor = 'rgba(255, 255, 255, 0.8)';
    ctx.shadowBlur = 4;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 0;

    const displayText = `${istRemote.toFixed(2)}h / ${maxRemote.toFixed(2)}h (${usedPercentage.toFixed(2)}%)`;
    ctx.fillText(displayText, width / 2, height / 2 + 6);

    ctx.shadowColor = 'transparent';
    ctx.shadowBlur = 0;
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
        `${displayMonth} ${displayYear} | Quartal: ${displayQuartal} | Monat-Quote: ${Number(data.individuelle_quote).toFixed(2)}% (Ist: ${actualRemoteQuota.toFixed(2)}%)`;

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

    const rawVerbleibend = (data.max_remote_stunden || 0) - (data.ist_remote_stunden_laufend || 0);
    const verbleibendEl = document.getElementById('display-verbleibend');
    const displayVerbleibend = Math.max(0, rawVerbleibend);
    verbleibendEl.textContent = `${displayVerbleibend.toFixed(2)}h`;

    if (rawVerbleibend < 0) {
        verbleibendEl.className = 'text-4xl font-extrabold p-3 rounded-lg text-white bg-red-600';
    } else if (rawVerbleibend < 10) {
        verbleibendEl.className = 'text-4xl font-extrabold p-3 rounded-lg text-white bg-yellow-500';
    } else {
        verbleibendEl.className = 'text-4xl font-extrabold p-3 rounded-lg text-white bg-green-600';
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
        recordList.innerHTML = '<li class="p-2 text-sm text-gray-500">' + t('no_entries') + '</li>';
    } else {
        records.sort((a, b) => {
            const d = b.datum.localeCompare(a.datum);
            if (d !== 0) return d;
            return (a.startTime||'').localeCompare(b.startTime||'');
        });
        recordList.innerHTML = records.map(r => `
            <li class="p-3 hover:bg-gray-50 transition">
                <div class="flex justify-between items-start">
                    <div>
                        <p class="font-bold text-gray-900">${r.datum}</p>
                        <p class="text-sm text-gray-600">
                            ${r.startTime} - ${r.endTime} (Pause: ${Number(r.pauseMinutes).toFixed(0)}min)
                        </p>
                        <p class="text-sm text-gray-700 font-medium">
                            Remote: ${Number(r.remoteStundenHeute).toFixed(2)}h | Gesamt: ${Number(r.totalStundenHeute).toFixed(2)}h
                        </p>
                        ${r.source === 'pdf_import' ? '<p class="text-xs text-purple-600 font-bold">📄 PDF Import</p>' : ''}
                        ${r.pauseWarning && r.source !== 'pdf_import' ? `<p class="text-xs text-red-600 font-bold mt-1">${r.pauseWarning}</p>` : ''}
                    </div>
                    <div class="flex items-center gap-2">
                        <button onclick="handleEdit('${r.id || (r.datum + '|' + (r.startTime||'') + '|' + (r.endTime||''))}')" 
                                class="bg-yellow-500 hover:bg-yellow-600 text-white font-bold py-1 px-3 rounded-lg text-sm">
                            ${t('edit')}
                        </button>
                        <button onclick="handleDelete('${r.id || (r.datum + '|' + (r.startTime||'') + '|' + (r.endTime||''))}')" 
                                class="bg-red-500 hover:bg-red-600 text-white font-bold py-1 px-3 rounded-lg text-sm">
                            ${t('delete')}
                        </button>
                    </div>
                </div>
            </li>
        `).join('');
    }

    const historyList = document.getElementById('history-list');
    const history = trackerState.monatliche_historie || [];

    if (history.length === 0) {
        historyList.innerHTML = '<li class="p-2 text-sm text-gray-500">Keine Monate abgeschlossen</li>';
    } else {
        historyList.innerHTML = sortedHistory(history).map(m => {
            // Berechne tatsächliche Remote-Quote falls nicht vorhanden
            const tatsaechlicheQuote = m.tatsaechliche_remote_quote ||
                (m.soll_stunden_gesamt > 0 ? (m.ist_remote_stunden_laufend / m.soll_stunden_gesamt * 100) : 0);

            // Zeige Quartals-Quote nur wenn vorhanden
            const quartalQuoteHtml = m.quartal_quote !== undefined ? `
                <p class="text-sm font-semibold text-blue-700 mt-2 pt-2 border-t">
                    ${m.quartal}: Quartals-Quote: ${Number(m.quartal_quote).toFixed(2)}%
                    (${Number(m.quartal_remote).toFixed(2)}h / ${Number(m.quartal_soll).toFixed(2)}h)
                </p>
            ` : '';

            return `
            <li class="p-3 border-b last:border-b-0${isOverQuota(m) ? ' over-quota' : ''}"${isOverQuota(m) ? ` data-over-quota="true" title="${t('over_quota_hint')}"` : ''}>
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <p class="font-bold text-gray-900">${m.monat} ${m.jahr} <span class="text-sm font-semibold text-indigo-600">(${m.quartal || 'Q?'})</span></p>
                        <p class="text-sm text-gray-600">
                            Quote: ${Number(m.individuelle_quote).toFixed(2)}% |
                            ${t('actual_remote_quota')}: ${Number(tatsaechlicheQuote).toFixed(2)}%
                        </p>
                        <p class="text-sm text-gray-700">
                            Remote: ${Number(m.ist_remote_stunden_laufend).toFixed(2)}h / ${Number(m.max_remote_stunden).toFixed(2)}h
                        </p>
                        <p class="text-sm text-gray-700">
                            Gesamt: ${Number(m.ist_arbeitszeit_laufend).toFixed(2)}h / ${Number(m.soll_stunden_gesamt).toFixed(2)}h
                        </p>
                        ${quartalQuoteHtml}
                    </div>
                    <button onclick="handleDeleteMonth('${m.monat}', ${m.jahr})"
                            class="ml-3 bg-red-500 hover:bg-red-600 text-white text-xs font-bold py-1 px-3 rounded transition"
                            data-i18n="delete_month">
                        ${t('delete_month')}
                    </button>
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
    if (!report.quarters.length) return `<p class="text-sm text-gray-600">${t('report_empty')}</p>`;
    const o = report.overall;
    const quarters = report.quarters.map(q => `
        <section class="mb-4 border rounded-xl overflow-hidden" data-quartal="${escapeHtml(q.quartal)}" data-rating="${q.rating}">
            <div class="flex flex-wrap justify-between items-center p-3 rating-${q.rating}">
                <h3 class="font-extrabold">${escapeHtml(q.quartal)}${q.complete ? '' : ` <span class="text-xs font-semibold">(${t('report_quarter_incomplete')}: ${q.month_count}/3)</span>`}</h3>
                <span class="font-bold">${t('rating_' + q.rating)}</span>
            </div>
            <p class="px-3 pt-2 text-sm text-gray-700">
                Remote ${f(q.remote)}h / ${t('report_limit')} ${f(q.max_remote)}h (${Math.round(q.usage * 100)} %) |
                ${t('report_quota')} ${f(q.actual_quote)}% | ${q.months_over} ${t('report_months_over')}
            </p>
            <ul class="p-3 text-sm">
                ${q.months.map(m => `<li class="flex justify-between py-1 px-2 rounded${m.over ? ' over-quota' : ''}">
                    <span>${escapeHtml(m.monat)} ${m.jahr}</span>
                    <span>Remote ${f(m.remote)}h / ${f(m.max_remote)}h | ${f(m.actual_quote)}%</span></li>`).join('')}
            </ul>
        </section>`).join('');
    return `
        <div class="mb-4 p-3 rounded-xl rating-${o.rating}" data-overall-rating="${o.rating}">
            <p class="font-extrabold">${t('report_overall')}: ${t('rating_' + o.rating)}</p>
            <p class="text-sm">${o.months} ${t('report_months')}, ${o.quarters} Q | Remote ${f(o.remote)}h / ${t('report_limit')} ${f(o.max_remote)}h | ${t('report_quota')} ${f(o.actual_quote)}% | ${o.months_over} ${t('report_months_over')}</p>
        </div>
        ${quarters}
        <p class="text-xs text-gray-500">${t('report_rule')}</p>`;
}

async function handleFinalReport() {
    try {
        const res = await fetch('/api/report/final');
        const data = await res.json();
        document.getElementById('final-report-body').innerHTML = renderFinalReport(data.report);
        document.getElementById('final-report-modal').classList.remove('hidden');
    } catch (e) {
        showMessage('Fehler beim Laden des Abschlussberichts: ' + e, 'error');
    }
}

function closeFinalReport() {
    document.getElementById('final-report-modal').classList.add('hidden');
}

// Local calendar date (YYYY-MM-DD). toISOString() would give the UTC date: yesterday shortly after midnight.
function localToday() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// B4: choose any month to look at (entries and totals of that month)
function syncViewSelectors() {
    const monthSel = document.getElementById('view-month-select');
    const yearSel = document.getElementById('view-year-select');
    if (!monthSel || !yearSel || !trackerState) return;
    if (!monthSel.options.length) {
        Object.keys(MONTH_NUMBERS).forEach(m => monthSel.add(new Option(m, m)));
    }
    const years = new Set([2025, 2026, 2027, 2028, 2029, 2030, trackerState.view_year, trackerState.aktuelles_jahr]);
    (trackerState.monatliche_historie || []).forEach(h => years.add(h.jahr));
    const sorted = [...years].sort((a, b) => a - b);
    if (yearSel.options.length !== sorted.length) {
        yearSel.innerHTML = '';
        sorted.forEach(y => yearSel.add(new Option(String(y), String(y))));
    }
    monthSel.value = trackerState.view_month;
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
            showMessage(result.message || 'Fehler', 'error');
        }
    } catch (e) {
        showMessage('Fehler beim Wechsel des Monats: ' + e, 'error');
    }
}

// B3: restore a JSON backup from the UI (the API existed, the button did not)
async function handleRestoreFile(input) {
    const file = input.files && input.files[0];
    input.value = '';
    if (!file || !confirm(t('confirm_restore'))) return;
    try {
        const fd = new FormData();
        fd.append('file', file);
        const res = await fetch('/api/restore', {method: 'POST', body: fd});
        const result = await res.json();
        if (result.success) {
            trackerState = result.state;
            updateUI();
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message || 'Fehler', 'error');
        }
    } catch (e) {
        showMessage('Fehler bei der Wiederherstellung: ' + e, 'error');
    }
}

window.addEventListener('DOMContentLoaded', () => {
    loadState();
    const today = localToday();
    document.getElementById('input-date').value = today;
});
