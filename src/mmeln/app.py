import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg
import uvicorn
from fastapi import FastAPI, HTTPException
from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from psycopg.rows import dict_row
from pydantic import BaseModel

logger = logging.getLogger("mmeln.app")
logger.setLevel(logging.INFO)


def setup_telemetry(fastapi_app: FastAPI) -> None:
    if os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "mmeln-api")
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "0.3.0",
            "deployment.environment": os.getenv("DEPLOYMENT_ENV", "local"),
        }
    )

    # 1. Tracing (Трасування)
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )
    trace.set_tracer_provider(tracer_provider)

    # 2. Metrics (Метрики)
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=endpoint, insecure=True),
        export_interval_millis=5000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # 3. Logging (Логування з прив'язкою до trace_id / span_id)
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint, insecure=True))
    )
    set_logger_provider(logger_provider)
    LoggingInstrumentor().instrument(set_logging_format=True)

    otel_handler = LoggingHandler(
        level=logging.INFO, logger_provider=logger_provider
    )
    logging.getLogger().addHandler(otel_handler)
    logging.getLogger().setLevel(logging.INFO)

    FastAPIInstrumentor.instrument_app(fastapi_app)


tracer = trace.get_tracer("mmeln.tracer")
meter = metrics.get_meter("mmeln.meter")
items_created_counter = meter.create_counter(
    name="mmeln_items_created_total",
    description="Total number of created items in PostgreSQL",
    unit="1",
)
db_query_counter = meter.create_counter(
    name="mmeln_db_queries_total",
    description="Total number of executed database queries",
    unit="1",
)


def _setup_telemetry() -> tuple[logging.Logger, trace.Tracer, metrics.Counter]:
    service_name = os.getenv("OTEL_SERVICE_NAME", "mmeln-api")
    resource = Resource.create({"service.name": service_name})

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)
    otel_tracer = trace.get_tracer("mmeln.app")

    metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
    meter = metrics.get_meter("mmeln.app")
    queries_counter = meter.create_counter(
        name="db.queries",
        description="Total number of database queries executed",
        unit="1",
    )

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter())
    )
    set_logger_provider(logger_provider)

    app_logger = logging.getLogger("mmeln.app")
    app_logger.setLevel(logging.INFO)
    app_logger.addHandler(
        LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
    )
    return app_logger, otel_tracer, queries_counter


logger, tracer, db_queries_counter = _setup_telemetry()


def record_db_query(operation: str) -> None:
    db_queries_counter.add(1, {"db.operation": operation})


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
    with tracer.start_as_current_span("db.init_db"):
        record_db_query("ddl")
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
        logger.info("Database initialized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("SKIP_DB_INIT", "false").lower() != "true":
        init_db()
    logger.info("Application startup completed with OpenTelemetry enabled")
    yield


app = FastAPI(title="mmeln API", version="0.2.0", lifespan=lifespan)
FastAPIInstrumentor.instrument_app(app)


class ItemCreate(BaseModel):
    title: str
    description: str = ""


@app.get("/health")
def health_check():
    try:
        with tracer.start_as_current_span("db.health_check"):
            record_db_query("health")
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
        return {"status": "OK", "database": "connected"}
    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        raise HTTPException(
            status_code=503, detail=f"Database unavailable: {exc}"
        ) from exc


@app.get("/greet")
def api_greet(name: str = "World"):
    logger.info("Greeting requested for name=%s", name)
    return {"message": greet(name)}


@app.post("/items", status_code=201)
def create_item(item: ItemCreate):
    with tracer.start_as_current_span("db.create_item"):
        record_db_query("insert")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO items (title, description) "
                    "VALUES (%s, %s) RETURNING id, title, description;",
                    (item.title, item.description),
                )
                created = cur.fetchone()
            conn.commit()
    logger.info("Created item id=%s", created["id"])
    return created


@app.get("/items")
def list_items():
    with tracer.start_as_current_span("db.list_items"):
        record_db_query("select")
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, title, description FROM items ORDER BY id ASC;"
                )
                rows = cur.fetchall()
    return {"items": rows}


@app.get("/items/{item_id}")
def get_item(item_id: int):
    with tracer.start_as_current_span("db.get_item"):
        record_db_query("select")
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
    with tracer.start_as_current_span("db.delete_item"):
        record_db_query("delete")
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
    logger.info("Deleted item id=%s", deleted["id"])
    return {"deleted_id": deleted["id"]}


def main() -> None:
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("mmeln.app:app", host=host, port=port)


if __name__ == "__main__":
    main()
