class FaceAnalysisApp {
    constructor() {
        // DOM Elements
        this.video = document.getElementById('videoElement');
        this.overlay = document.getElementById('overlay');
        this.ctx = this.overlay.getContext('2d');
        this.stats = document.getElementById('stats');
        this.status = document.getElementById('status');
        this.reactiveGlow = document.querySelector('.reactive-glow');

        // Audio Processing
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;

        // WebSocket
        this.ws = null;
        this.isProcessing = false;

        // Initialize
        this.initialize();
    }

    async initialize() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                },
                audio: true
            });

            // Set up video stream
            this.video.srcObject = stream;
            this.overlay.width = 640;
            this.overlay.height = 480;

            // Initialize components
            this.initializeWebSocket();
            this.initializeAudio(stream);

            this.video.addEventListener('play', () => {
                this.processFrame();
            });

        } catch (err) {
            console.error('Initialization error:', err);
            this.updateStatus('Error', false);
        }
    }

    async initializeAudio(stream) {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 64;

            const audioSource = this.audioContext.createMediaStreamSource(stream);
            audioSource.connect(this.analyser);

            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);

            this.visualizeAudio();

        } catch (err) {
            console.error('Audio initialization error:', err);
        }
    }

    initializeWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

        this.ws.onopen = () => {
            this.updateStatus('متصل', true);
            console.log('WebSocket connected');  // Debug log
        };

        this.ws.onclose = () => {
            this.updateStatus('قطع شده', false);
            console.log('WebSocket disconnected');  // Debug log
            setTimeout(() => this.initializeWebSocket(), 1000);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);  // Debug log
        };

        this.ws.onmessage = (event) => {
            try {
                const results = JSON.parse(event.data);
                this.drawResults(results);
                this.isProcessing = false;
            } catch (error) {
                console.error('Error processing message:', error);  // Debug log
            }
        };
    }

    async processFrame() {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN || this.isProcessing) {
            requestAnimationFrame(() => this.processFrame());
            return;
        }

        try {
            this.isProcessing = true;

            const canvas = document.createElement('canvas');
            canvas.width = this.video.videoWidth;
            canvas.height = this.video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(this.video, 0, 0);

            const frame = canvas.toDataURL('image/jpeg', 0.7);
            this.ws.send(frame);

            console.log('Frame sent');  // Debug log
        } catch (error) {
            console.error('Error processing frame:', error);  // Debug log
            this.isProcessing = false;
        }

        requestAnimationFrame(() => this.processFrame());
    }

    updateStatus(message, isConnected) {
        this.status.className = isConnected ? 'status connected' : 'status';
        this.status.querySelector('.status-text').textContent = message;
    }

    visualizeAudio() {
        this.analyser.getByteFrequencyData(this.dataArray);

        // Calculate average volume
        const average = Array.from(this.dataArray).reduce((a, b) => a + b, 0) / this.dataArray.length;

        // Calculate reactive glow intensity
        const intensity = Math.min(1, average / 128);
        const scale = 1 + (intensity * 0.6); // Scale from 1 to 1.3
        const opacity = intensity * 0.8; // Max opacity 0.8

        // Update reactive glow
        this.reactiveGlow.style.opacity = opacity;
        this.reactiveGlow.style.transform = `scale(${scale})`;

        requestAnimationFrame(() => this.visualizeAudio());
    }


    drawResults(results) {
        this.ctx.clearRect(0, 0, this.overlay.width, this.overlay.height);

        if (!results || !results.bbox) {
            return;
        }

        const [x1, y1, x2, y2] = results.bbox;

        // Draw face detection box with gradient stroke
        const gradient = this.ctx.createLinearGradient(x1, y1, x2, y2);
        gradient.addColorStop(0, '#ff9500');
        gradient.addColorStop(1, '#00b8ff');

        this.ctx.strokeStyle = gradient;
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

        // Draw mesh landmarks if available
        if (results.landmarks && results.landmarks.length > 0) {
            this.ctx.fillStyle = '#ff0000';  // red dots for landmarks
            results.landmarks.forEach(point => {
                const [px, py] = point;
                this.ctx.beginPath();
                this.ctx.arc(px, py, 1.5, 0, 2 * Math.PI);
                this.ctx.fill();
            });
        }

        // Process the gender value to ensure it's a string
        let genderValue = results.gender;
        if (typeof genderValue === 'object') {
            genderValue = genderValue.value || genderValue.label ||
                Object.values(genderValue)[0] || 'Unknown';
        }

        // Update stats with proper gender value
        this.stats.innerHTML = `
            <div style="opacity: 0.7; text-align: right; direction: ltr;">**AI Analysis** </div>
            <div style="margin: 8px 0; text-align: right; direction: rtl;">
                سن: <strong>${results.age}</strong><br>
                جنسیت: <strong>${results.gender}</strong><br>
                حالت چهره: <strong>${results.emotion}</strong>
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new FaceAnalysisApp();
});