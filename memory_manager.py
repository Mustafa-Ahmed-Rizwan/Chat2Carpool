"""
Memory Management System for Ride-Sharing Bot
Handles conversation history with automatic cleanup and session management
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import threading
import time


@dataclass
class ConversationMessage:
    """Represents a single message in the conversation"""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, str]:
        """Convert to LangChain-compatible format"""
        return {"role": self.role, "content": self.content}

    def __repr__(self) -> str:
        time_str = self.timestamp.strftime("%H:%M:%S")
        return f"[{time_str}] {self.role}: {self.content[:50]}..."


@dataclass
class ConversationSession:
    """Represents a complete conversation session for a user"""

    session_id: str
    messages: List[ConversationMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    ride_details: Dict[str, Any] = field(default_factory=dict)
    current_intent: Optional[str] = None
    is_complete: bool = False

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """Add a new message to the conversation"""
        message = ConversationMessage(
            role=role, content=content, metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_activity = datetime.now()

    def get_messages_for_llm(
        self, last_n: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """Get messages in LangChain format, optionally limiting to last N messages"""
        messages_to_use = self.messages[-last_n:] if last_n else self.messages
        return [msg.to_dict() for msg in messages_to_use]

    def get_conversation_text(self) -> str:
        """Get full conversation as formatted text"""
        lines = []
        for msg in self.messages:
            prefix = "User" if msg.role == "user" else "Bot"
            lines.append(f"{prefix}: {msg.content}")
        return "\n".join(lines)

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired due to inactivity"""
        elapsed = datetime.now() - self.last_activity
        return elapsed > timedelta(minutes=timeout_minutes)

    def clear(self):
        """Clear conversation history (keep session metadata)"""
        self.messages.clear()
        self.ride_details.clear()
        self.current_intent = None
        self.is_complete = False
        self.last_activity = datetime.now()


