import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(page_title="Chat2Carpool", page_icon="🚗", layout="wide")

# API endpoints
API_BASE = "http://localhost:8002"
API_TEST = f"{API_BASE}/test"
API_MEMORY_STATS = f"{API_BASE}/memory/stats"
API_SESSION_INFO = f"{API_BASE}/memory/session"
API_CLEAR_SESSION = f"{API_BASE}/memory/clear"

st.title("🚗 Ride Sharing Bot - Testing Interface (With Memory)")
st.markdown("### Multi-turn conversations with context awareness")
st.markdown("---")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = f"user_{datetime.now().strftime('%H%M%S')}"

# Sidebar
with st.sidebar:
    st.header("🎛️ Session Control")

    # Display current session ID
    st.info(f"**Session ID:** `{st.session_state.session_id}`")

    # New session button
    if st.button("🆕 Start New Session", type="primary"):
        st.session_state.session_id = f"user_{datetime.now().strftime('%H%M%S')}"
        st.session_state.messages = []
        st.success(f"New session: {st.session_state.session_id}")
        st.rerun()

    # Clear current session
    if st.button("🗑️ Clear This Session"):
        try:
            response = requests.post(
                f"{API_CLEAR_SESSION}/{st.session_state.session_id}"
            )
            if response.status_code == 200:
                st.session_state.messages = []
                st.success("Session cleared!")
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    st.markdown("---")

    # Memory stats
    st.header("📊 Memory Stats")
    try:
        response = requests.get(API_MEMORY_STATS, timeout=5)
        if response.status_code == 200:
            stats = response.json()
            st.metric("Active Sessions", stats["stats"]["active_sessions"])
            st.metric("Total Messages", stats["stats"]["total_messages"])
            st.metric(
                "Avg Messages/Session",
                f"{stats['stats']['avg_messages_per_session']:.1f}",
            )
        else:
            st.warning("Could not fetch stats")
    except Exception as e:
        st.warning("API not responding")

    st.markdown("---")

    # Example messages
    st.header("📋 Example Messages")

    st.subheader("Multi-turn Request:")
    example_flow = [
        "Need a ride to airport",
        "From DHA",
        "Tomorrow",
        "5 PM",
        "2 people",
    ]
    for i, ex in enumerate(example_flow, 1):
        if st.button(f"{i}. {ex}", key=f"flow_{i}"):
            st.session_state.test_message = ex

    st.subheader("Complete Request:")
    complete_examples = [
        "Need ride from DHA to Airport tomorrow at 5pm for 2 people",
        "Going from Clifton to mall at 3pm today",
    ]
    for ex in complete_examples:
        if st.button(ex[:30] + "...", key=f"complete_{ex[:20]}"):
            st.session_state.test_message = ex

# Main chat interface
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Conversation")

    # Display conversation history
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f"**👤 You:** {msg['content']}")
            else:
                st.markdown(f"**🤖 Bot:** {msg['content']}")
                if msg.get("details"):
                    with st.expander("📊 Details"):
                        st.json(msg["details"])

    # Input area
    user_input = st.text_input(
        "Type your message:",
        value=st.session_state.get("test_message", ""),
        key="user_input_box",
        placeholder="e.g., Need a ride to airport",
    )

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])

    with col_btn1:
        send_button = st.button("📤 Send", type="primary", use_container_width=True)

    with col_btn2:
        if st.button("🔄 Reset Input", use_container_width=True):
            st.session_state.test_message = ""
            st.rerun()

    # Process message
    if send_button and user_input:
        # Add user message to history
        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            }
        )

        # Show loading
        with st.spinner("🤔 Processing..."):
            try:
                # Call API with session ID
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

                    # Add bot response to history
                    st.session_state.messages.append(
                        {
                            "role": "bot",
                            "content": result["data"]["response"],
                            "details": result["data"],
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                        }
                    )

                    # Clear input
                    st.session_state.test_message = ""
                    st.rerun()
                else:
                    st.error(f"API Error: {response.status_code}")
                    st.code(response.text)

            except requests.exceptions.ConnectionError:
                st.error(
                    "❌ Cannot connect to API. Make sure FastAPI is running on port 8002!"
                )
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

with col2:
    st.subheader("📊 Analysis")

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "bot":
        latest = st.session_state.messages[-1]["details"]

        # Intent
        intent = latest.get("intent", "N/A").upper()
        intent_emoji = {"RIDE_REQUEST": "🙋", "RIDE_OFFER": "🚗", "OTHER": "❓"}
        st.metric("Intent", f"{intent_emoji.get(intent, '')} {intent}")

        # Confidence
        if "confidence" in latest:
            confidence = latest["confidence"] * 100
            st.metric("Confidence", f"{confidence:.1f}%")

        # Status
        is_complete = latest.get("is_complete", False)
        status_emoji = "✅" if is_complete else "⏳"
        status_text = "Complete" if is_complete else "Incomplete"
        st.metric("Status", f"{status_emoji} {status_text}")

        # Next action
        next_action = latest.get("next_action", "N/A")
        st.info(f"**Next:** {next_action.replace('_', ' ').title()}")

        # Missing fields
        if not is_complete and latest.get("missing_fields"):
            st.warning("**Still needed:**")
            for field in latest["missing_fields"]:
                st.markdown(f"- {field.replace('_', ' ').title()}")

        # Extracted details
        st.markdown("---")
        st.markdown("**📋 Extracted Details:**")
        details = latest.get("details", {})

        if details and isinstance(details, dict):
            displayed = {k: v for k, v in details.items() if v is not None}

            if displayed:
                for key, value in displayed.items():
                    icon = {
                        "pickup_location": "📍",
                        "drop_location": "🎯",
                        "route": "🛣️",
                        "date": "📅",
                        "time": "🕒",
                        "passengers": "👥",
                        "available_seats": "💺",
                    }.get(key, "•")
                    if key == "route" and isinstance(value, list):
                        route_display = " → ".join(value)
                        st.markdown(f"{icon} **Route:** {route_display}")
                    else:
                        st.markdown(
                            f"{icon} **{key.replace('_', ' ').title()}:** {value}"
                        )
            else:
                st.info("No details yet")
        else:
            st.info("No details available")

        # Session info button
        st.markdown("---")
        if st.button("🔍 View Full Session", use_container_width=True):
            try:
                response = requests.get(
                    f"{API_SESSION_INFO}/{st.session_state.session_id}", timeout=5
                )
                if response.status_code == 200:
                    session_data = response.json()
                    st.json(session_data)
            except Exception as e:
                st.error(f"Error: {e}")

    else:
        st.info("Send a message to see analysis")

# Footer
st.markdown("---")
col_f1, col_f2 = st.columns(2)
with col_f1:
    st.caption(f"🚗 Ride Sharing Bot | Session: `{st.session_state.session_id}`")
with col_f2:
    st.caption("Built with FastAPI + LangChain + Groq + Memory")
