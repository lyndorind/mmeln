from unittest.mock import MagicMock, patch

import allure
from fastapi.testclient import TestClient

from mmeln.app import (
    add,
    app,
    farewell,
    get_db_dsn,
    get_db_password,
    greet,
    init_db,
    status,
    subtract,
)

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


@allure.feature("Database config")
@allure.story("Secret file and DSN resolution")
def test_db_password_from_file(tmp_path, monkeypatch):
    secret_file = tmp_path / "db_password.txt"
    secret_file.write_text("super_secret\n", encoding="utf-8")
    monkeypatch.setenv("DB_PASSWORD_FILE", str(secret_file))
    assert get_db_password() == "super_secret"
    assert "password=super_secret" in get_db_dsn()


@allure.feature("Database config")
@allure.story("Init DB table creation")
@patch("mmeln.app.get_connection")
def test_init_db(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn.return_value.__enter__.return_value = mock_conn

    init_db()
    mock_cur.execute.assert_called_once()
    mock_conn.commit.assert_called_once()


@allure.feature("API module")
@allure.story("API Greet endpoint")
def test_api_greet():
    response = client.get("/greet?name=Student")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, Student!"}


@allure.feature("API module")
@allure.story("API Health endpoint OK")
@patch("mmeln.app.get_connection")
def test_api_health_ok(mock_get_conn):
    mock_conn = MagicMock()
    mock_get_conn.return_value.__enter__.return_value = mock_conn
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK", "database": "connected"}


@allure.feature("API module")
@allure.story("API Health endpoint DB Error")
@patch("mmeln.app.get_connection", side_effect=RuntimeError("Connection refused"))
def test_api_health_unavailable(mock_get_conn):
    response = client.get("/health")
    assert response.status_code == 503
    assert "Database unavailable" in response.json()["detail"]


@allure.feature("API module")
@allure.story("Full CRUD items flow")
@patch("mmeln.app.get_connection")
def test_items_crud_flow(mock_get_conn):
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_get_conn.return_value.__enter__.return_value = mock_conn

    # Create
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

    # List
    mock_cur.fetchall.return_value = [
        {"id": 1, "title": "Lab 7", "description": "Docker Compose"}
    ]
    res_get_all = client.get("/items")
    assert res_get_all.status_code == 200
    assert len(res_get_all.json()["items"]) == 1

    # Get single (found & not found)
    mock_cur.fetchone.return_value = {
        "id": 1,
        "title": "Lab 7",
        "description": "Docker Compose",
    }
    res_get_one = client.get("/items/1")
    assert res_get_one.status_code == 200

    mock_cur.fetchone.return_value = None
    res_not_found = client.get("/items/999")
    assert res_not_found.status_code == 404

    # Delete (found & not found)
    mock_cur.fetchone.return_value = {"id": 1}
    res_del = client.delete("/items/1")
    assert res_del.status_code == 200
    assert res_del.json() == {"deleted_id": 1}

    mock_cur.fetchone.return_value = None
    res_del_missing = client.delete("/items/999")
    assert res_del_missing.status_code == 404