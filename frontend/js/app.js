/**
 * ViralClipper - Frontend Application
 * AI-Powered Viral Clip Generator & Dead-Air Remover
 */

// Determine backend URL automatically
const API_BASE = (window.location.origin.startsWith('http') && !window.location.origin.includes(':3000') && !window.location.origin.includes(':5500'))
    ? window.location.origin
    : 'http://localhost:8000';

// ─── State ───────────────────────────────────────────────────────────────────

let currentState = 'upload';
let activeInputTab = 'upload'; // 'upload' or 'youtube'
let currentJobId = null;
let selectedFile = null;
let pollInterval = null;

// Settings loaded from localStorage
const settings = {
    apiKey: localStorage.getItem('viralclipper_gemini_key') || '',
    groqKey: localStorage.getItem('viralclipper_groq_key') || '',
    duration: localStorage.getItem('viralclipper_duration_v3') || '20-40',
    removeDeadAir: localStorage.getItem('viralclipper_dead_air') !== 'false',
};

// Fun loading messages
const loadingMessages = [
    "Analyzing your content for viral gold...",
    "Teaching Whisper AI what makes content pop...",
    "Detecting dead air pauses & silent moments...",
    "Finding the moments that'll stop users scrolling...",
    "Identifying emotional hooks & surprising takes...",
    "Excising dead air and splicing clips...",
    "Ranking outputs by viral potential...",
];
let messageIndex = 0;
let messageInterval = null;

// ─── DOM Elements ────────────────────────────────────────────────────────────

const stateUpload = document.getElementById('state-upload');
const stateProcessing = document.getElementById('state-processing');
const stateResults = document.getElementById('state-results');
const stateError = document.getElementById('state-error');

// Input tabs
const tabUpload = document.getElementById('tab-upload');
const tabYoutube = document.getElementById('tab-youtube');
const youtubeInputZone = document.getElementById('youtube-input-zone');
const inputYoutubeUrl = document.getElementById('input-youtube-url');
const btnPasteYt = document.getElementById('btn-paste-yt');

// Drop zone elements
const dropZone = document.getElementById('drop-zone');
const dropZoneContent = document.getElementById('drop-zone-content');
const filePreview = document.getElementById('file-preview');
const fileInput = document.getElementById('file-input');
const fileName = document.getElementById('file-name');
const fileSize = document.getElementById('file-size');
const btnChangeFile = document.getElementById('btn-change-file');
const btnGenerate = document.getElementById('btn-generate');
const uploadProgress = document.getElementById('upload-progress');
const uploadProgressBar = document.getElementById('upload-progress-bar');
const uploadProgressText = document.getElementById('upload-progress-text');

// Processing elements
const progressCircle = document.getElementById('progress-circle');
const progressPercent = document.getElementById('progress-percent');
const processingStep = document.getElementById('processing-step');
const stepIcon = document.getElementById('step-icon');
const stepText = document.getElementById('step-text');
const processingMessage = document.getElementById('processing-message');

// Results elements
const resultsSummary = document.getElementById('results-summary');
const clipsGrid = document.getElementById('clips-grid');
const btnNewVideo = document.getElementById('btn-new-video');

// Error elements
const errorMessage = document.getElementById('error-message');
const btnRetry = document.getElementById('btn-retry');
const btnErrorReset = document.getElementById('btn-error-reset');

// Settings Elements
const btnOpenSettings = document.getElementById('btn-open-settings');
const btnCloseSettings = document.getElementById('btn-close-settings');
const settingsModal = document.getElementById('settings-modal');
const inputGroqKey = document.getElementById('input-groq-key');
const inputApiKey = document.getElementById('input-api-key');
const btnToggleKeyVis = document.getElementById('btn-toggle-key-vis');
const selectDuration = document.getElementById('select-duration');
const checkDeadAir = document.getElementById('check-dead-air');
const btnSaveSettings = document.getElementById('btn-save-settings');

// Badges
const aiEngineText = document.getElementById('ai-engine-text');
const previewDuration = document.getElementById('preview-duration');
const previewDeadair = document.getElementById('preview-deadair');
const previewEngine = document.getElementById('preview-engine');

