from langchain.prompts import PromptTemplate

# Intent Classification Prompt
INTENT_CLASSIFICATION_PROMPT = PromptTemplate(
    input_variables=["message"],
    template="""You are a ride-sharing classification AI. Classify the user's intent.

USER MESSAGE: "{message}"

CLASSIFICATION RULES:
1. "ride_request" = User NEEDS transportation (they want to be a passenger)
   Examples: "need ride", "want to go", "take me to", "I'm going to X", "traveling from X to Y"

2. "ride_offer" = User is OFFERING to drive (they have a car and available seats)
   Examples: "offering ride", "have space", "can take passengers", "driving to X", "have empty seats"

3. "other" = Greetings, questions, unrelated messages
   Examples: "hello", "how does this work?", "thanks"

RESPOND WITH ONLY THIS JSON FORMAT (no markdown, no code blocks, no extra text):
{{
    "intent": "ride_request",
    "confidence": 0.95,
    "reasoning": "Brief explanation"
}}

JSON:""",
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
- pickup_location: Starting point
- drop_location: Destination
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

4. For ride_request: Default passengers to 1 if not mentioned

5. Return ALL fields (new + existing) in the response

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

NOW EXTRACT FROM THE CURRENT MESSAGE ABOVE.

RESPOND WITH ONLY THIS JSON (no markdown, no explanation):
{{
    "details": {{
        "pickup_location": ...,
        "drop_location": ...,
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
3. date → "When do you need this ride? (today/tomorrow/specific date)"
4. time → "What time do you need the ride?"
5. passengers → "How many passengers will be traveling?"
6. available_seats → "How many seats do you have available?"

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
📅 Date: [date]
🕒 Time: [time]
👥 Passengers: [number]

Is everything correct? Reply 'Yes' to confirm or let me know what to change."

Generate the confirmation message (plain text only, no JSON):""",
)
