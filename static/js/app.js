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
        batch_import_btn: 'Mehrere Nachweise',
        batch_import: 'Mehrere Zeitnachweise importieren',
        batch_import_desc: 'Laden Sie mehrere Zeitnachweise (PDF) auf einmal. Jeder Nachweis wird geprüft. Nur fehlerfreie Monate werden übernommen; ist der Monat vorbei, kommt er sortiert in die Historie. Die Tage bleiben in der Tageshistorie, Ihre Quote wird nicht verändert. Die Dokumente verlassen diesen Rechner nicht.',
        batch_files: 'PDF-Dateien',
        batch_analyze: 'Prüfen',
        batch_close: 'Schließen',
        batch_pick: 'Bitte wählen Sie mindestens eine PDF-Datei aus',
        batch_do_import: 'Ausgewählte Monate importieren',
        batch_nothing_selected: 'Kein Monat ausgewählt',
        batch_status_ok: 'In Ordnung',
        batch_status_warning: 'Bitte prüfen',
        batch_status_error: 'Fehler: wird nicht importiert',
        batch_target_history: 'Kommt in die Historie',
        batch_target_daily: 'Monat ist noch offen: nur Tageshistorie',
        batch_summary: '{days} Tage, {net} h netto, {remote} h remote',
        batch_quote: 'Quote dieses Monats (%)',
        batch_select: 'Importieren',
        batch_select_warning: 'Trotz Warnung importieren',
        batch_result_imported: 'Importiert',
        batch_result_rejected: 'Abgelehnt',
        issue_not_pdf: 'Keine PDF-Datei',
        issue_file_too_large: 'Datei zu groß (max. 10 MB)',
        issue_parse_failed: 'Nachweis nicht lesbar: {detail}',
        issue_period_unknown: 'Monat im Nachweis nicht eindeutig erkannt',
        issue_period_from_filename: 'Monat nur aus dem Dateinamen erkannt, bitte prüfen',
        issue_period_multi_month: 'Nachweis reicht über mehrere Monate (bis {detail})',
        issue_no_sessions: 'Keine Zeitbuchungen gefunden',
        issue_too_many_sessions: 'Zu viele Buchungen ({detail})',
        issue_future_month: 'Der Monat liegt in der Zukunft',
        issue_future_date: '{date}: Datum liegt in der Zukunft',
        issue_invalid_date: 'Ungültiges Datum: {detail}',
        issue_date_outside_month: '{date}: Datum liegt nicht im Nachweismonat',
        issue_invalid_time: '{date}: Ungültige Zeit ({detail})',
        issue_end_not_after_start: '{date}: Ende nicht nach dem Beginn ({detail})',
        issue_overlap: '{date}: Buchungen überschneiden sich',
        issue_duplicate_month: 'Mehrere Dateien für denselben Monat ({detail})',
        issue_overlaps_existing: '{date}: überschneidet sich mit einem eigenen Eintrag',
        issue_invalid_quote: 'Ungültige Quote ({detail})',
        issue_non_working_day: '{date}: Buchung an einem Wochenende oder Feiertag',
        issue_long_day: '{date}: mehr als 10 Stunden netto ({detail} h)',
        issue_replaces_history: 'Ersetzt den vorhandenen Monat in der Historie',
        issue_has_manual_entries: '{detail} eigene Einträge dieses Monats bleiben erhalten und zählen mit',
        issue_needs_confirmation: 'Warnungen nicht bestätigt',
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
        flex_title: 'Gleitzeit-Verlauf', flex_chart_empty: 'Noch keine Gleitzeit-Daten. Laden Sie Zeitnachweise, um den Verlauf zu sehen.',
        flex_legend_total: 'Saldo am Monatsende', flex_legend_change: 'Änderung im Monat', flex_gap_note: 'Gestrichelt: Monate ohne Nachweis',
        flex_latest: 'Aktuell', flex_min: 'Tiefstand', flex_max: 'Höchststand', flex_quarter_end: 'Gleitzeit Quartalsende',
        flex_short: 'GLZ', flex_chart_label: 'Gleitzeit-Saldo pro Monat in Stunden', err_flex: 'Fehler beim Laden der Gleitzeit: ',
        flex_band_yellow: 'Gelb: über ±40 h', flex_band_red: 'Rot: über ±60 h (Kappung)',
        flex_status_label: 'Status', flex_status_ok: 'Im grünen Bereich', flex_status_yellow_pos: 'Gelb: über 40 h',
        flex_status_red_pos: 'Rot: über 60 h', flex_status_yellow_neg: 'Gelb: unter −40 h', flex_status_red_neg: 'Rot: unter −60 h',
        flex_advice_title: 'Empfehlungen', flex_advice_as_of: 'Grundlage: Saldo {balance} am Ende {month}. Ziel: unter {target} h.',
        flex_month_title: 'Monatsanalyse', flex_month_pick: 'Monat',
        advice_prio_high: 'Dringend', advice_prio_medium: 'Empfohlen', advice_prio_info: 'Hinweis',
        advice_none: 'Keine Gleitzeit-Daten für Empfehlungen.',
        advice_cap_cut: 'Das Saldo liegt über {limit} h. Stunden über {limit} h werden am Monatsende abgeschnitten ({over} h gehen verloren).',
        advice_reduce: 'Das Saldo von {balance} h liegt {over} h über der gelben Grenze von {limit} h. Ziel: unter {target} h, also {need} h abbauen.',
        advice_near_limit: 'Das Saldo von {balance} h liegt nur {to_limit} h unter der gelben Grenze von {limit} h. Ein Puffer bis {target} h wäre sicherer ({need} h abbauen).',
        advice_flex_days: 'Gleitzeittage nehmen: {days} Tage à {soll} h (volle Tage: {full_days}, dazu {rest} h).',
        advice_shorter_days: 'Oder früher Feierabend machen: {per_day} h pro Tag an jedem der {workdays} Arbeitstage bis {until}.',
        advice_approval: 'Ab etwa 50 h mit der Führungskraft sprechen: Sie entscheidet, ob die Stunden abgebaut, vergütet oder ein weiterer Aufbau untersagt wird.',
        advice_trend_up: 'Das Saldo wächst im Schnitt um {trend} h pro Monat. Ohne Gegenmaßnahme ist die gelbe Grenze von {limit} h in etwa {months} Monaten erreicht.',
        advice_trend_up_over: 'Das Saldo wächst im Schnitt um {trend} h pro Monat und steigt ohne Gegenmaßnahme weiter.',
        advice_long_days: 'Tage mit mehr als {limit} h im letzten Monat: {n}. Tagesenden und Pausen prüfen, solche Tage vermeiden.',
        advice_daily_surplus: 'Im Schnitt {avg_over} h mehr als das Soll von {soll} h pro Tag, das sind rund {per_month} h im Monat.',
        advice_weekend_work: 'Einträge an Wochenende oder Feiertag: {n}. Dafür ist eine vorherige Genehmigung nötig.',
        advice_outside_window: 'Tage mit Arbeit vor 06:00 oder nach 20:00 Uhr: {n}. Diese Zeiten zählen nicht ins Gleitzeitkonto.',
        advice_build_up: 'Das Saldo ist negativ ({balance} h). Zum Ausgleich {need} h mehr arbeiten oder Fehlbuchungen prüfen.',
        advice_check_missing: 'Das Saldo von {balance} h ist stark negativ. Eventuell fehlen Arbeitszeiten: Buchungen prüfen (sechs Wochen rückwirkend selbst änderbar).',
        advice_on_track: 'Das Saldo von {balance} h liegt im grünen Bereich. Keine Maßnahme nötig.',
        fm_balance_start: 'Saldo Monatsbeginn', fm_balance_end: 'Saldo Monatsende', fm_change_sap: 'Änderung (Nachweis)',
        fm_change_calc: 'Netto minus Soll (Tageseinträge)', fm_difference: 'Differenz', fm_avg_day: 'Ø Netto pro Arbeitstag',
        fm_avg_times: 'Ø Beginn / Ende', fm_longest: 'Längster Tag', fm_long_days: 'Tage über 10 h', fm_outside: 'Vor 06:00 / nach 20:00',
        fm_non_working: 'Wochenende / Feiertag', fm_missing: 'Werktage ohne Eintrag',
        fm_diff_hint: 'Die Differenz entsteht durch Tage ohne Eintrag (Urlaub, Gleitzeittag, Abwesenheit) und die Rundung des Nachweises.',
        fm_col_soll: 'Soll', fm_weeks: 'Wochen', fm_days: 'Tage', fm_week: 'KW', fm_col_date: 'Datum', fm_col_time: 'Zeit', fm_col_net: 'Netto', fm_col_delta: 'Δ Soll',
        fm_col_balance: 'Verlauf', fm_col_flags: 'Hinweis', fm_flag_no_entry: 'kein Eintrag', fm_flag_long_day: 'über 10 h',
        fm_flag_early: 'vor 06:00', fm_flag_late: 'nach 20:00', fm_flag_non_working_day: 'Wochenende/Feiertag',
        fm_no_data: 'Für diesen Monat sind keine Tageseinträge mehr vorhanden (zum Beispiel nach „Monat abschließen“). Es gelten die Zahlen des Nachweises.', fm_incomplete: 'Der Monat läuft noch: das Soll zählt nur bis heute.',
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
        batch_import_btn: 'Several statements',
        batch_import: 'Import several time statements',
        batch_import_desc: 'Upload several time statements (PDF) at once. Every statement is checked. Only correct months are imported; a month that is over goes into the history, sorted. The days stay in the daily history and your quota is not changed. The documents never leave this computer.',
        batch_files: 'PDF files',
        batch_analyze: 'Check',
        batch_close: 'Close',
        batch_pick: 'Please choose at least one PDF file',
        batch_do_import: 'Import selected months',
        batch_nothing_selected: 'No month selected',
        batch_status_ok: 'OK',
        batch_status_warning: 'Please check',
        batch_status_error: 'Error: will not be imported',
        batch_target_history: 'Goes into the history',
        batch_target_daily: 'Month is still open: daily history only',
        batch_summary: '{days} days, {net} h net, {remote} h remote',
        batch_quote: 'Quota of this month (%)',
        batch_select: 'Import',
        batch_select_warning: 'Import despite warnings',
        batch_result_imported: 'Imported',
        batch_result_rejected: 'Rejected',
        issue_not_pdf: 'Not a PDF file',
        issue_file_too_large: 'File too large (max. 10 MB)',
        issue_parse_failed: 'Statement could not be read: {detail}',
        issue_period_unknown: 'Month of the statement not clearly recognised',
        issue_period_from_filename: 'Month only taken from the file name, please check',
        issue_period_multi_month: 'Statement covers several months (until {detail})',
        issue_no_sessions: 'No time bookings found',
        issue_too_many_sessions: 'Too many bookings ({detail})',
        issue_future_month: 'The month is in the future',
        issue_future_date: '{date}: date is in the future',
        issue_invalid_date: 'Invalid date: {detail}',
        issue_date_outside_month: '{date}: date is not in the month of the statement',
        issue_invalid_time: '{date}: invalid time ({detail})',
        issue_end_not_after_start: '{date}: end is not after start ({detail})',
        issue_overlap: '{date}: bookings overlap',
        issue_duplicate_month: 'Several files for the same month ({detail})',
        issue_overlaps_existing: '{date}: overlaps an entry you typed in',
        issue_invalid_quote: 'Invalid quota ({detail})',
        issue_non_working_day: '{date}: booking on a weekend or public holiday',
        issue_long_day: '{date}: more than 10 hours net ({detail} h)',
        issue_replaces_history: 'Replaces the existing month in the history',
        issue_has_manual_entries: '{detail} entries of this month that you typed in are kept and counted',
        issue_needs_confirmation: 'Warnings not confirmed',
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
        flex_title: 'Flextime trend', flex_chart_empty: 'No flextime data yet. Load time statements to see the trend.',
        flex_legend_total: 'Balance at month end', flex_legend_change: 'Change during the month', flex_gap_note: 'Dashed: months without a statement',
        flex_latest: 'Current', flex_min: 'Lowest', flex_max: 'Highest', flex_quarter_end: 'Flextime at quarter end',
        flex_short: 'Flex', flex_chart_label: 'Flextime balance per month in hours', err_flex: 'Error loading flextime: ',
        flex_band_yellow: 'Yellow: beyond ±40 h', flex_band_red: 'Red: beyond ±60 h (cut off)',
        flex_status_label: 'Status', flex_status_ok: 'In the green zone', flex_status_yellow_pos: 'Yellow: above 40 h',
        flex_status_red_pos: 'Red: above 60 h', flex_status_yellow_neg: 'Yellow: below −40 h', flex_status_red_neg: 'Red: below −60 h',
        flex_advice_title: 'Recommendations', flex_advice_as_of: 'Based on: balance {balance} at the end of {month}. Goal: below {target} h.',
        flex_month_title: 'Month analysis', flex_month_pick: 'Month',
        advice_prio_high: 'Urgent', advice_prio_medium: 'Recommended', advice_prio_info: 'Note',
        advice_none: 'No flextime data for recommendations.',
        advice_cap_cut: 'The balance is above {limit} h. Hours above {limit} h are cut off at the end of the month ({over} h are lost).',
        advice_reduce: 'The balance of {balance} h is {over} h above the yellow limit of {limit} h. Goal: below {target} h, so reduce {need} h.',
        advice_near_limit: 'The balance of {balance} h is only {to_limit} h below the yellow limit of {limit} h. A buffer down to {target} h would be safer (reduce {need} h).',
        advice_flex_days: 'Take flextime days: {days} days of {soll} h (full days: {full_days}, plus {rest} h).',
        advice_shorter_days: 'Or finish earlier: {per_day} h per day on each of the {workdays} working days until {until}.',
        advice_approval: 'From about 50 h, talk to your manager: they decide whether the hours are reduced, paid out or further build-up is forbidden.',
        advice_trend_up: 'The balance grows by {trend} h per month on average. Without counter-measures the yellow limit of {limit} h is reached in about {months} months.',
        advice_trend_up_over: 'The balance grows by {trend} h per month on average and keeps rising without counter-measures.',
        advice_long_days: 'Days with more than {limit} h last month: {n}. Check the end of the day and breaks, avoid such days.',
        advice_daily_surplus: 'On average {avg_over} h more than the target of {soll} h per day, about {per_month} h per month.',
        advice_weekend_work: 'Entries on a weekend or holiday: {n}. They need prior approval.',
        advice_outside_window: 'Days with work before 06:00 or after 20:00: {n}. These hours do not count towards flextime.',
        advice_build_up: 'The balance is negative ({balance} h). To compensate, work {need} h more or check wrong bookings.',
        advice_check_missing: 'The balance of {balance} h is strongly negative. Working hours may be missing: check the bookings (you can change them yourself up to six weeks back).',
        advice_on_track: 'The balance of {balance} h is in the green zone. No action needed.',
        fm_balance_start: 'Balance at start of month', fm_balance_end: 'Balance at end of month', fm_change_sap: 'Change (statement)',
        fm_change_calc: 'Net minus target (daily entries)', fm_difference: 'Difference', fm_avg_day: 'Avg net per working day',
        fm_avg_times: 'Avg start / end', fm_longest: 'Longest day', fm_long_days: 'Days above 10 h', fm_outside: 'Before 06:00 / after 20:00',
        fm_non_working: 'Weekend / holiday', fm_missing: 'Working days without an entry',
        fm_diff_hint: 'The difference comes from days without an entry (leave, flextime day, absence) and the rounding of the statement.',
        fm_col_soll: 'Target', fm_weeks: 'Weeks', fm_days: 'Days', fm_week: 'Wk', fm_col_date: 'Date', fm_col_time: 'Time', fm_col_net: 'Net', fm_col_delta: 'Δ target',
        fm_col_balance: 'Running', fm_col_flags: 'Note', fm_flag_no_entry: 'no entry', fm_flag_long_day: 'over 10 h',
        fm_flag_early: 'before 06:00', fm_flag_late: 'after 20:00', fm_flag_non_working_day: 'weekend/holiday',
        fm_no_data: 'There are no daily entries left for this month (for example after "close month"). The figures of the statement apply.', fm_incomplete: 'The month is still running: the target only counts until today.',
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