// ─── Initialization ──────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', init);

async function init() {
    initSettingsUI();
    initDragDrop();
    initEventListeners();
    await checkBackendHealth();
}

function initSettingsUI() {
    if (inputGroqKey) inputGroqKey.value = settings.groqKey;
    inputApiKey.value = settings.apiKey;
    selectDuration.value = settings.duration;
    checkDeadAir.checked = settings.removeDeadAir;
    updateBadges();
}

function updateBadges() {
    const hasKey = Boolean(settings.apiKey.trim());
    const hasGroq = Boolean(settings.groqKey.trim());
    if (hasGroq && hasKey) {
        aiEngineText.textContent = 'Groq V3 + Gemini';
        previewEngine.textContent = 'Groq V3 + Gemini';
        previewEngine.className = 'text-emerald-400 font-semibold';
    } else if (hasGroq) {
        aiEngineText.textContent = 'Groq Whisper-V3 Cloud';
        previewEngine.textContent = 'Groq V3 Cloud';
        previewEngine.className = 'text-emerald-400 font-semibold';
    } else if (hasKey) {
        aiEngineText.textContent = 'Gemini 2.0 AI';
        previewEngine.textContent = 'Gemini AI';
        previewEngine.className = 'text-emerald-400 font-semibold';
    } else {
        aiEngineText.textContent = 'Local AI Engine';
        previewEngine.textContent = 'Local Smart AI';
        previewEngine.className = 'text-primary-light font-semibold';
    }

    previewDuration.textContent = `${settings.duration} sec`;
    previewDeadair.textContent = settings.removeDeadAir ? 'Active' : 'Off';
    previewDeadair.className = settings.removeDeadAir ? 'text-emerald-400' : 'text-gray-400';
}

function initEventListeners() {
    // Input method tabs
    tabUpload.addEventListener('click', () => switchInputTab('upload'));
    tabYoutube.addEventListener('click', () => switchInputTab('youtube'));

    // File events
    fileInput.addEventListener('change', handleFileSelect);
    btnChangeFile.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    // YouTube events
    inputYoutubeUrl.addEventListener('input', () => {
        const val = inputYoutubeUrl.value.trim();
        btnGenerate.disabled = !isValidYouTubeUrl(val);
    });

    btnPasteYt.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                inputYoutubeUrl.value = text.trim();
                btnGenerate.disabled = !isValidYouTubeUrl(text.trim());
                showToast('Pasted YouTube link from clipboard!', 'success');
            }
        } catch {
            showToast('Unable to read clipboard. Please paste manually (Ctrl+V).', 'error');
        }
    });

    // Processing actions
    btnGenerate.addEventListener('click', handleGenerate);
    btnNewVideo.addEventListener('click', resetApp);
    btnRetry.addEventListener('click', handleRetry);
    btnErrorReset.addEventListener('click', resetApp);

    // Settings Modal
    btnOpenSettings.addEventListener('click', () => {
        if (inputGroqKey) inputGroqKey.value = settings.groqKey;
        inputApiKey.value = settings.apiKey;
        selectDuration.value = settings.duration;
        checkDeadAir.checked = settings.removeDeadAir;
        settingsModal.classList.remove('hidden');
    });

    btnCloseSettings.addEventListener('click', () => {
        settingsModal.classList.add('hidden');
    });

    settingsModal.addEventListener('click', (e) => {
        if (e.target === settingsModal) settingsModal.classList.add('hidden');
    });

    btnToggleKeyVis.addEventListener('click', () => {
        inputApiKey.type = inputApiKey.type === 'password' ? 'text' : 'password';
        if (inputGroqKey) inputGroqKey.type = inputGroqKey.type === 'password' ? 'text' : 'password';
    });

    btnSaveSettings.addEventListener('click', () => {
        if (inputGroqKey) settings.groqKey = inputGroqKey.value.trim();
        settings.apiKey = inputApiKey.value.trim();
        settings.duration = selectDuration.value;
        settings.removeDeadAir = checkDeadAir.checked;

        localStorage.setItem('viralclipper_groq_key', settings.groqKey);
        localStorage.setItem('viralclipper_gemini_key', settings.apiKey);
        localStorage.setItem('viralclipper_duration_v3', settings.duration);
        localStorage.setItem('viralclipper_dead_air', String(settings.removeDeadAir));

        updateBadges();
        settingsModal.classList.add('hidden');
        showToast('Settings saved successfully!', 'success');
    });
}

