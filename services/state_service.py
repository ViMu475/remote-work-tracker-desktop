import json
import os
from datetime import datetime, timezone
from config import Config
from services.calculation import (
    get_current_month_from_system, 
    get_quartal_for_month, 
    berechne_soll_stunden_monat,
    check_time_overlap,
    is_working_day_valid,
    calculate_net_hours
)

class StateService:
    def __init__(self, data_file=Config.DATA_FILE):
        self.data_file = data_file

    def get_initial_state(self):
        current_month, current_year = get_current_month_from_system()
        current_quartal = get_quartal_for_month(current_month, current_year)

        return {
            'individuelle_quote_prozent': Config.BASIS_QUOTE_PROZENT,
            'soll_stunden_pro_tag': Config.SOLL_STUNDEN_PRO_TAG,
            'aktuelles_jahr': current_year,
            'current_quartal': current_quartal,
            'aktueller_monat': current_month,
            'dark_mode': False,
            'language': 'de',
            'monatliche_historie': [],
            'daily_records': {},
            'current_month_data': {
                'monat': current_month,
                'jahr': current_year,
                'soll_stunden_gesamt': 0.0,
                'ist_remote_stunden_laufend': 0.0,
                'ist_arbeitszeit_laufend': 0.0,
                'max_remote_stunden': 0.0,
                'individuelle_quote': Config.BASIS_QUOTE_PROZENT
            }
        }

    def load_state(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    
                    # Ensure defaults
                    if 'soll_stunden_pro_tag' not in state:
                        state['soll_stunden_pro_tag'] = Config.SOLL_STUNDEN_PRO_TAG
                    if 'dark_mode' not in state:
                        state['dark_mode'] = False
                    if 'language' not in state:
                        state['language'] = 'de'
                    if 'daily_records' not in state:
                        state['daily_records'] = {}

                    # Update current date info
                    system_month, system_year = get_current_month_from_system()
                    month_changed = (state.get('aktueller_monat') != system_month or
                                    state.get('aktuelles_jahr') != system_year)

                    state['aktueller_monat'] = system_month
                    state['aktuelles_jahr'] = system_year
                    state['current_quartal'] = get_quartal_for_month(system_month, system_year)

                    if 'current_month_data' not in state:
                        state['current_month_data'] = {}

                    if 'view_month' not in state:
                        state['view_month'] = system_month
                    if 'view_year' not in state:
                        state['view_year'] = system_year

                    # Migration logic for IDs (simplified from original)
                    changed = month_changed
                    dr = state.get('daily_records', {})
                    if isinstance(dr, dict):
                        for dkey, val in list(dr.items()):
                            if isinstance(val, dict):
                                rec = val
                                if 'id' not in rec:
                                    sid = f"{rec.get('datum', dkey)}|{rec.get('startTime', '')}|{rec.get('endTime', '')}|{int(datetime.now(timezone.utc).timestamp() * 1000)}"
                                    rec['id'] = sid
                                    changed = True
                                dr[dkey] = [rec]
                                changed = True
                            elif isinstance(val, list):
                                new_list = []
                                for rec in val:
                                    if isinstance(rec, dict) and 'id' not in rec:
                                        rec['id'] = f"{rec.get('datum', dkey)}|{rec.get('startTime', '')}|{rec.get('endTime', '')}|{int(datetime.now(timezone.utc).timestamp() * 1000)}"
                                        changed = True
                                    new_list.append(rec)
                                dr[dkey] = new_list
                        state['daily_records'] = dr

                    # The monthly totals must always describe the month that is being viewed.
                    # The stored copy can be stale (view switched, backup restored, ...), so
                    # never hand it out without recalculating.
                    try:
                        self.recalc_monthly_totals(state)
                    except Exception:
                        pass
                    if changed:
                        self.save_state(state)
                    return state
            except Exception as e:
                print(f"Fehler beim Laden: {e}")
        return self.get_initial_state()

    def save_state(self, state):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Fehler beim Speichern: {e}")
            return False

    def calculate_quartal_totals(self, state):
        current_quartal = state.get('current_quartal', 'Q4/2025')
        quartal_monate = Config.QUARTALS_PLANUNG.get(current_quartal, [])

        quartal_remote = 0.0
        quartal_gesamt = 0.0
        quartal_soll = 0.0

        dr = state.get('daily_records', {}) or {}
        month_names_de = list(Config.MONATS_NUMMERN.keys())

        if isinstance(dr, dict):
            for date_key, val in dr.items():
                try:
                    date_obj = datetime.strptime(date_key, '%Y-%m-%d')
                    monat_name = month_names_de[date_obj.month - 1]

                    if monat_name in quartal_monate:
                        if isinstance(val, list):
                            for r in val:
                                try:
                                    quartal_remote += float(r.get('remoteStundenHeute', 0.0))
                                    quartal_gesamt += float(r.get('totalStundenHeute', 0.0))
                                except Exception:
                                    pass
                except Exception:
                    pass

        for monat_name in quartal_monate:
            monat_nummer = Config.MONATS_NUMMERN[monat_name]
            soll = berechne_soll_stunden_monat(state['aktuelles_jahr'], monat_nummer, state['soll_stunden_pro_tag'])
            quartal_soll += soll

        return {
            'quartal_remote': quartal_remote,
            'quartal_gesamt': quartal_gesamt,
            'quartal_soll': quartal_soll,
            'quartal_quote': (quartal_remote / quartal_soll * 100) if quartal_soll > 0 else 0.0
        }

    def recalc_monthly_totals(self, state):
        total_remote = 0.0
        total_netto = 0.0
        dr = state.get('daily_records', {}) or {}

        view_month = state.get('view_month', state.get('aktueller_monat'))
        view_year = state.get('view_year', state.get('aktuelles_jahr'))
        view_month_num = Config.MONATS_NUMMERN.get(view_month, 1)

        if isinstance(dr, dict):
            for date_key, val in dr.items():
                try:
                    date_obj = datetime.strptime(date_key, '%Y-%m-%d')
                    if date_obj.year != view_year or date_obj.month != view_month_num:
                        continue
                except Exception:
                    continue

                if isinstance(val, list):
                    for r in val:
                        try:
                            total_remote += float(r.get('remoteStundenHeute', 0.0))
                            total_netto += float(r.get('totalStundenHeute', 0.0))
                        except Exception:
                            pass

        state['current_month_data']['ist_remote_stunden_laufend'] = total_remote
        state['current_month_data']['ist_arbeitszeit_laufend'] = total_netto

        soll = berechne_soll_stunden_monat(view_year, view_month_num, state['soll_stunden_pro_tag'])
        quote = state['individuelle_quote_prozent']
        max_remote = soll * (quote / 100.0)

        state['current_month_data']['soll_stunden_gesamt'] = soll
        state['current_month_data']['max_remote_stunden'] = max_remote
        state['current_month_data']['individuelle_quote'] = quote
        state['current_month_data']['monat'] = view_month
        state['current_month_data']['jahr'] = view_year

        quartal_data = self.calculate_quartal_totals(state)
        state['quartal_data'] = quartal_data

    def initialisiere_monat(self, state, monat_name: str, should_save: bool = True):
        monat_nummer = Config.MONATS_NUMMERN[monat_name]
        soll = berechne_soll_stunden_monat(state['aktuelles_jahr'], monat_nummer, state['soll_stunden_pro_tag'])
        quote = state['individuelle_quote_prozent']
        max_remote = soll * (quote / 100.0)

        state['aktueller_monat'] = monat_name

        if should_save:
            state['daily_records'] = {}
            state['current_month_data'] = {
                'monat': monat_name,
                'jahr': state['aktuelles_jahr'],
                'soll_stunden_gesamt': soll,
                'ist_remote_stunden_laufend': 0.0,
                'ist_arbeitszeit_laufend': 0.0,
                'max_remote_stunden': max_remote,
                'individuelle_quote': quote
            }
        else:
            self.recalc_monthly_totals(state)
            state['current_month_data']['soll_stunden_gesamt'] = soll
            state['current_month_data']['max_remote_stunden'] = max_remote
            state['current_month_data']['individuelle_quote'] = quote
