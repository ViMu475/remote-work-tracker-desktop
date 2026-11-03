import pytest
import json
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import app as flask_app
from services.state_service import StateService
import routes.api as api_module

SAMPLE_DATA_DIR = os.path.join(os.path.dirname(__file__), 'sample_data')

# The tests and sample data assume "March 2026" (Q1/2026). The services read the
# real system date, so freeze it to keep the suite independent of today's date.
FROZEN_NOW = '2026-03-15 10:00:00'


@pytest.fixture(autouse=True)
def frozen_date():
    from freezegun import freeze_time
    with freeze_time(FROZEN_NOW):
        yield

@pytest.fixture
def app(tmp_path):
    state_file = str(tmp_path / 'tracker_state.json')
    src = os.path.join(SAMPLE_DATA_DIR, 'test_state.json')
    shutil.copy(src, state_file)
    flask_app.config['TESTING'] = True
    flask_app.config['DATA_FILE'] = state_file
    original_init = StateService.__init__
    def patched_init(self, data_file=None):
        original_init(self, data_file=state_file)
    StateService.__init__ = patched_init
    # Also patch the module-level state_service instance used by route handlers
    original_data_file = api_module.state_service.data_file
    api_module.state_service.data_file = state_file
    yield flask_app
    StateService.__init__ = original_init
    api_module.state_service.data_file = original_data_file

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def state_service(tmp_path):
    state_file = str(tmp_path / 'tracker_state.json')
    src = os.path.join(SAMPLE_DATA_DIR, 'test_state.json')
    shutil.copy(src, state_file)
    return StateService(data_file=state_file)

@pytest.fixture
def empty_state_service(tmp_path):
    state_file = str(tmp_path / 'tracker_state.json')
    return StateService(data_file=state_file)

@pytest.fixture
def sample_state():
    with open(os.path.join(SAMPLE_DATA_DIR, 'test_state.json'), encoding='utf-8') as f:
        return json.load(f)

def load_test_state(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)
