from langchain.prompts import PromptTemplate

# Intent Classification Prompt
# prompts.py

INTENT_CLASSIFICATION_PROMPT = PromptTemplate(
    input_variables=["message"],
    template="""You are a strict logic engine for a carpooling app. Your ONLY job is to classify if the user is a DRIVER (offering) or a PASSENGER (requesting).

Analyze the "Actor" in the sentence:
- If the user says "I am driving", "I have seats", "I can take", they are the **PROVIDER** -> "ride_offer".
- If the user says "I need", "I want", "looking for", "can you take me", they are the **CONSUMER** -> "ride_request".

### FEW-SHOT EXAMPLES (Study these carefully):

Message: "I need a ride to the airport"
Actor: Wants a service.
Intent: ride_request

Message: "I am driving to the airport and have 2 empty seats"
Actor: Providing a service.
Intent: ride_offer

Message: "Anyone going to Gulshan?"
Actor: Asking for a ride.
Intent: ride_request

Message: "Offering a lift to North Nazimabad"
Actor: Providing a service.
Intent: ride_offer

Message: "I have space for 3 people going to Clifton"
Actor: Providing a service.
Intent: ride_offer

Message: "Can someone take me to the mall?"
Actor: Wants a service.
Intent: ride_request

### END EXAMPLES

USER MESSAGE: "{message}"

RESPONSE FORMAT (JSON ONLY):
{{
    "intent": "ride_request" | "ride_offer" | "other",
    "confidence": 1.0,
    "reasoning": "Explain WHY. e.g., 'User explicitly mentioned having empty seats.'"
}}

JSON:"""
)

# Context-Aware Extraction Prompt - NEW!
CONTEXT_AWARE_EXTRACTION_PROMPT = PromptTemplate(
    input_variables=["message", "intent", "conversation_history", "existing_details"],
    template="""You are an expert information extraction AI with conversation memory.

CURRENT MESSAGE: "{message}"
USER INTENT: {intent}

CONVERSATION HISTORY:
{conversation_history}

EXISTING DETAILS FROM PREVIOUS MESSAGES:
{existing_details}

YOUR TASK:
Extract NEW information from the current message and combine it with existing details.

FIELDS TO EXTRACT:
- pickup_location: Starting point (if route is provided, extract FIRST stop as pickup)
- drop_location: Destination (if route is provided, extract LAST stop as drop)
- route: List of stops in order (e.g., ["FAST", "Drigh Road", "Millennium", "Gulshan Chowrangi"]). Extract if user mentions "route:", "via", or lists multiple places with arrows/dashes. Set to null if not mentioned.
- date: "today", "tomorrow", or specific date
- time: "5pm", "10:00 AM", "morning", "afternoon"
- passengers: Number of people (for ride_request, default 1)
- available_seats: Number of seats (for ride_offer only)
- additional_info: Any other relevant details

CRITICAL RULES:
1. If the user is ANSWERING a question, extract that specific information
   Example: Bot asked "Where from?" → User says "DHA" → Extract pickup_location: "DHA"

2. If a field already has a value in EXISTING DETAILS, keep it UNLESS the user explicitly changes it
   Example: If pickup was "DHA" and user says "Actually, from Clifton" → Update to "Clifton"

3. Extract ONLY what's mentioned in the current message, don't invent data
4. ROUTE EXTRACTION RULES:
   - If user provides route like "FAST – Drigh Road – Millennium – Nagan" or "Fast-> kala board ->model colony"
   - Extract as list: ["FAST", "Drigh Road", "Millennium", "Nagan"]
   - Set pickup_location = first stop in route
   - Set drop_location = last stop in route
   - Clean up arrows (->), dashes (–), and extra spaces
   - If no route mentioned, set route to null

5. For ride_request: Default passengers to 1 if not mentioned

6. Return ALL fields (new + existing) in the response

EXAMPLES:

Example 1 - First Message:
Current: "Need ride to airport tomorrow"
Existing: {{}}
Extract: {{"pickup_location": null, "drop_location": "airport", "date": "tomorrow", "time": null, "passengers": 1, "available_seats": null, "additional_info": null}}

Example 2 - Follow-up Answer:
Current: "From DHA"
Existing: {{"drop_location": "airport", "date": "tomorrow", "passengers": 1}}
Extract: {{"pickup_location": "DHA", "drop_location": "airport", "date": "tomorrow", "time": null, "passengers": 1, "available_seats": null, "additional_info": null}}

Example 3 - Adding More Details:
Current: "5pm please"
Existing: {{"pickup_location": "DHA", "drop_location": "airport", "date": "tomorrow", "passengers": 1}}
Extract: {{"pickup_location": "DHA", "drop_location": "airport", "date": "tomorrow", "time": "5pm", "passengers": 1, "available_seats": null, "additional_info": null}}

Example 4 - Complete from Start:
Current: "Going from Clifton to mall at 3pm today, 2 people"
Existing: {{}}
Extract: {{"pickup_location": "Clifton", "drop_location": "mall", "date": "today", "time": "3pm", "passengers": 2, "available_seats": null, "additional_info": null}}

Example 5 - Route Provided:
Current: "Route: FAST – Drigh Road – Millennium – Gulshan Chowrangi – Sohrab Goth"
Existing: {{}}
Extract: {{
    "pickup_location": "FAST",
    "drop_location": "Sohrab Goth",
    "route": ["FAST", "Drigh Road", "Millennium", "Gulshan Chowrangi", "Sohrab Goth"],
    "date": null,
    "time": null,
    "passengers": 1,
    "available_seats": null,
    "additional_info": null
}}

Example 6 - Route with Arrows:
Current: "Going Fast-> kala board ->model colony -> kazimabad at 5pm today"
Existing: {{}}
Extract: {{
    "pickup_location": "Fast",
    "drop_location": "kazimabad",
    "route": ["Fast", "kala board", "model colony", "kazimabad"],
    "date": "today",
    "time": "5pm",
    "passengers": 1,
    "available_seats": null,
    "additional_info": null
}}

Example 7 - No Route (Normal Message):
Current: "Need ride from DHA to Airport at 3pm"
Existing: {{}}
Extract: {{
    "pickup_location": "DHA",
    "drop_location": "Airport",
    "route": null,
    "date": null,
    "time": "3pm",
    "passengers": 1,
    "available_seats": null,
    "additional_info": null
}}

NOW EXTRACT FROM THE CURRENT MESSAGE ABOVE.

RESPOND WITH ONLY THIS JSON (no markdown, no explanation):
{{
    "details": {{
        "pickup_location": ...,
        "drop_location": ...,
        "route": [...] or null,
        "date": ...,
        "time": ...,
        "passengers": ...,
        "available_seats": ...,
        "additional_info": ...
    }},
    "missing_fields": [...],
    "is_complete": true/false
}}

JSON:""",
)

