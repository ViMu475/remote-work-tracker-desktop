"""The batch import dialog: every message is translated and every element the script uses exists."""
import os
import re

import pytest

from services.statement_import import ERRORS, WARNINGS

ROOT = os.path.join(os.path.dirname(__file__), '..')
JS = open(os.path.join(ROOT, 'static', 'js', 'app.js'), encoding='utf-8').read()
HTML = open(os.path.join(ROOT, 'templates', 'index.html'), encoding='utf-8').read()


def language_block(name):
    """The text of translations.<name> = { ... } (the object ends at the first line that is just a closing brace)."""
    start = JS.index(f'    {name}: {{') + len(f'    {name}: {{')
    return JS[start:JS.index('\n    }', start)]


def keys(block):
    return set(re.findall(r"^\s{8}(\w+):", block, re.M)) | set(re.findall(r"[,{]\s*(\w+):\s*'", block))


DE, EN = keys(language_block('de')), keys(language_block('en'))
BATCH_KEYS = {k for k in DE | EN if k.startswith(('batch_', 'issue_'))}


def test_both_languages_have_the_same_batch_texts():
    assert BATCH_KEYS and {k for k in DE if k.startswith(('batch_', 'issue_'))} == {k for k in EN if k.startswith(('batch_', 'issue_'))}


@pytest.mark.parametrize('code', sorted(set(ERRORS) | set(WARNINGS) | {'needs_confirmation'}))
def test_every_issue_the_server_can_report_has_a_text_in_both_languages(code):
    assert f'issue_{code}' in DE and f'issue_{code}' in EN


def test_the_translated_texts_use_the_same_placeholders():
    def texts(block):
        return dict(re.findall(r"(\w+): '((?:[^'\\]|\\.)*)'", block))
    de, en = texts(language_block('de')), texts(language_block('en'))
    for key in BATCH_KEYS:
        assert sorted(re.findall(r'\{\w+\}', de[key])) == sorted(re.findall(r'\{\w+\}', en[key])), key


def test_the_script_only_uses_elements_that_exist():
    ids = set(re.findall(r"getElementById\('(batch-[\w-]+)'\)", JS))
    assert ids >= {'batch-reports', 'batch-import-btn', 'batch-file-input', 'batch-analyze-btn', 'batch-import-modal'}
    for element_id in ids:
        assert f'id="{element_id}"' in HTML, element_id


def test_dialog_and_button_are_in_the_page():
    assert "openDialog('batch-import-modal')" in HTML
    tag = re.search(r'<input type="file" id="batch-file-input"[^>]*>', HTML).group(0)
    assert 'multiple' in tag and 'accept=".pdf"' in tag
    for handler in ('handleBatchAnalyze', 'handleBatchImport', 'closeBatchModal', 'resetBatchModal'):
        assert f'function {handler}' in JS and handler in HTML


def test_the_dialog_sends_what_the_server_expects():
    assert "formData.append('files'" in JS and '/api/pdf/batch/analyze' in JS and '/api/pdf/batch/import' in JS
    for field in ('year', 'month', 'sessions', 'flex_balance', 'confirmed', 'quote'):
        assert field in JS.split('async function handleBatchImport')[1]
