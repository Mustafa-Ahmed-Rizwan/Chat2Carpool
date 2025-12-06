from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from dotenv import load_dotenv
import os
from typing import Dict, Any

from llm_service import RideSharingLLMService
from models import ProcessedMessage
from memory_manager import memory_manager
from metrics import init_metrics
from whatsapp_service import whatsapp_service
from fastapi.responses import Response

load_dotenv()

app = FastAPI(title="Chat2Carpool WhatsApp API")

# Initialize LLM Service
llm_service = RideSharingLLMService()


def validate_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure response has all required fields with correct types"""
    return {
        "intent": result.get("intent", "other"),
        "confidence": result.get("confidence", 0.0),
        "details": result.get("details") or {},
        "missing_fields": result.get("missing_fields", []),
        "is_complete": result.get("is_complete", False),
        "response": result.get("response", "Sorry, something went wrong."),
        "next_action": result.get("next_action", "awaiting_input"),
        "matches_found": result.get("matches_found", 0),
        "matches": result.get("matches", []),
    }


@app.on_event("startup")
async def startup_event():
    init_metrics(port=8001)
    print("✅ Chat2Carpool WhatsApp API Started!")
    print(f"📱 Twilio Number: {os.getenv('TWILIO_PHONE_NUMBER')}")


@app.get("/")
def read_root():
    return {
        "message": "Chat2Carpool WhatsApp API is running!",
        "status": "active",
        "integration": "Twilio WhatsApp",
        "endpoints": {
            "webhook": "/webhook/whatsapp",
            "status": "/webhook/status",
        }
    }


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(None),
):
    """
    Main WhatsApp webhook - handles all incoming messages
    """
    try:
        # Extract session ID from phone number
        session_id = From.replace("whatsapp:", "").replace("+", "")
        user_message = Body.strip()

        print(f"\n{'='*60}")
        print(f"📱 WhatsApp Message Received")
        print(f"From: {From}")
        print(f"Session: {session_id}")
        print(f"Message: {user_message}")
        print(f"{'='*60}\n")

        # Check for special commands (accept/reject match)
        if user_message.lower().startswith("accept "):
            return handle_match_action(session_id, user_message, "accept")

        if user_message.lower().startswith("reject "):
            return handle_match_action(session_id, user_message, "reject")

        # Process normal conversation message
        result = llm_service.process_message(user_message, session_id=session_id)
        validated_result = validate_response(result)

        # Format response for WhatsApp
        response_text = validated_result["response"]

        # If matches found, format them nicely
        if validated_result.get("matches_found", 0) > 0:
            matches = validated_result.get("matches", [])
            matches_text = whatsapp_service.format_matches_message(matches)
            response_text = f"{response_text}\n\n{matches_text}"

        print(f"🤖 Sending response: {response_text[:100]}...")

        # Return TwiML response with correct content type
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{response_text}</Message>
</Response>"""

        return Response(content=twiml, media_type="application/xml")

    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        import traceback

        traceback.print_exc()

        error_twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Sorry, I encountered an error. Please try again or type 'help' for assistance.</Message>
</Response>"""
        return Response(content=error_twiml, media_type="application/xml")


def handle_match_action(session_id: str, message: str, action: str) -> Response:
    """
    Handle accept/reject match commands
    Example: "accept 15" or "reject 15"
    """
    try:
        from database import SessionLocal
        from db_service import DatabaseService

        # Extract match ID from message
        parts = message.strip().split()
        if len(parts) < 2:
            return Response(
                content=create_twiml_response(
                    "❌ Please provide a match ID.\nExample: `accept 15`"
                ),
                media_type="application/xml",
            )

        try:
            match_id = int(parts[1])
        except ValueError:
            return Response(
                content=create_twiml_response(
                    "❌ Invalid match ID. Please use a number.\nExample: `accept 15`"
                ),
                media_type="application/xml",
            )

        db = SessionLocal()

        try:
            if action == "accept":
                # Confirm the match
                result = DatabaseService.confirm_match(db, match_id, session_id)

                if not result["success"]:
                    return Response(
                        content=create_twiml_response(f"❌ {result['error']}"),
                        media_type="application/xml",
                    )

                # Format success message
                response_msg = whatsapp_service.format_confirmation_message(
                    {
                        "message": f"""🎉 *Match Confirmed!*

📋 *Ride Details:*
📍 From: {result['offer'].pickup_location}
🎯 To: {result['offer'].drop_location}
📅 Date: {result['offer'].date}
🕐 Time: {result['offer'].time}
👥 Passengers: {result['request'].passengers}

{'💺 Driver has ' + str(result['remaining_seats']) + ' seat(s) left.' if result['offer_still_active'] else '💺 All seats filled!'}

📞 Contact details will be shared separately.
🚗 Have a safe journey!"""
                    }
                )

                return Response(
                    content=create_twiml_response(response_msg),
                    media_type="application/xml",
                )

            elif action == "reject":
                # Reject the match
                result = DatabaseService.reject_match(db, match_id, session_id)

                if not result["success"]:
                    return Response(
                        content=create_twiml_response(f"❌ {result['error']}"),
                        media_type="application/xml",
                    )

                return Response(
                    content=create_twiml_response(
                        "✅ Match rejected successfully.\n\n"
                        "Other matches are still available. Type 'my matches' to see them."
                    ),
                    media_type="application/xml",
                )

        finally:
            db.close()

    except Exception as e:
        print(f"❌ Error handling match action: {e}")
        import traceback

        traceback.print_exc()
        return Response(
            content=create_twiml_response(
                "❌ Sorry, something went wrong. Please try again."
            ),
            media_type="application/xml",
        )


def create_twiml_response(message: str) -> str:
    """Helper to create TwiML response"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{message}</Message>
</Response>"""


@app.post("/webhook/status")
async def whatsapp_status(request: Request):
    """
    Handle delivery status callbacks from Twilio
    """
    form_data = await request.form()
    print(f"📊 Message Status: {form_data.get('MessageStatus')}")
    print(f"   Message SID: {form_data.get('MessageSid')}")
    return Response(status_code=200)


@app.get("/health")
def health_check():
    """Health check endpoint"""
    stats = memory_manager.get_memory_stats()
    return {
        "status": "healthy",
        "service": "Chat2Carpool WhatsApp API",
        "twilio_configured": bool(os.getenv("TWILIO_ACCOUNT_SID")),
        "memory_stats": stats,
    }


# Keep existing memory management endpoints
@app.get("/memory/stats")
def get_memory_stats():
    stats = memory_manager.get_memory_stats()
    active_sessions = memory_manager.get_active_sessions()
    return {
        "stats": stats,
        "active_sessions": active_sessions,
        "total_sessions": len(active_sessions),
    }


@app.post("/memory/clear/{session_id}")
def clear_session(session_id: str):
    try:
        memory_manager.clear_session(session_id)
        return {"success": True, "message": f"Session {session_id} cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
