"""
WebRTC server for receiving live camera streams
Uses aiortc to handle WebRTC peer connections and frame extraction
"""
import asyncio
import logging
import time
from typing import Dict
import numpy as np
import av

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaRelay

from config import settings
from server.session_manager import SessionManager
from server.inference import inference_worker

logger = logging.getLogger(__name__)


class FrameProcessor:
    """Processes video frames from WebRTC track"""
    
    def __init__(self, session_id: str, session_manager: SessionManager):
        self.session_id = session_id
        self.session_manager = session_manager
        self.sample_rate = settings.frame_sample_rate
        self.last_sample_time = 0.0
        self.frames_received = 0
        self.frames_sampled = 0
        self.default_prompt = "What do you see in this image? Describe it briefly."
    
    async def process_track(self, track: VideoStreamTrack):
        """
        Process frames from video track
        Samples at configured rate and sends to inference worker
        """
        logger.info(f"Starting frame processing for session {self.session_id}")
        
        try:
            while True:
                try:
                    # Receive frame from WebRTC track
                    frame = await asyncio.wait_for(track.recv(), timeout=5.0)
                    self.frames_received += 1
                    
                    # Check if we should sample this frame
                    current_time = time.time()
                    time_since_last = current_time - self.last_sample_time
                    
                    if time_since_last >= (1.0 / self.sample_rate):
                        # Convert frame to numpy array
                        img = frame.to_ndarray(format="bgr24")
                        
                        # Update session
                        session = self.session_manager.get_session(self.session_id)
                        if session:
                            session.last_activity = current_time
                            session.frames_processed += 1
                        
                        # Get prompt from session chat history or use default
                        prompt = self._get_current_prompt(session)
                        
                        # Send to inference worker
                        success = await inference_worker.enqueue_frame(
                            session_id=self.session_id,
                            frame=img,
                            prompt=prompt,
                            callback=self._on_inference_result
                        )
                        
                        if success:
                            self.frames_sampled += 1
                            self.last_sample_time = current_time
                            logger.debug(
                                f"Session {self.session_id}: sampled frame {self.frames_sampled} "
                                f"({self.frames_received} received)"
                            )
                
                except asyncio.TimeoutError:
                    logger.warning(f"Frame timeout for session {self.session_id}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error processing track for session {self.session_id}: {e}")
        finally:
            logger.info(
                f"Stopped processing for session {self.session_id} "
                f"(received: {self.frames_received}, sampled: {self.frames_sampled})"
            )
    
    def _get_current_prompt(self, session) -> str:
        """Get the current prompt from session or use default"""
        if session and session.chat_history:
            # Get last user message
            for msg in reversed(session.chat_history):
                if msg.get("role") == "user" and msg.get("type") == "text":
                    return msg["content"]
        
        return self.default_prompt
    
    async def _on_inference_result(self, result: Dict):
        """Callback when inference completes - send to client via WebSocket"""
        session = self.session_manager.get_session(self.session_id)
        
        if not session or not session.websocket:
            logger.warning(f"No websocket for session {self.session_id}")
            return
        
        try:
            # Send result to client
            message = {
                "type": "response",
                "text": result.get("text", ""),
                "inference_time": result.get("inference_time", 0),
                "error": result.get("error", False)
            }
            
            await session.websocket.send_json(message)
            
            # Add to chat history
            session.chat_history.append({
                "role": "assistant",
                "content": result.get("text", ""),
                "timestamp": time.time()
            })
            
            logger.info(f"Sent response to session {self.session_id}: {result.get('text', '')[:100]}")
            
        except Exception as e:
            logger.error(f"Error sending result to client: {e}")


class WebRTCManager:
    """Manages WebRTC peer connections"""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.relay = MediaRelay()
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
    
    async def handle_offer(self, session_id: str, sdp: str, type: str) -> Dict:
        """
        Handle WebRTC offer from client
        
        Args:
            session_id: Session identifier
            sdp: Session Description Protocol
            type: SDP type (should be "offer")
            
        Returns:
            Dict with answer SDP
        """
        logger.info(f"Handling WebRTC offer for session {session_id}")
        
        # Create RTCPeerConnection
        pc = RTCPeerConnection()
        self.peer_connections[session_id] = pc
        
        # Get or create session
        session = self.session_manager.get_session(session_id)
        if not session:
            session = self.session_manager.create_session(session_id)
        session.pc = pc
        
        # Create frame processor
        processor = FrameProcessor(session_id, self.session_manager)
        
        @pc.on("track")
        async def on_track(track):
            """Handle incoming media track"""
            logger.info(f"Track received: {track.kind} for session {session_id}")
            
            if track.kind == "video":
                # Relay track and process frames
                local_track = self.relay.subscribe(track)
                asyncio.create_task(processor.process_track(local_track))
            
            @track.on("ended")
            async def on_ended():
                logger.info(f"Track ended for session {session_id}")
        
        @pc.on("connectionstatechange")
        async def on_connection_state_change():
            logger.info(f"Connection state: {pc.connectionState} for session {session_id}")
            
            if pc.connectionState == "failed" or pc.connectionState == "closed":
                await self.close_peer_connection(session_id)
        
        # Set remote description
        offer = RTCSessionDescription(sdp=sdp, type=type)
        await pc.setRemoteDescription(offer)
        
        # Create answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        logger.info(f"Created answer for session {session_id}")
        
        return {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        }
    
    async def close_peer_connection(self, session_id: str):
        """Close peer connection for session"""
        pc = self.peer_connections.pop(session_id, None)
        if pc:
            await pc.close()
            logger.info(f"Closed peer connection for session {session_id}")
    
    async def close_all(self):
        """Close all peer connections"""
        for session_id in list(self.peer_connections.keys()):
            await self.close_peer_connection(session_id)

