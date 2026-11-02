from flask import Blueprint, request, jsonify, Response
import io
import csv
import json
import hmac
import os
import secrets
import shutil
import tempfile
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from services.state_service import StateService
from services.calculation import (
    calculate_net_hours, 
    check_time_overlap, 
    is_working_day_valid,
    get_quartal_for_month
)
from services.pdf_service import PDFService
from services.report_service import ReportService
from services.final_report import build_final_report, sort_history
from config import Config

api = Blueprint('api', __name__)
state_service = StateService()
pdf_service = PDFService()
report_service = ReportService()

@api.route('/state', methods=['GET'])
def get_state():
    state = state_service.load_state()
    state_service.recalc_monthly_totals(state)
    state_service.save_state(state)
    return jsonify(state)

@api.route('/protokoll', methods=['POST'])
def protokoll():
    data = request.json
    state = state_service.load_state()

    datum = data.get('datum', '')
    start = data.get('start', '')
    end = data.get('end', '')

    if not datum or not start or not end:
        return jsonify({'success': False, 'message': 'Fehlende Pflichtfelder'}), 400

    try:
        pause = float(data.get('pause', 0))
    except ValueError:
        return jsonify({'success': False, 'message': 'Ungültige Pausenangabe'}), 400

    validation_error = is_working_day_valid(datum, state)
    if validation_error:
        return jsonify({'success': False, 'message': validation_error}), 400

    overlap_error = check_time_overlap(datum, start, end, state)
    if overlap_error:
        return jsonify({'success': False, 'message': overlap_error}), 400

    if start == end:                       # same as the Kotlin apps: no zero-length (or 24 h) entries
        return jsonify({'success': False, 'message': 'Ungültige Zeitangabe!'}), 400

    time_result = calculate_net_hours(start, end, pause)
    total_stunden = time_result['net']

    if total_stunden < 0:
        return jsonify({'success': False, 'message': 'Ungültige Zeitangabe!'}), 400

    try:
        remote_raw = data.get('remote', '')
        remote_stunden = float(remote_raw) if remote_raw != '' else total_stunden
    except ValueError:
        return jsonify({'success': False, 'message': 'Ungültige Remote-Stundenangabe'}), 400

    if remote_stunden > total_stunden:
        return jsonify({'success': False,
                        'message': f'Remote-Stunden ({remote_stunden}h) > Netto ({total_stunden:.2f}h)'}), 400

    day_list = state['daily_records'].get(datum)
    if not isinstance(day_list, list):
        day_list = [] if day_list is None else ([day_list] if isinstance(day_list, dict) else [])

    entry_id = f"{datum}|{start}|{end}|{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    new_entry = {
        'id': entry_id,
        'datum': datum,
        'startTime': start,
        'endTime': end,
        'pauseMinutes': pause,
        'remoteStundenHeute': remote_stunden,
        'totalStundenHeute': total_stunden,
        'pauseWarning': time_result['pause_warning'],
        'pauseWarningDe': time_result['pause_warning_de'],
        'pauseWarningEn': time_result['pause_warning_en']
    }
    day_list.append(new_entry)
    state['daily_records'][datum] = day_list

    state_service.recalc_monthly_totals(state)
    state_service.save_state(state)

    msg_de = f"Protokoll für {datum} gespeichert. Netto: {total_stunden:.2f}h"
    msg_en = f"Log for {datum} saved. Net: {total_stunden:.2f}h"
    warn_text = time_result['pause_warning_en'] if state.get('language', 'de') == 'en' else time_result['pause_warning_de']
    msg = msg_en if state.get('language', 'de') == 'en' else msg_de
    if warn_text:
        msg += f" | {warn_text}"

    return jsonify({'success': True, 'message': msg, 'state': state})

