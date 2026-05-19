import os
import re

_SRC = os.path.join(os.path.dirname(__file__), '..', 'nhl-dashboard', 'frontend', 'src')
_TOKENS = os.path.join(_SRC, 'styles', 'tokens.css')
_APP_CSS = os.path.join(_SRC, 'styles', 'app.css')
_MAIN_JSX = os.path.join(_SRC, 'main.jsx')


# ── tokens.css ────────────────────────────────────────────────────────────────

def test_tokens_css_imports_google_fonts():
    with open(_TOKENS) as f:
        content = f.read()
    assert '@import' in content
    assert 'fonts.googleapis.com' in content
    assert 'Geist' in content
    assert 'Geist+Mono' in content


def test_tokens_css_root_light_tokens_present():
    with open(_TOKENS) as f:
        content = f.read()
    required = [
        '--paper', '--bg', '--ink', '--muted', '--faint',
        '--rule', '--rule-strong', '--accent', '--accent-deep', '--accent-soft',
        '--hot', '--hot-soft', '--up', '--up-soft', '--down', '--warn',
        '--shadow', '--shadow-lg',
    ]
    for token in required:
        assert token in content, f"tokens.css missing: {token}"


def test_tokens_css_dark_block_present():
    with open(_TOKENS) as f:
        content = f.read()
    assert '.dark' in content


# ── app.css — required classes ────────────────────────────────────────────────

def test_app_css_has_chip_class():
    with open(_APP_CSS) as f:
        content = f.read()
    assert '.chip' in content


def test_app_css_has_icon_btn_class():
    with open(_APP_CSS) as f:
        content = f.read()
    assert '.icon-btn' in content


def test_app_css_has_live_dot_class():
    with open(_APP_CSS) as f:
        content = f.read()
    assert '.live-dot' in content


def test_app_css_game_row_has_grid_layout():
    with open(_APP_CSS) as f:
        content = f.read()
    assert '.game-row' in content
    assert 'grid-template-columns' in content


def test_app_css_has_cell_classes():
    with open(_APP_CSS) as f:
        content = f.read()
    for cls in ['.status-cell', '.matchup-cell', '.ml-cell', '.sparkline-cell', '.edge-cell']:
        assert cls in content, f"app.css missing class: {cls}"


def test_app_css_has_shimmer_animation():
    with open(_APP_CSS) as f:
        content = f.read()
    assert '@keyframes shimmer' in content
    assert '.bar-shimmer' in content


def test_app_css_has_pulse_dot_animation():
    with open(_APP_CSS) as f:
        content = f.read()
    assert '@keyframes pulse-dot' in content


def test_app_css_has_density_variants():
    with open(_APP_CSS) as f:
        content = f.read()
    for variant in ['.density-compact', '.density-regular', '.density-comfy']:
        assert variant in content, f"app.css missing density variant: {variant}"


# ── app.css — no hardcoded colors ─────────────────────────────────────────────

def test_app_css_no_hardcoded_hex_colors():
    with open(_APP_CSS) as f:
        content = f.read()
    hex_colors = re.findall(r'(?<!\w)#[0-9a-fA-F]{3,8}(?!\w)', content)
    assert hex_colors == [], f"app.css has hardcoded hex colors: {hex_colors}"


def test_app_css_no_hardcoded_rgb_values():
    with open(_APP_CSS) as f:
        content = f.read()
    rgb_values = re.findall(r'\brgba?\s*\(', content)
    assert rgb_values == [], f"app.css has hardcoded rgb values: {rgb_values}"


# ── main.jsx — imports ────────────────────────────────────────────────────────

def test_main_jsx_imports_tokens_css():
    with open(_MAIN_JSX) as f:
        content = f.read()
    assert 'tokens.css' in content


def test_main_jsx_imports_app_css():
    with open(_MAIN_JSX) as f:
        content = f.read()
    assert 'app.css' in content
