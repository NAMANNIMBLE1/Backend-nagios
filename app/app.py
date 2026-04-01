import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import health, data, prediction , routes
from app.scheduler import start_scheduler, stop_scheduler
from app.services.training_service import run_training_pipeline  # ← add this

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        run_training_pipeline()
    except Exception as e:
        logging.error(f"Startup training failed: {e}")

    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title    = "Power Usage Prediction API",
    version  = "1.0.0",
    docs_url = "/docs",
    redoc_url= "/redoc",
    lifespan = lifespan,          # ← also make sure lifespan is passed here
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(data.router)
app.include_router(prediction.router)
app.include_router(routes.router)

# ── Root ──
@app.get("/", tags=["Root"])
def root():
    return {
        "name"   : "Power Usage Prediction API",
        "version": "1.0.0",
        "docs"   : "/docs",
        "routes" : {
            "health"  : [
                "GET /health/",
            ],
            "data"    : [
                "GET /data/raw",
                "GET /data/processed",
                "GET /data/stats",
                "GET /data/timeseries",
            ],
            "prediction": [
                "GET /predict/metrics",
                "GET /predict/forecast",
                "GET /predict/summary",
                "GET /predict/actual-vs-predicted",
                "GET /predict/run",
            ],
        },
    }