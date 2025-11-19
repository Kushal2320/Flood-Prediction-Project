# app/main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flood-backend")

# create the FastAPI app first
app = FastAPI(title="Flood Prediction Backend")

# CORS for development (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# helper to include routers without crashing app startup
def try_include(module_path: str, router_name: str = "router", prefix: str = ""):
    try:
        mod = __import__(module_path, fromlist=[router_name])
        router = getattr(mod, router_name)
        if prefix:
            app.include_router(router, prefix=prefix)
            logger.info(f"Included router {module_path}.{router_name} at prefix {prefix}")
        else:
            app.include_router(router)
            logger.info(f"Included router {module_path}.{router_name}")
    except Exception as e:
        logger.exception(f"Failed to include router {module_path}.{router_name}: {e}")

# include routers (these are optional; app will still start if they fail)
try_include("app.temp_api")   # expects app/temp_api.py exposing `router`
try_include("app.db")   
try_include("app.risk_engine")


@app.get("/")
def read_root():
    return {"message": "Backend running (check logs for router load status)."}
