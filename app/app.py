from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import health, data, prediction

app = FastAPI(
    title       = "Power Usage Prediction API",
    description = "REST API for Nagios-based power usage forecasting using Machine Learning",
    version     = "1.0.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

# ── CORS — allow frontend dev servers ──
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],   
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Register routers ──
app.include_router(health.router)
app.include_router(data.router)
app.include_router(prediction.router)


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