// ---- Import of several time statements at once -------------------------------------------------
let batchReports = [];

function issueText(issue){
    return t('issue_' + issue.code)
        .replace('{date}', issue.date ? dateLabel(issue.date) : '')
        .replace('{detail}', issue.detail === undefined || issue.detail === null ? '' : issue.detail);
}

function batchCard(r, i){
    const selectable = r.status !== 'error';
    const color = {ok: '--success', warning: '--warning', error: '--error'}[r.status];
    const badge = {ok: 'rating-good', warning: 'rating-tight', error: 'rating-exceeded'}[r.status];
    const title = r.key ? `${escapeHtml(monthLabel(r.month_name))} ${r.year}` : escapeHtml(r.filename);
    const s = r.summary || {};
    const summary = s.days !== undefined
        ? t('batch_summary').replace('{days}', s.days).replace('{net}', Number(s.net_hours).toFixed(2)).replace('{remote}', Number(s.remote_hours).toFixed(2))
        : '';
    const issues = r.errors.map(e => `<li class="warn-text">✖ ${escapeHtml(issueText(e))}</li>`)
        .concat(r.warnings.map(w => `<li class="edit-hint">⚠ ${escapeHtml(issueText(w))}</li>`)).join('');
    const quote = r.target === 'history' && selectable ? `
        <div class="mt-2">
            <label for="batch-quote-${i}" class="field-label">${escapeHtml(t('batch_quote'))}</label>
            <input type="number" step="any" id="batch-quote-${i}" class="field" value="${Number(r.quote)}" style="max-width:10rem">
        </div>` : '';
    return `
        <div class="tile" style="border-left:4px solid var(${color})">
            <div class="flex flex-wrap items-center justify-between gap-2">
                <strong>${title}</strong>
                <span class="badge ${badge}">${escapeHtml(t('batch_status_' + r.status))}</span>
            </div>
            <p class="text-xs muted">${escapeHtml(r.filename)}${r.target ? ' · ' + escapeHtml(t('batch_target_' + r.target)) : ''}</p>
            ${summary ? `<p class="text-sm">${escapeHtml(summary)}</p>` : ''}
            ${issues ? `<ul class="text-sm mt-2">${issues}</ul>` : ''}
            ${quote}
            <label class="text-sm font-semibold mt-2 block">
                <input type="checkbox" id="batch-sel-${i}" ${r.status === 'ok' ? 'checked' : ''} ${selectable ? '' : 'disabled'} onchange="updateBatchImportButton()">
                ${escapeHtml(t(r.status === 'warning' ? 'batch_select_warning' : 'batch_select'))}
            </label>
        </div>`;
}

