"""BERU FastAPI service entrypoint.

Run:
    cd GP-MODEL-OPS/BERU-AI
    uvicorn api.main:app --host 0.0.0.0 --port 8088 --reload

Docs:
    http://localhost:8088/docs       (Swagger UI — interactive)
    http://localhost:8088/redoc      (ReDoc)
    http://localhost:8088/openapi.json
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

app = FastAPI(
    title="BERU GRC Analyst API",
    description=(
        "HTTP service wrapping the BERU LangGraph agent. "
        "Grades SSPs, audits scanner output, generates POA&Ms, drafts CISO briefings. "
        "Hard architectural floor: B/S-rank findings route to the HITL queue and "
        "cannot be auto-output. NIST AI RMF MANAGE-2.2 + GOVERN-1.5."
    ),
    version="1.4.0",
)

# Permissive CORS for the demo — tighten before any deploy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/beru")


@app.get("/")
def root():
    return {
        "service": "BERU GRC Analyst",
        "version": "1.4.0",
        "docs": "/docs",
        "endpoints": "/api/beru/*",
    }
