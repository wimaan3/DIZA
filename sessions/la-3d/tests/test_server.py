"""Run after npm run build; isolates backend state and disables provider calls."""
import os
import sys
import tempfile
from pathlib import Path

TEMP = tempfile.TemporaryDirectory(prefix='diza-city-test-')
os.environ['DIZA_DB'] = str(Path(TEMP.name) / 'test.sqlite3')
os.environ['OPS_API_TOKEN'] = 'local-map-test-token'
os.environ.pop('RETELL_API_KEY', None)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from server import app


def test_additive_ui_and_original_api_auth():
    with TestClient(app) as client:
        page = client.get('/city-3d/')
        assert page.status_code == 200
        assert 'DIZA · Los Angeles 3D' in page.text
        assert client.get('/city-3d', follow_redirects=False).status_code == 307
        assert client.get('/api/ops').status_code == 401
        response = client.get('/api/ops', headers={'Authorization': 'Bearer local-map-test-token'})
        assert response.status_code == 200
        assert isinstance(response.json()['incidents'], list)
        assert isinstance(response.json()['zones'], list)
        assert client.post('/api/reports', json={}).status_code == 401
