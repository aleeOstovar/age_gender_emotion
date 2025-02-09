// main.js
class FaceAnalysisApp {
    constructor() {
        this.initializeElements();
        this.initializeState();
        this.initialize();
    }

    initializeElements() {
        this.video = document.getElementById('videoElement');
        this.overlay = document.getElementById('overlay');
        this.landmarkOverlay = document.getElementById('landmarkOverlay');
        this.ctx = this.overlay.getContext('2d');
        this.landmarkCtx = this.landmarkOverlay.getContext('2d');
        this.stats = document.getElementById('stats');
        this.confidenceBars = document.getElementById('confidenceBars');
        this.status = document.getElementById('status');
        this.reactiveGlow = document.querySelector('.reactive-glow');
    }

    initializeState() {
        this.audioContext = null;
        this.analyser = null;
        this.dataArray = null;
        this.ws = null;
        this.isProcessing = false;
        this.lastResults = null;
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

            this.setupVideo(stream);
            this.initializeWebSocket();
            this.initializeAudio(stream);

        } catch (err) {
            console.error('Initialization error:', err);
            this.updateStatus('خطا در راه‌اندازی', false);
        }
    }

    setupVideo(stream) {
        this.video.srcObject = stream;
        this.overlay.width = 640;
        this.overlay.height = 480;
        this.landmarkOverlay.width = 640;
        this.landmarkOverlay.height = 480;

        this.video.addEventListener('play', () => {
            this.processFrame();
        });
    }

    drawLandmarks(landmarks) {
        this.landmarkCtx.clearRect(0, 0, this.landmarkOverlay.width, this.landmarkOverlay.height);
        
        if (!landmarks || !landmarks.length) return;

        // Draw connections between landmarks for different facial features
        this.landmarkCtx.strokeStyle = 'rgba(0, 255, 149, 0.5)';
        this.landmarkCtx.lineWidth = 1;

        // Draw points
        landmarks.forEach(([x, y]) => {
            this.landmarkCtx.beginPath();
            this.landmarkCtx.arc(x, y, 1, 0, 2 * Math.PI);
            this.landmarkCtx.fillStyle = 'rgba(0, 184, 255, 0.8)';
            this.landmarkCtx.fill();
        });
    }

    updateConfidenceBars(results) {
        const confidences = {
            'سن': results.age_confidence,
            'جنسیت': results.gender_confidence,
            'حالت چهره': results.emotion_confidence
        };

        this.confidenceBars.innerHTML = Object.entries(confidences)
            .map(([label, value]) => `
                <div class="confidence-bar">
                    <div class="confidence-label">${label}: ${(value * 100).toFixed(0)}%</div>
                    <div class="bar-container">
                        <div class="bar-fill" style="width: ${value * 100}%"></div>
                    </div>
                </div>
            `).join('');
    }

    drawResults(results) {
        this.ctx.clearRect(0, 0, this.overlay.width, this.overlay.height);
        
        if (!results || !results.bbox) return;

        const [x1, y1, x2, y2] = results.bbox;

        // Draw face detection box with gradient
        const gradient = this.ctx.createLinearGradient(x1, y1, x2, y2);
        gradient.addColorStop(0, '#00ff95');
        gradient.addColorStop(1, '#00b8ff');

        this.ctx.strokeStyle = gradient;
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

        // Draw landmarks
        if (results.landmarks) {
            this.drawLandmarks(results.landmarks);
        }

        // Update stats
        this.stats.innerHTML = `
            <div style="opacity: 0.7; text-align: right; direction: ltr;">** تحلیل هوشمند **</div>
            <div style="margin: 8px 0; text-align: right; direction: rtl;">
                سن: <strong>${results.age}</strong><br>
                جنسیت: <strong>${results.gender}</strong><br>
                حالت چهره: <strong>${results.emotion}</strong>
            </div>
        `;

        // Update confidence bars
        this.updateConfidenceBars(results);
    }

    // Rest of the methods (initializeAudio, initializeWebSocket, processFrame, etc.) 
    // remain the same as in the original code
}

document.addEventListener('DOMContentLoaded', () => {
    new FaceAnalysisApp();
});