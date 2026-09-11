import asyncio
import datetime
import os
import time
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psutil

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, select

# --- Database Setup ---
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/telemetry")
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


class IncidentModel(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    severity: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(String(255))
    analysis: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    resolution_message: Mapped[str] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


# --- FastAPI App Setup ---
app = FastAPI(title="AI Infra Monitor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                pass


manager = ConnectionManager()

# Configurable state
last_auto_heal_time = 0
AUTO_HEAL_COOLDOWN_SECONDS = 15
TARGET_PROCESS_NAME = "heavy_worker.py"
AUTO_HEAL_THRESHOLD = float(os.getenv("AUTO_HEAL_THRESHOLD", "85.0"))


def find_and_kill_process(target_script: str) -> dict:
    killed_pids = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline') or []
            cmd_str = " ".join(cmdline)
            if target_script in cmd_str:
                pid = proc.info['pid']
                p = psutil.Process(pid)
                p.terminate()
                killed_pids.append(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if killed_pids:
        return {"success": True, "message": f"Auto-healed: Terminated {target_script} (PIDs: {killed_pids})"}
    return {"success": False, "message": f"Process {target_script} not found"}


async def save_incident_to_db(incident_data: dict):
    """Persists an incident report to PostgreSQL."""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            incident = IncidentModel(
                incident_id=incident_data["incident_id"],
                severity=incident_data["severity"],
                summary=incident_data["summary"],
                analysis=incident_data["analysis"],
                status=incident_data["status"],
                resolution_message=incident_data.get("resolution_message"),
                recommended_action=incident_data.get("recommended_action")
            )
            session.add(incident)


async def telemetry_background_loop():
    global last_auto_heal_time

    while True:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent

        telemetry_payload = {
            "type": "telemetry",
            "cpu_percent": cpu,
            "memory_percent": mem,
            "disk_usage_percent": disk,
            "timestamp": time.time()
        }
        await manager.broadcast(telemetry_payload)

        now = time.time()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if (cpu > AUTO_HEAL_THRESHOLD or mem > AUTO_HEAL_THRESHOLD) and (
                now - last_auto_heal_time > AUTO_HEAL_COOLDOWN_SECONDS):
            last_auto_heal_time = now
            incident_id = f"INC-AUTO-{int(now)}"

            remediation_result = find_and_kill_process(TARGET_PROCESS_NAME)

            if remediation_result["success"]:
                incident_payload = {
                    "type": "incident_report",
                    "incident_id": incident_id,
                    "severity": "CRITICAL",
                    "summary": f"High System Load Detected ({cpu}% CPU / {mem}% RAM)",
                    "analysis": f"Resource threshold ({AUTO_HEAL_THRESHOLD}%) exceeded by '{TARGET_PROCESS_NAME}'. Autonomous SRE initiated process kill.",
                    "status": "RESOLVED",
                    "resolution_message": remediation_result["message"],
                    "created_at": now_iso
                }
            else:
                incident_payload = {
                    "type": "incident_report",
                    "incident_id": incident_id,
                    "severity": "CRITICAL",
                    "summary": f"High System Load Detected ({cpu}% CPU)",
                    "analysis": f"Resource exhaustion detected (> {AUTO_HEAL_THRESHOLD}%), but script '{TARGET_PROCESS_NAME}' was not running.",
                    "status": "OPEN",
                    "recommended_action": "Inspect active processes manually",
                    "created_at": now_iso
                }

            await save_incident_to_db(incident_payload)
            await manager.broadcast(incident_payload)

        await asyncio.sleep(3)


@app.on_event("startup")
async def startup_event():
    # Initialize DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    asyncio.create_task(telemetry_background_loop())


@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


class RemediateRequest(BaseModel):
    incident_id: str
    action: str
    target_process: str = TARGET_PROCESS_NAME


@app.post("/api/remediate")
async def manual_remediate(req: RemediateRequest):
    if req.action == "kill_process":
        res = find_and_kill_process(req.target_process)

        # Update incident status in DB if exists
        async with AsyncSessionLocal() as session:
            async with session.begin():
                stmt = select(IncidentModel).where(IncidentModel.incident_id == req.incident_id)
                result = await session.execute(stmt)
                incident = result.scalar_one_or_none()
                if incident:
                    incident.status = "RESOLVED"
                    incident.resolution_message = res["message"]

        await manager.broadcast({
            "type": "incident_resolved",
            "id": req.incident_id,
            "message": res["message"]
        })
        return res
    return {"status": "action_received"}


@app.get("/api/incidents")
async def get_incidents():
    """Fetches past incident reports from PostgreSQL."""
    async with AsyncSessionLocal() as session:
        stmt = select(IncidentModel).order_by(IncidentModel.created_at.desc())
        result = await session.execute(stmt)
        incidents = result.scalars().all()

        return {
            "incidents": [
                {
                    "incident_id": inc.incident_id,
                    "severity": inc.severity,
                    "summary": inc.summary,
                    "analysis": inc.analysis,
                    "status": inc.status,
                    "resolution_message": inc.resolution_message,
                    "recommended_action": inc.recommended_action,
                    "created_at": inc.created_at.isoformat()
                }
                for inc in incidents
            ]
        }