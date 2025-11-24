import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(page_title="Chat2Carpool", page_icon="🚗", layout="wide")

# API endpoint - FIXED PORT TO MATCH main.py
API_URL = "http://localhost:8002/test"

st.title("🚗 Ride Sharing Bot - Testing Interface")
st.markdown("---")

# Initialize session state for conversation history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar with example messages
with st.sidebar:
    st.header("📋 Example Messages")

    st.subheader("Ride Requests:")
    examples_request = [
        "I need to go from Connaught Place to IGI Airport tomorrow at 5 PM",
        "Need a ride to Gurgaon tomorrow morning",
        "Going to office from home, need ride for 2 people",
    ]
    for ex in examples_request:
        if st.button(ex, key=f"req_{ex[:20]}"):
            st.session_state.test_message = ex

    st.subheader("Ride Offers:")
    examples_offer = [
        "I'm going from CP to Airport at 6 PM, have 2 empty seats",
        "Driving to Noida tomorrow, can take 3 passengers",
        "Heading to mall from DLF, space available",
    ]
    for ex in examples_offer:
        if st.button(ex, key=f"off_{ex[:20]}"):
            st.session_state.test_message = ex

    st.markdown("---")
    if st.button("🗑️ Clear Conversation"):
        st.session_state.messages = []
        st.rerun()

# Main chat interface
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Chat Interface")

    # Display conversation history
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f"**🧑 You:** {msg['content']}")
            else:
                st.markdown(f"**🤖 Bot:** {msg['content']}")
                if msg.get("details"):
                    with st.expander("📊 Extracted Details"):
                        st.json(msg["details"])

    # Input area
    user_input = st.text_input(
        "Type your message:",
        value=st.session_state.get("test_message", ""),
        key="user_input_box",
        placeholder="e.g., I need a ride to airport tomorrow at 5 PM",
    )

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])

    with col_btn1:
        send_button = st.button("📤 Send", type="primary", use_container_width=True)

    with col_btn2:
        if st.button("🔄 Reset", use_container_width=True):
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
                # Call API with correct parameter format
                response = requests.post(
                    API_URL, params={"message": user_input}, timeout=30
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
                    st.error(f"API Error: {response.status_code} - {response.text}")

            except requests.exceptions.ConnectionError:
                st.error(
                    "❌ Cannot connect to API. Make sure FastAPI server is running on port 8002!"
                )
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

with col2:
    st.subheader("📊 Latest Analysis")

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "bot":
        latest = st.session_state.messages[-1]["details"]

        # Intent
        st.metric("Intent", latest.get("intent", "N/A").upper())

        # Confidence
        if "confidence" in latest:
            st.metric("Confidence", f"{latest['confidence']*100:.1f}%")

        # Completion status
        is_complete = latest.get("is_complete", False)
        st.metric("Status", "✅ Complete" if is_complete else "⏳ Incomplete")

        # Missing fields
        if not is_complete and latest.get("missing_fields"):
            st.warning("**Missing:**")
            for field in latest["missing_fields"]:
                st.markdown(f"- {field.replace('_', ' ').title()}")

        # Details - FIX THIS SECTION
        st.markdown("**Extracted Details:**")
        details = latest.get("details", {})

        # Check if details is a dict and not None
        if details and isinstance(details, dict):
            # Filter out None values
            displayed_details = {k: v for k, v in details.items() if v is not None}

            if displayed_details:
                for key, value in displayed_details.items():
                    st.markdown(f"- **{key.replace('_', ' ').title()}:** {value}")
            else:
                st.info("No details extracted yet")
        else:
            st.info("No details available")
    else:
        st.info("Send a message to see analysis")

# Footer
st.markdown("---")
st.caption("🚗 Ride Sharing Bot | Built with FastAPI + LangChain + Gemini + Streamlit")