@api.route('/pdf/analyze', methods=['POST'])
def analyze_pdf():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Keine Datei hochgeladen'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Keine Datei ausgewählt'}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'success': False, 'message': 'Nur PDF-Dateien unterstützt'}), 400

    # Never use the client-supplied name as a path: it may contain "../" or be
    # absolute. Keep a sanitized version of the name (PDFService reads the date
    # range from it as a fallback) and save into a private scratch directory so
    # that concurrent uploads with the same name cannot collide.
    safe_name = secure_filename(file.filename) or 'upload.pdf'
    if not safe_name.lower().endswith('.pdf'):
        safe_name += '.pdf'

    scratch_dir = None
    try:
        # Use tempfile for cross-platform compatibility (Windows/Linux/Mac)
        scratch_dir = tempfile.mkdtemp(prefix='rw_upload_', dir=tempfile.gettempdir())
        temp_path = os.path.join(scratch_dir, safe_name)
        file.save(temp_path)

        result = pdf_service.analyze_pdf(temp_path)

        return jsonify(result)

    except Exception as e:
        print(f"CRITICAL ERROR in analyze_pdf: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Fehler bei PDF-Analyse: {str(e)}'
        }), 500

    finally:
        if scratch_dir:
            shutil.rmtree(scratch_dir, ignore_errors=True)

@api.route('/pdf/import', methods=['POST'])
def import_pdf_sessions():
    data = request.json
    state = state_service.load_state()

    sessions = data.get('sessions', [])
    imported_count = 0
    errors = []

    for session in sessions:
        try:
            datum = session.get('date')
            start = session.get('start_time')
            end = session.get('end_time')
            is_remote = session.get('is_remote', True)

            if not datum or not start or not end:
                errors.append(f"Ungültige Session: {session}")
                continue

            # Use allow_historical=True for PDF imports to accept past years/months
            validation_error = is_working_day_valid(datum, state, allow_historical=True)
            if validation_error:
                errors.append(f"{datum}: {validation_error}")
                continue

            overlap_error = check_time_overlap(datum, start, end, state)
            if overlap_error:
                errors.append(f"{datum}: {overlap_error}")
                continue

            time_result = calculate_net_hours(start, end, 0)
            total_stunden = time_result['net']
            remote_stunden = total_stunden if is_remote else 0

            day_list = state['daily_records'].get(datum, [])
            if not isinstance(day_list, list):
                day_list = [] if day_list is None else ([day_list] if isinstance(day_list, dict) else [])

            entry_id = f"{datum}|{start}|{end}|{int(datetime.now(timezone.utc).timestamp() * 1000)}"
            new_entry = {
                'id': entry_id,
                'datum': datum,
                'startTime': start,
                'endTime': end,
                'pauseMinutes': 0,
                'remoteStundenHeute': remote_stunden,
                'totalStundenHeute': total_stunden,
                'source': 'pdf_import',
                # A statement lists sessions without breaks (pause is stored as 0), so a break
                # warning would be wrong for every long session: no warning for imported entries.
                'pauseWarning': None,
                'pauseWarningDe': None,
                'pauseWarningEn': None
            }

            day_list.append(new_entry)
            state['daily_records'][datum] = day_list
            imported_count += 1

        except Exception as e:
            errors.append(f"Fehler bei Session {session}: {str(e)}")

    # Show the month of the statement that was just loaded, even if all of its sessions
    # were already present (duplicates): the user loaded that statement to look at it.
    for session in sessions:
        try:
            date_obj = datetime.strptime(session.get('date') or '', '%Y-%m-%d')
        except (ValueError, TypeError, AttributeError):
            continue
        month_names = list(Config.MONATS_NUMMERN.keys())
        state['view_month'] = month_names[date_obj.month - 1]
        state['view_year'] = date_obj.year
        break

    state_service.recalc_monthly_totals(state)
    state_service.save_state(state)

    msg = f"{imported_count} Sessions importiert"
    if errors:
        msg += f" ({len(errors)} Fehler)"

    return jsonify({
        'success': True,
        'message': msg,
        'imported_count': imported_count,
        'errors': errors,
        'state': state
    })

