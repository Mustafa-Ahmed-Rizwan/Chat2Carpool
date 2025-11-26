from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class IntentResponse(BaseModel):
    """Response from intent classification"""

    intent: Literal["ride_request", "ride_offer", "other"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class RideDetails(BaseModel):
    """Extracted ride information"""

    pickup_location: Optional[str] = None
    drop_location: Optional[str] = None
    route: Optional[list[str]] = None
    date: Optional[str] = None
    time: Optional[str] = None
    passengers: Optional[int] = None  # For ride requests
    available_seats: Optional[int] = None  # For ride offers
    additional_info: Optional[str] = None


class ExtractionResponse(BaseModel):
    """Response from information extraction"""

    details: RideDetails
    missing_fields: list[str]
    is_complete: bool
    clarifying_question: Optional[str] = None


class WhatsAppMessage(BaseModel):
    """Incoming WhatsApp message"""

    From: str
    To: str
    Body: str
    MessageSid: str


class ProcessedMessage(BaseModel):
    """Final processed message response"""

    intent: str
    details: RideDetails
    is_complete: bool
    response_message: str
    next_action: str