class MemoryManager:
    """
    Manages conversation memory for multiple users
    Features:
    - Session-based memory (per user)
    - Automatic cleanup of expired sessions
    - Thread-safe operations
    - Configurable retention policies
    """

    def __init__(
        self,
        session_timeout_minutes: int = 30,
        cleanup_interval_minutes: int = 10,
        max_messages_per_session: int = 50,
        enable_auto_cleanup: bool = True,
    ):
        self.session_timeout_minutes = session_timeout_minutes
        self.cleanup_interval_minutes = cleanup_interval_minutes
        self.max_messages_per_session = max_messages_per_session
        self.enable_auto_cleanup = enable_auto_cleanup

        # Thread-safe storage
        self.sessions: Dict[str, ConversationSession] = {}
        self.lock = threading.Lock()

        # Start background cleanup thread
        if self.enable_auto_cleanup:
            self._start_cleanup_thread()

    def get_session(self, session_id: str) -> ConversationSession:
        """Get or create a conversation session"""
        with self.lock:
            if session_id not in self.sessions:
                print(f"🆕 Creating new session for: {session_id}")
                self.sessions[session_id] = ConversationSession(session_id=session_id)
            else:
                # Update last activity
                self.sessions[session_id].last_activity = datetime.now()

            return self.sessions[session_id]

    def add_user_message(
        self, session_id: str, message: str, metadata: Dict[str, Any] = None
    ):
        """Add a user message to the session"""
        session = self.get_session(session_id)
        session.add_message("user", message, metadata)
        print(f"💬 User message added to session {session_id}: {message[:50]}...")

    def add_assistant_message(
        self, session_id: str, message: str, metadata: Dict[str, Any] = None
    ):
        """Add an assistant message to the session"""
        session = self.get_session(session_id)
        session.add_message("assistant", message, metadata)
        print(f"🤖 Assistant message added to session {session_id}: {message[:50]}...")

    def get_conversation_history(
        self,
        session_id: str,
        last_n: Optional[int] = None,
        format_type: str = "langchain",
    ) -> Any:
        """
        Get conversation history in various formats

        Args:
            session_id: Session identifier
            last_n: Limit to last N messages (None = all)
            format_type: "langchain" (list of dicts) or "text" (formatted string)
        """
        session = self.get_session(session_id)

        if format_type == "langchain":
            return session.get_messages_for_llm(last_n)
        elif format_type == "text":
            return session.get_conversation_text()
        else:
            raise ValueError(f"Unknown format_type: {format_type}")

    def update_ride_details(self, session_id: str, details: Dict[str, Any]):
        """Update ride details for the session"""
        session = self.get_session(session_id)
        session.ride_details.update(details)
        print(f"📊 Updated ride details for session {session_id}")

    def set_intent(self, session_id: str, intent: str):
        """Set the current intent for the session"""
        session = self.get_session(session_id)
        session.current_intent = intent
        print(f"🎯 Set intent for session {session_id}: {intent}")

    def mark_complete(self, session_id: str):
        """Mark a session as complete"""
        session = self.get_session(session_id)
        session.is_complete = True
        print(f"✅ Session {session_id} marked as complete")

    def clear_session(self, session_id: str):
        """Clear a specific session's conversation"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id].clear()
                print(f"🗑️ Cleared session: {session_id}")

    def delete_session(self, session_id: str):
        """Completely remove a session"""
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                print(f"🗑️ Deleted session: {session_id}")

    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        with self.lock:
            return list(self.sessions.keys())

    def get_session_count(self) -> int:
        """Get total number of active sessions"""
        with self.lock:
            return len(self.sessions)

    def print_session_summary(self, session_id: str):
        """Print a detailed summary of a session"""
        session = self.get_session(session_id)

        print(f"\n{'='*60}")
        print(f"📋 SESSION SUMMARY: {session_id}")
        print(f"{'='*60}")
        print(f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Last Activity: {session.last_activity.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Messages: {len(session.messages)}")
        print(f"Intent: {session.current_intent or 'Not set'}")
        print(f"Complete: {session.is_complete}")

        if session.ride_details:
            print(f"\n📊 Ride Details:")
            for key, value in session.ride_details.items():
                if value is not None:
                    print(f"   • {key}: {value}")

        print(f"\n💬 Conversation History:")
        for i, msg in enumerate(session.messages, 1):
            prefix = "👤" if msg.role == "user" else "🤖"
            print(f"   {i}. {prefix} {msg.content[:60]}...")

        print(f"{'='*60}\n")

    def _cleanup_expired_sessions(self):
        """Remove expired sessions (background task)"""
        with self.lock:
            expired = [
                session_id
                for session_id, session in self.sessions.items()
                if session.is_expired(self.session_timeout_minutes)
            ]

            for session_id in expired:
                print(f"🧹 Cleaning up expired session: {session_id}")
                del self.sessions[session_id]

            if expired:
                print(f"🧹 Cleaned up {len(expired)} expired sessions")

    def _start_cleanup_thread(self):
        """Start background thread for automatic cleanup"""

        def cleanup_loop():
            while True:
                time.sleep(self.cleanup_interval_minutes * 60)
                self._cleanup_expired_sessions()

        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()
        print(
            f"🧹 Started automatic cleanup thread (interval: {self.cleanup_interval_minutes} min)"
        )

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about memory usage"""
        with self.lock:
            total_messages = sum(len(s.messages) for s in self.sessions.values())
            active_sessions = len(self.sessions)

            return {
                "active_sessions": active_sessions,
                "total_messages": total_messages,
                "avg_messages_per_session": (
                    total_messages / active_sessions if active_sessions > 0 else 0
                ),
                "timeout_minutes": self.session_timeout_minutes,
            }

    def print_memory_stats(self):
        """Print memory statistics"""
        stats = self.get_memory_stats()

        print(f"\n{'='*60}")
        print(f"📊 MEMORY STATISTICS")
        print(f"{'='*60}")
        print(f"Active Sessions: {stats['active_sessions']}")
        print(f"Total Messages: {stats['total_messages']}")
        print(f"Avg Messages/Session: {stats['avg_messages_per_session']:.1f}")
        print(f"Session Timeout: {stats['timeout_minutes']} minutes")
        print(f"{'='*60}\n")


# Global memory manager instance
memory_manager = MemoryManager(
    session_timeout_minutes=30,
    cleanup_interval_minutes=10,
    max_messages_per_session=50,
    enable_auto_cleanup=True,
)


# Convenience functions for easy access
def get_memory() -> MemoryManager:
    """Get the global memory manager instance"""
    return memory_manager


def get_conversation_history(
    session_id: str, last_n: Optional[int] = None
) -> List[Dict[str, str]]:
    """Quick access to conversation history"""
    return memory_manager.get_conversation_history(session_id, last_n, "langchain")


def add_to_memory(session_id: str, user_message: str, assistant_message: str):
    """Quick way to add both user and assistant messages"""
    memory_manager.add_user_message(session_id, user_message)
    memory_manager.add_assistant_message(session_id, assistant_message)
