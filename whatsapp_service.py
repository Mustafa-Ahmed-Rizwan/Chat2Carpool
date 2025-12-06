# whatsapp_service.py
from typing import List, Dict, Any
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()


class WhatsAppService:
    """Service to handle WhatsApp message formatting and sending"""

    def __init__(self):
        self.client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")
        )
        self.from_number = f"whatsapp:{os.getenv('TWILIO_PHONE_NUMBER')}"

    def format_matches_message(self, matches: List[Dict[str, Any]]) -> str:
        """
        Format matches into WhatsApp-friendly message with reply options
        """
        if not matches:
            return "No matches found yet. We'll notify you when one becomes available!"

        message = f"🎉 *Found {len(matches)} Match(es)!*\n\n"

        for idx, match in enumerate(matches, 1):
            score_percent = int(match["match_score"] * 100)
            message += f"*Match #{idx}* ({score_percent}% compatible)\n"
            message += f"📍 From: {match['pickup']}\n"
            message += f"🎯 To: {match['drop']}\n"
            message += f"📅 Date: {match['date']}\n"
            message += f"🕐 Time: {match['time']}\n"
            message += f"💺 Seats: {match['remaining_seats']}\n"
            message += f"🆔 Match ID: {match['match_id']}\n"
            message += "─────────────\n\n"

        message += "📝 *To accept a match, reply:*\n"
        message += "👉 `accept <match_id>`\n"
        message += "Example: `accept 15`\n\n"
        message += "To reject: `reject <match_id>`"

        return message

    def format_confirmation_message(self, data: Dict[str, Any]) -> str:
        """Format match confirmation message"""
        msg = data.get("message", "")

        # Make it WhatsApp-friendly
        msg = msg.replace("🎉", "🎉 ")
        msg = msg.replace("📋", "📋 ")
        msg = msg.replace("📍", "📍 ")
        msg = msg.replace("🎯", "🎯 ")
        msg = msg.replace("📅", "📅 ")
        msg = msg.replace("🕐", "🕐 ")
        msg = msg.replace("👥", "👥 ")
        msg = msg.replace("💺", "💺 ")

        return msg

    def send_message(self, to_number: str, message: str):
        """
        Send WhatsApp message to user
        Used for proactive notifications
        """
        try:
            message = self.client.messages.create(
                body=message, from_=self.from_number, to=f"whatsapp:{to_number}"
            )
            print(f"✅ Message sent to {to_number}: {message.sid}")
            return message.sid
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            return None


# Global instance
whatsapp_service = WhatsAppService()
