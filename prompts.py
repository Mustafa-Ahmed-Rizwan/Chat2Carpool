from langchain.prompts import PromptTemplate

# Intent Classification Prompt - IMPROVED VERSION
INTENT_CLASSIFICATION_PROMPT = PromptTemplate(
    input_variables=["message"],
    template="""You are an expert AI assistant for a ride-sharing platform. Your job is to classify user messages accurately.

CLASSIFICATION RULES:
1. "ride_request" - User NEEDS a ride (they are a passenger looking for transportation)
   - Keywords: "need ride", "looking for ride", "need to go", "want to go", "take me to", "I'm going to", "traveling to"
   - Even if not explicitly stated, if they mention going FROM one place TO another, it's usually a request

2. "ride_offer" - User is OFFERING a ride (they are a driver with available seats)
   - Keywords: "offering ride", "have space", "empty seats", "can take", "driving to", "going to [place] and have room"
   - Must explicitly mention having space/seats available OR offering to take someone

3. "other" - ONLY for: greetings, questions about the service, complaints, or completely irrelevant messages
   - Do NOT classify legitimate ride requests/offers as "other"

IMPORTANT: Be SMART and LIBERAL in classification. If there's ANY indication of ride intent, classify it as request/offer, NOT "other".

User Message: "{message}"

Analyze carefully and respond with ONLY valid JSON (no markdown, no code blocks):
{{
    "intent": "ride_request",
    "confidence": 0.95,
    "reasoning": "User mentions needing transportation from point A to B"
}}

JSON Response:""",
)

# Information Extraction Prompt - IMPROVED VERSION
# Information Extraction Prompt - ROBUST VERSION
EXTRACTION_PROMPT = PromptTemplate(
    input_variables=["message", "intent"],
    template="""You are an AI that extracts structured ride information from natural language messages.

USER MESSAGE: "{message}"
INTENT: {intent}

YOUR TASK:
Extract all ride details from the message. If information is missing, set it to null.

FIELD DEFINITIONS:
- pickup_location: Where the ride starts (any location mentioned as origin)
- drop_location: Where the ride ends (destination)
- date: When the ride is needed (today/tomorrow/specific date)
- time: What time (extract as-is: "5pm", "10:00 AM", "noon", etc.)
- passengers: Number of people needing ride (default to 1 if not mentioned for ride_request)
- available_seats: Number of seats available (only for ride_offer)
- additional_info: Any other relevant details

EXTRACTION EXAMPLES:

Example 1:
Message: "Need ride to airport tomorrow 5pm"
{{
    "details": {{
        "pickup_location": null,
        "drop_location": "airport",
        "date": "tomorrow",
        "time": "5pm",
        "passengers": 1,
        "available_seats": null,
        "additional_info": null
    }},
    "missing_fields": ["pickup_location"],
    "is_complete": false
}}

Example 2:
Message: "Going from DHA to Clifton at 3pm today, need ride for 2 people"
{{
    "details": {{
        "pickup_location": "DHA",
        "drop_location": "Clifton",
        "date": "today",
        "time": "3pm",
        "passengers": 2,
        "available_seats": null,
        "additional_info": null
    }},
    "missing_fields": [],
    "is_complete": true
}}

Example 3:
Message: "Driving to mall tomorrow afternoon, have 3 seats"
{{
    "details": {{
        "pickup_location": null,
        "drop_location": "mall",
        "date": "tomorrow",
        "time": "afternoon",
        "passengers": null,
        "available_seats": 3,
        "additional_info": null
    }},
    "missing_fields": ["pickup_location"],
    "is_complete": false
}}

RULES:
1. Extract what IS mentioned, don't make assumptions
2. For ride_request: Mark complete if has pickup, drop, date, time, passengers (default 1)
3. For ride_offer: Mark complete if has pickup, drop, date, time, available_seats
4. missing_fields should list ONLY required fields that are null
5. Return ONLY valid JSON, no extra text

NOW EXTRACT FROM THE USER MESSAGE ABOVE:
""",
)


# Clarifying Question Generator - ROBUST VERSION
CLARIFICATION_PROMPT = PromptTemplate(
    input_variables=["intent", "missing_fields", "existing_details"],
    template="""Generate ONE friendly question to get the most important missing information.

Missing fields: {missing_fields}
Already known: {existing_details}
Intent: {intent}

Ask for the FIRST missing field in this priority order:
1. pickup_location → "Where will you be starting from?"
2. drop_location → "Where do you need to go?"
3. date → "When do you need this ride? (today/tomorrow/specific date)"
4. time → "What time? (e.g., 5pm, morning, afternoon)"
5. passengers → "How many passengers will be traveling?"
6. available_seats → "How many seats do you have available?"

Return ONLY the question text, nothing else:""",
)

# Confirmation Message Generator - IMPROVED VERSION
CONFIRMATION_PROMPT = PromptTemplate(
    input_variables=["intent", "details"],
    template="""Generate a warm, professional confirmation message.

Intent: {intent}
Details: {details}

Create a message that:
1. Confirms the ride details clearly
2. Is friendly and reassuring
3. Asks user to confirm with "Yes" or make corrections
4. Uses natural, conversational language

Format example:
"Perfect! Let me confirm your ride:
📍 From: [pickup]
📍 To: [drop]
📅 Date: [date]
🕐 Time: [time]
👥 Passengers: [number]

Is this correct? Reply 'Yes' to confirm or let me know what needs to be changed."

Generate the confirmation message (just the text, no JSON):""",
)
