"""Conversation commands for RAG CLI.

This module implements CLI commands for conversation operations including
session management, message handling, summarization, and enhanced features.
"""

from rag_solution.cli.client import RAGAPIClient
from rag_solution.cli.config import RAGConfig

from .base import BaseCommand, CommandResult


class ConversationCommands(BaseCommand):
    """Commands for conversation operations.

    This class implements all conversation-related CLI commands,
    providing methods to interact with the chat and conversation APIs.
    """

    def __init__(self, api_client: RAGAPIClient, config: RAGConfig | None = None) -> None:
        """Initialize conversation commands.

        Args:
            api_client: HTTP API client instance
            config: Optional configuration settings
        """
        super().__init__(api_client, config)

    def create_session(
        self, collection_id: str, session_name: str, context_window_size: int = 4000, max_messages: int = 50
    ) -> CommandResult:
        """Create a new conversation session.

        Args:
            collection_id: Collection to chat with
            session_name: Name for the conversation session
            context_window_size: Size of context window
            max_messages: Maximum number of messages

        Returns:
            CommandResult with session information
        """
        self._require_authentication()

        try:
            # Get current user to obtain user_id
            current_user = self.api_client.get("/api/auth/me")
            user_id = current_user.get("uuid") or current_user.get("id")

            if not user_id:
                return self._create_error_result("Could not determine user ID")

            payload = {
                "user_id": user_id,
                "collection_id": collection_id,
                "session_name": session_name,
                "context_window_size": context_window_size,
                "max_messages": max_messages,
                "metadata": {},
            }

            response = self.api_client.post("/api/chat/sessions", data=payload)

            return CommandResult(
                success=True,
                message=f"Created conversation session: {response['session_name']}",
                data={
                    "session_id": response["id"],
                    "session_name": response["session_name"],
                    "collection_id": response["collection_id"],
                    "status": response["status"],
                    "created_at": response["created_at"],
                },
            )

        except Exception as e:
            return self._create_error_result(f"Failed to create session: {e!s}")

    def list_sessions(self, limit: int = 20) -> CommandResult:
        """List conversation sessions for the current user.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            CommandResult with list of sessions
        """
        self._require_authentication()

        try:
            # Get current user to obtain user_id
            current_user = self.api_client.get("/api/auth/me")
            user_id = current_user.get("uuid") or current_user.get("id")

            if not user_id:
                return self._create_error_result("Could not determine user ID")

            response = self.api_client.get(f"/api/chat/sessions?user_id={user_id}")

            sessions = response if isinstance(response, list) else []
            limited_sessions = sessions[:limit]

            return CommandResult(
                success=True,
                message=f"Found {len(limited_sessions)} conversation sessions",
                data={
                    "sessions": [
                        {
                            "id": session["id"],
                            "name": session["session_name"],
                            "collection_id": session["collection_id"],
                            "status": session["status"],
                            "message_count": session.get("message_count", 0),
                            "created_at": session["created_at"],
                            "updated_at": session["updated_at"],
                        }
                        for session in limited_sessions
                    ]
                },
            )

        except Exception as e:
            return self._create_error_result(f"Failed to list sessions: {e!s}")

    def get_session(self, session_id: str) -> CommandResult:
        """Get details of a specific conversation session.

        Args:
            session_id: Session ID to retrieve

        Returns:
            CommandResult with session details
        """
        self._require_authentication()

        try:
            # Get current user to obtain user_id
            current_user = self.api_client.get("/api/auth/me")
            user_id = current_user.get("uuid") or current_user.get("id")

            if not user_id:
                return self._create_error_result("Could not determine user ID")

            response = self.api_client.get(f"/api/chat/sessions/{session_id}?user_id={user_id}")

            return CommandResult(
                success=True,
                message=f"Retrieved session: {response['session_name']}",
                data={
                    "session": {
                        "id": response["id"],
                        "name": response["session_name"],
                        "collection_id": response["collection_id"],
                        "status": response["status"],
                        "context_window_size": response["context_window_size"],
                        "max_messages": response["max_messages"],
                        "message_count": response.get("message_count", 0),
                        "created_at": response["created_at"],
                        "updated_at": response["updated_at"],
                        "metadata": response.get("metadata", {}),
                    }
                },
            )

        except Exception as e:
            return self._create_error_result(f"Failed to get session: {e!s}")

    def send_message(self, session_id: str, message: str) -> CommandResult:
        """Send a message in a conversation session and get AI response.

        Args:
            session_id: Session ID to send message to
            message: Message content

        Returns:
            CommandResult with AI response
        """
        self._require_authentication()

        try:
            payload = {"session_id": session_id, "content": message, "role": "user", "message_type": "question"}

            response = self.api_client.post(f"/api/chat/sessions/{session_id}/process", data=payload)

            return CommandResult(
                success=True,
                message="Message processed successfully",
                data={
                    "user_message": message,
                    "ai_response": {
                        "id": response["id"],
                        "content": response["content"],
                        "role": response["role"],
                        "message_type": response["message_type"],
                        "created_at": response["created_at"],
                        "token_count": response.get("token_count"),
                        "execution_time": response.get("execution_time"),
                        "metadata": response.get("metadata", {}),
                    },
                },
            )

        except Exception as e:
            return self._create_error_result(f"Failed to send message: {e!s}")

    def get_messages(self, session_id: str, limit: int = 20) -> CommandResult:
        """Get messages from a conversation session.

        Args:
            session_id: Session ID to get messages from
            limit: Maximum number of messages to return

        Returns:
            CommandResult with message list
        """
        self._require_authentication()

        try:
            # Get current user to obtain user_id
            current_user = self.api_client.get("/api/auth/me")
            user_id = current_user.get("uuid") or current_user.get("id")

            if not user_id:
                return self._create_error_result("Could not determine user ID")

            response = self.api_client.get(f"/api/chat/sessions/{session_id}/messages?user_id={user_id}&limit={limit}")

            messages = response if isinstance(response, list) else []

            return CommandResult(
                success=True,
                message=f"Retrieved {len(messages)} messages",
                data={
                    "messages": [
                        {
                            "id": msg["id"],
                            "content": msg["content"],
                            "role": msg["role"],
                            "message_type": msg["message_type"],
                            "created_at": msg["created_at"],
                            "token_count": msg.get("token_count"),
                            "execution_time": msg.get("execution_time"),
                        }
                        for msg in messages
                    ]
                },
            )

        except Exception as e:
            return self._create_error_result(f"Failed to get messages: {e!s}")

    def get_suggestions(self, session_id: str, current_message: str = "", max_suggestions: int = 3) -> CommandResult:
        """Get question suggestions for a conversation.

        Args:
            session_id: Session ID to get suggestions for
            current_message: Current message context
            max_suggestions: Maximum number of suggestions

        Returns:
            CommandResult with question suggestions
        """
        self._require_authentication()

        try:
            # Get current user to obtain user_id
            current_user = self.api_client.get("/api/auth/me")
            user_id = current_user.get("uuid") or current_user.get("id")

            if not user_id:
                return self._create_error_result("Could not determine user ID")

            params = {
                "user_id": user_id,
                "current_message": current_message or "What should I ask next?",
                "max_suggestions": max_suggestions,
            }

            response = self.api_client.get(f"/api/chat/sessions/{session_id}/suggestions", params=params)

            return CommandResult(
                success=True,
                message=f"Generated {len(response.get('suggestions', []))} suggestions",
                data={
                    "suggestions": response.get("suggestions", []),
                    "confidence_scores": response.get("confidence_scores", []),
                    "reasoning": response.get("reasoning", ""),
                },
            )

        except Exception as e:
            return self._create_error_result(f"Failed to get suggestions: {e!s}")

    def create_summary(
        self, session_id: str, message_count: int = 10, strategy: str = "recent_plus_summary"
    ) -> CommandResult:
        """Create a conversation summary.

        Args:
            session_id: Session ID to summarize
            message_count: Number of messages to include in summary
            strategy: Summarization strategy to use

        Returns:
            CommandResult with summary information
        """
        self._require_authentication()

        try:
            # Get current user to obtain user_id
            current_user = self.api_client.get("/api/auth/me")
            user_id = current_user.get("uuid") or current_user.get("id")

            if not user_id:
                return self._create_error_result("Could not determine user ID")

            payload = {
                "session_id": session_id,
                "message_count_to_summarize": message_count,
                "strategy": strategy,
                "preserve_context": True,
                "include_decisions": True,
                "include_questions": True,
            }

            response = self.api_client.post(
                f"/api/chat/sessions/{session_id}/summaries?user_id={user_id}", data=payload
            )

            return CommandResult(
                success=True,
                message="Created conversation summary",
                data={
                    "summary": {
                        "id": response["id"],
                        "summary_text": response["summary_text"],
                        "summarized_message_count": response["summarized_message_count"],
                        "tokens_saved": response["tokens_saved"],
                        "key_topics": response["key_topics"],
                        "important_decisions": response["important_decisions"],
                        "unresolved_questions": response["unresolved_questions"],
                        "strategy": response["summary_strategy"],
                        "created_at": response["created_at"],
                    }
                },
            )

        except Exception as e:
            return self._create_error_result(f"Failed to create summary: {e!s}")

    def list_summaries(self, session_id: str, limit: int = 10) -> CommandResult:
        """List summaries for a conversation session.

        Args:
            session_id: Session ID to get summaries for
            limit: Maximum number of summaries to return

        Returns:
            CommandResult with summary list
        """
        self._require_authentication()

        try:
            # Get current user to obtain user_id
            current_user = self.api_client.get("/api/auth/me")
            user_id = current_user.get("uuid") or current_user.get("id")

            if not user_id:
                return self._create_error_result("Could not determine user ID")

            response = self.api_client.get(f"/api/chat/sessions/{session_id}/summaries?user_id={user_id}&limit={limit}")

            summaries = response if isinstance(response, list) else []

            return CommandResult(
                success=True,
                message=f"Found {len(summaries)} summaries",
                data={
                    "summaries": [
                        {
                            "id": summary["id"],
                            "summary_text": summary["summary_text"][:200] + "..."
                            if len(summary["summary_text"]) > 200
                            else summary["summary_text"],
                            "message_count": summary["summarized_message_count"],
                            "tokens_saved": summary["tokens_saved"],
                            "key_topics": summary["key_topics"],
                            "strategy": summary["summary_strategy"],
                            "created_at": summary["created_at"],
                        }
                        for summary in summaries
                    ]
                },
            )

        except Exception as e:
            return self._create_error_result(f"Failed to list summaries: {e!s}")

    def export_conversation(
        self, session_id: str, format: str = "json", include_summaries: bool = True, include_metadata: bool = True
    ) -> CommandResult:
        """Export a conversation session.

        Args:
            session_id: Session ID to export
            format: Export format (json, csv, txt, pdf)
            include_summaries: Whether to include summaries
            include_metadata: Whether to include metadata

        Returns:
            CommandResult with export data
        """
        self._require_authentication()

        try:
            payload = {
                "session_id": session_id,
                "format": format,
                "include_metadata": include_metadata,
                "include_timestamps": True,
                "include_token_counts": False,
                "include_summaries": include_summaries,
                "custom_fields": [],
            }

            response = self.api_client.post(f"/api/chat/sessions/{session_id}/enhanced-export", data=payload)

            return CommandResult(
                success=True,
                message=f"Exported conversation in {format} format",
                data={
                    "export": {
                        "session_data": response["session_data"],
                        "message_count": response["total_messages"],
                        "summary_count": len(response.get("summaries", [])),
                        "export_format": response["export_format"],
                        "export_timestamp": response["export_timestamp"],
                        "total_tokens": response["total_tokens"],
                        "metadata": response["metadata"],
                    },
                    "messages": response["messages"],
                    "summaries": response.get("summaries", []),
                },
            )

        except Exception as e:
            return self._create_error_result(f"Failed to export conversation: {e!s}")

    def get_statistics(self, session_id: str) -> CommandResult:
        """Get statistics for a conversation session.

        Args:
            session_id: Session ID to get statistics for

        Returns:
            CommandResult with session statistics
        """
        self._require_authentication()

        try:
            # Get current user to obtain user_id
            current_user = self.api_client.get("/api/auth/me")
            user_id = current_user.get("uuid") or current_user.get("id")

            if not user_id:
                return self._create_error_result("Could not determine user ID")

            response = self.api_client.get(f"/api/chat/sessions/{session_id}/statistics?user_id={user_id}")

            return CommandResult(
                success=True,
                message="Retrieved session statistics",
                data={
                    "statistics": {
                        "session_id": response["session_id"],
                        "message_count": response["message_count"],
                        "user_messages": response["user_messages"],
                        "assistant_messages": response["assistant_messages"],
                        "total_tokens": response["total_tokens"],
                        "cot_usage_count": response.get("cot_usage_count", 0),
                        "context_enhancement_count": response.get("context_enhancement_count", 0),
                        "created_at": response["created_at"],
                        "last_activity": response["last_activity"],
                    }
                },
            )

        except Exception as e:
            return self._create_error_result(f"Failed to get statistics: {e!s}")

    def delete_session(self, session_id: str) -> CommandResult:
        """Delete a conversation session.

        Args:
            session_id: Session ID to delete

        Returns:
            CommandResult with deletion confirmation
        """
        self._require_authentication()

        try:
            # Get current user to obtain user_id
            current_user = self.api_client.get("/api/auth/me")
            user_id = current_user.get("uuid") or current_user.get("id")

            if not user_id:
                return self._create_error_result("Could not determine user ID")

            self.api_client.delete(f"/api/chat/sessions/{session_id}?user_id={user_id}")

            return CommandResult(
                success=True, message=f"Deleted conversation session: {session_id}", data={"session_id": session_id}
            )

        except Exception as e:
            return self._create_error_result(f"Failed to delete session: {e!s}")

    def check_context_threshold(self, session_id: str) -> CommandResult:
        """Check if a session needs summarization based on context threshold.

        Args:
            session_id: Session ID to check

        Returns:
            CommandResult with threshold check results
        """
        self._require_authentication()

        try:
            # Get current user to obtain user_id
            current_user = self.api_client.get("/api/auth/me")
            user_id = current_user.get("uuid") or current_user.get("id")

            if not user_id:
                return self._create_error_result("Could not determine user ID")

            response = self.api_client.get(f"/api/chat/sessions/{session_id}/context-threshold?user_id={user_id}")

            return CommandResult(
                success=True,
                message="Checked context threshold",
                data={
                    "session_id": response["session_id"],
                    "needs_summarization": response["needs_summarization"],
                    "threshold_config": response["threshold_config"],
                },
            )

        except Exception as e:
            return self._create_error_result(f"Failed to check context threshold: {e!s}")