function switchInputTab(tab) {
    activeInputTab = tab;

    if (tab === 'upload') {
        tabUpload.className = 'flex-1 py-2 px-3 rounded-xl text-xs font-semibold transition-all bg-primary text-white shadow-md flex items-center justify-center gap-1.5';
        tabYoutube.className = 'flex-1 py-2 px-3 rounded-xl text-xs font-semibold transition-all text-gray-400 hover:text-white flex items-center justify-center gap-1.5';

        dropZone.classList.remove('hidden');
        youtubeInputZone.classList.add('hidden');
        btnGenerate.disabled = !selectedFile;
    } else {
        tabYoutube.className = 'flex-1 py-2 px-3 rounded-xl text-xs font-semibold transition-all bg-primary text-white shadow-md flex items-center justify-center gap-1.5';
        tabUpload.className = 'flex-1 py-2 px-3 rounded-xl text-xs font-semibold transition-all text-gray-400 hover:text-white flex items-center justify-center gap-1.5';

        dropZone.classList.add('hidden');
        youtubeInputZone.classList.remove('hidden');
        btnGenerate.disabled = !isValidYouTubeUrl(inputYoutubeUrl.value.trim());
    }
}

function isValidYouTubeUrl(url) {
    if (!url) return false;
    const reg = /^(https?:\/\/)?(www\.|m\.)?(youtube\.com\/(watch\?.*?v=|shorts\/|embed\/)|youtu\.be\/)([\w\-]{11})/i;
    return reg.test(url.trim());
}

async function checkBackendHealth() {
    try {
        const res = await fetch(`${API_BASE}/api/health`, { method: 'GET' });
        if (res.ok) {
            const data = await res.json();
            if (data.has_groq_key && !settings.groqKey) {
                aiEngineText.textContent = 'Groq Whisper-V3 Cloud';
                previewEngine.textContent = 'Groq V3 Cloud';
                previewEngine.className = 'text-emerald-400 font-semibold';
            }
            if (data.has_gemini_key && !settings.apiKey) {
                aiEngineText.textContent = data.has_groq_key ? 'Groq V3 + Gemini' : 'Gemini 2.0 (Server)';
                previewEngine.textContent = data.has_groq_key ? 'Groq V3 + Gemini' : 'Gemini AI';
                previewEngine.className = 'text-emerald-400 font-semibold';
            }
        }
    } catch {
        console.warn('Backend not responding yet on', API_BASE);
    }
}

// ─── Drag & Drop ─────────────────────────────────────────────────────────────

function initDragDrop() {
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            setSelectedFile(files[0]);
        }
    });

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(event => {
        document.body.addEventListener(event, (e) => e.preventDefault());
    });
}

// ─── File Handling ───────────────────────────────────────────────────────────

function handleFileSelect(e) {
    if (e.target.files.length > 0) {
        setSelectedFile(e.target.files[0]);
    }
}

