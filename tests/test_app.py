import pytest
import sys
import os

# Add the parent directory to sys.path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_homepage_loads(client):
    """Test that the homepage returns a 200 status code."""
    response = client.get('/')
    assert response.status_code == 200

def test_teams_page_loads(client):
    """Test that the teams page loads properly."""
    response = client.get('/teams/')
    assert response.status_code == 200