function selectedBatchIndexes(){
    return batchReports.map((r, i) => i).filter(i => {
        const cb = document.getElementById('batch-sel-' + i);
        return cb && !cb.disabled && cb.checked;
    });
}

function updateBatchImportButton(){
    const btn = document.getElementById('batch-import-btn');
    const n = selectedBatchIndexes().length;
    btn.textContent = `${t('batch_do_import')} (${n})`;
    btn.disabled = n === 0;
    btn.style.display = batchReports.length ? 'block' : 'none';
}

function resetBatchModal(){
    batchReports = [];
    document.getElementById('batch-reports').innerHTML = '';
    document.getElementById('batch-import-btn').style.display = 'none';
    document.getElementById('batch-file-input').value = '';
}

function closeBatchModal(){
    const dlg = document.getElementById('batch-import-modal');
    if (dlg.open) dlg.close();
    resetBatchModal();
}

async function handleBatchAnalyze(){
    const input = document.getElementById('batch-file-input');
    if (!input.files.length) { showMessage(t('batch_pick'), 'error'); return; }
    batchReports = [];
    document.getElementById('batch-reports').innerHTML = '';
    document.getElementById('batch-import-btn').style.display = 'none';

    const formData = new FormData();
    for (const file of input.files) formData.append('files', file);
    try {
        await withBusy(document.getElementById('batch-analyze-btn'), async () => {
            const res = await fetch('/api/pdf/batch/analyze', {method: 'POST', body: formData});
            const result = await res.json();
            if (result.success) {
                batchReports = result.reports;
                document.getElementById('batch-reports').innerHTML = batchReports.map(batchCard).join('');
                updateBatchImportButton();
            } else {
                showMessage(result.message, 'error');
            }
        });
    } catch (e) {
        showMessage(t('err_pdf_upload') + e, 'error');
    }
}