function setSelectedFile(file) {
    const validTypes = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/x-matroska', 'video/webm'];
    const validExts = ['.mp4', '.mov', '.avi', '.mkv', '.webm'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();

    if (!validTypes.includes(file.type) && !validExts.includes(ext)) {
        showToast('Invalid file format. Please upload an MP4, MOV, AVI, MKV, or WEBM video.', 'error');
        return;
    }

    if (file.size > 2048 * 1024 * 1024) {
        showToast('File too large. Maximum supported size is 2GB.', 'error');
        return;
    }

    selectedFile = file;
    dropZoneContent.classList.add('hidden');
    filePreview.classList.remove('hidden');
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    btnGenerate.disabled = false;
}

// ─── Upload & Process ────────────────────────────────────────────────────────

async function handleGenerate() {
    btnGenerate.disabled = true;

    try {
        let jobId;

        if (activeInputTab === 'upload') {
            if (!selectedFile) return;
            btnGenerate.textContent = 'Uploading Video...';
            uploadProgress.classList.remove('hidden');
            jobId = await uploadFile(selectedFile);
        } else {
            // YouTube URL mode
            const ytUrl = inputYoutubeUrl.value.trim();
            if (!isValidYouTubeUrl(ytUrl)) {
                showToast('Please enter a valid YouTube video or Shorts link.', 'error');
                btnGenerate.disabled = false;
                return;
            }

            btnGenerate.innerHTML = '<span>Downloading from YouTube...</span><span class="animate-spin">⏳</span>';
            uploadProgress.classList.remove('hidden');
            uploadProgressBar.style.width = '100%';
            uploadProgressText.textContent = 'Downloading video stream from YouTube in HD...';

            jobId = await downloadFromYouTube(ytUrl);
        }

        currentJobId = jobId;
        await startProcessing(jobId);
    } catch (err) {
        showToast(`${err.message}`, 'error');
        btnGenerate.disabled = false;
        btnGenerate.innerHTML = '<span>Generate Viral Clips</span><span>⚡</span>';
        uploadProgress.classList.add('hidden');
    }
}

function uploadFile(file) {
    return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${API_BASE}/api/upload`);

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                uploadProgressBar.style.width = `${percent}%`;
                uploadProgressText.textContent = `Uploading video... ${percent}%`;
            }
        });

        xhr.addEventListener('load', () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                const data = JSON.parse(xhr.responseText);
                resolve(data.job_id);
            } else {
                try {
                    const err = JSON.parse(xhr.responseText);
                    reject(new Error(err.detail || 'Upload failed'));
                } catch {
                    reject(new Error(`Upload failed (HTTP ${xhr.status})`));
                }
            }
        });

        xhr.addEventListener('error', () => reject(new Error('Network error. Make sure the backend server is running.')));
        xhr.addEventListener('timeout', () => reject(new Error('Upload timed out')));
        xhr.timeout = 900000; // 15 minutes for large up to 2GB uploads

        xhr.send(formData);
    });
}

async function downloadFromYouTube(url) {
    const res = await fetch(`${API_BASE}/api/youtube`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url }),
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `YouTube download failed (HTTP ${res.status})`);
    }

    const data = await res.json();
    return data.job_id;
}

async function startProcessing(jobId) {
    try {
        const [minStr, maxStr] = settings.duration.split('-');
        const minDur = parseInt(minStr, 10) || 20;
        const maxDur = parseInt(maxStr, 10) || 40;

        const payload = {
            gemini_api_key: settings.apiKey || null,
            groq_api_key: settings.groqKey || null,
            target_duration_min: minDur,
            target_duration_max: maxDur,
            remove_dead_air: settings.removeDeadAir,
        };

        const res = await fetch(`${API_BASE}/api/process/${jobId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Failed to start processing');
        }

        switchState('processing');
        startPolling(jobId);
        startMessageRotation();
    } catch (err) {
        showToast(`Processing failed: ${err.message}`, 'error');
        resetApp();
    }
}

// ─── Status Polling ──────────────────────────────────────────────────────────

