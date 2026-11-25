from unittest.mock import MagicMock, patch

import allure
from fastapi.testclient import TestClient

from mmeln.app import add, app, farewell, greet, status, subtract

client = TestClient(app)


@allure.feature("Greeting module")
@allure.story("Default greeting")
def test_greet_default():
    assert greet() == "Hello, World!"


@allure.feature("Greeting module")
@allure.story("Personalized greeting")
def test_greet_custom_name():
    assert greet("Marharyta") == "Hello, Marharyta!"


@allure.feature("Farewell module")
@allure.story("Personalized farewell")
def test_farewell():
    assert farewell("KPI") == "Goodbye, KPI!"


@allure.feature("System module")
@allure.story("Health status check")
def test_status():
    assert status() == "OK"


@allure.feature("Math module")
@allure.story("Addition")
def test_add():
    assert add(2, 3) == 5


@allure.feature("Math module")
@allure.story("Subtraction")
def test_subtract():
    assert subtract(10, 4) == 6


@allure.feature("API module")
@allure.story("API Greet endpoint")
def test_api_greet():
    response = client.get("/greet?name=Student")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, Student!"}


@allure.feature("API module")
@allure.story("API Health endpoint")
@patch("mmeln.app.get_connection")
def test_api_health_ok(mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value.__enter__.return_value = mock_conn
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK", "database": "connected"}


@allure.feature("API module")
@allure.story("Create and list items")
@patch("mmeln.app.get_connection")
def test_create_and_list_items(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn.return_value.__enter__.return_value = mock_conn

    mock_cur.fetchone.return_value = {
        "id": 1,
        "title": "Lab 7",
        "description": "Docker Compose",
    }
    res_post = client.post(
        "/items", json={"title": "Lab 7", "description": "Docker Compose"}
    )
    assert res_post.status_code == 201
    assert res_post.json()["title"] == "Lab 7"

    mock_cur.fetchall.return_value = [
        {"id": 1, "title": "Lab 7", "description": "Docker Compose"}
    ]
    res_get = client.get("/items")
    assert res_get.status_code == 200
    assert len(res_get.json()["items"]) == 1