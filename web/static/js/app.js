/**
 * Banco Caja Social - Virtual Advisor
 * Web chat logic
 */

const API_BASE = window.location.origin;

// ---- DOM Elements ----
const chatArea = document.getElementById('chatArea');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const micBtn = document.getElementById('micBtn');
const stopBtn = document.getElementById('stopBtn');
const statusBar = document.getElementById('statusBar');
const typingIndicator = document.getElementById('typingIndicator');
const voiceSelect = document.getElementById('voiceSelect');
const rateControl = document.getElementById('rateControl');
const rateValue = document.getElementById('rateValue');
const settingsBtn = document.getElementById('settingsBtn');
const voiceControls = document.getElementById('voiceControls');

// ---- State ----
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let currentAudio = null;

// ---- Microphone Recording ----
async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = async () => {
            // Stop all mic tracks
            stream.getTracks().forEach(t => t.stop());

            const blob = new Blob(audioChunks, { type: 'audio/webm' });
            if (blob.size === 0) {
                clearStatus();
                return;
            }

            setStatus('Procesando...', false);

            // Send audio to server for transcription
            const formData = new FormData();
            formData.append('audio', blob, 'recording.webm');

            try {
                const response = await fetch(`${API_BASE}/transcribe`, {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                clearStatus();
                if (data.text && data.text.trim()) {
                    messageInput.value = data.text.trim();
                    sendMessage();
                } else {
                    setStatus('No se detecto voz. Intente de nuevo.', false);
                    setTimeout(clearStatus, 3000);
                }
            } catch (err) {
                console.error('Transcription error:', err);
                clearStatus();
            }
        };

        mediaRecorder.start();
        isRecording = true;
        micBtn.classList.add('recording');
        setStatus('Grabando...', true);

    } catch (err) {
        console.error('Microphone error:', err);
        setStatus('Error al acceder al microfono.', false);
        setTimeout(clearStatus, 3000);
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    isRecording = false;
    micBtn.classList.remove('recording');
}

// ---- Audio (Azure TTS) ----
let selectedEdgeVoice = null; // Will be set from dropdown on init
function cleanTextForTTS(text) {
    let clean = text.replace(/\*\*(.+?)\*\*/g, '$1');
    clean = clean.replace(/\$([\d.,]+)/g, '$1 pesos');
    return clean;
}

async function prepareAudio(text) {
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }

    const response = await fetch(`${API_BASE}/voz`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto: cleanTextForTTS(text), voz: selectedEdgeVoice })
    });

    if (!response.ok) throw new Error('Error generando audio');

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.playbackRate = parseFloat(rateControl.value);

    await new Promise((resolve, reject) => {
        audio.oncanplaythrough = resolve;
        audio.onerror = reject;
        audio.load();
    });

    return { audio, url };
}

function playAudio(audio, url) {
    currentAudio = audio;
    stopBtn.classList.add('active');

    const cleanup = () => {
        stopBtn.classList.remove('active');
        URL.revokeObjectURL(url);
        currentAudio = null;
    };

    currentAudio.onended = cleanup;
    currentAudio.onerror = cleanup;
    currentAudio.play();
}

// ---- Messages ----
function renderMarkdown(text) {
    const escaped = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    return escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

function addMessage(text, isUser) {
    const div = document.createElement('div');
    div.className = `message ${isUser ? 'user' : 'bot'}`;
    div.innerHTML = isUser ? text : renderMarkdown(text);
    chatArea.insertBefore(div, typingIndicator);
    chatArea.scrollTop = chatArea.scrollHeight;
}

function showTyping() {
    typingIndicator.classList.add('active');
    chatArea.scrollTop = chatArea.scrollHeight;
}

function hideTyping() {
    typingIndicator.classList.remove('active');
}

// ---- Status ----
function setStatus(text, isRecording) {
    statusBar.textContent = text;
    statusBar.classList.toggle('recording', isRecording);
}

function clearStatus() {
    statusBar.textContent = '';
    statusBar.classList.remove('recording');
}

// ---- Send Message ----
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    addMessage(message, true);
    messageInput.value = '';
    showTyping();

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        const data = await response.json();

        // Prepare audio while still showing typing indicator
        let audioData = null;
        try {
            audioData = await prepareAudio(data.response);
        } catch (e) {
            console.error('Error preparando audio:', e);
        }

        hideTyping();
        addMessage(data.response, false);

        if (audioData) playAudio(audioData.audio, audioData.url);

    } catch (error) {
        console.error('Error:', error);
        hideTyping();
        addMessage('Error al conectar con el servidor. Verifique que este ejecutandose.', false);
    }
}

// ---- Reset ----
async function resetConversation() {
    try {
        await fetch(`${API_BASE}/reset`, { method: 'POST' });
        const messages = chatArea.querySelectorAll('.message');
        messages.forEach((msg, i) => { if (i > 0) msg.remove(); });
        clearStatus();
    } catch (e) {
        console.error('Error reseteando:', e);
    }
}

// ---- Event Listeners ----
function init() {
    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    micBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    });

    stopBtn.addEventListener('click', () => {
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }
        stopBtn.classList.remove('active');
    });

    rateControl.addEventListener('input', (e) => {
        rateValue.textContent = e.target.value;
    });

    voiceSelect.addEventListener('change', (e) => {
        selectedEdgeVoice = e.target.value;
    });

    // Initialize voice from dropdown default
    selectedEdgeVoice = voiceSelect.value;

    settingsBtn.addEventListener('click', () => {
        voiceControls.classList.toggle('visible');
    });

    messageInput.focus();
}

document.addEventListener('DOMContentLoaded', init);
