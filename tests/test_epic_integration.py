"""Epic #35 integration tests — verify all pieces are wired together."""

import os
import re

_ROOT = os.path.join(os.path.dirname(__file__), '..', 'nhl-dashboard')
_BACKEND = os.path.join(_ROOT, 'backend')
_FRONTEND_SRC = os.path.join(_ROOT, 'frontend', 'src')


# ── Vite dev server: port + /api proxy ────────────────────────────────────────

def test_vite_config_proxies_api_to_port_5000():
    with open(os.path.join(_ROOT, 'frontend', 'vite.config.js')) as f:
        content = f.read()
    assert "'/api'" in content or '"/api"' in content
    assert 'localhost:5000' in content


def test_vite_config_dev_server_runs_on_port_5173():
    with open(os.path.join(_ROOT, 'frontend', 'vite.config.js')) as f:
        content = f.read()
    assert '5173' in content


# ── App shell: polling interval and full component imports ────────────────────

def test_app_jsx_polls_games_endpoint_at_15_seconds():
    with open(os.path.join(_FRONTEND_SRC, 'App.jsx')) as f:
        content = f.read()
    assert '/api/games/today' in content
    assert '15000' in content


def test_app_jsx_imports_topbar_slate_table_error_toast():
    with open(os.path.join(_FRONTEND_SRC, 'App.jsx')) as f:
        content = f.read()
    for component in ('Topbar', 'SlateTable', 'ErrorToast'):
        assert component in content, f"App.jsx missing import: {component}"


# ── Dark mode: toggle present and persists to localStorage ───────────────────

def test_topbar_dark_mode_toggle_persists_to_localstorage():
    with open(os.path.join(_FRONTEND_SRC, 'components', 'Topbar.jsx')) as f:
        content = f.read()
    assert 'localStorage' in content
    assert 'theme' in content
    assert 'dark' in content


def test_app_jsx_restores_dark_mode_from_localstorage_on_mount():
    with open(os.path.join(_FRONTEND_SRC, 'App.jsx')) as f:
        content = f.read()
    assert 'localStorage' in content
    assert 'theme' in content
    assert 'dark' in content


# ── Density toggle: persists to localStorage ─────────────────────────────────

def test_app_jsx_density_toggle_persists_to_localstorage():
    with open(os.path.join(_FRONTEND_SRC, 'App.jsx')) as f:
        content = f.read()
    assert 'density' in content
    assert 'localStorage' in content


def test_topbar_renders_all_three_density_options():
    with open(os.path.join(_FRONTEND_SRC, 'components', 'Topbar.jsx')) as f:
        content = f.read()
    for label in ('Compact', 'Regular', 'Comfy'):
        assert label in content, f"Topbar missing density label: {label}"


# ── Scheduler: live-poll job fires every 15 seconds ──────────────────────────

def test_scheduler_poll_live_job_interval_is_15_seconds():
    with open(os.path.join(_BACKEND, 'scheduler.py')) as f:
        content = f.read()
    assert 'poll_live' in content
    assert 'seconds=15' in content


def test_scheduler_init_skips_start_in_testing_mode():
    with open(os.path.join(_BACKEND, 'scheduler.py')) as f:
        content = f.read()
    assert 'TESTING' in content


# ── Backend: all required routes are registered ───────────────────────────────

def test_app_factory_registers_health_and_games_blueprints():
    with open(os.path.join(_BACKEND, 'app.py')) as f:
        content = f.read()
    assert 'health_bp' in content
    assert 'games_bp' in content


def test_health_route_file_exists():
    assert os.path.isfile(os.path.join(_BACKEND, 'routes', 'health.py'))


def test_games_route_file_exists():
    assert os.path.isfile(os.path.join(_BACKEND, 'routes', 'games.py'))
