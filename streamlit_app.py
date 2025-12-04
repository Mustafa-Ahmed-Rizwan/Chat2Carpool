import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(page_title="Chat2Carpool", page_icon="🚗", layout="wide")

# API endpoints
API_BASE = "http://localhost:8002"
API_TEST = f"{API_BASE}/test"
API_MEMORY_STATS = f"{API_BASE}/memory/stats"
API_CONFIRM_MATCH = f"{API_BASE}/confirm-match"

# Custom CSS for better UI
st.markdown(
    """
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .chat-container {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        max-height: 500px;
        overflow-y: auto;
    }
    .user-message {
        background: #e3f2fd;
        padding: 0.8rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #2196f3;
    }
    .bot-message {
        background: #f3e5f5;
        padding: 0.8rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #9c27b0;
    }
    .match-card {
        background: white;
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.8rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .match-card:hover {
        border-color: #667eea;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .status-pill {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .status-complete {
        background: #d4edda;
        color: #155724;
    }
    .status-incomplete {
        background: #fff3cd;
        color: #856404;
    }
    .input-container {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = f"user_{datetime.now().strftime('%H%M%S')}"
if "pending_matches" not in st.session_state:
    st.session_state.pending_matches = []

# Header
st.markdown(
    """
<div class="main-header">
    <h1>🚗 Chat2Carpool</h1>
    <p>Your Smart Ride Sharing Assistant</p>
</div>
""",
    unsafe_allow_html=True,
)

# Sidebar - Simplified
with st.sidebar:
    st.markdown("### 🎛️ Session Control")
    st.info(f"**Session:** `{st.session_state.session_id[-6:]}`")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🆕 New", use_container_width=True):
            st.session_state.session_id = f"user_{datetime.now().strftime('%H%M%S')}"
            st.session_state.messages = []
            st.session_state.pending_matches = []
            st.rerun()

    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.messages = []
            st.session_state.pending_matches = []
            st.rerun()

    st.markdown("---")

    # Quick examples
    st.markdown("### 💡 Quick Examples")

    examples = [
        "Need ride to airport",
        "Offering ride from DHA to Clifton",
        "Going from Gulshan to FAST at 5pm",
    ]

    for ex in examples:
        if st.button(ex, key=f"ex_{ex[:10]}", use_container_width=True):
            st.session_state.user_input = ex

# Main chat area
st.markdown("### 💬 Conversation")

# Chat container
chat_html = '<div class="chat-container">'
for msg in st.session_state.messages:
    if msg["role"] == "user":
        chat_html += (
            f'<div class="user-message">👤 <strong>You:</strong> {msg["content"]}</div>'
        )
    else:
        chat_html += (
            f'<div class="bot-message">🤖 <strong>Bot:</strong> {msg["content"]}</div>'
        )
chat_html += "</div>"

st.markdown(chat_html, unsafe_allow_html=True)

# Display matches if available
if st.session_state.pending_matches:
    st.markdown("---")
    st.markdown("### 🎯 Available Matches")

    for idx, match in enumerate(st.session_state.pending_matches):
        with st.container():
            st.markdown(
                f"""
            <div class="match-card">
                <h4>🚗 Match #{idx + 1} - {int(match['match_score'] * 100)}% Compatible</h4>
                <p><strong>📍 From:</strong> {match['pickup']}</p>
                <p><strong>🎯 To:</strong> {match['drop']}</p>
                <p><strong>📅 Date:</strong> {match['date']} | <strong>🕐 Time:</strong> {match['time']}</p>
                <p><strong>💺 Available Seats:</strong> {match['remaining_seats']}</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns([1, 1, 4])
            with col1:
                if st.button(
                    "✅ Accept",
                    key=f"accept_{match['match_id']}",
                    use_container_width=True,
                ):
                    try:
                        response = requests.post(
                            API_CONFIRM_MATCH,
                            params={
                                "match_id": match["match_id"],
                                "session_id": st.session_state.session_id,
                            },
                            timeout=10,
                        )

                        if response.status_code == 200:
                            result = response.json()
                            if result["success"]:
                                st.success("🎉 Match confirmed!")
                                # Remove this match from pending
                                st.session_state.pending_matches = [
                                    m
                                    for m in st.session_state.pending_matches
                                    if m["match_id"] != match["match_id"]
                                ]
                                # Add confirmation message to chat
                                st.session_state.messages.append(
                                    {"role": "bot", "content": result["message"]}
                                )
                                st.rerun()
                            else:
                                st.error(result["message"])
                        else:
                            st.error("Failed to confirm match")
                    except Exception as e:
                        st.error(f"Error: {e}")

            with col2:
                if st.button(
                    "❌ Reject",
                    key=f"reject_{match['match_id']}",
                    use_container_width=True,
                ):
                    # Remove from pending matches
                    st.session_state.pending_matches = [
                        m
                        for m in st.session_state.pending_matches
                        if m["match_id"] != match["match_id"]
                    ]
                    st.info("Match rejected")
                    st.rerun()

# Input area
st.markdown("---")
st.markdown('<div class="input-container">', unsafe_allow_html=True)

user_input = st.text_input(
    "Type your message:",
    value=st.session_state.get("user_input", ""),
    key="message_input",
    placeholder="e.g., Need a ride to airport tomorrow at 5pm",
    label_visibility="collapsed",
)

col1, col2, col3 = st.columns([1, 1, 4])

with col1:
    send_button = st.button("📤 Send", type="primary", use_container_width=True)

with col2:
    if st.button("🔄 Reset", use_container_width=True):
        st.session_state.user_input = ""
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# Process message
if send_button and user_input:
    # Add user message
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("🤔 Processing..."):
        try:
            response = requests.post(
                API_TEST,
                params={
                    "message": user_input,
                    "session_id": st.session_state.session_id,
                },
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                data = result["data"]

                # Add bot response
                st.session_state.messages.append(
                    {"role": "bot", "content": data["response"]}
                )

                # Check if matches were found
                if data.get("matches_found", 0) > 0 and data.get("matches"):
                    st.session_state.pending_matches = data["matches"]
                    # Add a separator message if there are matches
                    if data.get("matches_found", 0) > 0:
                        st.session_state.messages.append({
                            "role": "bot",
                            "content": f"🎯 Displaying {len(data['matches'])} match(es) below!"
                        })

                # Clear input
                st.session_state.user_input = ""
                st.rerun()
            else:
                st.error(f"API Error: {response.status_code}")

        except requests.exceptions.ConnectionError:
            st.error(
                "❌ Cannot connect to API. Make sure FastAPI is running on port 8002!"
            )
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Status indicator at bottom
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"**Session:** `{st.session_state.session_id[-8:]}`")

with col2:
    st.markdown(f"**Messages:** {len(st.session_state.messages)}")

with col3:
    st.markdown(f"**Pending Matches:** {len(st.session_state.pending_matches)}")
