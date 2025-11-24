# Chat2Carpool
AI-Powered Carpool Request and Offer Extraction from WhatsApp Chats

## 🚀 Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/Mustafa-Ahmed-Rizwan/Chat2Carpool.git
cd Chat2Carpool
```

### 2. (Optional) Install **uv** if not already installed
```bash
pip install uv
```

### 3. Initialize uv Environment
```bash
uv init
```

### 4. Sync Dependencies
```bash
uv sync
```

### 5. Activate the Virtual Environment
```bash
source .venv/bin/activate        # Linux / macOS
# OR
.\.venv\Scripts\activate       # Windows
```

## ▶️ Running the Project

### Backend (FastAPI)
```bash
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```

### Frontend (Streamlit)
```bash
streamlit run streamlit_app.py
```