@api.route('/delete/<entry_id>', methods=['DELETE'])
def delete_record(entry_id):
    state = state_service.load_state()
    found = False
    for datum, val in list(state.get('daily_records', {}).items()):
        lst = val if isinstance(val, list) else ([val] if isinstance(val, dict) else [])
        for idx, rec in enumerate(list(lst)):
            if isinstance(rec, dict) and rec.get('id') == entry_id:
                del lst[idx]
                found = True
                break
        if found:
            if lst:
                state['daily_records'][datum] = lst
            else:
                del state['daily_records'][datum]
            break

    if not found:
        return jsonify({'success': False, 'message': 'Eintrag nicht gefunden'}), 404

    state_service.recalc_monthly_totals(state)
    state_service.save_state(state)
    return jsonify({'success': True, 'message': 'Eintrag gelöscht', 'state': state})

@api.route('/update/<entry_id>', methods=['PUT'])
def update_record(entry_id):
    data = request.json or {}
    state = state_service.load_state()

    datum = data.get('datum', '')
    start = data.get('start', '')
    end = data.get('end', '')

    if not datum or not start or not end:
        return jsonify({'success': False, 'message': 'Fehlende Pflichtfelder'}), 400

    try:
        pause = float(data.get('pause', 0))
    except ValueError:
        return jsonify({'success': False, 'message': 'Ungültige Pausenangabe'}), 400

    validation_error = is_working_day_valid(datum, state)
    if validation_error:
        return jsonify({'success': False, 'message': validation_error}), 400

    overlap_error = check_time_overlap(datum, start, end, state, exclude_id=entry_id)
    if overlap_error:
        return jsonify({'success': False, 'message': overlap_error}), 400

    if start == end:                       # same as the Kotlin apps: no zero-length (or 24 h) entries
        return jsonify({'success': False, 'message': 'Ungültige Zeitangabe!'}), 400

    time_result = calculate_net_hours(start, end, pause)
    total_stunden = time_result['net']
    if total_stunden < 0:
        return jsonify({'success': False, 'message': 'Ungültige Zeitangabe!'}), 400

    try:
        remote_raw = data.get('remote', '')
        remote_stunden = float(remote_raw) if remote_raw != '' else total_stunden
    except ValueError:
        return jsonify({'success': False, 'message': 'Ungültige Remote-Stundenangabe'}), 400

    if remote_stunden > total_stunden:
        return jsonify({'success': False,
                        'message': f'Remote-Stunden ({remote_stunden}h) > Netto ({total_stunden:.2f}h)'}), 400

    found = False
    for d, val in list(state.get('daily_records', {}).items()):
        lst = val if isinstance(val, list) else ([val] if isinstance(val, dict) else [])
        for i, rec in enumerate(list(lst)):
            if isinstance(rec, dict) and rec.get('id') == entry_id:
                found = True
                del lst[i]
                if lst:
                    state['daily_records'][d] = lst
                else:
                    del state['daily_records'][d]
                break
        if found:
            break

    if not found:
        return jsonify({'success': False, 'message': 'Eintrag nicht gefunden'}), 404

    updated_entry = {
        'id': entry_id,
        'datum': datum,
        'startTime': start,
        'endTime': end,
        'pauseMinutes': pause,
        'remoteStundenHeute': remote_stunden,
        'totalStundenHeute': total_stunden,
        'pauseWarning': time_result['pause_warning'],
        'pauseWarningDe': time_result['pause_warning_de'],
        'pauseWarningEn': time_result['pause_warning_en']
    }

    target_list = state['daily_records'].get(datum, [])
    if not isinstance(target_list, list):
        target_list = [] if target_list is None else ([target_list] if isinstance(target_list, dict) else [])
    target_list.append(updated_entry)
    state['daily_records'][datum] = target_list

    state_service.recalc_monthly_totals(state)
    state_service.save_state(state)

    msg_de = f"Eintrag aktualisiert für {datum}. Netto: {total_stunden:.2f}h"
    msg_en = f"Entry updated for {datum}. Net: {total_stunden:.2f}h"
    warn_text = time_result['pause_warning_en'] if state.get('language', 'de') == 'en' else time_result['pause_warning_de']
    msg = msg_en if state.get('language', 'de') == 'en' else msg_de
    if warn_text:
        msg += f" | {warn_text}"

    return jsonify({'success': True, 'message': msg, 'state': state})

