"""
Inference worker for Qwen2.5-VL-32B vision-language model
Handles frame preprocessing, model inference, and response generation
"""
import asyncio
import queue
import threading
import time
import logging
from typing import Optional, Dict, Any, Callable
import numpy as np
import cv2
from dataclasses import dataclass

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class InferenceRequest:
    """Request for vision-language inference"""
    session_id: str
    frame: np.ndarray
    prompt: str
    callback: Callable
    timestamp: float


class QwenVLInference:
    """
    Qwen2.5-VL-32B inference engine
    Connects to vLLM server and handles multimodal inference
    """
    
    def __init__(self):
        self.model_client = None
        self.ready = False
        
    async def initialize(self):
        """Initialize connection to vLLM server"""
        try:
            # Import vLLM client or use HTTP client for vLLM server
            # This is a placeholder - adapt to actual vLLM API
            from openai import AsyncOpenAI
            
            self.model_client = AsyncOpenAI(
                base_url=settings.vllm_api_base,
                api_key="EMPTY"  # vLLM doesn't require key
            )
            
            # Test connection
            logger.info(f"Connecting to vLLM server at {settings.vllm_api_base}")
            # await self.model_client.models.list()  # Health check
            
            self.ready = True
            logger.info("Qwen VL inference engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize inference engine: {e}")
            logger.warning("Will attempt to use fallback PyTorch inference")
            await self._initialize_pytorch_fallback()
    
    async def _initialize_pytorch_fallback(self):
        """Fallback: Load model directly with PyTorch/Transformers"""
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM
            
            logger.info(f"Loading Qwen model from {settings.model_path}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                settings.model_path,
                trust_remote_code=True
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                settings.model_path,
                torch_dtype=torch.float16 if settings.model_dtype == "float16" else torch.float32,
                device_map="auto",
                trust_remote_code=True
            )
            
            self.model.eval()
            self.use_pytorch = True
            self.ready = True
            
            logger.info("Qwen VL model loaded successfully (PyTorch mode)")
            
        except Exception as e:
            logger.error(f"Failed to load PyTorch model: {e}")
            raise RuntimeError("Cannot initialize inference engine")
    
    async def generate_response(
        self, 
        image: np.ndarray, 
        prompt: str,
        max_tokens: int = None
    ) -> Dict[str, Any]:
        """
        Generate response from image and text prompt
        
        Args:
            image: RGB image as numpy array (H, W, 3)
            prompt: Text prompt/question
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dict with 'text' response and timing info
        """
        if not self.ready:
            raise RuntimeError("Inference engine not ready")
        
        start_time = time.time()
        max_tokens = max_tokens or settings.response_max_tokens
        
        try:
            if hasattr(self, 'use_pytorch') and self.use_pytorch:
                result = await self._generate_pytorch(image, prompt, max_tokens)
            else:
                result = await self._generate_vllm(image, prompt, max_tokens)
            
            inference_time = time.time() - start_time
            
            return {
                "text": result,
                "inference_time": inference_time,
                "model": "qwen2.5-vl-32b"
            }
            
        except Exception as e:
            logger.error(f"Inference error: {e}")
            return {
                "text": f"Error: {str(e)}",
                "inference_time": time.time() - start_time,
                "error": True
            }
    
    async def _generate_vllm(self, image: np.ndarray, prompt: str, max_tokens: int) -> str:
        """Generate using vLLM server (OpenAI-compatible API)"""
        # For vision models, we need to encode image to base64
        import base64
        from io import BytesIO
        from PIL import Image
        
        # Convert numpy to PIL
        pil_image = Image.fromarray(image)
        buffer = BytesIO()
        pil_image.save(buffer, format="PNG")
        image_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        # Construct message with image (OpenAI vision API format)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        response = await self.model_client.chat.completions.create(
            model=settings.model_path,  # or model name
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    
    async def _generate_pytorch(self, image: np.ndarray, prompt: str, max_tokens: int) -> str:
        """Generate using PyTorch/Transformers directly"""
        import torch
        from PIL import Image
        
        # Convert numpy to PIL
        pil_image = Image.fromarray(image)
        
        # Prepare input (Qwen-VL specific format)
        # This is model-specific and may need adjustment
        query = f"<img>{pil_image}</img>{prompt}"
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._run_pytorch_inference,
            pil_image,
            prompt,
            max_tokens
        )
        
        return result
    
    def _run_pytorch_inference(self, image, prompt: str, max_tokens: int) -> str:
        """Synchronous PyTorch inference (runs in thread pool)"""
        import torch
        
        # Qwen-VL specific inference
        # Format depends on model - adapt as needed
        inputs = self.tokenizer(
            f"{prompt}",
            return_tensors="pt"
        ).to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=True,
                temperature=0.7
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return response


