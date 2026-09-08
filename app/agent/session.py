from typing import Dict, Any, List, Optional


class SessionManager:
    """Manages volatile in-memory conversation state for active Telegram chats."""

    def __init__(self):
        self._sessions: Dict[int, Dict[str, Any]] = {}

    def get_session(self, chat_id: int) -> Dict[str, Any]:
        if chat_id not in self._sessions:
            self._sessions[chat_id] = {
                "active_bill_id": None,
                "history": []
            }
        return self._sessions[chat_id]

    def get_history(self, chat_id: int) -> List[Dict[str, Any]]:
        """Retrieves the conversation history for a specific chat."""
        session = self.get_session(chat_id)
        return session["history"]

    def add_message(self, chat_id: int, role: str, text: str) -> None:
        """Appends a message entry to the chat's conversation history."""
        session = self.get_session(chat_id)
        session["history"].append({"role": role, "parts": [text]})

    def set_active_bill(self, chat_id: int, bill_id: Optional[int]) -> None:
        session = self.get_session(chat_id)
        session["active_bill_id"] = bill_id

    def get_active_bill(self, chat_id: int) -> Optional[int]:
        session = self.get_session(chat_id)
        return session.get("active_bill_id")

    def reset_session(self, chat_id: int) -> None:
        """Resets active bill and conversation memory for /new command."""
        self._sessions[chat_id] = {
            "active_bill_id": None,
            "history": []
        }


session_manager = SessionManager()