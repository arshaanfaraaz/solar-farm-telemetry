import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from ai_analysis import AIAnalyzer
from anomaly import AnomalyDetector
from incidents import IncidentStore
from simulator import SolarFarmSimulator

# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------

simulator = SolarFarmSimulator()
detector = AnomalyDetector()
store = IncidentStore()

_analyzer: Optional[AIAnalyzer] = None
try:
    _analyzer = AIAnalyzer()
    print("[startup] LangGraph AI analyzer ready (classify → analyze → route)")
except ValueError as exc:
    print(f"[startup] AI analysis disabled: {exc}")


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self) -> None:
        self._active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._active.append(ws)
        print(f"[ws] client connected  — {len(self._active)} total")

    def disconnect(self, ws: WebSocket) -> None:
        self._active.remove(ws)
        print(f"[ws] client disconnected — {len(self._active)} total")

    async def broadcast(self, payload: dict) -> None:
        dead: list[WebSocket] = []
        for ws in self._active:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._active.remove(ws)

    @property
    def client_count(self) -> int:
        return len(self._active)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Background telemetry loop (runs every 2 s)
# ---------------------------------------------------------------------------

async def telemetry_loop() -> None:
    """
    Pipeline per tick:
      simulator.generate()
        → anomaly detector
        → LangGraph workflow (classify → analyze → route) in thread pool
        → incident store (with alert latency)
        → WebSocket broadcast
    """
    while True:
        try:
            t_start = time.monotonic()
            reading = simulator.generate()
            anomalies = detector.detect(reading)

            analysis = None
            if anomalies and _analyzer:
                analysis = await asyncio.to_thread(_analyzer.analyze, reading, anomalies)

            alert_latency_ms = int((time.monotonic() - t_start) * 1000)
            incident = (
                store.create(reading, anomalies, analysis, alert_latency_ms)
                if anomalies else None
            )

            await manager.broadcast({
                "telemetry": reading.to_dict(),
                "anomalies": [a.to_dict() for a in anomalies],
                "incident": incident.to_dict() if incident else None,
            })
        except Exception as exc:
            print(f"[loop] error: {exc}")

        await asyncio.sleep(2)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(telemetry_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Solar Farm Telemetry API",
    description="Real-time telemetry ingestion, anomaly detection, and LangGraph AI diagnosis.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ws_clients": manager.client_count,
        "ai_enabled": _analyzer is not None,
    }


@app.get("/incidents")
async def list_incidents():
    return [i.to_dict() for i in store.get_all()]


@app.get("/observability")
async def observability():
    return store.observability_stats()


@app.post("/incidents/{incident_id}/acknowledge")
async def acknowledge_incident(incident_id: str):
    if not store.acknowledge(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"status": "acknowledged", "id": incident_id}


@app.post("/incidents/{incident_id}/resolve")
async def resolve_incident(incident_id: str):
    if not store.resolve(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"status": "resolved", "id": incident_id}


@app.post("/incidents/{incident_id}/false-positive")
async def mark_false_positive(incident_id: str):
    if not store.mark_false_positive(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"status": "false_positive", "id": incident_id}


@app.delete("/incidents/{incident_id}")
async def delete_incident(incident_id: str):
    if not store.delete(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"status": "deleted", "id": incident_id}


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
