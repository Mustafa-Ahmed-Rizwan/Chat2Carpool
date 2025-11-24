from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv
import os
from typing import Dict, Any

from llm_service import RideSharingLLMService
from models import ProcessedMessage

load_dotenv()

app = FastAPI(title="Chat2Carpool API")

# Initialize LLM Service
llm_service = RideSharingLLMService()


def validate_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure response has all required fields with correct types"""
    return {
        "intent": result.get("intent", "other"),
        "confidence": result.get("confidence", 0.0),
        "details": result.get("details") or {},  # Ensure never None
        "missing_fields": result.get("missing_fields", []),
        "is_complete": result.get("is_complete", False),
        "response": result.get("response", "Sorry, something went wrong."),
        "next_action": result.get("next_action", "awaiting_input"),
    }


@app.get("/")
def read_root():
    return {
        "message": "Ride Sharing Bot API is running!",
        "endpoints": {"webhook": "/webhook/whatsapp", "test": "/test"},
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
    Receives incoming messages and processes them
    """
    try:
        print(f"\n{'='*50}")
        print(f"Received message from: {From}")
        print(f"Message: {Body}")
        print(f"{'='*50}\n")

        # Process message through LLM
        result = llm_service.process_message(Body)
        validated_result = validate_response(result)  # ADD THIS LINE

        # Log the result
        print(f"Intent: {validated_result['intent']}")
        print(f"Complete: {validated_result['is_complete']}")
        print(f"Response: {validated_result['response']}")

        # Send response back via Twilio TwiML
        twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{validated_result['response']}</Message>
</Response>"""

        return twiml_response

    except Exception as e:
        print(f"Error processing webhook: {e}")
        error_response = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>Sorry, I encountered an error. Please try again.</Message>
</Response>"""
        return error_response


@app.post("/test")
async def test_message(message: str) -> Dict[str, Any]:
    """
    Test endpoint to process messages without WhatsApp
    """
    try:
        result = llm_service.process_message(message)
        validated_result = validate_response(result)
        return {"success": True, "data": validated_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Ride Sharing Bot"}
