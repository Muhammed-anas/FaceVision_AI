const video = document.getElementById('video');
    const statusEl = document.getElementById('status');
    const indicatorEl = document.getElementById('indicator');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const captureCountEl = document.getElementById('captureCount');
    
    let capturing = false;
    let isRunning = false;
    let intervalId = null;
    let captureCount = 0;
    let stream = null;

    async function initCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ 
                video: { width: { ideal: 640 }, height: { ideal: 480 } } 
            });
            video.srcObject = stream;
            setStatus('Camera ready - Click "Start Analysis"', 'ok');
        } catch(err) {
            setStatus('Camera access denied: ' + err.message, 'error');
        }
    }

    function setStatus(text, type) {
        statusEl.innerText = text;
        statusEl.className = type ? `status-${type}` : '';
        if (type === 'ok' && isRunning) indicatorEl.className = 'indicator active';
        else if (type === 'error') indicatorEl.className = 'indicator inactive';
        else if (type === 'processing') indicatorEl.className = 'indicator active';
        else indicatorEl.className = 'indicator inactive';
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    function captureAndSend() {
        if (capturing || !isRunning) return;
        capturing = true;

        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        if (!ctx || !video.videoWidth) {
            setStatus('Waiting for camera...', 'processing');
            capturing = false;
            return;
    }
        
        ctx.drawImage(video, 0, 0);
        let base64Image;
        try {
            base64Image = canvas.toDataURL('image/jpeg', 0.8).split(',')[1];
            if (!base64Image || base64Image.length < 100) throw new Error('Failed to encode image');
            setStatus('Analyzing face... (Capture #' + (captureCount + 1) + ')', 'processing');
        } catch (err) {
            setStatus('Capture failed: ' + err.message, 'error');
            capturing = false;
            return;
        }

        const csrftoken = getCookie('csrftoken');
        const startTime = Date.now();
        
        fetch('/api/camera/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken || '' },
            body: JSON.stringify({ image: base64Image, timestamp: new Date().toISOString() })
        })
        .then(res => {
            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            console.log(`Response in ${elapsed}s:`, res.status);
            if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            return res.json();
        })
        .then(data => {
            captureCount++;
            captureCountEl.innerText = captureCount;
            document.getElementById('raw').innerText = `Last Response (${new Date().toLocaleTimeString()}):\n${JSON.stringify(data, null, 2)}`;

            let payload = data?.data || (data.age !== undefined ? data : null);
            if (payload) {
                document.getElementById('age').innerText = payload.age ?? '-';
                document.getElementById('gender').innerText = payload.gender || '-';
                document.getElementById('emotion').innerText = payload.emotion || '-';
                setStatus(payload.error ? '⚠️ ' + payload.error : '✅ Analysis complete (#' + captureCount + ')', 'ok');
            } else if (data?.error) {
                setStatus('❌ Error: ' + data.error, 'error');
                if (data.error.includes('AI service error') || data.error.includes('connection'))
                    document.getElementById('setupInfo').style.display = 'block';
            } else setStatus('⚠️ Unexpected response', 'error');
        })
        .catch(err => {
            console.error('API error:', err);
            setStatus('❌ Network error: ' + err.message, 'error');
            document.getElementById('setupInfo').style.display = 'block';
        })
        .finally(() => { capturing = false; });
    }

    function startAnalysis() {
        if (isRunning) return;
        isRunning = true;
        startBtn.disabled = true;
        stopBtn.disabled = false;
        document.getElementById('setupInfo').style.display = 'none';
        setStatus('Starting continuous analysis...', 'processing');
        setTimeout(() => {
            captureAndSend();
            intervalId = setInterval(captureAndSend, 3000);
        }, 500);
    }

    function stopAnalysis() {
        if (!isRunning) return;
        isRunning = false;
        capturing = false;
        if (intervalId) clearInterval(intervalId);
        startBtn.disabled = false;
        stopBtn.disabled = true;
        setStatus('Analysis stopped', 'ok');
    }

    function restartAnalysis() {
        stopAnalysis();
        captureCount = 0;
        captureCountEl.innerText = '0';
        document.getElementById('age').innerText = '-';
        document.getElementById('gender').innerText = '-';
        document.getElementById('emotion').innerText = '-';
        document.getElementById('raw').innerText = '';
        setStatus('Ready to restart - Click "Start Analysis"', 'ok');
        if (stream) stream.getTracks().forEach(track => track.stop());
        initCamera();
    }

    window.addEventListener('load', initCamera);
    window.addEventListener('beforeunload', () => {
        stopAnalysis();
        if (stream) stream.getTracks().forEach(track => track.stop());
    });