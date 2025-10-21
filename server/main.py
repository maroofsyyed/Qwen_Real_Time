"""
Main FastAPI application
Handles HTTP endpoints, WebSocket connections, and WebRTC signaling
"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from config import settings
from server.auth import get_current_user, generate_session_token
from server.session_manager import SessionManager
from server.webrtc_server import WebRTCManager
from server.inference import inference_worker

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.log_file) if settings.log_file else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)


# Application lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Qwen Vision-Language Realtime Service")
    
    # Initialize components
    await session_manager.start()
    await inference_worker.start()
    
    logger.info(f"Service started on {settings.host}:{settings.port}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down service...")
    await webrtc_manager.close_all()
    await session_manager.stop()
    await inference_worker.stop()
    logger.info("Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Qwen Vision-Language Realtime Service",
    description="Production realtime camera streaming with Qwen2.5-VL-32B inference",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration - adjust for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
session_manager = SessionManager(
    max_sessions=settings.max_concurrent_sessions,
    session_timeout=3600
)
webrtc_manager = WebRTCManager(session_manager)


# ============================================================================
# HTTP Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Qwen Vision-Language Realtime Service",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "inference_ready": inference_worker.engine.ready,
        "sessions": session_manager.get_stats(),
        "inference": inference_worker.get_stats()
    }


@app.post("/api/token")
async def create_token():
    """
    Generate ephemeral session token
    No authentication required - creates anonymous session
    """
    token = generate_session_token()
    return {"access_token": token, "token_type": "bearer"}


@app.post("/api/webrtc/offer")
async def webrtc_offer(
    request: Dict,
    user: dict = Depends(get_current_user)
):
    """
    Handle WebRTC offer from client
    
    Request body:
    {
        "sdp": "...",
        "type": "offer"
    }
    
    Returns:
    {
        "sdp": "...",
        "type": "answer"
    }
    """
    session_id = user.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="Invalid session")
    
    try:
        sdp = request.get("sdp")
        sdp_type = request.get("type")
        
        if not sdp or sdp_type != "offer":
            raise HTTPException(status_code=400, detail="Invalid WebRTC offer")
        
        answer = await webrtc_manager.handle_offer(session_id, sdp, sdp_type)
        
        return answer
        
    except Exception as e:
        logger.error(f"Error handling WebRTC offer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket connection for chat messages and responses
    """
    await websocket.accept()
    
    logger.info(f"WebSocket connected for session {session_id}")
    
    # Get or create session
    session = session_manager.get_session(session_id)
    if not session:
        session = session_manager.create_session(session_id)
    
    session.websocket = websocket
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            message_type = data.get("type")
            
            if message_type == "chat":
                # User sent a text message/question
                content = data.get("content", "")
                
                # Add to chat history
                session.chat_history.append({
                    "role": "user",
                    "type": "text",
                    "content": content,
                    "timestamp": asyncio.get_event_loop().time()
                })
                
                logger.info(f"Session {session_id} received message: {content}")
                
                # Acknowledge receipt
                await websocket.send_json({
                    "type": "ack",
                    "message": "Question received"
                })
            
            elif message_type == "ping":
                # Keep-alive ping
                await websocket.send_json({"type": "pong"})
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
    finally:
        if session:
            session.websocket = None


# ============================================================================
# Security: Explicitly disable file upload endpoints
# ============================================================================

@app.post("/upload")
@app.post("/api/upload")
@app.post("/api/image/upload")
@app.post("/api/video/upload")
async def upload_disabled():
    """File uploads are explicitly disabled - camera stream only"""
    raise HTTPException(
        status_code=403,
        detail="File uploads are not allowed. This service accepts live camera streams only."
    )


# ============================================================================
# Monitoring Endpoints
# ============================================================================

@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics"""
    if not settings.enable_metrics:
        raise HTTPException(status_code=404)
    
    stats = {
        "sessions": session_manager.get_stats(),
        "inference": inference_worker.get_stats()
    }
    
    # Format as Prometheus metrics
    lines = []
    lines.append(f"# HELP sessions_total Total number of sessions")
    lines.append(f"# TYPE sessions_total gauge")
    lines.append(f"sessions_total {stats['sessions']['total_sessions']}")
    
    lines.append(f"# HELP inference_requests_total Total inference requests")
    lines.append(f"# TYPE inference_requests_total counter")
    lines.append(f"inference_requests_total {stats['inference']['total_requests']}")
    
    lines.append(f"# HELP inference_time_avg Average inference time in seconds")
    lines.append(f"# TYPE inference_time_avg gauge")
    lines.append(f"inference_time_avg {stats['inference'].get('avg_inference_time', 0)}")
    
    return HTMLResponse(content="\n".join(lines))


# ============================================================================
# Run server
# ============================================================================

def main():
    """Main entry point"""
    uvicorn_config = {
        "app": "server.main:app",
        "host": settings.host,
        "port": settings.port,
        "log_level": settings.log_level.lower(),
    }
    
    if settings.https_enabled and settings.ssl_cert_path and settings.ssl_key_path:
        uvicorn_config.update({
            "ssl_certfile": settings.ssl_cert_path,
            "ssl_keyfile": settings.ssl_key_path,
        })
    
    uvicorn.run(**uvicorn_config)


if __name__ == "__main__":
    main()