function startPolling(jobId) {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/status/${jobId}`);
            if (!res.ok) throw new Error('Failed to fetch status');

            const status = await res.json();
            updateProgressUI(status);

            if (status.status === 'done') {
                stopPolling();
                stopMessageRotation();
                await fetchResults(jobId);
            } else if (status.status === 'error') {
                stopPolling();
                stopMessageRotation();
                showError(status.error_message || status.step_description || 'An error occurred during video processing.');
            }
        } catch (err) {
            console.error('Polling error:', err);
        }
    }, 2000);
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

function updateProgressUI(status) {
    const percent = Math.min(100, Math.max(0, status.progress));
    const circumference = 2 * Math.PI * 54;
    const offset = circumference - (percent / 100) * circumference;

    progressCircle.style.strokeDashoffset = offset;
    progressPercent.textContent = `${percent}%`;

    const stepIcons = {
        transcribing: '🎙️',
        analyzing: '🧠',
        cutting: '✂️',
        done: '✅',
    };
    stepIcon.textContent = stepIcons[status.status] || '⏳';
    stepText.textContent = status.step_description;

    const steps = ['transcribing', 'analyzing', 'cutting'];
    const currentIdx = steps.indexOf(status.status);

    for (let i = 0; i < 3; i++) {
        const el = document.getElementById(`step-${i + 1}`);
        el.className = el.className.replace(/step-active|step-done/g, '').trim();
        if (i < currentIdx) {
            el.classList.add('step-done');
        } else if (i === currentIdx) {
            el.classList.add('step-active');
        }
    }
}

// ─── Results ─────────────────────────────────────────────────────────────────

async function fetchResults(jobId) {
    try {
        const res = await fetch(`${API_BASE}/api/results/${jobId}`);
        if (!res.ok) throw new Error('Failed to fetch results');

        const data = await res.json();
        renderResults(data);
        switchState('results');
    } catch (err) {
        showError(`Failed to load results: ${err.message}`);
    }
}

function renderResults(data) {
    resultsSummary.textContent = `${data.total_clips} viral clips generated from ${formatDuration(data.video_duration)} video • Processed in ${data.processing_time}s`;
    clipsGrid.innerHTML = '';

    data.clips.forEach((clip) => {
        const card = createClipCard(clip, data.job_id);
        clipsGrid.appendChild(card);
    });
}

function createClipCard(clip, jobId) {
    const card = document.createElement('div');
    card.className = 'clip-card fade-in';

    const rankClass = clip.rank <= 3 ? `rank-${clip.rank}` : 'rank-default';
    const viralityClass = clip.virality_score >= 75 ? 'virality-high' : clip.virality_score >= 50 ? 'virality-mid' : 'virality-low';
    const clipUrl = `${API_BASE}/api/clips/${jobId}/${clip.filename}`;

    card.innerHTML = `
        <div class="relative">
            <div class="rank-badge ${rankClass}">#${clip.rank}</div>
            <video controls preload="metadata" class="w-full rounded-t-2xl">
                <source src="${clipUrl}" type="video/mp4">
                Your browser does not support video playback.
            </video>
        </div>
        <div class="p-4">
            <div class="flex items-start justify-between gap-2 mb-2">
                <h3 class="font-bold text-sm text-gray-100 flex-1 leading-snug">${escapeHtml(clip.title)}</h3>
                <span class="text-[11px] font-mono text-gray-400 whitespace-nowrap bg-dark-700 px-2 py-0.5 rounded-md">
                    ${formatDuration(clip.start_time)} - ${formatDuration(clip.end_time)}
                </span>
            </div>

            <div class="flex items-center gap-2 mb-2.5">
                <div class="virality-bar flex-1">
                    <div class="virality-bar-fill ${viralityClass}" style="width: ${clip.virality_score}%"></div>
                </div>
                <span class="text-xs font-extrabold ${clip.virality_score >= 75 ? 'text-emerald-400' : clip.virality_score >= 50 ? 'text-amber-400' : 'text-rose-400'}">
                    ${clip.virality_score}/100
                </span>
            </div>

            <p class="text-[11px] text-gray-300 italic mb-2 bg-dark-900/60 p-2 rounded-lg border border-dark-700/50 leading-relaxed">
                ${escapeHtml(clip.description)}
            </p>

            <p class="text-xs text-gray-400 mb-3 bg-dark-800/80 p-2.5 rounded-xl border border-dark-700/80 leading-relaxed">
                <span class="text-primary-light font-medium">Lesson & Value:</span> ${escapeHtml(clip.reason)}
            </p>

            <div class="flex items-center justify-between pt-1">
                <span class="text-[11px] font-medium px-2 py-0.5 bg-dark-700 rounded-full text-gray-400">
                    ⏱️ ${clip.duration.toFixed(1)}s
                </span>
                
                <div class="flex items-center gap-2">
                    <button class="btn-copy-caption px-2.5 py-1.5 bg-dark-700 hover:bg-dark-600 rounded-lg text-xs text-gray-300 font-medium transition-all" title="Copy title & hook caption">
                        📋 Copy
                    </button>
                    <a href="${clipUrl}" download="${clip.filename}" class="btn-download text-xs font-semibold">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                        </svg>
                        Download
                    </a>
                </div>
            </div>
        </div>
    `;

    const btnCopy = card.querySelector('.btn-copy-caption');
    btnCopy.addEventListener('click', () => {
        const textToCopy = `${clip.title}\n\n${clip.reason}\n\n#viral #shorts #reels`;
        navigator.clipboard.writeText(textToCopy).then(() => {
            btnCopy.textContent = '✓ Copied!';
            setTimeout(() => { btnCopy.textContent = '📋 Copy'; }, 2000);
            showToast('Caption copied to clipboard!', 'success');
        });
    });

    return card;
}