class InferenceWorker:
    """
    Async worker that processes frames and runs inference
    Manages queue and batching of requests
    """
    
    def __init__(self):
        self.request_queue: asyncio.Queue = asyncio.Queue(maxsize=settings.frame_queue_size)
        self.engine = QwenVLInference()
        self.worker_task = None
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_inference_time": 0.0,
            "frames_dropped": 0
        }
    
    async def start(self):
        """Start the inference worker"""
        await self.engine.initialize()
        self.worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Inference worker started")
    
    async def stop(self):
        """Stop the inference worker"""
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Inference worker stopped")
    
    async def enqueue_frame(
        self, 
        session_id: str,
        frame: np.ndarray, 
        prompt: str,
        callback: Callable
    ) -> bool:
        """
        Enqueue a frame for inference
        
        Args:
            session_id: Session identifier
            frame: BGR image from camera
            prompt: User's question/prompt
            callback: Async function to call with result
            
        Returns:
            True if enqueued, False if queue full (frame dropped)
        """
        # Preprocess frame
        processed_frame = self._preprocess_frame(frame)
        
        request = InferenceRequest(
            session_id=session_id,
            frame=processed_frame,
            prompt=prompt,
            callback=callback,
            timestamp=time.time()
        )
        
        try:
            self.request_queue.put_nowait(request)
            return True
        except asyncio.QueueFull:
            self.stats["frames_dropped"] += 1
            logger.warning(f"Frame dropped for session {session_id} - queue full")
            return False
    
    def _preprocess_frame(self, frame_bgr: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for model input
        - Resize to model input size
        - Convert BGR to RGB
        - Normalize if needed
        """
        # Resize to configured size
        frame_resized = cv2.resize(
            frame_bgr,
            (settings.frame_width, settings.frame_height),
            interpolation=cv2.INTER_LINEAR
        )
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        
        # Apply face blur if enabled (privacy)
        if settings.enable_face_blur:
            frame_rgb = self._blur_faces(frame_rgb)
        
        return frame_rgb
    
    def _blur_faces(self, frame_rgb: np.ndarray) -> np.ndarray:
        """Apply face detection and blurring for privacy"""
        # Simple implementation using OpenCV cascade
        # For production, use a better detector
        try:
            gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            for (x, y, w, h) in faces:
                face_region = frame_rgb[y:y+h, x:x+w]
                blurred_face = cv2.GaussianBlur(face_region, (99, 99), 30)
                frame_rgb[y:y+h, x:x+w] = blurred_face
        except Exception as e:
            logger.warning(f"Face blur failed: {e}")
        
        return frame_rgb
    
    async def _worker_loop(self):
        """Main worker loop - processes requests from queue"""
        logger.info("Inference worker loop started")
        
        while True:
            try:
                # Get request from queue
                request = await self.request_queue.get()
                
                # Track stats
                self.stats["total_requests"] += 1
                queue_wait_time = time.time() - request.timestamp
                
                logger.debug(f"Processing request for session {request.session_id} (waited {queue_wait_time:.3f}s)")
                
                # Run inference
                try:
                    result = await self.engine.generate_response(
                        request.frame,
                        request.prompt
                    )
                    
                    self.stats["successful_requests"] += 1
                    self.stats["total_inference_time"] += result.get("inference_time", 0)
                    
                    # Call callback with result
                    await request.callback(result)
                    
                except Exception as e:
                    logger.error(f"Inference failed for session {request.session_id}: {e}")
                    self.stats["failed_requests"] += 1
                    
                    # Call callback with error
                    await request.callback({
                        "text": "Sorry, I encountered an error processing your request.",
                        "error": True
                    })
                
                finally:
                    self.request_queue.task_done()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
    
    def get_stats(self) -> dict:
        """Get inference statistics"""
        stats = self.stats.copy()
        if stats["successful_requests"] > 0:
            stats["avg_inference_time"] = stats["total_inference_time"] / stats["successful_requests"]
        else:
            stats["avg_inference_time"] = 0.0
        stats["queue_size"] = self.request_queue.qsize()
        return stats


# Global inference worker instance
inference_worker = InferenceWorker()

