"""
Session management for WebRTC connections and chat state
"""
import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents a user session with WebRTC connection"""
    session_id: str
    created_at: float = field(default_factory=time.time)
    pc: Optional[object] = None  # RTCPeerConnection
    websocket: Optional[object] = None
    chat_history: list = field(default_factory=list)
    last_activity: float = field(default_factory=time.time)
    frames_processed: int = 0
    active: bool = True


class SessionManager:
    """Manages active user sessions"""
    
    def __init__(self, max_sessions: int = 10, session_timeout: int = 3600):
        self.sessions: Dict[str, Session] = {}
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self._cleanup_task = None
    
    async def start(self):
        """Start background cleanup task"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """Stop cleanup and close all sessions"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all sessions
        for session_id in list(self.sessions.keys()):
            await self.remove_session(session_id)
    
    def create_session(self, session_id: str) -> Session:
        """Create a new session"""
        if len(self.sessions) >= self.max_sessions:
            # Remove oldest inactive session
            oldest = min(
                (s for s in self.sessions.values() if not s.active),
                key=lambda s: s.last_activity,
                default=None
            )
            if oldest:
                asyncio.create_task(self.remove_session(oldest.session_id))
            else:
                raise RuntimeError("Maximum concurrent sessions reached")
        
        session = Session(session_id=session_id)
        self.sessions[session_id] = session
        logger.info(f"Created session {session_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        session = self.sessions.get(session_id)
        if session:
            session.last_activity = time.time()
        return session
    
    async def remove_session(self, session_id: str):
        """Remove and cleanup session"""
        session = self.sessions.pop(session_id, None)
        if session:
            session.active = False
            
            # Close WebSocket
            if session.websocket:
                try:
                    await session.websocket.close()
                except Exception as e:
                    logger.warning(f"Error closing websocket: {e}")
            
            # Close RTCPeerConnection
            if session.pc:
                try:
                    await session.pc.close()
                except Exception as e:
                    logger.warning(f"Error closing peer connection: {e}")
            
            logger.info(f"Removed session {session_id} (processed {session.frames_processed} frames)")
    
    async def _cleanup_loop(self):
        """Periodically cleanup expired sessions"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                now = time.time()
                
                expired = [
                    sid for sid, session in self.sessions.items()
                    if now - session.last_activity > self.session_timeout
                ]
                
                for session_id in expired:
                    logger.info(f"Session {session_id} expired due to inactivity")
                    await self.remove_session(session_id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def get_stats(self) -> dict:
        """Get session statistics"""
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": sum(1 for s in self.sessions.values() if s.active),
            "total_frames_processed": sum(s.frames_processed for s in self.sessions.values())
        }

