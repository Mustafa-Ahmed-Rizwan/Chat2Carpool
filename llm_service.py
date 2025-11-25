import os
import json
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from prompts import (
    INTENT_CLASSIFICATION_PROMPT,
    EXTRACTION_PROMPT,
    CLARIFICATION_PROMPT,
    CONFIRMATION_PROMPT,
)
from models import IntentResponse, ExtractionResponse, RideDetails

load_dotenv()


class RideSharingLLMService:
    """Service class to handle all LLM operations"""

    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0,  # Keep 0 for consistent extraction
        )
        # self.llm = ChatGoogleGenerativeAI(
        #     model="gemini-2.0-flash-exp",
        #     google_api_key=os.getenv("GEMINI_API_KEY"),
        #     temperature=0.0,
        #     convert_system_message_to_human=True,
        # )

    def _parse_json_response(self, response_text: str) -> dict:
        """Robust JSON parsing with cleaning"""
        text = response_text.strip()

        # Remove markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        # Find JSON object
        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)

        return json.loads(text)

    def classify_intent(self, message: str) -> IntentResponse:
        """Classify message intent"""
        try:
            print(f"\n{'='*60}")
            print(f"🎯 INTENT CLASSIFICATION")
            print(f"{'='*60}")
            print(f"📝 User Message: {message}")

            chain = INTENT_CLASSIFICATION_PROMPT | self.llm
            response = chain.invoke({"message": message})
            result_text = response.content.strip()

            print(f"🤖 LLM Raw Response:\n{result_text}")

            result = self._parse_json_response(result_text)

            print(f"✅ Parsed Intent: {result['intent']}")
            print(f"✅ Confidence: {result['confidence']}")
            print(f"✅ Reasoning: {result['reasoning']}")
            print(f"{'='*60}\n")

            return IntentResponse(**result)

        except Exception as e:
            print(f"❌ Intent Classification Error: {e}")
            import traceback
            traceback.print_exc()

            # Simple fallback without regex
            message_lower = message.lower()
            if any(word in message_lower for word in ["need", "want", "looking for", "going to"]):
                intent = "ride_request"
            elif any(word in message_lower for word in ["offering", "have space", "driving"]):
                intent = "ride_offer"
            else:
                intent = "other"

            print(f"⚠️ Using fallback intent: {intent}")

            return IntentResponse(
                intent=intent,
                confidence=0.7,
                reasoning=f"Fallback due to error: {str(e)}"
            )

    def extract_information(self, message: str, intent: str) -> ExtractionResponse:
        """Extract ride details from message"""
        try:
            print(f"\n{'='*60}")
            print(f"🔍 INFORMATION EXTRACTION")
            print(f"{'='*60}")
            print(f"📝 Message: {message}")
            print(f"🎯 Intent: {intent}")

            chain = EXTRACTION_PROMPT | self.llm
            response = chain.invoke({"message": message, "intent": intent})
            result_text = response.content.strip()

            print(f"\n🤖 LLM Raw Response:")
            print(f"{result_text}")
            print(f"{'-'*60}")

            result = self._parse_json_response(result_text)

            print(f"\n✅ Successfully Parsed JSON")
            print(f"📊 Extracted Details:")
            for key, value in result["details"].items():
                print(f"   • {key}: {value}")

            # Set defaults
            if intent == "ride_request" and result["details"].get("passengers") is None:
                result["details"]["passengers"] = 1
                print(f"   • passengers: 1 (default)")

            # Determine required fields
            required_fields = ["pickup_location", "drop_location", "date", "time"]
            if intent == "ride_request":
                required_fields.append("passengers")
            elif intent == "ride_offer":
                required_fields.append("available_seats")

            # Calculate missing fields
            missing = [
                field for field in required_fields
                if result["details"].get(field) is None
            ]

            result["is_complete"] = len(missing) == 0
            result["missing_fields"] = missing

            print(f"\n📋 Analysis:")
            print(f"   • Required fields: {', '.join(required_fields)}")
            print(f"   • Missing fields: {', '.join(missing) if missing else 'None'}")
            print(f"   • Is complete: {result['is_complete']}")

            # Generate clarifying question if incomplete
            clarifying_question = None
            if not result["is_complete"] and missing:
                clarifying_question = self.generate_clarifying_question(
                    intent=intent,
                    missing_fields=missing,
                    existing_details=result["details"]
                )
                print(f"   • Clarifying question: {clarifying_question}")

            print(f"{'='*60}\n")

            return ExtractionResponse(
                details=RideDetails(**result["details"]),
                missing_fields=missing,
                is_complete=result["is_complete"],
                clarifying_question=clarifying_question
            )

        except Exception as e:
            print(f"\n❌ EXTRACTION ERROR: {e}")
            import traceback
            traceback.print_exc()

            # Return empty extraction
            print(f"⚠️ Returning empty extraction response")
            print(f"{'='*60}\n")

            required_fields = ["pickup_location", "drop_location", "date", "time"]
            if intent == "ride_request":
                required_fields.append("passengers")
            elif intent == "ride_offer":
                required_fields.append("available_seats")

            return ExtractionResponse(
                details=RideDetails(),
                missing_fields=required_fields,
                is_complete=False,
                clarifying_question="I'm having trouble understanding. Could you please provide your ride details? Include pickup location, destination, date, and time."
            )

    def generate_clarifying_question(
        self, intent: str, missing_fields: list, existing_details: Dict[str, Any]
    ) -> str:
        """Generate a clarifying question for missing information"""
        try:
            chain = CLARIFICATION_PROMPT | self.llm
            response = chain.invoke(
                {
                    "intent": intent,
                    "missing_fields": ", ".join(missing_fields),
                    "existing_details": json.dumps(existing_details),
                }
            )
            return response.content.strip()
        except Exception as e:
            print(f"⚠️ Clarification generation error: {e}")

            # Priority-based question generation
            field_questions = {
                "pickup_location": "Where will you be starting from?",
                "drop_location": "Where do you need to go?",
                "date": "When do you need this ride? (e.g., today, tomorrow)",
                "time": "What time do you need the ride?",
                "passengers": "How many passengers will be traveling?",
                "available_seats": "How many seats do you have available?"
            }

            for field in missing_fields:
                if field in field_questions:
                    return field_questions[field]

            return "Could you please provide more details about your ride?"

    def generate_confirmation_message(self, intent: str, details: RideDetails) -> str:
        """Generate confirmation message"""
        try:
            chain = CONFIRMATION_PROMPT | self.llm
            response = chain.invoke(
                {"intent": intent, "details": details.model_dump_json()}
            )
            return response.content.strip()
        except Exception as e:
            print(f"⚠️ Confirmation generation error: {e}")

            # Fallback confirmation
            msg = "Let me confirm your ride:\n"
            if details.pickup_location:
                msg += f"📍 From: {details.pickup_location}\n"
            if details.drop_location:
                msg += f"📍 To: {details.drop_location}\n"
            if details.date:
                msg += f"📅 Date: {details.date}\n"
            if details.time:
                msg += f"🕒 Time: {details.time}\n"
            if details.passengers:
                msg += f"👥 Passengers: {details.passengers}\n"
            if details.available_seats:
                msg += f"💺 Available Seats: {details.available_seats}\n"

            msg += "\nIs this correct? Reply 'Yes' to confirm."
            return msg

    def process_message(self, message: str) -> Dict[str, Any]:
        """Complete message processing pipeline"""

        print(f"\n{'#'*60}")
        print(f"🚀 PROCESSING NEW MESSAGE")
        print(f"{'#'*60}\n")

        # Step 1: Classify intent
        intent_result = self.classify_intent(message)

        if intent_result.intent == "other":
            print(f"ℹ️ Intent classified as 'other' - sending greeting\n")
            return {
                "intent": "other",
                "confidence": intent_result.confidence,
                "response": "Hello! I can help you find rides or offer rides. Please tell me if you need a ride or if you're offering one.",
                "is_complete": False,
                "details": {},
                "missing_fields": [],
                "next_action": "awaiting_intent"
            }

        # Step 2: Extract information
        extraction_result = self.extract_information(message, intent_result.intent)

        # Step 3: Generate appropriate response
        if extraction_result.is_complete:
            confirmation_msg = self.generate_confirmation_message(
                intent_result.intent, extraction_result.details
            )
            response_message = confirmation_msg
            next_action = "awaiting_confirmation"
            print(f"✅ Extraction complete - sending confirmation")
        else:
            response_message = extraction_result.clarifying_question
            next_action = "awaiting_details"
            print(f"⏳ Extraction incomplete - asking for clarification")

        print(f"\n{'#'*60}")
        print(f"✅ PROCESSING COMPLETE")
        print(f"{'#'*60}\n")

        return {
            "intent": intent_result.intent,
            "confidence": intent_result.confidence,
            "details": extraction_result.details.model_dump(),
            "missing_fields": extraction_result.missing_fields,
            "is_complete": extraction_result.is_complete,
            "response": response_message,
            "next_action": next_action,
        }
