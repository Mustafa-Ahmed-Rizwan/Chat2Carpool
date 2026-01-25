# 🚗 Chat2Carpool

> **AI-Powered Conversational Carpooling Assistant** — Seamlessly extract ride requests and offers from natural language conversations via WhatsApp and match riders with drivers intelligently.

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-Groq-orange.svg)](https://www.langchain.com/)
[![Prometheus](https://img.shields.io/badge/Monitoring-Prometheus-red.svg)](https://prometheus.io/)

---

## 📖 Overview

**Chat2Carpool** is an end-to-end intelligent ride-sharing platform that leverages **Large Language Models (LLMs)** to understand natural language conversations and automatically extract ride requests and offers. The system integrates with **WhatsApp via Twilio** for real-time messaging, uses **sophisticated matching algorithms** to connect riders with drivers, and provides comprehensive **observability** through Prometheus and Grafana.

### 🎯 Key Highlights

- **Natural Language Understanding (NLU)**: Uses Groq-hosted LLMs with LangChain for intent classification, entity extraction, and multi-turn conversation handling
- **WhatsApp Integration**: Production-ready Twilio webhook for real-time message processing
- **Intelligent Matching Engine**: Multi-factor matching algorithm considering location alignment, route compatibility, and time flexibility
- **Cloud-Native Database**: PostgreSQL on Neon for scalable, serverless data persistence
- **Full Observability Stack**: Prometheus metrics with pre-configured Grafana dashboards
- **Session Memory Management**: Thread-safe conversation tracking with automatic cleanup

---

## 🏗️ Architecture

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        WA[WhatsApp / Twilio]
        UI[Streamlit UI]
    end

    subgraph API["Backend Services"]
        FA[FastAPI Server]
        LLM[LLM Service<br/>Groq + LangChain]
        MM[Memory Manager]
        MS[Matching Service]
        WS[WhatsApp Service]
    end

    subgraph Data["Data Layer"]
        DB[(Neon PostgreSQL)]
    end

    subgraph Observability["Observability"]
        PR[Prometheus]
        GR[Grafana]
    end

    WA --> FA
    UI --> FA
    FA --> LLM
    FA --> MM
    FA --> MS
    FA --> WS
    LLM --> DB
    MS --> DB
    FA --> PR
    PR --> GR
```

---

## ✨ Features

### 🤖 AI-Powered Conversation Processing

| Capability | Description |
|------------|-------------|
| **Intent Classification** | Distinguishes between ride requests, ride offers, and general queries with confidence scoring |
| **Entity Extraction** | Extracts pickup/drop locations, routes (multi-stop), dates, times, and passenger counts |
| **Context-Aware Responses** | Maintains conversation history for multi-turn clarification dialogues |
| **Dynamic Clarification** | Generates natural follow-up questions for missing information |

### 🔗 Multi-Channel Support

- **WhatsApp Integration** — Twilio webhooks for real-time messaging with formatted responses
- **Streamlit Dashboard** — Interactive web UI for testing and demonstration
- **REST API** — Full programmatic access for custom integrations

### 🎯 Smart Matching Algorithm

- **Location Alignment** (70% weight): Exact match, partial route alignment, or destination overlap
- **Time Compatibility** (30% weight): Flexible time window matching
- **Route Intelligence**: Understands multi-stop routes and matches intermediate pickups/drops
- **Seat Availability**: Real-time tracking of remaining seats in ride offers

### 📊 Production-Ready Observability

| Metric | Type | Description |
|--------|------|-------------|
| `chat2carpool_intent_total` | Counter | Total intents classified by type |
| `chat2carpool_db_ops_total` | Counter | Database operations with status |
| `chat2carpool_matches_found_total` | Counter | Matches found by type |
| `chat2carpool_llm_duration_seconds` | Histogram | LLM operation latency |

---

## 🛠️ Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | FastAPI, Pydantic, Python 3.12+ |
| **AI/ML** | LangChain, Groq (GPT-compatible models) |
| **Database** | PostgreSQL (Neon Serverless), SQLAlchemy ORM |
| **Messaging** | Twilio WhatsApp API |
| **Frontend** | Streamlit |
| **Monitoring** | Prometheus, Grafana |
| **DevOps** | Docker Compose, uv (package manager) |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Docker & Docker Compose (for monitoring stack)
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

### 1. Clone the Repository

```bash
git clone https://github.com/Mustafa-Ahmed-Rizwan/Chat2Carpool.git
cd Chat2Carpool
```

### 2. Install Dependencies

```bash
# Install uv if not already installed
pip install uv

# Initialize and sync environment
uv init
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# OR
.\.venv\Scripts\activate   # Windows
```

### 3. Configure Environment Variables

Create a `.env` file with the following:

```env
# LLM Configuration
GROQ_API_KEY=your_groq_api_key

# Database (Neon PostgreSQL)
DATABASE_URL=postgresql://user:password@host/database

# Twilio WhatsApp Integration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_whatsapp_number
```

### 4. Initialize the Database

```bash
python init_db.py
```

### 5. Run the Application

**Backend (FastAPI):**
```bash
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

**Frontend (Streamlit):**
```bash
streamlit run streamlit_app.py
```

---

## 📊 Monitoring Setup (Prometheus & Grafana)

### 1. Configure Prometheus Target

For Windows/WSL users, update `prometheus.yml` with your local IP:

```yaml
scrape_configs:
  - job_name: 'chat2carpool_app'
    static_configs:
      - targets: ['YOUR_LOCAL_IP:8000']  # e.g., 192.168.1.15:8000
```

### 2. Start the Monitoring Stack

```bash
docker compose -f docker-compose.monitoring.yml up -d
```

### 3. Access Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | `admin` / `admin` |
| **Prometheus** | http://localhost:9090 | — |

---

## 📁 Project Structure

```
Chat2Carpool/
├── main.py                 # FastAPI application & webhook endpoints
├── llm_service.py          # LangChain + Groq LLM integration
├── matching_service.py     # Intelligent ride matching algorithms
├── memory_manager.py       # Session & conversation management
├── db_service.py           # Database CRUD operations
├── database.py             # SQLAlchemy models & Neon connection
├── whatsapp_service.py     # Twilio WhatsApp message formatting
├── prompts.py              # LLM prompt templates
├── models.py               # Pydantic data models
├── metrics.py              # Prometheus instrumentation
├── streamlit_app.py        # Interactive web UI
├── docker-compose.monitoring.yml  # Prometheus + Grafana stack
├── prometheus.yml          # Prometheus scrape configuration
└── grafana/                # Pre-configured Grafana dashboards
```

---

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check & API info |
| `/whatsapp-webhook` | POST | Twilio webhook for incoming messages |
| `/test` | POST | Testing endpoint for message processing |
| `/confirm-match` | POST | Accept/reject a match |
| `/memory/stats` | GET | Session memory statistics |
| `/clear/{session_id}` | DELETE | Clear session history |
| `/health` | GET | Health check with LLM status |

---

## 💡 Example Conversation Flow

```
User: "I need a ride from FAST to Gulshan tomorrow at 5pm"
Bot:  "Let me confirm your ride request:
       📍 From: FAST
       📍 To: Gulshan
       📅 Date: tomorrow
       🕒 Time: 5pm
       👥 Passengers: 1

       Is everything correct? Reply 'Yes' to confirm."

User: "Yes"
Bot:  "🎉 Found 2 Match(es)!

       Match #1 (92% compatible)
       📍 From: FAST
       🎯 To: Sohrab Goth
       🛣️ Route: FAST → Drigh Road → Millennium → Gulshan → Sohrab Goth
       📅 Date: tomorrow
       🕐 Time: 5:15pm
       💺 Seats: 3

       To accept: reply 'accept 15'"
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License.

---

## 👤 Author

**Mustafa Ahmed Rizwan**

- GitHub: [@Mustafa-Ahmed-Rizwan](https://github.com/Mustafa-Ahmed-Rizwan)

---

<p align="center">
  <b>Built with ❤️ using FastAPI, LangChain, and Groq</b>
</p>
