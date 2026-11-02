"""Startup safety: local-only by default, debug only on explicit opt-in, and a
predictable location for the state file when running as a packaged .exe."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import app as app_module
from config import resolve_data_file


# ── server_settings ───────────────────────────────────────────────────

class TestServerSettings:
    def test_defaults_are_local_only_without_debug(self):
        s = app_module.server_settings({})
        assert s == {'host': '127.0.0.1', 'port': 5000, 'debug': False,
                     'open_browser': True}

    def test_port_from_environment(self):
        assert app_module.server_settings({'PORT': '8081'})['port'] == 8081

    @pytest.mark.parametrize('bad', ['abc', '', '0', '-5', '70000', '5000.5'])
    def test_invalid_port_falls_back_to_default(self, bad):
        assert app_module.server_settings({'PORT': bad})['port'] == 5000

    @pytest.mark.parametrize('value', ['1', 'true', 'TRUE', 'Yes', 'on'])
    def test_debug_can_be_enabled_on_loopback(self, value):
        s = app_module.server_settings({'RW_DEBUG': value})
        assert s['debug'] is True
        assert s['host'] == '127.0.0.1'

    @pytest.mark.parametrize('value', ['0', '', 'false', 'no', 'off', 'maybe'])
    def test_debug_stays_off_for_other_values(self, value):
        assert app_module.server_settings({'RW_DEBUG': value})['debug'] is False

    def test_flask_debug_variable_alone_does_not_enable_debug(self):
        # Flask's own FLASK_DEBUG must not silently turn on the debugger here.
        assert app_module.server_settings({'FLASK_DEBUG': '1'})['debug'] is False

    def test_public_host_needs_explicit_opt_in(self):
        s = app_module.server_settings({'HOST': '0.0.0.0'})
        assert s['host'] == '0.0.0.0'
        assert s['debug'] is False

    def test_debug_is_refused_on_a_public_host(self):
        s = app_module.server_settings({'HOST': '0.0.0.0', 'RW_DEBUG': '1'})
        assert s['host'] == '0.0.0.0'
        assert s['debug'] is False

    @pytest.mark.parametrize('host', ['127.0.0.1', 'localhost', '::1'])
    def test_debug_allowed_on_every_loopback_name(self, host):
        s = app_module.server_settings({'HOST': host, 'RW_DEBUG': '1'})
        assert s['debug'] is True

    def test_blank_host_falls_back_to_loopback(self):
        assert app_module.server_settings({'HOST': '  '})['host'] == '127.0.0.1'

    def test_browser_opening_can_be_disabled(self):
        assert app_module.server_settings({'RW_NO_BROWSER': '1'})['open_browser'] is False

    def test_reads_the_real_environment_by_default(self, monkeypatch):
        monkeypatch.setenv('RW_DEBUG', '1')
        monkeypatch.setenv('PORT', '9999')
        s = app_module.server_settings()
        assert s['debug'] is True and s['port'] == 9999


# ── no SECRET_KEY ─────────────────────────────────────────────────────

APP_DIR = os.path.join(os.path.dirname(__file__), '..')
SESSION_USE = [
    r'from\s+flask\s+import[^\n]*\b(session|flash|get_flashed_messages)\b',
    r'\bflask\.session\b',
    r'\bflash\s*\(',
    r'\bsession\s*\[',
    r'flask_login|flask_wtf|itsdangerous',
]


def _project_sources():
    import re
    paths = ['app.py', 'config.py', 'mcp_server.py']
    for folder in ('routes', 'services'):
        base = os.path.join(APP_DIR, folder)
        paths += [os.path.join(folder, f) for f in os.listdir(base) if f.endswith('.py')]
    paths += [os.path.join('templates', f) for f in os.listdir(os.path.join(APP_DIR, 'templates'))]
    for rel in paths:
        with open(os.path.join(APP_DIR, rel), encoding='utf-8') as fh:
            yield rel, fh.read()


class TestNoSecretKey:
    """The app has no sessions, flash messages or signed cookies, so Flask needs
    no secret key. A known default key would only make forged cookies possible
    if sessions were added later; without a key Flask fails loudly instead."""

    def test_config_defines_no_secret_key(self):
        from config import Config
        assert not hasattr(Config, 'SECRET_KEY')
        with open(os.path.join(APP_DIR, 'config.py'), encoding='utf-8') as fh:
            assert 'SECRET_KEY' not in fh.read()

    def test_flask_app_has_no_secret_key(self):
        assert app_module.app.secret_key is None
        assert app_module.app.config.get('SECRET_KEY') is None

    def test_environment_variable_is_not_picked_up(self, monkeypatch):
        monkeypatch.setenv('SECRET_KEY', 'from-the-environment')
        from flask import Flask
        from config import Config
        fresh = Flask(__name__)
        fresh.config.from_object(Config)
        assert fresh.secret_key is None

    def test_start_page_and_state_work_without_a_key(self, client):
        assert client.get('/').status_code == 200
        assert client.get('/api/state').status_code == 200

    def test_code_uses_no_sessions_or_signed_cookies(self):
        import re
        offenders = [(rel, pat) for rel, text in _project_sources()
                     for pat in SESSION_USE if re.search(pat, text)]
        assert offenders == [], (
            'Sessions/flash/signing need a SECRET_KEY. Add one deliberately '
            f'(random per installation, never a default) if this is intended: {offenders}')


# ── resolve_data_file ─────────────────────────────────────────────────

class TestResolveDataFile:
    def test_development_default_is_relative(self):
        assert resolve_data_file({}, frozen=False) == 'tracker_state.json'

    def test_frozen_exe_stores_next_to_the_executable(self, tmp_path):
        exe = str(tmp_path / 'RemoteWorkTracker.exe')
        path = resolve_data_file({}, frozen=True, executable=exe)
        assert path == os.path.join(str(tmp_path), 'tracker_state.json')

    def test_environment_override_wins(self, tmp_path):
        target = str(tmp_path / 'custom.json')
        assert resolve_data_file({'RW_DATA_FILE': target}, frozen=True,
                                 executable='/x/app.exe') == target
        assert resolve_data_file({'RW_DATA_FILE': target}, frozen=False) == target

    def test_blank_override_is_ignored(self):
        assert resolve_data_file({'RW_DATA_FILE': '  '}, frozen=False) == 'tracker_state.json'