@api.route('/quote', methods=['POST'])
def update_quote():
    data = request.json
    try:
        new_quote = float(data['quote'])
    except (KeyError, ValueError):
        return jsonify({'success': False, 'message': 'Ungültige Quote'}), 400

    if not (Config.MIN_INDIVIDUELLE_QUOTE_PROZENT <= new_quote <= Config.MAX_INDIVIDUELLE_QUOTE_PROZENT):
        return jsonify({'success': False,
                        'message': f'Quote muss zwischen {Config.MIN_INDIVIDUELLE_QUOTE_PROZENT}% und {Config.MAX_INDIVIDUELLE_QUOTE_PROZENT}% liegen'}), 400

    state = state_service.load_state()
    state['individuelle_quote_prozent'] = new_quote
    # recalculate for the VIEWED month (initialisiere_monat would use the system month)
    state_service.recalc_monthly_totals(state)
    state_service.save_state(state)

    return jsonify({'success': True, 'message': f'Quote auf {new_quote}% gesetzt', 'state': state})

@api.route('/sollstunden', methods=['POST'])
def update_sollstunden():
    data = request.json
    try:
        new_stunden = float(data['sollStunden'])
    except (KeyError, ValueError):
        return jsonify({'success': False, 'message': 'Ungültige Stunden'}), 400

    if not (1.0 <= new_stunden <= 10.0):
        return jsonify({'success': False,
                        'message': 'Soll-Stunden müssen zwischen 1.0 und 10.0 liegen'}), 400

    state = state_service.load_state()
    state['soll_stunden_pro_tag'] = new_stunden
    # recalculate for the VIEWED month (initialisiere_monat would use the system month)
    state_service.recalc_monthly_totals(state)
    state_service.save_state(state)

    return jsonify({'success': True, 'message': f'Soll-Stunden auf {new_stunden}h/Tag gesetzt', 'state': state})

@api.route('/darkmode', methods=['POST'])
def toggle_darkmode():
    data = request.json
    dark_mode = bool(data.get('darkMode', False))

    state = state_service.load_state()
    state['dark_mode'] = dark_mode
    state_service.save_state(state)

    return jsonify(
        {'success': True, 'message': f'Dark Mode {"aktiviert" if dark_mode else "deaktiviert"}', 'state': state})

@api.route('/language', methods=['POST'])
def set_language():
    data = request.json
    lang = data.get('language', 'de')
    if lang not in ('de', 'en'):
        return jsonify({'success': False, 'message': 'Unsupported language'}), 400
    state = state_service.load_state()
    state['language'] = lang
    state_service.save_state(state)
    return jsonify(
        {'success': True, 'message': 'Sprache geändert' if lang == 'de' else 'Language changed', 'state': state})