// ─── State Management ────────────────────────────────────────────────────────

function switchState(state) {
    currentState = state;

    stateUpload.classList.add('hidden');
    stateProcessing.classList.add('hidden');
    stateResults.classList.add('hidden');
    stateError.classList.add('hidden');

    switch (state) {
        case 'upload':
            stateUpload.classList.remove('hidden');
            break;
        case 'processing':
            stateProcessing.classList.remove('hidden');
            break;
        case 'results':
            stateResults.classList.remove('hidden');
            break;
        case 'error':
            stateError.classList.remove('hidden');
            break;
    }
}

function showError(message) {
    errorMessage.textContent = message;
    switchState('error');
}

function resetApp() {
    stopPolling();
    stopMessageRotation();

    currentJobId = null;
    selectedFile = null;

    dropZoneContent.classList.remove('hidden');
    filePreview.classList.add('hidden');
    btnGenerate.disabled = true;
    btnGenerate.innerHTML = '<span>Generate Viral Clips</span><span>⚡</span>';
    uploadProgress.classList.add('hidden');
    uploadProgressBar.style.width = '0%';
    fileInput.value = '';
    inputYoutubeUrl.value = '';

    progressCircle.style.strokeDashoffset = 339.292;
    progressPercent.textContent = '0%';

    for (let i = 1; i <= 3; i++) {
        const el = document.getElementById(`step-${i}`);
        el.className = el.className.replace(/step-active|step-done/g, '').trim();
    }

    clipsGrid.innerHTML = '';
    switchState('upload');
    switchInputTab(activeInputTab);
}

async function handleRetry() {
    if (!currentJobId) {
        resetApp();
        return;
    }
    switchState('processing');
    await startProcessing(currentJobId);
}

// ─── Loading Messages ────────────────────────────────────────────────────────

function startMessageRotation() {
    messageIndex = 0;
    processingMessage.textContent = loadingMessages[0];

    messageInterval = setInterval(() => {
        messageIndex = (messageIndex + 1) % loadingMessages.length;
        processingMessage.style.opacity = '0';
        setTimeout(() => {
            processingMessage.textContent = loadingMessages[messageIndex];
            processingMessage.style.opacity = '1';
        }, 250);
    }, 4500);
}

function stopMessageRotation() {
    if (messageInterval) {
        clearInterval(messageInterval);
        messageInterval = null;
    }
}

// ─── Toast Notifications ─────────────────────────────────────────────────────

function showToast(message, type = 'error') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type === 'success' ? 'toast-success' : ''}`;
    toast.innerHTML = `
        <div class="flex items-start gap-2.5">
            <span class="text-base">${type === 'error' ? '❌' : '✅'}</span>
            <p class="text-xs font-medium text-gray-200 flex-1 leading-snug">${escapeHtml(message)}</p>
            <button class="text-gray-400 hover:text-white text-base leading-none" onclick="this.closest('.toast').remove()">&times;</button>
        </div>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-in forwards';
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

// ─── Utilities ───────────────────────────────────────────────────────────────

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
}

function formatDuration(seconds) {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min}:${sec.toString().padStart(2, '0')}`;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