function renderBatchResults(results){
    document.getElementById('batch-reports').innerHTML = results.map(r => {
        const ok = r.status === 'imported';
        const [year, month] = (r.key || '').split('-');
        const names = Object.keys(MONTH_NUMBERS);
        const title = r.key ? `${escapeHtml(monthLabel(names[Number(month) - 1]))} ${year}` : escapeHtml(r.filename || '');
        const reasons = ok ? '' : `<ul class="text-sm mt-2">${r.codes.map(c => `<li class="warn-text">✖ ${escapeHtml(issueText({code: c}))}</li>`).join('')}</ul>`;
        return `
            <div class="tile" style="border-left:4px solid var(${ok ? '--success' : '--error'})">
                <div class="flex flex-wrap items-center justify-between gap-2">
                    <strong>${title}</strong>
                    <span class="badge ${ok ? 'rating-good' : 'rating-exceeded'}">${escapeHtml(t(ok ? 'batch_result_imported' : 'batch_result_rejected'))}</span>
                </div>
                ${ok ? `<p class="text-xs muted">${escapeHtml(t('batch_target_' + r.target))}</p>` : reasons}
            </div>`;
    }).join('');
    batchReports = [];
    document.getElementById('batch-import-btn').style.display = 'none';
    document.getElementById('batch-file-input').value = '';
}

