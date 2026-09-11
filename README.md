# Autonomous AIOps & Infrastructure Telemetry Monitor

An autonomous SRE observability and remediation engine built with **FastAPI**, **React**, **PostgreSQL**, and **Docker Compose**. The system streams live hardware telemetry over WebSockets, automatically detects resource exhaustion anomalies, autonomously terminates offending processes via host system signals, and logs audit events to PostgreSQL.

---

## 🏗️ Architecture & Data Flow

```mermaid
flowchart TD
    subgraph Host Environment
        P[psutil Process Telemetry / Heavy Worker]
    end

    subgraph Docker Containers
        B[FastAPI Backend Engine]
        DB[(PostgreSQL Database)]
        F[React / TypeScript Dashboard]
    end

    P -->|System Metrics & PID Tracking| B
    B -->|WebSocket Stream /ws/telemetry| F
    B -->|Async ORM Logging / SQLAlchemy| DB
    DB -->|Historical Incidents /api/incidents| F
    B -.->|Autonomous Signal SIGTERM| P