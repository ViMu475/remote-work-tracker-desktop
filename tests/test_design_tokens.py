"""WCAG 2.x contrast of the shared design tokens (the same values are used by the Android and iOS apps).

The colour pairs are read from the :root / .dark-mode blocks of static/css/app.css, so a change of the
stylesheet that breaks AA fails here. Normal text needs 4.5:1, large text and UI components 3:1.
"""
import os
import re

import pytest

ROOT = os.path.join(os.path.dirname(__file__), '..')
CSS = open(os.path.join(ROOT, 'static', 'css', 'app.css'), encoding='utf-8').read()
HTML = open(os.path.join(ROOT, 'templates', 'index.html'), encoding='utf-8').read()


def _vars(block):
    def full(v):   # the minifier writes #fff for #ffffff
        v = v.upper()
        return '#' + ''.join(c * 2 for c in v[1:]) if len(v) == 4 else v
    return {k: full(v) for k, v in re.findall(r'--([\w-]+):\s*(#[0-9a-fA-F]{3,6})\b', block)}


def _block(selector_start):
    i = CSS.index(selector_start) + len(selector_start)
    return CSS[i:CSS.index('}', i)]


LIGHT = _vars(_block(':root{'))
DARK = _vars(_block('.dark-mode{'))
DARK_MEDIA = _vars(_block('(prefers-color-scheme:dark){:root:not(.light-mode){'))


def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hexcolor):
    h = hexcolor.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# (foreground token, background token, minimum ratio)
TEXT_PAIRS = [
    ('on-primary', 'primary', 4.5), ('on-success', 'success', 4.5), ('on-warning', 'warning', 4.5),
    ('on-error', 'error', 4.5), ('on-info', 'info', 4.5), ('on-neutral', 'neutral', 4.5),
    ('text', 'surface', 4.5), ('text', 'card', 4.5), ('text', 'page', 4.5),
    ('muted', 'surface', 4.5), ('muted', 'card', 4.5), ('muted', 'page', 4.5),
    ('primary', 'surface', 4.5), ('primary', 'card', 4.5),     # links / headings in the accent colour
    ('error', 'surface', 4.5),                                  # outlined danger buttons, warnings
    ('good-fg', 'good-bg', 4.5), ('tight-fg', 'tight-bg', 4.5), ('bad-fg', 'bad-bg', 4.5),
    ('text', 'bad-bg', 4.5),
]
UI_PAIRS = [('border', 'surface', 3.0), ('primary', 'surface', 3.0), ('error', 'bad-bg', 3.0)]


@pytest.mark.parametrize('theme,tokens', [('light', LIGHT), ('dark', DARK), ('dark-media', DARK_MEDIA)])
@pytest.mark.parametrize('fg,bg,minimum', TEXT_PAIRS + UI_PAIRS)
def test_contrast_pairs(theme, tokens, fg, bg, minimum):
    ratio = contrast(tokens[fg], tokens[bg])
    assert ratio >= minimum, f'{theme}: {fg} {tokens[fg]} on {bg} {tokens[bg]} = {ratio:.2f}:1 (< {minimum})'


def test_specified_token_values():
    assert {LIGHT[k] for k in ('primary', 'success', 'warning', 'error', 'info')} == \
        {'#4F46E5', '#047857', '#B45309', '#B91C1C', '#1D4ED8'}
    assert (LIGHT['text'], LIGHT['muted'], LIGHT['surface'], LIGHT['card']) == ('#111827', '#4B5563', '#FFFFFF', '#F3F4F6')
    assert (DARK['page'], DARK['surface'], DARK['card']) == ('#111827', '#1F2937', '#374151')
    assert (DARK['primary'], DARK['on-primary'], DARK['success'], DARK['on-success']) == ('#A5B4FC', '#1E1B4B', '#34D399', '#052E1C')
    assert (DARK['warning'], DARK['on-warning'], DARK['error'], DARK['on-error']) == ('#FBBF24', '#1F1300', '#FCA5A5', '#450A0A')


def test_light_filled_buttons_with_white_text_reach_5_to_1():
    for token in ('primary', 'success', 'warning', 'error', 'info'):
        assert contrast('#FFFFFF', LIGHT[token]) >= 5.0, token


def test_dark_media_block_matches_dark_class():
    assert DARK_MEDIA == DARK


def test_page_uses_no_external_resources_and_has_a_focus_style():
    assert 'http://' not in HTML.replace('http://www.w3.org', '') and 'https://' not in HTML
    assert ':focus-visible{outline:3px solid var(--primary);outline-offset:2px}' in CSS.replace('\n', '')