# Original Extraction Prompt (kept as backup)
EXTRACTION_PROMPT = PromptTemplate(
    input_variables=["message", "intent"],
    template="""You are an expert information extraction AI. Extract structured ride details.

USER MESSAGE: "{message}"
USER INTENT: {intent}

EXTRACTION TASK:
Read the message carefully and extract these fields:
- pickup_location: Starting point (set to null if not mentioned)
- drop_location: Destination (set to null if not mentioned)
- date: When the ride is needed - "today", "tomorrow", specific date (null if not mentioned)
- time: Time of day - "5pm", "10:00 AM", "morning", "afternoon" (null if not mentioned)
- passengers: Number of people (for ride_request only, default to 1 if not specified)
- available_seats: Number of seats available (for ride_offer only)
- additional_info: Any other details (null if none)

RESPOND WITH ONLY THIS JSON (no markdown):
{{
    "details": {{...}},
    "missing_fields": [...],
    "is_complete": true/false
}}

JSON:""",
)

# Clarifying Question Generator
CLARIFICATION_PROMPT = PromptTemplate(
    input_variables=["intent", "missing_fields", "existing_details"],
    template="""Generate ONE natural, friendly question to get missing information.

CONTEXT:
- Intent: {intent}
- Missing: {missing_fields}
- Already have: {existing_details}

QUESTION PRIORITY:
1. pickup_location → "Where will you be starting from?"
2. drop_location → "Where do you need to go?" / "Where are you heading?"
3. route → "Could you share your route? (Optional - helps find better matches)"
4. date → "When do you need this ride? (today/tomorrow/specific date)"
5. time → "What time do you need the ride?"
6. passengers → "How many passengers will be traveling?"
7. available_seats → "How many seats do you have available?"

SPECIAL RULE FOR ROUTE:
- Route is OPTIONAL. If pickup and drop are already provided, DO NOT ask for route.
- Only suggest route if user seems open to providing more details.
- Keep the tone casual: "Would you like to share your route for better matches? (Optional)"

RULES:
- Ask about the FIRST missing field only
- Be conversational and friendly
- Keep it short and clear
- Don't ask multiple questions

Return ONLY the question text (no JSON, no quotes):""",
)

# Confirmation Message Generator
CONFIRMATION_PROMPT = PromptTemplate(
    input_variables=["intent", "details"],
    template="""Generate a friendly confirmation message for the ride details.

INTENT: {intent}
DETAILS: {details}

Create a message that:
1. Confirms all provided details clearly
2. Uses emojis for visual clarity (📍 for location, 📅 for date, 🕒 for time, 👥 for passengers, 💺 for seats)
3. Asks user to confirm with "Yes" or make corrections
4. Is warm and professional

FORMAT EXAMPLE:
"Great! Let me confirm your ride:
📍 From: [pickup]
📍 To: [drop]
🛣️ Route: [stop1 → stop2 → stop3] (if provided, otherwise skip this line)
📅 Date: [date]
🕒 Time: [time]
👥 Passengers: [number]

Is everything correct? Reply 'Yes' to confirm or let me know what to change."

Generate the confirmation message (plain text only, no JSON):""",
)
