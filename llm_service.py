import os
import json
from typing import Dict, Any, Optional, List
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
import time
from metrics import INTENT_COUNTER, LLM_LATENCY, DB_OPERATION_COUNTER, MATCH_COUNTER

load_dotenv()


class RideSharingLLMService:
    """Service class to handle all LLM operations with conversation memory"""

    def __init__(self):
        self.llm = ChatGroq(
            model="openai/gpt-oss-120b",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0,
        )
        self.memory = memory_manager

    def format_matches_for_response(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format matches for frontend display"""
        formatted_matches = []

        for match in matches:
            offer = match["offer"]
            formatted_matches.append({
                "match_id": match.get("match_id"),
                "match_type": match["match_type"],
                "match_score": match["overall_score"],
                "pickup": offer.pickup_location,
                "drop": offer.drop_location,
                "route": offer.route,
                "date": offer.date,
                "time": offer.time,
                "remaining_seats": match["remaining_seats"],
                "additional_info": offer.additional_info
            })

        return formatted_matches

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
                "response": "I don't have any ride details to confirm. Please start over.",
                "matches": []
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
                user_id = session_id

                print(f"💾 Saving to database...")
                print(f"   Intent: {intent}")
                print(f"   Details: {details}")

                # Save to database
                if intent == "ride_request":
                    ride_entry = DatabaseService.save_ride_request(db, session_id, user_id, details)

                    DB_OPERATION_COUNTER.labels(operation="save_request", status="success").inc()

                    # Find matches
                    print(f"\n🔍 Starting matching process...")
                    available_offers = DatabaseService.get_active_ride_offers(db, date=details.get("date"))

                    matches = MatchingService.find_matches(ride_entry, available_offers)

                    if matches:
                        print(f"📈 Metric: Recording {len(matches)} matches found")
                        MATCH_COUNTER.labels(type="found").inc(len(matches))

                    # Save matches to database and get match IDs
                    saved_matches = []
                    for match in matches:
                        db_match = DatabaseService.save_match(
                            db,
                            request_id=ride_entry.id,
                            offer_id=match["offer_id"],
                            match_type=match["match_type"],
                            match_score=match["overall_score"]
                        )
                        match["match_id"] = db_match.id
                        saved_matches.append(match)

                    # Format matches for frontend
                    formatted_matches = self.format_matches_for_response(saved_matches)

                    # Generate appropriate response
                    if saved_matches:
                        response_msg = (
                            f"✅ Your ride request has been posted successfully!\n\n"
                            f"🎉 Great news! We found {len(saved_matches)} matching ride(s)!\n\n"
                            f"Please review the matches below and accept the one that works best for you."
                        )
                    else:
                        response_msg = (
                            f"✅ Your ride request has been posted successfully!\n\n"
                            f"📋 Details saved:\n"
                            f"📍 From: {details['pickup_location']}\n"
                            f"🎯 To: {details['drop_location']}\n"
                            f"📅 Date: {details['date']}\n"
                            f"🕐 Time: {details['time']}\n"
                            f"👥 Passengers: {details['passengers']}\n\n"
                            f"🔍 No matches found yet.\n"
                            f"We'll notify you when a matching ride becomes available!"
                        )

                    # Mark session as complete and clear
                    self.memory.mark_complete(session_id)

                    return {
                        "status": "success",
                        "saved_to_db": True,
                        "ride_type": "request",
                        "ride_id": ride_entry.id,
                        "matches_found": len(saved_matches),
                        "matches": formatted_matches,
                        "response": response_msg,
                        "next_action": "completed"
                    }

                # 2222
                elif intent == "ride_offer":
                    ride_entry = DatabaseService.save_ride_offer(db, session_id, user_id, details)

                    DB_OPERATION_COUNTER.labels(operation="save_offer", status="success").inc()

                    # Find matching requests for this offer
                    print(f"\n🔍 Checking for matching requests...")
                    active_requests = DatabaseService.get_active_ride_requests(db, date=details.get("date"))

                    saved_matches = []
                    for request in active_requests:
                        matches = MatchingService.find_matches(request, [ride_entry])
                        if matches:
                            # Save match
                            db_match = DatabaseService.save_match(
                                db,
                                request_id=request.id,
                                offer_id=ride_entry.id,
                                match_type=matches[0]["match_type"],
                                match_score=matches[0]["overall_score"]
                            )
                            # Add match_id to the match object
                            matches[0]["match_id"] = db_match.id
                            # Add the request object to the match
                            matches[0]["request"] = request
                            saved_matches.append(matches[0])

                    if saved_matches:
                        print(f"📈 Metric: Recording {len(saved_matches)} matches found")
                        MATCH_COUNTER.labels(type="found").inc(len(saved_matches))

                    # Format matches for frontend (IMPORTANT: Now we format them!)
                    formatted_matches = []
                    for match in saved_matches:
                        request = match["request"]
                        formatted_matches.append({
                            "match_id": match.get("match_id"),
                            "match_type": match["match_type"],
                            "match_score": match["overall_score"],
                            "pickup": ride_entry.pickup_location,
                            "drop": ride_entry.drop_location,
                            "route": ride_entry.route,
                            "date": ride_entry.date,
                            "time": ride_entry.time,
                            "remaining_seats": ride_entry.available_seats - ride_entry.seats_filled,
                            "additional_info": ride_entry.additional_info,
                            "requester_passengers": request.passengers  # Extra info about the requester
                        })

                    response_msg = (
                        f"✅ Your ride offer has been posted successfully!\n\n"
                        f"📋 Details saved:\n"
                        f"📍 From: {details['pickup_location']}\n"
                        f"🎯 To: {details['drop_location']}\n"
                    )

                    if details.get("route"):
                        route_str = " → ".join(details["route"])
                        response_msg += f"🛣️ Route: {route_str}\n"

                    response_msg += (
                        f"📅 Date: {details['date']}\n"
                        f"🕐 Time: {details['time']}\n"
                        f"💺 Available Seats: {details['available_seats']}\n\n"
                    )

                    if len(saved_matches) > 0:
                        response_msg += f"🎉 Great news! {len(saved_matches)} rider(s) are looking for similar rides!\n\n"
                        response_msg += f"Please review the matches below."
                    else:
                        response_msg += "We'll notify you when riders are looking for your route!"

                    # Mark session as complete
                    self.memory.mark_complete(session_id)

                    return {
                        "status": "success",
                        "saved_to_db": True,
                        "ride_type": "offer",
                        "ride_id": ride_entry.id,
                        "matches_found": len(saved_matches),
                        "matches": formatted_matches,  # ← NOW RETURNING FORMATTED MATCHES!
                        "response": response_msg,
                        "next_action": "completed"
                    }

            except Exception as e:
                print(f"\n❌ DATABASE ERROR: {e}")
                import traceback
                traceback.print_exc()

                DB_OPERATION_COUNTER.labels(operation="save_db", status="error").inc()

                return {
                    "status": "error",
                    "response": "Sorry, there was an error saving your ride. Please try again later.",
                    "matches": []
                }
            finally:
                db.close()

        # Handle NO or corrections
        elif message_lower in ["no", "nope", "wrong", "incorrect"]:
            self.memory.clear_session(session_id)

            return {
                "status": "correction_needed",
                "response": "No problem! Let's start over. What would you like to change? Or tell me about your ride again from the beginning.",
                "matches": []
            }

        # If not clear yes/no, treat as correction
        else:
            print(f"🔄 User wants to make corrections: {message}")
            session.is_complete = False
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
        start_time = time.time()
        """Classify message intent with conversation context"""
        try:
            print(f"\n{'='*60}")
            print(f"🎯 INTENT CLASSIFICATION")
            print(f"{'='*60}")
            print(f"👤 Session ID: {session_id}")
            print(f"📝 User Message: {message}")

            history = self.memory.get_conversation_history(session_id, last_n=5)

            if history:
                print(f"🧠 Using conversation history ({len(history)} messages)")
                for i, msg in enumerate(history[-3:], 1):
                    print(f"   {i}. {msg['role']}: {msg['content'][:50]}...")
            else:
                print(f"🧠 No conversation history (first message)")

            chain = INTENT_CLASSIFICATION_PROMPT | self.llm
            response = chain.invoke({"message": message})

            duration = time.time() - start_time
            LLM_LATENCY.labels(operation="classify").observe(duration)
            result_text = response.content.strip()

            print(f"🤖 LLM Raw Response:\n{result_text}")

            result = self._parse_json_response(result_text)

            intent_type = result.get("intent", "unknown")
            INTENT_COUNTER.labels(intent_type=intent_type).inc()

            print(f"✅ Parsed Intent: {result['intent']}")
            print(f"✅ Confidence: {result['confidence']}")
            print(f"✅ Reasoning: {result['reasoning']}")

            self.memory.set_intent(session_id, result["intent"])

            print(f"{'='*60}\n")

            return IntentResponse(**result)

        except Exception as e:
            print(f"❌ Intent Classification Error: {e}")
            import traceback

            traceback.print_exc()

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
        start_time = time.time()
        """Extract ride details from message using conversation context"""
        try:
            print(f"\n{'='*60}")
            print(f"🔍 INFORMATION EXTRACTION")
            print(f"{'='*60}")
            print(f"👤 Session ID: {session_id}")
            print(f"📝 Message: {message}")
            print(f"🎯 Intent: {intent}")

            session = self.memory.get_session(session_id)
            existing_details = session.ride_details

            if existing_details:
                print(f"\n📊 Existing Details from Memory:")
                for key, value in existing_details.items():
                    if value is not None:
                        print(f"   • {key}: {value}")

            conversation_text = self.memory.get_conversation_history(
                session_id, last_n=5, format_type="text"
            )

            chain = CONTEXT_AWARE_EXTRACTION_PROMPT | self.llm
            response = chain.invoke(
                {
                    "message": message,
                    "intent": intent,
                    "conversation_history": conversation_text,
                    "existing_details": json.dumps(existing_details),
                }
            )

            duration = time.time() - start_time
            LLM_LATENCY.labels(operation="extract").observe(duration)

            result_text = response.content.strip()

            print(f"\n🤖 LLM Raw Response:")
            print(f"{result_text}")
            print(f"{'-'*60}")

            result = self._parse_json_response(result_text)

            print(f"\n✅ Successfully Parsed JSON")
            print(f"📊 Newly Extracted Details:")
            for key, value in result["details"].items():
                print(f"   • {key}: {value}")

            merged_details = {**existing_details, **result["details"]}

            if intent == "ride_request" and merged_details.get("passengers") is None:
                merged_details["passengers"] = 1
                print(f"   • passengers: 1 (default)")

            self.memory.update_ride_details(session_id, merged_details)

            required_fields = ["pickup_location", "drop_location", "date", "time"]
            if intent == "ride_request":
                required_fields.append("passengers")
            elif intent == "ride_offer":
                required_fields.append("available_seats")

            missing = [
                field for field in required_fields if merged_details.get(field) is None
            ]

            is_complete = len(missing) == 0

            print(f"\n📋 Analysis (After Merging):")
            print(f"   • Required fields: {', '.join(required_fields)}")
            print(f"   • Missing fields: {', '.join(missing) if missing else 'None'}")
            print(f"   • Is complete: {is_complete}")

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

            session = self.memory.get_session(session_id)
            existing_details = session.ride_details or {}

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
            self.memory.print_session_summary(session_id)

            chain = CONFIRMATION_PROMPT | self.llm
            response = chain.invoke(
                {"intent": intent, "details": details.model_dump_json()}
            )
            return response.content.strip()
        except Exception as e:
            print(f"⚠️ Confirmation generation error: {e}")

            msg = "Let me confirm your ride:\n"
            if details.pickup_location:
                msg += f"📍 From: {details.pickup_location}\n"
            if details.drop_location:
                msg += f"🎯 To: {details.drop_location}\n"
            if details.route:
                route_str = " → ".join(details.route)
                msg += f"🛣️ Route: {route_str}\n"
            if details.date:
                msg += f"📅 Date: {details.date}\n"
            if details.time:
                msg += f"🕐 Time: {details.time}\n"
            if details.passengers:
                msg += f"👥 Passengers: {details.passengers}\n"
            if details.available_seats:
                msg += f"💺 Available Seats: {details.available_seats}\n"

            msg += "\nIs everything correct? Reply 'Yes' to confirm."
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

        self.memory.add_user_message(session_id, message)

        session = self.memory.get_session(session_id)
        if session.is_complete and session.current_intent in ["ride_request", "ride_offer"]:
            print(f"⏳ Session is complete, waiting for confirmation...")
            confirmation_result = self.handle_confirmation(message, session_id)

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
                "matches_found": confirmation_result.get("matches_found", 0),
                "matches": confirmation_result.get("matches", [])
            }

        if session.current_intent and session.current_intent != "other" and not session.is_complete:
            print(f"🔄 Continuing existing conversation with intent: {session.current_intent}")
            intent_result = IntentResponse(
                intent=session.current_intent,
                confidence=0.95,
                reasoning="Continuing existing conversation flow"
            )
        else:
            intent_result = self.classify_intent(message, session_id)

        if intent_result.intent == "other":
            print(f"ℹ️ Intent classified as 'other' - sending greeting\n")
            response_msg = "Hello! I can help you find rides or offer rides. Please tell me if you need a ride or if you're offering one."

            self.memory.add_assistant_message(session_id, response_msg)

            return {
                "intent": "other",
                "confidence": intent_result.confidence,
                "response": response_msg,
                "is_complete": False,
                "details": {},
                "missing_fields": [],
                "next_action": "awaiting_intent",
                "matches": []
            }

        extraction_result = self.extract_information(
            message, intent_result.intent, session_id
        )

        if extraction_result.is_complete:
            confirmation_msg = self.generate_confirmation_message(
                intent_result.intent, extraction_result.details, session_id
            )
            response_message = confirmation_msg
            next_action = "awaiting_confirmation"

            self.memory.mark_complete(session_id)

            print(f"✅ Extraction complete - sending confirmation")
        else:
            response_message = extraction_result.clarifying_question
            next_action = "awaiting_details"
            print(f"⏳ Extraction incomplete - asking for clarification")

        self.memory.add_assistant_message(session_id, response_message)

        print(f"\n{'#'*60}")
        print(f"✅ PROCESSING COMPLETE")
        print(f"{'#'*60}\n")

        self.memory.print_memory_stats()

        return {
            "intent": intent_result.intent,
            "confidence": intent_result.confidence,
            "details": extraction_result.details.model_dump(),
            "missing_fields": extraction_result.missing_fields,
            "is_complete": extraction_result.is_complete,
            "response": response_message,
            "next_action": next_action,
            "matches": []
        }
