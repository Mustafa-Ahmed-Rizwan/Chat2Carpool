import os
import json
from typing import Dict, Any, Optional
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from prompts import (
    INTENT_CLASSIFICATION_PROMPT,
    EXTRACTION_PROMPT,
    CLARIFICATION_PROMPT,
    CONFIRMATION_PROMPT,
    CONTEXT_AWARE_EXTRACTION_PROMPT,
)
from models import IntentResponse, ExtractionResponse, RideDetails
from memory_manager import memory_manager

load_dotenv()


class RideSharingLLMService:
    """Service class to handle all LLM operations with conversation memory"""

    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0,
        )
        self.memory = memory_manager

    def handle_confirmation(self, message: str, session_id: str) -> Dict[str, Any]:
        """
        Handle user confirmation (Yes/No) after details are complete
        """
        from database import SessionLocal
        from db_service import DatabaseService
        from matching_service import MatchingService

        message_lower = message.lower().strip()

        # Get session data
        session = self.memory.get_session(session_id)

        # Check if there are details to confirm
        if not session.ride_details or not session.current_intent:
            return {
                "status": "error",
                "response": "I don't have any ride details to confirm. Please start over."
            }

        # Handle YES confirmation
        if message_lower in ["yes", "yep", "yeah", "correct", "confirm", "confirmed", "ok", "okay"]:
            print(f"\n{'='*60}")
            print(f"✅ USER CONFIRMED DETAILS")
            print(f"{'='*60}")

            # Get database session
            db = SessionLocal()

            try:
                details = session.ride_details
                intent = session.current_intent
                user_id = session_id  # Using session_id as user_id (phone number)

                print(f"💾 Saving to database...")
                print(f"   Intent: {intent}")
                print(f"   Details: {details}")

                # Save to database
                if intent == "ride_request":
                    ride_entry = DatabaseService.save_ride_request(db, session_id, user_id, details)

                    # Find matches
                    print(f"\n🔍 Starting matching process...")
                    available_offers = DatabaseService.get_active_ride_offers(db, date=details.get("date"))

                    matches = MatchingService.find_matches(ride_entry, available_offers)

                    # Save matches to database
                    for match in matches:
                        DatabaseService.save_match(
                            db,
                            request_id=ride_entry.id,
                            offer_id=match["offer_id"],
                            match_type=match["match_type"],
                            match_score=match["overall_score"]
                        )

                    # Generate response message
                    response_msg = MatchingService.format_match_message(ride_entry, matches)

                    # Mark session as complete and clear
                    self.memory.mark_complete(session_id)

                    return {
                        "status": "success",
                        "saved_to_db": True,
                        "ride_type": "request",
                        "ride_id": ride_entry.id,
                        "matches_found": len(matches),
                        "response": response_msg,
                        "next_action": "completed"
                    }

                elif intent == "ride_offer":
                    ride_entry = DatabaseService.save_ride_offer(db, session_id, user_id, details)

                    # Find matching requests for this offer
                    print(f"\n🔍 Checking for matching requests...")
                    active_requests = DatabaseService.get_active_ride_requests(db, date=details.get("date"))

                    matches_count = 0
                    for request in active_requests:
                        matches = MatchingService.find_matches(request, [ride_entry])
                        if matches:
                            # Save match
                            DatabaseService.save_match(
                                db,
                                request_id=request.id,
                                offer_id=ride_entry.id,
                                match_type=matches[0]["match_type"],
                                match_score=matches[0]["overall_score"]
                            )
                            matches_count += 1

                    response_msg = (
                        f"✅ Your ride offer has been posted successfully!\n\n"
                        f"📋 Details saved:\n"
                        f"📍 From: {details['pickup_location']}\n"
                        f"📍 To: {details['drop_location']}\n"
                    )

                    if details.get("route"):
                        route_str = " → ".join(details["route"])
                        response_msg += f"🛣️ Route: {route_str}\n"

                    response_msg += (
                        f"📅 Date: {details['date']}\n"
                        f"🕒 Time: {details['time']}\n"
                        f"💺 Available Seats: {details['available_seats']}\n\n"
                    )

                    if matches_count > 0:
                        response_msg += f"🎉 Great news! {matches_count} rider(s) are looking for similar rides. We'll connect you soon!"
                    else:
                        response_msg += "We'll notify you when riders are looking for your route!"

                    # Mark session as complete
                    self.memory.mark_complete(session_id)

                    return {
                        "status": "success",
                        "saved_to_db": True,
                        "ride_type": "offer",
                        "ride_id": ride_entry.id,
                        "matches_found": matches_count,
                        "response": response_msg,
                        "next_action": "completed"
                    }

            except Exception as e:
                print(f"\n❌ DATABASE ERROR: {e}")
                import traceback
                traceback.print_exc()

                return {
                    "status": "error",
                    "response": "Sorry, there was an error saving your ride. Please try again later."
                }
            finally:
                db.close()

        # Handle NO or corrections
        elif message_lower in ["no", "nope", "wrong", "incorrect"]:
            # Clear session and start over
            self.memory.clear_session(session_id)

            return {
                "status": "correction_needed",
                "response": "No problem! Let's start over. What would you like to change? Or tell me about your ride again from the beginning."
            }

        # If not clear yes/no, treat as correction
        else:
            print(f"🔄 User wants to make corrections: {message}")

            # Reset completion flag but keep intent
            session.is_complete = False

            # Process the correction message
            result = self.process_message(message, session_id)

            return result

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

        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            text = json_match.group(0)

        return json.loads(text)

    def classify_intent(self, message: str, session_id: str) -> IntentResponse:
        """Classify message intent with conversation context"""
        try:
            print(f"\n{'='*60}")
            print(f"🎯 INTENT CLASSIFICATION")
            print(f"{'='*60}")
            print(f"👤 Session ID: {session_id}")
            print(f"📝 User Message: {message}")

            # Get conversation history
            history = self.memory.get_conversation_history(session_id, last_n=5)

            if history:
                print(f"🧠 Using conversation history ({len(history)} messages)")
                for i, msg in enumerate(history[-3:], 1):  # Show last 3
                    print(f"   {i}. {msg['role']}: {msg['content'][:50]}...")
            else:
                print(f"🧠 No conversation history (first message)")

            chain = INTENT_CLASSIFICATION_PROMPT | self.llm
            response = chain.invoke({"message": message})
            result_text = response.content.strip()

            print(f"🤖 LLM Raw Response:\n{result_text}")

            result = self._parse_json_response(result_text)

            print(f"✅ Parsed Intent: {result['intent']}")
            print(f"✅ Confidence: {result['confidence']}")
            print(f"✅ Reasoning: {result['reasoning']}")

            # Store intent in memory
            self.memory.set_intent(session_id, result["intent"])

            print(f"{'='*60}\n")

            return IntentResponse(**result)

        except Exception as e:
            print(f"❌ Intent Classification Error: {e}")
            import traceback

            traceback.print_exc()

            # Simple fallback
            message_lower = message.lower()
            if any(
                word in message_lower
                for word in ["need", "want", "looking for", "going to"]
            ):
                intent = "ride_request"
            elif any(
                word in message_lower for word in ["offering", "have space", "driving"]
            ):
                intent = "ride_offer"
            else:
                intent = "other"

            print(f"⚠️ Using fallback intent: {intent}")

            return IntentResponse(
                intent=intent,
                confidence=0.7,
                reasoning=f"Fallback due to error: {str(e)}",
            )

    def extract_information(
        self, message: str, intent: str, session_id: str
    ) -> ExtractionResponse:
        """Extract ride details from message using conversation context"""
        try:
            print(f"\n{'='*60}")
            print(f"🔍 INFORMATION EXTRACTION")
            print(f"{'='*60}")
            print(f"👤 Session ID: {session_id}")
            print(f"📝 Message: {message}")
            print(f"🎯 Intent: {intent}")

            # Get session data
            session = self.memory.get_session(session_id)
            existing_details = session.ride_details

            if existing_details:
                print(f"\n📊 Existing Details from Memory:")
                for key, value in existing_details.items():
                    if value is not None:
                        print(f"   • {key}: {value}")

            # Get conversation history for context
            conversation_text = self.memory.get_conversation_history(
                session_id, last_n=5, format_type="text"
            )

            # Use context-aware extraction prompt
            chain = CONTEXT_AWARE_EXTRACTION_PROMPT | self.llm
            response = chain.invoke(
                {
                    "message": message,
                    "intent": intent,
                    "conversation_history": conversation_text,
                    "existing_details": json.dumps(existing_details),
                }
            )
            result_text = response.content.strip()

            print(f"\n🤖 LLM Raw Response:")
            print(f"{result_text}")
            print(f"{'-'*60}")

            result = self._parse_json_response(result_text)

            print(f"\n✅ Successfully Parsed JSON")
            print(f"📊 Newly Extracted Details:")
            for key, value in result["details"].items():
                print(f"   • {key}: {value}")

            # Merge with existing details
            merged_details = {**existing_details, **result["details"]}

            # Set defaults
            if intent == "ride_request" and merged_details.get("passengers") is None:
                merged_details["passengers"] = 1
                print(f"   • passengers: 1 (default)")

            # Update memory with merged details
            self.memory.update_ride_details(session_id, merged_details)

            # Determine required fields (route is optional, not required)
            required_fields = ["pickup_location", "drop_location", "date", "time"]
            if intent == "ride_request":
                required_fields.append("passengers")
            elif intent == "ride_offer":
                required_fields.append("available_seats")

            # Calculate missing fields from MERGED details
            missing = [
                field for field in required_fields if merged_details.get(field) is None
            ]

            is_complete = len(missing) == 0

            print(f"\n📋 Analysis (After Merging):")
            print(f"   • Required fields: {', '.join(required_fields)}")
            print(f"   • Missing fields: {', '.join(missing) if missing else 'None'}")
            print(f"   • Is complete: {is_complete}")

            # Generate clarifying question if incomplete
            clarifying_question = None
            if not is_complete and missing:
                clarifying_question = self.generate_clarifying_question(
                    intent=intent,
                    missing_fields=missing,
                    existing_details=merged_details,
                )
                print(f"   • Clarifying question: {clarifying_question}")

            print(f"{'='*60}\n")

            return ExtractionResponse(
                details=RideDetails(**merged_details),
                missing_fields=missing,
                is_complete=is_complete,
                clarifying_question=clarifying_question,
            )

        except Exception as e:
            print(f"\n❌ EXTRACTION ERROR: {e}")
            import traceback

            traceback.print_exc()

            # Get existing details from memory
            session = self.memory.get_session(session_id)
            existing_details = session.ride_details or {}

            # Determine what's still missing
            required_fields = ["pickup_location", "drop_location", "date", "time"]
            if intent == "ride_request":
                required_fields.append("passengers")
            elif intent == "ride_offer":
                required_fields.append("available_seats")

            missing = [
                field
                for field in required_fields
                if existing_details.get(field) is None
            ]

            print(f"⚠️ Returning partial extraction with existing memory")
            print(f"{'='*60}\n")

            return ExtractionResponse(
                details=RideDetails(**existing_details),
                missing_fields=missing,
                is_complete=False,
                clarifying_question="I'm having trouble understanding. Could you please provide more details?",
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
                "route": "Would you like to share your route for better matches? (Optional)",
                "date": "When do you need this ride? (e.g., today, tomorrow)",
                "time": "What time do you need the ride?",
                "passengers": "How many passengers will be traveling?",
                "available_seats": "How many seats do you have available?",
            }

            for field in missing_fields:
                if field in field_questions:
                    return field_questions[field]

            return "Could you please provide more details about your ride?"

    def generate_confirmation_message(
        self, intent: str, details: RideDetails, session_id: str
    ) -> str:
        """Generate confirmation message"""
        try:
            # Print session summary before confirmation
            self.memory.print_session_summary(session_id)

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
            if details.route:
                route_str = " → ".join(details.route)
                msg += f"🛣️ Route: {route_str}\n"
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

    def process_message(
    self, message: str, session_id: str = "default"
) -> Dict[str, Any]:
        """Complete message processing pipeline with memory"""

        print(f"\n{'#'*60}")
        print(f"🚀 PROCESSING NEW MESSAGE")
        print(f"{'#'*60}")
        print(f"👤 Session ID: {session_id}")
        print(f"📝 Message: {message}\n")

        # Add user message to memory
        self.memory.add_user_message(session_id, message)

        # CHECK IF WAITING FOR CONFIRMATION
        session = self.memory.get_session(session_id)
        if session.is_complete and session.current_intent in ["ride_request", "ride_offer"]:
            print(f"⏳ Session is complete, waiting for confirmation...")
            confirmation_result = self.handle_confirmation(message, session_id)

            # Add assistant response to memory
            self.memory.add_assistant_message(session_id, confirmation_result["response"])

            return {
                "intent": session.current_intent,
                "confidence": 1.0,
                "details": session.ride_details,
                "missing_fields": [],
                "is_complete": True,
                "response": confirmation_result["response"],
                "next_action": confirmation_result.get("next_action", "completed"),
                "saved_to_db": confirmation_result.get("saved_to_db", False),
                "matches_found": confirmation_result.get("matches_found", 0)
            }

        # CHECK IF CONVERSATION IS ALREADY IN PROGRESS
        if session.current_intent and session.current_intent != "other" and not session.is_complete:
            # Don't re-classify, use existing intent
            print(f"🔄 Continuing existing conversation with intent: {session.current_intent}")
            intent_result = IntentResponse(
                intent=session.current_intent,
                confidence=0.95,
                reasoning="Continuing existing conversation flow"
            )
        else:
            # Step 1: Classify intent
            intent_result = self.classify_intent(message, session_id)

        if intent_result.intent == "other":
            print(f"ℹ️ Intent classified as 'other' - sending greeting\n")
            response_msg = "Hello! I can help you find rides or offer rides. Please tell me if you need a ride or if you're offering one."

            # Add assistant response to memory
            self.memory.add_assistant_message(session_id, response_msg)

            return {
                "intent": "other",
                "confidence": intent_result.confidence,
                "response": response_msg,
                "is_complete": False,
                "details": {},
                "missing_fields": [],
                "next_action": "awaiting_intent",
            }

        # Step 2: Extract information with context
        extraction_result = self.extract_information(
            message, intent_result.intent, session_id
        )

        # Step 3: Generate appropriate response
        if extraction_result.is_complete:
            confirmation_msg = self.generate_confirmation_message(
                intent_result.intent, extraction_result.details, session_id
            )
            response_message = confirmation_msg
            next_action = "awaiting_confirmation"

            # Mark session as complete
            self.memory.mark_complete(session_id)

            print(f"✅ Extraction complete - sending confirmation")
        else:
            response_message = extraction_result.clarifying_question
            next_action = "awaiting_details"
            print(f"⏳ Extraction incomplete - asking for clarification")

        # Add assistant response to memory
        self.memory.add_assistant_message(session_id, response_message)

        print(f"\n{'#'*60}")
        print(f"✅ PROCESSING COMPLETE")
        print(f"{'#'*60}\n")

        # Print memory stats
        self.memory.print_memory_stats()

        return {
            "intent": intent_result.intent,
            "confidence": intent_result.confidence,
            "details": extraction_result.details.model_dump(),
            "missing_fields": extraction_result.missing_fields,
            "is_complete": extraction_result.is_complete,
            "response": response_message,
            "next_action": next_action,
        }
