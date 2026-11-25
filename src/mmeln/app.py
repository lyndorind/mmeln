import os
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg
import uvicorn
from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row
from pydantic import BaseModel


def greet(name: str = "World") -> str:
    return f"Hello, {name}!"


def farewell(name: str) -> str:
    return f"Goodbye, {name}!"


def status() -> str:
    return "OK"


def add(a: int, b: int) -> int:
    return a + b


def subtract(a: int, b: int) -> int:
    return a - b


def get_db_password() -> str:
    password_file = os.getenv("DB_PASSWORD_FILE")
    if password_file and Path(password_file).is_file():
        return Path(password_file).read_text(encoding="utf-8").strip()
    return os.getenv("DB_PASSWORD", "postgres")


def get_db_dsn() -> str:
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME", "mmeln_db")
    user = os.getenv("DB_USER", "postgres")
    password = get_db_password()
    return (
        f"host={host} port={port} dbname={dbname} "
        f"user={user} password={password}"
    )


def get_connection():
    return psycopg.connect(get_db_dsn(), row_factory=dict_row)


def init_db() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(100) NOT NULL,
                    description TEXT DEFAULT ''
                );
                """
            )
        conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("SKIP_DB_INIT", "false").lower() != "true":
        init_db()
    yield


app = FastAPI(title="mmeln API", version="0.2.0", lifespan=lifespan)


class ItemCreate(BaseModel):
    title: str
    description: str = ""


@app.get("/health")
def health_check():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return {"status": "OK", "database": "connected"}
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Database unavailable: {exc}"
        ) from exc


@app.get("/greet")
def api_greet(name: str = "World"):
    return {"message": greet(name)}


@app.post("/items", status_code=201)
def create_item(item: ItemCreate):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO items (title, description) "
                "VALUES (%s, %s) RETURNING id, title, description;",
                (item.title, item.description),
            )
            created = cur.fetchone()
        conn.commit()
    return created


@app.get("/items")
def list_items():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, description FROM items ORDER BY id ASC;"
            )
            rows = cur.fetchall()
    return {"items": rows}


@app.get("/items/{item_id}")
def get_item(item_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, description FROM items WHERE id = %s;",
                (item_id,),
            )
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Item not found")
    return row


@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM items WHERE id = %s RETURNING id;",
                (item_id,),
            )
            deleted = cur.fetchone()
        conn.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"deleted_id": deleted["id"]}


def main() -> None:
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("mmeln.app:app", host=host, port=port)


if __name__ == "__main__":
    main()