@api.route('/month/switch', methods=['POST'])
def switch_month():
    state = state_service.load_state()

    closing_month = state.get('view_month', state['aktueller_monat'])
    closing_year = state.get('view_year', state['aktuelles_jahr'])

    month_names = list(Config.MONATS_NUMMERN.keys())
    closing_index = month_names.index(closing_month)

    if closing_index == 11:
        next_month = "Januar"
        next_year = closing_year + 1
    else:
        next_month = month_names[closing_index + 1]
        next_year = closing_year

    state_service.recalc_monthly_totals(state)
    completed_month = state['current_month_data'].copy()

    soll_gesamt = completed_month.get('soll_stunden_gesamt', 0)
    ist_remote = completed_month.get('ist_remote_stunden_laufend', 0)
    tatsaechliche_remote_quote = (ist_remote / soll_gesamt * 100) if soll_gesamt > 0 else 0
    completed_month['tatsaechliche_remote_quote'] = tatsaechliche_remote_quote

    completed_month['quartal'] = get_quartal_for_month(closing_month, closing_year)

    # Close ONLY the viewed month: its entries leave the daily records, entries of every other
    # month stay. A month already in the history is not added twice: it is updated when it still
    # has entries (e.g. a statement was loaded again), otherwise the saved snapshot is kept.
    prefix = f"{closing_year}-{Config.MONATS_NUMMERN[closing_month]:02d}-"
    has_entries = any(k.startswith(prefix) and v for k, v in state.get('daily_records', {}).items())
    history = state['monatliche_historie']
    existing = next((i for i, m in enumerate(history)
                     if m.get('monat') == closing_month and m.get('jahr') == closing_year), None)
    history_changed = True
    if existing is None:
        history.append(completed_month)
    elif has_entries:
        history[existing] = completed_month
    else:
        history_changed = False
    state['monatliche_historie'] = sort_history(history)
    state['daily_records'] = {k: v for k, v in state.get('daily_records', {}).items() if not k.startswith(prefix)}

    state['aktuelles_jahr'] = next_year
    state['current_quartal'] = get_quartal_for_month(next_month, next_year)

    quartal_monate = Config.QUARTALS_PLANUNG.get(completed_month['quartal'], [])
    quartal_msg = None

    if history_changed and (closing_month == quartal_monate[-1] if quartal_monate else False):
        abgeschlossenes_quartal = completed_month['quartal']
        quartal_historie = [m for m in state['monatliche_historie']
                           if m.get('quartal') == abgeschlossenes_quartal]

        if len(quartal_historie) >= 3:
            gesamt_soll = sum(m['soll_stunden_gesamt'] for m in quartal_historie)
            gesamt_ist_remote = sum(m['ist_remote_stunden_laufend'] for m in quartal_historie)
            gesamt_ist_arbeitszeit = sum(m['ist_arbeitszeit_laufend'] for m in quartal_historie)

            monthly_quotes = [m.get('tatsaechliche_remote_quote', 0) for m in quartal_historie]
            quartal_quote = sum(monthly_quotes) / len(monthly_quotes) if monthly_quotes else 0

            for m in quartal_historie:
                m['quartal_quote'] = quartal_quote
                m['quartal_remote'] = gesamt_ist_remote
                m['quartal_gesamt'] = gesamt_ist_arbeitszeit
                m['quartal_soll'] = gesamt_soll

            aktuelle_quote = quartal_historie[0]['individuelle_quote']
            gesamt_max_remote = gesamt_soll * (aktuelle_quote / 100.0)

            if gesamt_ist_remote > gesamt_max_remote:
                neue_quote = max(aktuelle_quote - Config.QUOTEN_ANPASSUNG_PROZENT, Config.MIN_INDIVIDUELLE_QUOTE_PROZENT)
                quartal_msg = f"KRITISCH: Quote überschritten. Neue Quote: {neue_quote:.0f}%"
            else:
                neue_quote = min(aktuelle_quote + Config.QUOTEN_ANPASSUNG_PROZENT, Config.MAX_INDIVIDUELLE_QUOTE_PROZENT)
                quartal_msg = f"EINGEHALTEN: Neue Quote: {neue_quote:.0f}%"

            state['individuelle_quote_prozent'] = neue_quote

    state['aktueller_monat'] = next_month

    state['view_month'] = next_month
    state['view_year'] = next_year

    state_service.recalc_monthly_totals(state)
    state_service.save_state(state)

    msg = f"Monatswechsel zu {next_month} abgeschlossen."
    if quartal_msg:
        msg += f" | {quartal_msg}"

    return jsonify({'success': True, 'message': msg, 'quartal_msg': quartal_msg, 'state': state})

