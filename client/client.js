/**
 * Qwen Vision-Language Client
 * Handles WebRTC camera streaming and WebSocket chat
 * NO FILE UPLOAD - Camera stream only
 */

class QwenVisionClient {
    constructor() {
        // Server configuration
        this.serverUrl = window.location.origin;
        this.wsUrl = this.serverUrl.replace('http', 'ws');
        
        // State
        this.sessionId = null;
        this.token = null;
        this.peerConnection = null;
        this.websocket = null;
        this.localStream = null;
        this.connected = false;
        
        // UI elements
        this.videoElement = document.getElementById('videoElement');
        this.videoOverlay = document.getElementById('videoOverlay');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.statusText = document.getElementById('statusText');
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.startBtn = document.getElementById('startBtn');
        this.stopBtn = document.getElementById('stopBtn');
        
        this.initEventListeners();
    }
    
    initEventListeners() {
        this.startBtn.addEventListener('click', () => this.start());
        this.stopBtn.addEventListener('click', () => this.stop());
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
    }
    
    async start() {
        try {
            this.updateStatus('Initializing...');
            
            // Get session token
            await this.getToken();
            
            // Start camera
            await this.startCamera();
            
            // Connect WebRTC
            await this.connectWebRTC();
            
            // Connect WebSocket
            await this.connectWebSocket();
            
            this.updateStatus('Connected', true);
            this.startBtn.style.display = 'none';
            this.stopBtn.style.display = 'block';
            this.chatInput.disabled = false;
            this.sendBtn.disabled = false;
            this.videoOverlay.classList.add('hidden');
            
        } catch (error) {
            console.error('Failed to start:', error);
            this.addMessage('system', `Error: ${error.message}`, true);
            this.updateStatus('Failed to connect', false);
            this.stop();
        }
    }
    
    async stop() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }
        
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }
        
        this.videoElement.srcObject = null;
        this.connected = false;
        this.updateStatus('Disconnected', false);
        this.startBtn.style.display = 'block';
        this.stopBtn.style.display = 'none';
        this.chatInput.disabled = true;
        this.sendBtn.disabled = true;
        this.videoOverlay.classList.remove('hidden');
    }
    
    async getToken() {
        const response = await fetch(`${this.serverUrl}/api/token`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            throw new Error('Failed to get session token');
        }
        
        const data = await response.json();
        this.token = data.access_token;
        
        // Decode session ID from JWT (simple base64 decode)
        const payload = JSON.parse(atob(this.token.split('.')[1]));
        this.sessionId = payload.session_id;
        
        console.log('Session ID:', this.sessionId);
    }
    
    async startCamera() {
        try {
            const constraints = {
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'environment' // Use back camera on mobile
                },
                audio: false
            };
            
            this.localStream = await navigator.mediaDevices.getUserMedia(constraints);
            this.videoElement.srcObject = this.localStream;
            
            console.log('Camera started');
        } catch (error) {
            throw new Error(`Camera access denied: ${error.message}`);
        }
    }
    
    async connectWebRTC() {
        // Create peer connection
        const config = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' }
            ]
        };
        
        this.peerConnection = new RTCPeerConnection(config);
        
        // Add local stream tracks
        this.localStream.getTracks().forEach(track => {
            this.peerConnection.addTrack(track, this.localStream);
        });
        
        // Handle ICE candidates
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                console.log('ICE candidate:', event.candidate);
            }
        };
        
        this.peerConnection.oniceconnectionstatechange = () => {
            console.log('ICE connection state:', this.peerConnection.iceConnectionState);
        };
        
        // Create offer
        const offer = await this.peerConnection.createOffer();
        await this.peerConnection.setLocalDescription(offer);
        
        // Send offer to server
        const response = await fetch(`${this.serverUrl}/api/webrtc/offer`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.token}`
            },
            body: JSON.stringify({
                sdp: offer.sdp,
                type: offer.type
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to establish WebRTC connection');
        }
        
        const answer = await response.json();
        await this.peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
        
        console.log('WebRTC connected');
    }
    
    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            this.websocket = new WebSocket(`${this.wsUrl}/ws/${this.sessionId}`);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.connected = true;
                
                // Start keep-alive
                this.keepAliveInterval = setInterval(() => {
                    if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                        this.websocket.send(JSON.stringify({ type: 'ping' }));
                    }
                }, 30000);
                
                resolve();
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                reject(error);
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket closed');
                this.connected = false;
                clearInterval(this.keepAliveInterval);
                
                if (this.localStream) {
                    this.updateStatus('Connection lost', false);
                }
            };
        });
    }
    
    handleWebSocketMessage(data) {
        console.log('Received:', data);
        
        switch (data.type) {
            case 'response':
                this.addMessage('assistant', data.text, data.error);
                if (data.inference_time) {
                    console.log(`Inference time: ${data.inference_time.toFixed(3)}s`);
                }
                break;
                
            case 'ack':
                console.log('Message acknowledged');
                break;
                
            case 'pong':
                // Keep-alive response
                break;
                
            default:
                console.log('Unknown message type:', data.type);
        }
    }
    
    sendMessage() {
        const message = this.chatInput.value.trim();
        
        if (!message || !this.connected) return;
        
        // Add to UI
        this.addMessage('user', message);
        
        // Send to server
        this.websocket.send(JSON.stringify({
            type: 'chat',
            content: message
        }));
        
        // Clear input
        this.chatInput.value = '';
    }
    
    addMessage(role, content, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        if (isError) messageDiv.classList.add('error');
        
        const contentDiv = document.createElement('div');
        contentDiv.textContent = content;
        messageDiv.appendChild(contentDiv);
        
        const metaDiv = document.createElement('div');
        metaDiv.className = 'meta';
        metaDiv.textContent = new Date().toLocaleTimeString();
        messageDiv.appendChild(metaDiv);
        
        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    updateStatus(text, connected = null) {
        this.statusText.textContent = text;
        
        if (connected !== null) {
            this.statusIndicator.className = `status-indicator ${connected ? 'connected' : 'disconnected'}`;
        }
    }
}

// Initialize on page load
let client;
window.addEventListener('DOMContentLoaded', () => {
    client = new QwenVisionClient();
});

