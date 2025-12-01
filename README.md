# Chat2Carpool
AI-Powered Carpool Request and Offer Extraction from WhatsApp Chats

## 🚀 Setup Instructions

### 1. Clone the Repository
```bash
git clone [https://github.com/Mustafa-Ahmed-Rizwan/Chat2Carpool.git](https://github.com/Mustafa-Ahmed-Rizwan/Chat2Carpool.git)
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

## 📊 Monitoring Setup (Prometheus & Grafana)

This project uses Prometheus for metric collection and Grafana for visualization.

### 1. Configure Prometheus IP (Crucial Step for Windows/WSL)
By default, Docker containers on Windows/WSL may struggle to connect to `host.docker.internal` due to firewall rules. To fix this, you must use your actual **Wireless LAN IP**.

1.  Open PowerShell and run `ipconfig`.
2.  Copy your **IPv4 Address** (e.g., `192.168.1.15`).
3.  Open `prometheus.yml` in the project root.
4.  Update the targets section:

    ```yaml
    scrape_configs:
      - job_name: 'chat2carpool_app'
        static_configs:
          # REPLACE 'host.docker.internal' with your actual IPv4 address
          # Example: - targets: ['192.168.1.15:8000']
          - targets: ['YOUR_IP_HERE:8000'] 
    ```

### 2. Start the Monitoring Stack
Run the following command to start Prometheus and Grafana containers:

```bash
docker compose -f docker-compose.monitoring.yml up -d
```

### 3. Access Dashboards
* **Grafana:** [http://localhost:3000](http://localhost:3000) (Login: `admin` / `admin`)
* **Prometheus:** [http://localhost:9090](http://localhost:9090)