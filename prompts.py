from langchain.prompts import PromptTemplate

# Intent Classification Prompt - Ultra Robust
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

# Information Extraction Prompt - Chain of Thought
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

CRITICAL INSTRUCTIONS:
1. Extract EXACTLY what is mentioned - do not assume or infer
2. If a field is not mentioned, set it to null
3. For ride_request: If passengers not mentioned, set to 1
4. For ride_offer: If available_seats not mentioned, set to null
5. Keep location names as mentioned (don't modify them)
6. Keep time format as mentioned (don't convert)

STEP-BY-STEP PROCESS:
Step 1: Read the message word by word
Step 2: Identify locations mentioned (which is pickup? which is drop?)
Step 3: Find date references (today, tomorrow, specific dates)
Step 4: Find time references (5pm, morning, etc.)
Step 5: Count passengers or seats mentioned
Step 6: Construct the JSON

EXAMPLE EXTRACTIONS:

Example 1:
Message: "Need ride to airport tomorrow at 5pm"
Think: No pickup mentioned, drop is "airport", date is "tomorrow", time is "5pm", no passenger count so default 1
Output:
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
Message: "Going from DHA to Clifton at 3pm today, 2 people"
Think: pickup is "DHA", drop is "Clifton", date is "today", time is "3pm", passengers is 2
Output:
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
Message: "Driving to mall tomorrow afternoon, 3 seats available"
Think: No pickup, drop is "mall", date is "tomorrow", time is "afternoon", available_seats is 3
Output:
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

NOW EXTRACT FROM THE MESSAGE ABOVE.

RESPOND WITH ONLY THIS JSON FORMAT (no markdown, no code blocks, no explanation):
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
