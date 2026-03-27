"""
WebSocket connection manager.
Handles WebSocket connections and provides room management.
"""
from typing import Dict, List, Any
from fastapi import WebSocket
from starlette.websockets import WebSocketState


class ConnectionManager:
    """Manages WebSocket connections and rooms."""

    def __init__(self):
        # Active connections: {websocket: user_info}
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}

    async def accept(self, websocket: WebSocket, user: Dict[str, Any] = None):
        """
        Accept a WebSocket connection.

        Args:
            websocket: WebSocket connection
            user: Optional user info dict
        """
        await websocket.accept()
        if user:
            self.active_connections[websocket] = user
        else:
            self.active_connections[websocket] = {}

    async def disconnect(self, websocket: WebSocket):
        """
        Disconnect a WebSocket connection.

        Args:
            websocket: WebSocket connection
        """
        if websocket in self.active_connections:
            del self.active_connections[websocket]

        # Close if not already closed
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()

    def get_user(self, websocket: WebSocket) -> Dict[str, Any]:
        """
        Get user info for a connection.

        Args:
            websocket: WebSocket connection

        Returns:
            User info dict
        """
        return self.active_connections.get(websocket, {})

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send a message to a specific connection.

        Args:
            message: Message dict to send
            websocket: Target WebSocket connection
        """
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(message)

    async def broadcast_to_room(self, message: dict, room: str, exclude: WebSocket = None):
        """
        Broadcast a message to all connections in a room.

        Args:
            message: Message dict to broadcast
            room: Room name (e.g., "board:uuid")
            exclude: Optional WebSocket to exclude from broadcast
        """
        # Get all websockets in the room
        disconnected = []

        for websocket in self.active_connections:
            if websocket.client_state != WebSocketState.CONNECTED:
                disconnected.append(websocket)
                continue

            if websocket is exclude:
                continue

            # Check if websocket is in the room
            if room in getattr(websocket, "rooms", set()):
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            await self.disconnect(ws)

    async def broadcast(self, message: dict):
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message dict to broadcast
        """
        disconnected = []

        for websocket in self.active_connections:
            if websocket.client_state != WebSocketState.CONNECTED:
                disconnected.append(websocket)
                continue

            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            await self.disconnect(ws)

    def get_connections_count(self) -> int:
        """
        Get the number of active connections.

        Returns:
            Number of active connections
        """
        return len(self.active_connections)


# Global connection manager instance
connection_manager = ConnectionManager()