@api.route('/view/current_month', methods=['POST'])
def set_view_to_current_month():
    state = state_service.load_state()
    state['view_month'] = state['aktueller_monat']
    state['view_year'] = state['aktuelles_jahr']
    state_service.recalc_monthly_totals(state)
    state_service.save_state(state)

    lang = state.get('language', 'de')
    msg = f"Ansicht auf aktuellen Monat gesetzt: {state['aktueller_monat']} {state['aktuelles_jahr']}" if lang == 'de' else f"View set to current month: {state['aktueller_monat']} {state['aktuelles_jahr']}"

    return jsonify({'success': True, 'message': msg, 'state': state})

@api.route('/view/month', methods=['POST'])
def set_view_month():
    """Show any month (entries and totals of that month); the system month stays untouched."""
    data = request.get_json(silent=True) or {}
    month, year = data.get('month'), data.get('year')
    if month not in Config.MONATS_NUMMERN or isinstance(year, bool) or not isinstance(year, int) or not 1990 <= year <= 2100:
        return jsonify({'success': False, 'message': 'Ungültiger Monat oder ungültiges Jahr'}), 400
    state = state_service.load_state()
    state['view_month'] = month
    state['view_year'] = year
    state_service.recalc_monthly_totals(state)
    state_service.save_state(state)
    return jsonify({'success': True, 'message': f'Ansicht: {month} {year}', 'state': state})

@api.route('/report/final', methods=['GET'])
def final_report():
    """Quarterly final report over the closed months (see services/final_report.py)."""
    state = state_service.load_state()
    return jsonify({'success': True, 'report': build_final_report(state.get('monatliche_historie', []))})

