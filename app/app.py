import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import health, data, prediction, routes, hosts
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # No eager training on startup — models are trained lazily on first request
    # per (host, service) pair.  Use POST /hosts/{host}/services/{svc}/train
    # to pre-warm specific pairs if desired.
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title    = "Nagios Service Prediction API",
    version  = "2.0.0",
    docs_url = "/docs",
    redoc_url= "/redoc",
    lifespan = lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins    = ["*"],
    allow_credentials= True,
    allow_methods    = ["*"],
    allow_headers    = ["*"],
)

app.include_router(health.router)
app.include_router(hosts.router)
app.include_router(data.router)
app.include_router(prediction.router)
app.include_router(routes.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "name"   : "Nagios Service Prediction API",
        "version": "2.0.0",
        "docs"   : "/docs",
        "routes" : {
            "health": ["GET /health/"],
            "hosts" : [
                "GET  /hosts/",
                "GET  /hosts/{host_name}/services",
                "GET  /hosts/cache",
                "DELETE /hosts/cache?host=&service=",
                "POST /hosts/{host_name}/services/{service_name}/train",
            ],
            "data"  : [
                "GET /data/raw?host=&service=",
                "GET /data/processed?host=&service=",
                "GET /data/stats?host=&service=",
                "GET /data/timeseries?host=&service=",
            ],
            "predict": [
                "GET /predict/metrics?host=&service=",
                "GET /predict/forecast?host=&service=&days=7",
                "GET /predict/summary?host=&service=&days=7",
                "GET /predict/actual-vs-predicted?host=&service=",
                "GET /predict/run?host=&service=",
                "GET /predict/combined?host=&service=&days=7&granularity=hourly",
            ],
        },
    }
