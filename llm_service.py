import os
import json
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
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
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.0,
            convert_system_message_to_human=True,
        )
    def _fallback_extraction(self, message: str, intent: str) -> ExtractionResponse:
        """Fallback extraction using regex patterns when LLM fails"""
        import re

        details = {
            "pickup_location": None,
            "drop_location": None,
            "date": None,
            "time": None,
            "passengers": None,
            "available_seats": None,
            "additional_info": None
        }

        message_lower = message.lower()

        # Extract time patterns (5pm, 10:30am, etc.)
        time_patterns = [
            r'\b(\d{1,2}:\d{2}\s*(?:am|pm))\b',
            r'\b(\d{1,2}\s*(?:am|pm))\b',
            r'\b(morning|afternoon|evening|noon|night)\b'
        ]
        for pattern in time_patterns:
            match = re.search(pattern, message_lower)
            if match:
                details["time"] = match.group(1)
                break

        # Extract date patterns
        date_keywords = ["today", "tomorrow", "tonight"]
        for keyword in date_keywords:
            if keyword in message_lower:
                details["date"] = keyword
                break

        # Extract numbers for passengers/seats
        number_match = re.search(r'\b(\d+)\s*(?:people|person|passenger|seat)', message_lower)
        if number_match:
            number = int(number_match.group(1))
            if intent == "ride_request":
                details["passengers"] = number
            elif intent == "ride_offer":
                details["available_seats"] = number

        # Extract locations using "from X to Y" pattern
        from_to_pattern = r'from\s+([^to]+?)\s+to\s+([^at\s,]+)'
        match = re.search(from_to_pattern, message_lower)
        if match:
            details["pickup_location"] = match.group(1).strip()
            details["drop_location"] = match.group(2).strip()
        else:
            # Try "to X" pattern for destination
            to_pattern = r'to\s+([^at\s,]+)'
            match = re.search(to_pattern, message_lower)
            if match:
                details["drop_location"] = match.group(1).strip()

        # Set default passengers for ride_request
        if intent == "ride_request" and details["passengers"] is None:
            details["passengers"] = 1

        # Determine required fields
        required_fields = ["pickup_location", "drop_location", "date", "time"]
        if intent == "ride_request":
            required_fields.append("passengers")
        elif intent == "ride_offer":
            required_fields.append("available_seats")

        missing = [field for field in required_fields if details.get(field) is None]

        # Generate clarifying question
        clarifying_question = None
        if missing:
            # Prioritize asking for most important missing field
            if "pickup_location" in missing:
                clarifying_question = "Where will you be starting from?"
            elif "drop_location" in missing:
                clarifying_question = "Where do you need to go?"
            elif "date" in missing:
                clarifying_question = "When do you need this ride? (e.g., today, tomorrow)"
            elif "time" in missing:
                clarifying_question = "What time do you need the ride? (e.g., 5pm, morning)"
            elif "passengers" in missing:
                clarifying_question = "How many passengers?"
            elif "available_seats" in missing:
                clarifying_question = "How many seats do you have available?"

        print(f"⚠️ Using fallback extraction. Extracted: {details}")

        return ExtractionResponse(
            details=RideDetails(**details),
            missing_fields=missing,
            is_complete=len(missing) == 0,
            clarifying_question=clarifying_question or "Could you provide more details about your ride?"
        )

    def classify_intent(self, message: str) -> IntentResponse:
        """Classify message intent with improved error handling"""
        try:
            # Use modern LCEL syntax: prompt | llm
            chain = INTENT_CLASSIFICATION_PROMPT | self.llm
            response = chain.invoke({"message": message})
            result_text = response.content.strip()

            # Clean JSON from markdown code blocks if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            # Parse JSON
            result = json.loads(result_text)

            # Validate confidence - if too low, re-classify with fallback logic
            if result["confidence"] < 0.6:
                # Fallback: Use keyword matching
                message_lower = message.lower()

                # Check for ride request keywords
                request_keywords = ["need", "want", "looking for", "require", "going to", "going from", "need to go", "take me"]
                offer_keywords = ["offering", "have space", "empty seat", "can take", "available seat", "driving", "have room"]

                if any(keyword in message_lower for keyword in request_keywords):
                    result["intent"] = "ride_request"
                    result["confidence"] = 0.8
                    result["reasoning"] = "Detected ride request keywords"
                elif any(keyword in message_lower for keyword in offer_keywords):
                    result["intent"] = "ride_offer"
                    result["confidence"] = 0.8
                    result["reasoning"] = "Detected ride offer keywords"

            return IntentResponse(**result)

        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print(f"Response was: {result_text}")

            # Fallback classification using keywords
            message_lower = message.lower()
            if any(word in message_lower for word in ["need", "want", "going to", "going from"]):
                return IntentResponse(
                    intent="ride_request",
                    confidence=0.75,
                    reasoning="Fallback keyword detection"
                )
            elif any(word in message_lower for word in ["offering", "have space", "empty seat"]):
                return IntentResponse(
                    intent="ride_offer",
                    confidence=0.75,
                    reasoning="Fallback keyword detection"
                )
            else:
                return IntentResponse(
                    intent="other",
                    confidence=0.5,
                    reasoning="Failed to parse response"
                )
        except Exception as e:
            print(f"Intent classification error: {e}")
            # Try keyword fallback
            message_lower = message.lower()
            if "need" in message_lower or "going to" in message_lower:
                return IntentResponse(
                    intent="ride_request",
                    confidence=0.7,
                    reasoning=f"Error fallback: {str(e)}"
                )
            return IntentResponse(
                intent="other",
                confidence=0.5,
                reasoning=f"Error: {str(e)}"
            )

    def extract_information(self, message: str, intent: str) -> ExtractionResponse:
        """Extract ride details from message with robust error handling"""
        try:
            # Use modern LCEL syntax
            chain = EXTRACTION_PROMPT | self.llm
            response = chain.invoke({"message": message, "intent": intent})
            result_text = response.content.strip()

            print(f"\n{'='*50}")
            print(f"EXTRACTION DEBUG:")
            print(f"Message: {message}")
            print(f"Intent: {intent}")
            print(f"LLM Raw Response:\n{result_text}")
            print(f"{'='*50}\n")

            # Clean JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            # Find JSON in the text (sometimes LLM adds extra text)
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(0)

            result = json.loads(result_text)

            # Validate structure
            if "details" not in result:
                raise ValueError("Missing 'details' in response")

            # Set defaults for passengers if ride_request and not specified
            if intent == "ride_request" and result["details"].get("passengers") is None:
                result["details"]["passengers"] = 1

            # Determine required fields based on intent
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

            # Override is_complete based on missing fields
            result["is_complete"] = len(missing) == 0
            result["missing_fields"] = missing

            # Generate clarifying question if incomplete
            clarifying_question = None
            if not result["is_complete"] and missing:
                clarifying_question = self.generate_clarifying_question(
                    intent=intent,
                    missing_fields=missing,
                    existing_details=result["details"]
                )

            return ExtractionResponse(
                details=RideDetails(**result["details"]),
                missing_fields=missing,
                is_complete=result["is_complete"],
                clarifying_question=clarifying_question
            )

        except json.JSONDecodeError as e:
            print(f"❌ JSON Decode Error: {e}")
            print(f"Attempted to parse: {result_text}")

            # Fallback: Try to extract using regex patterns
            return self._fallback_extraction(message, intent)

        except Exception as e:
            print(f"❌ Extraction error: {e}")
            import traceback
            traceback.print_exc()

            return self._fallback_extraction(message, intent)

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
            print(f"Clarification generation error: {e}")
            return (
                f"Could you please provide the {missing_fields[0].replace('_', ' ')}?"
            )

    def generate_confirmation_message(self, intent: str, details: RideDetails) -> str:
        """Generate confirmation message"""
        try:
            chain = CONFIRMATION_PROMPT | self.llm
            response = chain.invoke(
                {"intent": intent, "details": details.model_dump_json()}
            )
            return response.content.strip()
        except Exception as e:
            print(f"Confirmation generation error: {e}")
            return "Please confirm if the details are correct."

    def process_message(self, message: str) -> Dict[str, Any]:
        """Complete message processing pipeline"""

        # Step 1: Classify intent
        intent_result = self.classify_intent(message)

        if intent_result.intent == "other":
            return {
                "intent": "other",
                "confidence": intent_result.confidence,  # ADD THIS
                "response": "Hello! I can help you find rides or offer rides. Please tell me if you need a ride or if you're offering one.",
                "is_complete": False,
                "details": {},  # CHANGE FROM None TO {}
                "missing_fields": [],  # ADD THIS
                "next_action": "awaiting_intent"  # ADD THIS
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
        else:
            response_message = extraction_result.clarifying_question
            next_action = "awaiting_details"

        return {
            "intent": intent_result.intent,
            "confidence": intent_result.confidence,
            "details": extraction_result.details.model_dump(),
            "missing_fields": extraction_result.missing_fields,
            "is_complete": extraction_result.is_complete,
            "response": response_message,
            "next_action": next_action,
        }