async function handleBatchImport(){
    const months = selectedBatchIndexes().map(i => {
        const r = batchReports[i];
        const month = {year: r.year, month: r.month, filename: r.filename, sessions: r.sessions,
                       flex_balance: r.flex_balance, confirmed: true};
        const quote = document.getElementById('batch-quote-' + i);
        if (quote && quote.value !== '') month.quote = Number(quote.value);
        return month;
    });
    if (!months.length) { showMessage(t('batch_nothing_selected'), 'error'); return; }
    try {
        await withBusy(document.getElementById('batch-import-btn'), async () => {
            const res = await fetch('/api/pdf/batch/import', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({months})
            });
            const result = await res.json();
            if (result.success) {
                trackerState = result.state;
                updateUI();
                renderBatchResults(result.results);
                showMessage(result.message, result.rejected_count ? 'warning' : 'success');
            } else {
                showMessage(result.message, 'error');
            }
        });
    } catch (e) {
        showMessage(t('err_import') + e, 'error');
    }
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
            ${q.flex_end != null ? `<p class="px-3 pt-1 text-sm font-semibold" data-flex-quarter>${t('flex_quarter_end')}: ${signedHours(q.flex_end)}${q.flex_change != null ? ` (Δ ${signedHours(q.flex_change)})` : ''} ${flexBadge(q.flex_status)}</p>` : ''}
            <ul class="p-3 text-sm">
                ${q.months.map(m => `<li class="flex flex-wrap justify-between gap-x-3 py-1 px-2 rounded${m.over ? ' over-quota' : ''}">
                    <span>${escapeHtml(monthLabel(m.monat))} ${m.jahr}${m.over ? ` <span class="badge badge-over"><span aria-hidden="true">⚠</span> ${t('over_limit')}</span>` : ''}</span>
                    <span>Remote ${f(m.remote)}h / ${f(m.max_remote)}h | ${f(m.actual_quote)}%${m.flex_total != null ? ` | <span data-flex-month>${t('flex_short')} ${signedHours(m.flex_total)}${m.flex_change != null ? ` (${signedHours(m.flex_change)})` : ''}</span> ${flexBadge(m.flex_status)}` : ''}</span></li>`).join('')}
            </ul>
        </section>`).join('');
    return `
        <div class="mb-4 p-3 rounded-xl rating-${o.rating}" data-overall-rating="${o.rating}">
            <p class="font-extrabold">${t('report_overall')}: ${t('rating_' + o.rating)}</p>
            <p class="text-sm">${o.months} ${t('report_months')}, ${o.quarters} Q | Remote ${f(o.remote)}h / ${t('report_limit')} ${f(o.max_remote)}h | ${t('report_quota')} ${f(o.actual_quote)}% | ${o.months_over} ${t('report_months_over')}</p>
        </div>
        <section class="mb-4" data-flex-section>
            <h3 class="font-extrabold mb-2">${t('flex_title')}</h3>
            ${renderFlexChart(report.flex)}
        </section>
        ${quarters}
        <p class="text-xs muted">${t('report_rule')}</p>`;
}

function signedHours(v) {
    const n = Number(v);
    return (n > 0 ? '+' : '') + n.toFixed(2) + 'h';
}

function flexBadge(status) {
    if (!status || status === 'ok') return '';
    const red = status.startsWith('red');
    return `<span class="badge ${red ? 'badge-over' : 'rating-tight'}" data-flex-status="${escapeHtml(status)}"><span aria-hidden="true">⚠</span> ${t('flex_status_' + status)}</span>`;
}

function tp(key, params) {
    return Object.entries(params || {}).reduce((text, [k, v]) => text.split('{' + k + '}').join(String(v)), t(key));
}

// Numbers for the texts: at most 2 decimals, no trailing zeros; the date of `until` in the local format.
function adviceParams(params) {
    const out = {};
    Object.entries(params || {}).forEach(([k, v]) => {
        out[k] = k === 'until' ? dateLabel(v) : (typeof v === 'number' ? String(Math.round(v * 100) / 100) : v);
    });
    return out;
}

function renderFlexAdvice(flex) {
    const advice = flex && flex.advice;
    if (!advice || !advice.items || !advice.items.length) return `<p class="text-sm muted" data-advice-empty>${t('advice_none')}</p>`;
    const target = (flex.limits && flex.limits.target) || 30;
    const css = {high: 'rating-exceeded', medium: 'rating-tight', info: 'rating-good'};
    const head = tp('flex_advice_as_of', {balance: signedHours(advice.balance),
        month: `${monthLabel(advice.as_of.monat_name)} ${advice.as_of.jahr}`, target});
    return `<p class="text-sm muted mb-2">${head}</p>
        <ul class="space-y-2" data-advice-list>${advice.items.map(item => `
            <li class="p-3 rounded-xl text-sm ${css[item.priority] || 'rating-good'}" data-advice="${escapeHtml(item.code)}" data-priority="${escapeHtml(item.priority)}">
                <span class="badge" style="border:1px solid currentColor">${t('advice_prio_' + item.priority)}</span>
                ${escapeHtml(tp('advice_' + item.code, adviceParams(item.params)))}
            </li>`).join('')}
        </ul>`;
}

function renderFlexMonth(a) {
    if (!a || (!a.has_entries && !a.flex)) return `<p class="text-sm muted" data-fm-empty>${t('fm_no_data')}</p>`;
    const f2 = v => Number(v).toFixed(2);
    const totals = a.totals, flex = a.flex || {};
    const dash = '–';
    const tile = (label, value, key) => `<div class="tile" data-fm="${key}"><p class="text-xs font-semibold muted uppercase">${t(label)}</p><p class="text-lg font-bold">${value}</p></div>`;
    const tiles = [
        tile('fm_balance_start', flex.vorperiode != null ? signedHours(flex.vorperiode) : dash, 'balance_start'),
        tile('fm_balance_end', flex.gesamt != null ? `${signedHours(flex.gesamt)} ${flexBadge(flex.status)}` : dash, 'balance_end'),
        tile('fm_change_sap', flex.aktuell != null ? signedHours(flex.aktuell) : dash, 'change_sap'),
        tile('fm_change_calc', signedHours(totals.delta_calc), 'change_calc'),
        tile('fm_difference', a.difference != null ? signedHours(a.difference) : dash, 'difference'),
        tile('fm_avg_day', totals.avg_net != null ? `${f2(totals.avg_net)}h` : dash, 'avg_day'),
        tile('fm_avg_times', totals.avg_start ? `${totals.avg_start} – ${totals.avg_end}` : dash, 'avg_times'),
        tile('fm_longest', totals.longest ? `${f2(totals.longest.net)}h (${dateLabel(totals.longest.datum)})` : dash, 'longest'),
        tile('fm_long_days', totals.long_days, 'long_days'),
        tile('fm_outside', totals.early_days + totals.late_days, 'outside'),
        tile('fm_non_working', totals.non_working_days, 'non_working'),
        tile('fm_missing', `${totals.missing_days.length} (${f2(totals.missing_hours)}h)`, 'missing'),
    ].slice(0, a.has_entries ? 12 : 3).join('');    // without daily entries (e.g. after "Monat abschließen") only the statement figures mean anything
    const cell = 'padding:.25rem .4rem;text-align:right;white-space:nowrap';
    const left = 'padding:.25rem .4rem;text-align:left;white-space:nowrap';
    const tone = v => `color:var(${v > 0.004 ? '--success' : v < -0.004 ? '--error' : '--muted'})`;
    const weeks = a.weeks.map(w => `<tr><td style="${left}">${t('fm_week')} ${w.week}</td><td style="${cell}">${w.days}</td>
        <td style="${cell}">${f2(w.net)}h</td><td style="${cell}">${f2(w.soll)}h</td><td style="${cell};${tone(w.delta)};font-weight:700">${signedHours(w.delta)}</td></tr>`).join('');
    const days = a.days.map(d => `<tr data-fm-day="${d.datum}" style="${d.flags.includes('no_entry') ? 'opacity:.7' : ''}">
        <td style="${left}">${dateLabel(d.datum)}</td>
        <td style="${cell}">${d.start ? `${d.start}–${d.end}` : ''}</td><td style="${cell}">${d.entries ? f2(d.net) + 'h' : ''}</td>
        <td style="${cell};${tone(d.delta)};font-weight:700">${d.soll || d.net ? signedHours(d.delta) : ''}</td>
        <td style="${cell}">${signedHours(d.balance)}</td>
        <td style="${left};color:var(--warning);font-weight:600">${d.flags.map(fl => t('fm_flag_' + fl)).join(', ')}</td></tr>`).join('');
    const th = (label, align) => `<th style="padding:.25rem .4rem;text-align:${align};border-bottom:1px solid var(--border)">${t(label)}</th>`;
    return `
        <div data-fm-analysis>
            <h4 class="font-bold mb-2">${escapeHtml(monthLabel(a.monat_name))} ${a.year}</h4>
            ${a.has_entries && !a.complete ? `<p class="text-xs muted mb-2">${t('fm_incomplete')}</p>` : ''}
            <div class="grid grid-cols-2 md:grid-cols-3 gap-2 mb-2">${tiles}</div>
            ${a.has_entries ? '' : `<p class="text-sm muted" data-fm-empty>${t('fm_no_data')}</p></div>`}
            ${a.has_entries ? `<p class="text-xs muted mb-4">${t('fm_diff_hint')}</p>
            <h4 class="font-bold mb-1">${t('fm_weeks')}</h4>
            <table class="text-sm mb-4" style="width:100%;border-collapse:collapse"><thead><tr>${th('fm_week', 'left')}${th('fm_days', 'right')}${th('fm_col_net', 'right')}${th('fm_col_soll', 'right')}${th('fm_col_delta', 'right')}</tr></thead><tbody>${weeks}</tbody></table>
            <h4 class="font-bold mb-1">${t('fm_days')}</h4>
            <div style="overflow-x:auto"><table class="text-sm" style="width:100%;border-collapse:collapse"><thead><tr>${th('fm_col_date', 'left')}${th('fm_col_time', 'right')}${th('fm_col_net', 'right')}${th('fm_col_delta', 'right')}${th('fm_col_balance', 'right')}${th('fm_col_flags', 'left')}</tr></thead><tbody>${days}</tbody></table></div>
        </div>` : ''}`;
}

async function loadFlexMonth(value) {
    const [year, month] = String(value).split('-').map(Number);
    const target = document.getElementById('flex-month-body');
    if (!target || !year || !month) return;
    try {
        const res = await fetch(`/api/flex/month/${year}/${month}`);
        const data = await res.json();
        target.innerHTML = renderFlexMonth(data.analysis);
    } catch (e) {
        showMessage(t('err_flex') + e, 'error');
    }
}

const MONTH_NAMES_DE = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];

// Flextime trend: bars = change during the month, line = balance at the end of the month (inline SVG, theme colours).
function renderFlexChart(flex) {
    const series = ((flex && flex.series) || []).filter(e => typeof e.gesamt === 'number' || typeof e.aktuell === 'number');
    if (!series.length) return `<p class="text-sm muted" data-flex-empty>${t('flex_chart_empty')}</p>`;
    const W = 720, H = 320, L = 56, R = 46, T = 24, B = 54, pw = W - L - R, ph = H - T - B;     // right margin: labels of the limit lines
    const idx = e => e.jahr * 12 + e.monat - 1;
    const first = idx(series[0]), last = idx(series[series.length - 1]), n = last - first + 1;
    const values = [0];
    series.forEach(e => { if (typeof e.gesamt === 'number') values.push(e.gesamt); if (typeof e.aktuell === 'number') values.push(e.aktuell); });
    let lo = Math.min(...values), hi = Math.max(...values);
    const limits = (flex && flex.limits) || {yellow: 40, red: 60};
    const reachHigh = hi, reachLow = lo;
    lo = Math.min(lo, -limits.yellow); hi = Math.max(hi, limits.yellow);                       // the yellow band is always visible
    if (reachHigh > limits.yellow - 5) hi = Math.max(hi, limits.red + 8);                      // room for the red band where it matters
    if (reachLow < -(limits.yellow - 5)) lo = Math.min(lo, -(limits.red + 8));
    const raw = ((hi - lo) || 1) / 5, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw);
    lo = Math.floor(lo / step + 1e-9) * step;
    hi = Math.ceil(hi / step - 1e-9) * step;
    if (hi === lo) hi = lo + step;
    const y = v => T + ph * (hi - v) / (hi - lo);
    const slot = pw / n, x = e => L + slot * (idx(e) - first + 0.5);
    const fmtTick = v => (Number.isInteger(step) ? v.toFixed(0) : v.toFixed(1));
    const parts = [];
    const band = (from, to, color, kind) => {                      // from/to: balance values, drawn only inside the chart
        const a = Math.max(Math.min(from, to), lo), b = Math.min(Math.max(from, to), hi);
        if (b > a) parts.push(`<rect data-flex-band="${kind}" x="${L}" y="${y(b).toFixed(1)}" width="${pw}" height="${(y(a) - y(b)).toFixed(1)}" style="fill:var(${color})" fill-opacity="0.16"/>`);
    };
    band(limits.yellow, limits.red, '--warning', 'yellow'); band(limits.red, hi, '--error', 'red');
    band(-limits.red, -limits.yellow, '--warning', 'yellow'); band(lo, -limits.red, '--error', 'red');
    [[limits.yellow, '--warning'], [-limits.yellow, '--warning'], [limits.red, '--error'], [-limits.red, '--error']].forEach(([v, color]) => {
        if (v < lo || v > hi) return;
        parts.push(`<line data-flex-limit="${v}" x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" style="stroke:var(${color})" stroke-width="1.5" stroke-dasharray="5 4"/>`);
        parts.push(`<text x="${W - R + 4}" y="${(y(v) + 3.5).toFixed(1)}" text-anchor="start" font-size="10" font-weight="700" style="fill:var(${color})">${v > 0 ? '+' : '−'}${Math.abs(v)} h</text>`);
    });
    for (let v = lo; v <= hi + step / 1000; v += step) {
        parts.push(`<line x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" style="stroke:var(--border)" stroke-opacity="${Math.abs(v) < step / 1000 ? 1 : 0.3}" stroke-width="${Math.abs(v) < step / 1000 ? 1.5 : 1}"/>`);
        parts.push(`<text x="${L - 6}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end" font-size="11" style="fill:var(--muted)">${fmtTick(v)}</text>`);
    }
    const barWidth = Math.min(28, slot * 0.55);
    series.forEach(e => {
        if (typeof e.aktuell !== 'number') return;
        const top = y(Math.max(0, e.aktuell)), height = Math.max(1, Math.abs(y(e.aktuell) - y(0)));
        parts.push(`<rect data-flex-bar x="${(x(e) - barWidth / 2).toFixed(1)}" y="${top.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${height.toFixed(1)}" rx="2" style="fill:var(${e.aktuell >= 0 ? '--success' : '--error'})" fill-opacity="0.55"/>`);
    });
    const points = series.filter(e => typeof e.gesamt === 'number');
    for (let i = 1; i < points.length; i++) {
        const gap = idx(points[i]) - idx(points[i - 1]) > 1;
        parts.push(`<line x1="${x(points[i - 1]).toFixed(1)}" y1="${y(points[i - 1].gesamt).toFixed(1)}" x2="${x(points[i]).toFixed(1)}" y2="${y(points[i].gesamt).toFixed(1)}" style="stroke:var(--primary)" stroke-width="2.5"${gap ? ' stroke-dasharray="6 5"' : ''}/>`);
    }
    points.forEach((e, i) => {
        const ring = /^red/.test(e.status || '') ? '--error' : /^yellow/.test(e.status || '') ? '--warning' : '--surface';
        parts.push(`<circle data-flex-point data-status="${escapeHtml(e.status || '')}" cx="${x(e).toFixed(1)}" cy="${y(e.gesamt).toFixed(1)}" r="5" style="fill:var(--primary);stroke:var(${ring})" stroke-width="${ring === '--surface' ? 2 : 3}"/>`);
        if (points.length <= 14 || i === points.length - 1) {
            const above = e.gesamt >= 0;
            parts.push(`<text x="${x(e).toFixed(1)}" y="${(y(e.gesamt) + (above ? -10 : 18)).toFixed(1)}" text-anchor="middle" font-size="11" font-weight="700" style="fill:var(--text);stroke:var(--surface);stroke-width:3px;paint-order:stroke">${signedHours(e.gesamt).replace('h', '')}</text>`);
        }
    });
    const stride = Math.ceil(n / 14);
    for (let k = 0; k < n; k += stride) {
        const m = (first + k) % 12, year = Math.floor((first + k) / 12), cx = L + slot * (k + 0.5);
        parts.push(`<text x="${cx.toFixed(1)}" y="${H - B + 18}" text-anchor="middle" font-size="11" style="fill:var(--muted)">${escapeHtml(monthLabel(MONTH_NAMES_DE[m]).slice(0, 3))}</text>`);
        if (m === 0 || k === 0) parts.push(`<text x="${cx.toFixed(1)}" y="${H - B + 34}" text-anchor="middle" font-size="11" font-weight="700" style="fill:var(--text)">${year}</text>`);
    }
    const s = (flex && flex.summary) || {};
    const monthText = ref => (ref ? ` (${escapeHtml(monthLabel(ref.monat_name))} ${ref.jahr})` : '');
    const hasGap = points.some((e, i) => i > 0 && idx(e) - idx(points[i - 1]) > 1);
    const legend = (color, text, opacity) => `<span class="flex items-center gap-2"><span aria-hidden="true" style="display:inline-block;width:14px;height:14px;border-radius:3px;background:var(${color});opacity:${opacity}"></span>${text}</span>`;
    return `
        <div data-flex-chart>
            <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${escapeHtml(t('flex_chart_label'))}" style="width:100%;height:auto;max-width:100%">
                <title>${escapeHtml(t('flex_chart_label'))}</title>${parts.join('')}
            </svg>
            <div class="flex flex-wrap gap-4 text-sm mt-2">
                ${legend('--primary', t('flex_legend_total'), 1)}${legend('--success', t('flex_legend_change') + ' (+)', 0.55)}${legend('--error', t('flex_legend_change') + ' (−)', 0.55)}
            </div>
            <div class="flex flex-wrap gap-4 text-sm mt-1">${legend('--warning', t('flex_band_yellow'), 0.4)}${legend('--error', t('flex_band_red'), 0.4)}</div>
            ${s.latest != null ? `<p class="text-sm mt-2" data-flex-summary><strong>${t('flex_latest')}: ${signedHours(s.latest)}</strong>${monthText(s.latest_month)} · ${t('flex_min')}: ${signedHours(s.min)}${monthText(s.min_month)} · ${t('flex_max')}: ${signedHours(s.max)}${monthText(s.max_month)}${s.status ? ` · ${t('flex_status_label')}: <strong data-flex-status="${s.status}">${t('flex_status_' + s.status)}</strong>` : ''}</p>` : ''}
            ${hasGap ? `<p class="text-xs muted mt-1">${t('flex_gap_note')}</p>` : ''}
        </div>`;
}

