from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
import os
from typing import Dict, Any

from llm_service import RideSharingLLMService
from models import ProcessedMessage
from memory_manager import memory_manager

load_dotenv()

app = FastAPI(title="Chat2Carpool API")

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
    }


@app.get("/")
def read_root():
    return {
        "message": "Ride Sharing Bot API with Memory is running!",
        "endpoints": {
            "webhook": "/webhook/whatsapp",
            "test": "/test",
            "memory_stats": "/memory/stats",
            "session_info": "/memory/session/{session_id}",
            "clear_session": "/memory/clear/{session_id}",
        },
        "features": [
            "Multi-turn conversations",
            "Context awareness",
            "Session management",
        ],
    }


@app.post("/webhook/whatsapp", response_class=PlainTextResponse)
async def whatsapp_webhook(
    From: str = Form(...),
    To: str = Form(...),
    Body: str = Form(...),
    MessageSid: str = Form(...),
):
    """
    Twilio WhatsApp webhook endpoint
    Receives incoming messages and processes them with memory
    """
    try:
        # Use phone number as session ID (normalize it)
        session_id = From.replace("whatsapp:", "").replace("+", "")

        print(f"\n{'='*50}")
        print(f"📱 WhatsApp Message Received")
        print(f"From: {From}")
        print(f"Session ID: {session_id}")
        print(f"Message: {Body}")
        print(f"{'='*50}\n")

        # Process message through LLM with memory
        result = llm_service.process_message(Body, session_id=session_id)
        validated_result = validate_response(result)

        # Log the result
        print(f"✅ Response prepared:")
        print(f"   Intent: {validated_result['intent']}")
        print(f"   Complete: {validated_result['is_complete']}")
        print(f"   Response: {validated_result['response'][:100]}...")

        # Send response back via Twilio TwiML
        twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{validated_result['response']}</Message>
</Response>"""

        return twiml_response

    except Exception as e:
        print(f"❌ Error processing webhook: {e}")
        import traceback

        traceback.print_exc()

        error_response = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Sorry, I encountered an error. Please try again.</Message>
</Response>"""
        return error_response


@app.post("/test")
async def test_message(message: str, session_id: str = "test_user") -> Dict[str, Any]:
    """
    Test endpoint to process messages without WhatsApp
    Supports session management for testing multi-turn conversations
    """
    try:
        print(f"\n{'='*50}")
        print(f"🧪 TEST MESSAGE")
        print(f"Session ID: {session_id}")
        print(f"Message: {message}")
        print(f"{'='*50}\n")

        result = llm_service.process_message(message, session_id=session_id)
        validated_result = validate_response(result)

        return {"success": True, "session_id": session_id, "data": validated_result}
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """Health check endpoint with memory statistics"""
    stats = memory_manager.get_memory_stats()
    return {
        "status": "healthy",
        "service": "Ride Sharing Bot with Memory",
        "memory_stats": stats,
    }


# Memory Management Endpoints


@app.get("/memory/stats")
def get_memory_stats():
    """Get overall memory statistics"""
    stats = memory_manager.get_memory_stats()
    active_sessions = memory_manager.get_active_sessions()

    return {
        "stats": stats,
        "active_sessions": active_sessions,
        "total_sessions": len(active_sessions),
    }


@app.get("/memory/session/{session_id}")
def get_session_info(session_id: str):
    """Get detailed information about a specific session"""
    try:
        session = memory_manager.get_session(session_id)

        return {
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat(),
            "message_count": len(session.messages),
            "current_intent": session.current_intent,
            "is_complete": session.is_complete,
            "ride_details": session.ride_details,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                }
                for msg in session.messages
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")


@app.post("/memory/clear/{session_id}")
def clear_session(session_id: str):
    """Clear a specific session's conversation history"""
    try:
        memory_manager.clear_session(session_id)
        return {
            "success": True,
            "message": f"Session {session_id} cleared successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/memory/session/{session_id}")
def delete_session(session_id: str):
    """Completely delete a session"""
    try:
        memory_manager.delete_session(session_id)
        return {
            "success": True,
            "message": f"Session {session_id} deleted successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/memory/clear-all")
def clear_all_sessions():
    """Clear all sessions (use with caution!)"""
    try:
        active_sessions = memory_manager.get_active_sessions()
        for session_id in active_sessions:
            memory_manager.delete_session(session_id)

        return {"success": True, "message": f"Cleared {len(active_sessions)} sessions"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Graceful shutdown
@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on shutdown"""
    print("🛑 Shutting down... Cleaning up memory")
    stats = memory_manager.get_memory_stats()
    print(f"📊 Final stats: {stats}")
