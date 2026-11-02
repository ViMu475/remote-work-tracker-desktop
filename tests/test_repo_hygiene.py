"""GDPR guard: the repository must stay free of personal data (see tools/check_privacy.py)."""
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import check_privacy  # noqa: E402


def test_repository_contains_no_personal_data():
    files = check_privacy.publishable_files(ROOT)
    if files is None:
        pytest.skip('not a Git checkout (a working folder may hold local, ignored files)')
    assert check_privacy.scan(ROOT, files) == []


@pytest.mark.parametrize('name', ['statement.pdf', 'Zeitnachweis_20310101_20310131.PDF', 'screenshot.png', 'export.csv',
                                  'tracker_state.json', 'tracker_state_backup.json', '.env', '.env.local',
                                  'remote_tracker_backup_2031.json', 'daily_records_Mai_2031.csv', 'data.sqlite'])
def test_forbidden_files_are_found(tmp_path, name):
    (tmp_path / name).write_bytes(b'x')
    assert [f[2] for f in check_privacy.scan(str(tmp_path))] == ['forbidden file type or name']


@pytest.mark.parametrize('text, what', [
    ('contact: someone@company.de', 'e-mail address'),
    ('Musterstraße 12', 'street address'),
    ('Hauptstr. 7', 'street address'),
    ('80331 München', 'postal code and city'),
    ('Tel. +49 89 1234567', 'phone number'),
    ('Tel. 089 12345678', 'phone number'),
    ('Personalnummer 12345678', 'personnel number'),
    ('cd /home/alice/work', 'home directory of a user'),
    ('C:\\Users\\Bob\\Documents\\x', 'home directory of a user'),
])
def test_personal_patterns_are_found(tmp_path, text, what):
    (tmp_path / 'notes.md').write_text(text, encoding='utf-8')
    assert what in [f[2] for f in check_privacy.scan(str(tmp_path))]


@pytest.mark.parametrize('text', [
    'mail: someone@example.com', 'ViMu475@users.noreply.github.com', 'cd <project folder> && python app.py',
    'Version 3.12.10 of 2031-07-01', 'port 5000 on 127.0.0.1', '8,50 h from 08:00 to 16:30', 'C:\\Users\\<user>\\x',
])
def test_harmless_text_is_not_flagged(tmp_path, text):
    (tmp_path / 'notes.md').write_text(text, encoding='utf-8')
    assert check_privacy.scan(str(tmp_path)) == []


def test_ignored_folders_are_skipped(tmp_path):
    (tmp_path / 'real_statements').mkdir()
    (tmp_path / 'real_statements' / 'a.pdf').write_bytes(b'x')
    assert check_privacy.scan(str(tmp_path)) == []
