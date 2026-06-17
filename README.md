# Solar Farm Telemetry

Real-time solar farm monitoring dashboard with AI-powered anomaly detection, fault classification, and root-cause analysis — built with **FastAPI**, **LangGraph**, **OpenAI**, and **React**.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      Frontend (Vite + React)              │
│   Metric Cards │ Live Charts │ Incident Panel │ Status   │
│                          ▲                                │
│                   WebSocket (JSON)                        │
│                          ▼                                │
│                    Backend (FastAPI)                       │
│  ┌───────────────────────────────────────────────────┐   │
│  │  Telemetry Loop (every 2 s)                       │   │
│  │  Simulator → Anomaly Detector → AI Analyzer →     │   │
│  │  Incident Store → WebSocket Broadcast             │   │
│  └───────────────────────────────────────────────────┘   │
│       ▲              ▲               ▲                    │
│  Solar Farm      Anomaly        LangGraph                 │
│  Simulator       Detector       + OpenAI                  │
└──────────────────────────────────────────────────────────┘
```

### Data Pipeline

1. **Simulator** — Generates realistic solar farm sensor readings (battery temperature, charge, health, solar output, sunlight intensity, voltage, current, inverter status)
2. **Anomaly Detector** — Checks readings against thresholds for battery overheat, voltage spikes, power drops, inverter faults, and more
3. **AI Analyzer** — LangGraph workflow that classifies fault severity/category then performs deep root-cause analysis via GPT-4o-mini
4. **Incident Store** — Persists incidents with AI analysis, alert latency, and LLM cost tracking
5. **WebSocket Broadcast** — Streams telemetry, anomalies, and incidents to connected dashboards in real time

## Project Structure

```
solar-farm-telemetry/
├── backend/
│   ├── main.py            # FastAPI app, WebSocket manager, telemetry loop
│   ├── simulator.py       # Solar farm data generator
│   ├── anomaly.py         # Threshold-based anomaly detection
│   ├── ai_analysis.py     # LangGraph + OpenAI fault analysis workflow
│   ├── incidents.py       # Incident data model & storage
│   ├── requirements.txt   # Python dependencies
│   └── start.sh           # Backend startup script
├── frontend/
│   ├── src/
│   │   ├── App.jsx                     # Main dashboard layout
│   │   ├── components/
│   │   │   ├── Header.jsx              # Dashboard header & connection status
│   │   │   ├── MetricCard.jsx          # Individual sensor metric display
│   │   │   ├── LiveChart.jsx           # Recharts time-series charts
│   │   │   ├── IncidentPanel.jsx       # Active incident list & management
│   │   │   └── ObservabilityPanel.jsx  # System health & observability
│   │   └── hooks/
│   │       └── useWebSocket.js         # WebSocket connection hook
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── .env                    # Environment variables (API keys)
```

## Prerequisites

- **Python** 3.10+
- **Node.js** 18+
- **OpenAI API key** (for AI analysis features)

## Setup

### 1. Environment Variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your-openai-api-key
```

The app will run without an API key — AI analysis will simply be disabled and anomaly detection will still function.

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 3. Frontend

```bash
cd frontend
npm install
```

## Running the Application

### Start the Backend

```bash
cd backend
bash start.sh
```

The API server starts at `http://localhost:8000`.

### Start the Frontend

```bash
cd frontend
npm run dev
```

The dashboard opens at `http://localhost:5173`.

## API Endpoints

| Method | Path                | Description                              |
|--------|---------------------|------------------------------------------|
| GET    | `/`                 | Health check                             |
| GET    | `/incidents`        | List all incidents                       |
| GET    | `/incidents/{id}`   | Get incident details                     |
| PATCH  | `/incidents/{id}`   | Acknowledge/resolve an incident          |
| GET    | `/observability`    | System metrics & cost tracking           |
| WS     | `/ws`               | Real-time telemetry, anomalies, incidents|

## Key Features

- **Live Dashboard** — Real-time charts and metric cards update every 2 seconds via WebSocket
- **8 Anomaly Types** — Battery overheat, low charge, voltage high/low, power drop, inverter offline/degraded, efficiency low
- **AI-Powered Analysis** — LangGraph orchestrates fault classification → root-cause analysis → actionable recommendations
- **Incident Management** — Acknowledge, resolve, or mark incidents as false positives with full audit trail
- **Observability** — Alert latency tracking and LLM cost monitoring built in

## Tech Stack

| Layer       | Technology                           |
|-------------|--------------------------------------|
| Backend     | Python, FastAPI, Uvicorn             |
| AI          | LangGraph, OpenAI GPT-4o-mini        |
| Frontend    | React 19, Vite 8, Tailwind CSS 4     |
| Charts      | Recharts                             |
| Real-time   | WebSockets (FastAPI native)          |