async function handleFlexChart() {
    try {
        const res = await fetch('/api/report/final');
        const data = await res.json();
        const flex = data.report.flex;
        const months = (flex.series || []).filter(e => typeof e.gesamt === 'number' || typeof e.aktuell === 'number');
        const picker = months.length ? `
            <label class="field-label mt-4 mb-1 block" for="flex-month-select">${t('flex_month_pick')}</label>
            <select id="flex-month-select" class="field mb-3" onchange="loadFlexMonth(this.value)">${months.slice().reverse().map(e =>
                `<option value="${e.jahr}-${e.monat}">${escapeHtml(monthLabel(e.monat_name))} ${e.jahr}</option>`).join('')}</select>
            <div id="flex-month-body"></div>` : '';
        document.getElementById('flex-chart-body').innerHTML = `
            ${renderFlexChart(flex)}
            <h3 class="font-extrabold mt-6 mb-2">${t('flex_advice_title')}</h3>
            ${renderFlexAdvice(flex)}
            <h3 class="font-extrabold mt-6 mb-1">${t('flex_month_title')}</h3>
            ${picker}`;
        openDialog('flex-chart-modal');
        if (months.length) loadFlexMonth(document.getElementById('flex-month-select').value);
    } catch (e) {
        showMessage(t('err_flex') + e, 'error');
    }
}

function closeFlexChart() {
    { const dlg = document.getElementById('flex-chart-modal'); if (dlg.open) dlg.close(); }
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