@api.route('/export/daily_csv', methods=['GET'])
def export_daily_csv():
    state = state_service.load_state()
    
    # Helper to collect records
    dr = state.get('daily_records', {}) or {}
    flat = []
    if isinstance(dr, dict):
        for date_key, val in dr.items():
            if isinstance(val, list):
                flat.extend(val)
            elif isinstance(val, dict):
                flat.append(val)
    flat.sort(key=lambda r: (r.get('datum', ''), r.get('startTime', '')))
    
    # Filter for current view month
    view_month = state.get('view_month', state.get('aktueller_monat'))
    view_year = state.get('view_year', state.get('aktuelles_jahr'))
    view_month_num = Config.MONATS_NUMMERN.get(view_month, 1)
    
    records = []
    for r in flat:
        try:
            d = datetime.strptime(r.get('datum'), '%Y-%m-%d')
            if d.year == view_year and d.month == view_month_num:
                records.append(r)
        except:
            pass

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ['datum', 'startTime', 'endTime', 'pauseMinutes', 'remoteStundenHeute', 'totalStundenHeute', 'pauseWarning'])
    for r in records:
        writer.writerow([
            r.get('datum', ''), r.get('startTime', ''), r.get('endTime', ''), r.get('pauseMinutes', 0),
            r.get('remoteStundenHeute', 0.0), r.get('totalStundenHeute', 0.0),
            '' if r.get('source') == 'pdf_import' else r.get('pauseWarning', '')
        ])
    csv_bytes = output.getvalue().encode('utf-8-sig')
    filename = f"daily_records_{view_month}_{view_year}.csv"
    return Response(csv_bytes, mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename={filename}'})

@api.route('/report/monthly_pdf', methods=['GET'])
def monthly_pdf():
    year = request.args.get('year', type=int)
    month = request.args.get('month')

    state = state_service.load_state()
    target_month = month or state['current_month_data']['monat']
    target_year = year or state['current_month_data']['jahr']

    month_data = None
    is_current = (target_month == state['current_month_data']['monat'] and target_year == state['current_month_data']['jahr'])
    
    day_records = []
    if is_current:
        state_service.recalc_monthly_totals(state)
        month_data = state['current_month_data']
        
        # Collect records
        dr = state.get('daily_records', {}) or {}
        flat = []
        if isinstance(dr, dict):
            for date_key, val in dr.items():
                if isinstance(val, list):
                    flat.extend(val)
                elif isinstance(val, dict):
                    flat.append(val)
        flat.sort(key=lambda r: (r.get('datum', ''), r.get('startTime', '')))
        
        # Filter
        view_month_num = Config.MONATS_NUMMERN.get(target_month, 1)
        for r in flat:
            try:
                d = datetime.strptime(r.get('datum'), '%Y-%m-%d')
                if d.year == target_year and d.month == view_month_num:
                    day_records.append(r)
            except:
                pass
    else:
        for m in state.get('monatliche_historie', []):
            if m.get('monat') == target_month and m.get('jahr') == target_year:
                month_data = m
                break

    if not month_data:
        return jsonify({'success': False, 'message': 'Monat/Jahr nicht gefunden'}), 404

    try:
        pdf = report_service.generate_monthly_pdf(month_data, day_records)
        filename = f"Monatsbericht_{target_month}_{target_year}.pdf"
        return Response(pdf, mimetype='application/pdf', headers={'Content-Disposition': f'attachment; filename={filename}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'PDF generation failed: {str(e)}'}), 500

@api.route('/backup', methods=['GET'])
def backup_state():
    state = state_service.load_state()
    data = json.dumps(state, ensure_ascii=False, indent=2).encode('utf-8')
    return Response(data, mimetype='application/json',
                    headers={'Content-Disposition': 'attachment; filename=tracker_state_backup.json'})

@api.route('/restore', methods=['POST'])
def restore_state():
    if 'file' in request.files:
        file = request.files['file']
        content = file.read()
    else:
        content = request.get_data()
    try:
        new_state = json.loads(content)
    except Exception:
        return jsonify({'success': False, 'message': 'Ungültige JSON-Datei'}), 400

    required_keys = {'individuelle_quote_prozent', 'soll_stunden_pro_tag', 'aktuelles_jahr', 'aktueller_monat',
                     'daily_records', 'current_month_data'}
    if not required_keys.issubset(new_state.keys()):
        return jsonify({'success': False, 'message': 'JSON enthält nicht alle erforderlichen Felder'}), 400

    try:
        state_service.recalc_monthly_totals(new_state)  # a backup may carry stale totals
    except Exception:
        pass

    if state_service.save_state(new_state):
        return jsonify({'success': True, 'message': 'Wiederherstellung erfolgreich', 'state': new_state})
    else:
        return jsonify({'success': False, 'message': 'Speichern fehlgeschlagen'}), 500

@api.route('/delete_all_entries', methods=['POST'])
def delete_all_entries():
    state = state_service.load_state()
    state['daily_records'] = {}
    state_service.recalc_monthly_totals(state)
    state_service.save_state(state)

    lang = state.get('language', 'de')
    msg = 'Alle Einträge wurden gelöscht' if lang == 'de' else 'All entries have been deleted'

    return jsonify({'success': True, 'message': msg, 'state': state})

@api.route('/delete_month/<string:month_name>/<int:year>', methods=['DELETE'])
def delete_month_from_history(month_name: str, year: int):
    state = state_service.load_state()
    lang = state.get('language', 'de')

    historie = state.get('monatliche_historie', [])
    original_length = len(historie)

    state['monatliche_historie'] = [
        m for m in historie
        if not (m.get('jahr') == year and m.get('monat') == month_name)
    ]

    if len(state['monatliche_historie']) < original_length:
        state_service.save_state(state)
        msg = f'Monat {month_name} {year} wurde gelöscht' if lang == 'de' else f'Month {month_name} {year} has been deleted'
        return jsonify({'success': True, 'message': msg, 'state': state})
    else:
        msg = 'Monat nicht gefunden' if lang == 'de' else 'Month not found'
        return jsonify({'success': False, 'message': msg}), 404

@api.route('/clear_all_history', methods=['POST'])
def clear_all_history():
    """Clear all monthly history and reset to current month."""
    state = state_service.load_state()
    lang = state.get('language', 'de')

    # Count before clearing
    history_count = len(state.get('monatliche_historie', []))

    # Clear history
    state['monatliche_historie'] = []

    # Clear daily records
    state['daily_records'] = {}

    # Reset to current system month
    now = datetime.now()
    month_names = list(Config.MONATS_NUMMERN.keys())
    current_month = month_names[now.month - 1]
    current_year = now.year

    state['aktueller_monat'] = current_month
    state['aktuelles_jahr'] = current_year
    state['view_month'] = current_month
    state['view_year'] = current_year
    state['current_quartal'] = get_quartal_for_month(current_month, current_year)

    # Reset quote to default
    state['individuelle_quote_prozent'] = Config.MIN_INDIVIDUELLE_QUOTE_PROZENT

    # Recalculate
    state_service.recalc_monthly_totals(state)
    state_service.save_state(state)

    if lang == 'de':
        msg = f'Komplette Historie gelöscht ({history_count} Monate). Zurückgesetzt auf {current_month} {current_year}.'
    else:
        msg = f'Complete history cleared ({history_count} months). Reset to {current_month} {current_year}.'

    return jsonify({'success': True, 'message': msg, 'state': state})


# Stopping the program must not be possible for other computers, for other web
# pages open in the browser (a cross-site POST needs no body), or via DNS
# rebinding. The app's own page receives this per-run token in a <meta> tag and
# sends it in a custom header, which other sites cannot do without a CORS
# preflight that this server never grants.
SHUTDOWN_TOKEN = secrets.token_urlsafe(32)
_LOOPBACK_ADDRESSES = {'127.0.0.1', '::1', '::ffff:127.0.0.1'}
_LOCAL_HOST_NAMES = {'localhost', '127.0.0.1', '[::1]'}


def _shutdown_refusal():
    """Return the reason this request may not stop the server, or None."""
    if request.remote_addr not in _LOOPBACK_ADDRESSES:
        return 'client is not on this computer'

    host = request.host.lower()
    host_name = host[:host.index(']') + 1] if host.startswith('[') else host.split(':')[0]
    if host_name not in _LOCAL_HOST_NAMES:
        return f"unexpected Host header '{request.host}'"

    origin = request.headers.get('Origin')
    if origin is not None and origin != request.host_url.rstrip('/'):
        return f"cross-origin request from '{origin}'"

    fetch_site = request.headers.get('Sec-Fetch-Site')
    if fetch_site and fetch_site.lower() not in ('same-origin', 'none'):
        return f"Sec-Fetch-Site '{fetch_site}'"

    supplied = request.headers.get('X-RW-Token', '')
    if not hmac.compare_digest(supplied.encode('utf-8'), SHUTDOWN_TOKEN.encode('utf-8')):
        return 'missing or wrong token'
    return None


@api.route('/shutdown', methods=['POST'])
def shutdown_server():
    """Shutdown the Flask server gracefully (local, same-site, token required)."""
    refusal = _shutdown_refusal()
    if refusal:
        print(f"WARNING: /api/shutdown refused: {refusal}")
        return jsonify({'success': False, 'message': 'Shutdown nicht erlaubt'}), 403

    state = state_service.load_state()
    state_service.save_state(state)

    import threading
    def _shutdown():
        import time
        time.sleep(1)
        os._exit(0)
    threading.Thread(target=_shutdown, daemon=True).start()
    return jsonify({'success': True, 'message': 'Server wird heruntergefahren...'})
