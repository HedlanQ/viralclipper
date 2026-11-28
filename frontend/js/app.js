/**
 * ViralClipper - Frontend Application (UI/UX Pro Max Cinema Studio Edition)
 * AI-Powered Viral Clip Generator & Dead-Air Remover
 */

// Determine backend URL automatically
const API_BASE = (window.location.origin.startsWith('http') && !window.location.origin.includes(':3000') && !window.location.origin.includes(':5500'))
    ? window.location.origin
    : 'http://localhost:8000';

// ─── SVG Icon Templates (Lucide / Heroicons 24x24) ───────────────────────────

const ICONS = {
    bolt: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>`,
    spinner: `<svg class="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg>`,
    mic: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>`,
    cpu: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg>`,
    scissors: `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="6" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><line x1="20" y1="4" x2="8.12" y2="15.88"></line><line x1="14.47" y1="14.48" x2="20" y2="20"></line><line x1="8.12" y1="8.12" x2="12" y2="12"></line></svg>`,
    check: `<svg class="w-3.5 h-3.5 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"></polyline></svg>`,
    copy: `<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`,
    fileVideo: `<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><polygon points="10 11 16 14 10 17 10 11"></polygon></svg>`,
    fileText: `<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>`,
    clock: `<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>`,
    inbox: `<svg class="w-8 h-8 text-slate-500 mx-auto" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"></polyline><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"></path></svg>`,
    checkCircle: `<svg class="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`,
    alertCircle: `<svg class="w-4 h-4 text-rose-400 shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`,
};

// ─── State ───────────────────────────────────────────────────────────────────

let currentState = 'upload';
let activeInputTab = 'upload'; // 'upload' or 'youtube'
let currentJobId = null;
let selectedFile = null;
let currentVideoLabel = '';
let pollInterval = null;
const HISTORY_STORAGE_KEY = 'viralclipper_history_v1';

// Settings loaded from localStorage
const settings = {
    apiKey: localStorage.getItem('viralclipper_gemini_key') || '',
    groqKey: localStorage.getItem('viralclipper_groq_key') || '',
    duration: localStorage.getItem('viralclipper_duration_v3') || '20-40',
    removeDeadAir: localStorage.getItem('viralclipper_dead_air') !== 'false',
};

// Loading messages
const loadingMessages = [
    "Analyzing your content for viral gold...",
    "Transcribing spoken words with Whisper AI...",
    "Detecting dead air pauses & silent moments...",
    "Finding the moments that stop users scrolling...",
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
const btnCopyTranscript = document.getElementById('btn-copy-transcript');
const btnCopyTranscriptText = document.getElementById('btn-copy-transcript-text');
const checkSelectAll = document.getElementById('check-select-all');
const selectedClipsCount = document.getElementById('selected-clips-count');
const btnDownloadSelected = document.getElementById('btn-download-selected');

let currentResultsData = null;
const selectedClipsSet = new Set();

// Error elements
const errorMessage = document.getElementById('error-message');
const btnRetry = document.getElementById('btn-retry');
const btnErrorReset = document.getElementById('btn-error-reset');

// Settings Elements (Modal + Inline Quick Studio Controls)
const btnOpenSettings = document.getElementById('btn-open-settings');
const btnCloseSettings = document.getElementById('btn-close-settings');
const settingsModal = document.getElementById('settings-modal');
const inputGroqKey = document.getElementById('input-groq-key');
const inputApiKey = document.getElementById('input-api-key');
const btnToggleKeyVis = document.getElementById('btn-toggle-key-vis');
const selectDuration = document.getElementById('select-duration');
const checkDeadAir = document.getElementById('check-dead-air');
const quickSelectDuration = document.getElementById('quick-select-duration');
const quickCheckDeadAir = document.getElementById('quick-check-dead-air');
const btnSaveSettings = document.getElementById('btn-save-settings');

// History Elements
const btnOpenHistory = document.getElementById('btn-open-history');
const btnCloseHistory = document.getElementById('btn-close-history');
const btnClearHistory = document.getElementById('btn-clear-history');
const historyModal = document.getElementById('history-modal');
const historyList = document.getElementById('history-list');
const historyCountBadge = document.getElementById('history-count-badge');

// Viral Captions Studio Modal Elements
const captionsModal = document.getElementById('captions-modal');
const captionsModalSubtitle = document.getElementById('captions-modal-subtitle');
const btnCloseCaptions = document.getElementById('btn-close-captions');
const captionBestPickText = document.getElementById('caption-best-pick-text');
const btnCopyBestPick = document.getElementById('btn-copy-best-pick');
const captionsLoadingIndicator = document.getElementById('captions-loading-indicator');
const captionFeedbackPills = document.getElementById('caption-feedback-pills');
const inputCaptionFeedback = document.getElementById('input-caption-feedback');
const btnSubmitCaptionFeedback = document.getElementById('btn-submit-caption-feedback');
const captionsOptionsList = document.getElementById('captions-options-list');
const btnCopyAllCaptions = document.getElementById('btn-copy-all-captions');

let activeCaptionContext = null;

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
    updateHistoryBadge();
    await checkBackendHealth();
}

function initSettingsUI() {
    if (inputGroqKey) inputGroqKey.value = settings.groqKey;
    inputApiKey.value = settings.apiKey;
    selectDuration.value = settings.duration;
    checkDeadAir.checked = settings.removeDeadAir;
    if (quickSelectDuration) quickSelectDuration.value = settings.duration;
    if (quickCheckDeadAir) quickCheckDeadAir.checked = settings.removeDeadAir;
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
        previewEngine.className = 'text-rose-300 font-semibold';
    }

    previewDuration.textContent = `${settings.duration} sec`;
    previewDeadair.textContent = settings.removeDeadAir ? 'Active' : 'Off';
    previewDeadair.className = settings.removeDeadAir ? 'text-emerald-400 font-semibold' : 'text-slate-400';
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

    // Inline Quick Studio Controls
    if (quickSelectDuration) {
        quickSelectDuration.addEventListener('change', () => {
            settings.duration = quickSelectDuration.value;
            selectDuration.value = settings.duration;
            localStorage.setItem('viralclipper_duration_v3', settings.duration);
            updateBadges();
        });
    }
    if (quickCheckDeadAir) {
        quickCheckDeadAir.addEventListener('change', () => {
            settings.removeDeadAir = quickCheckDeadAir.checked;
            checkDeadAir.checked = settings.removeDeadAir;
            localStorage.setItem('viralclipper_dead_air', String(settings.removeDeadAir));
            updateBadges();
        });
    }

    // Processing actions
    btnGenerate.addEventListener('click', handleGenerate);
    btnNewVideo.addEventListener('click', resetApp);
    btnRetry.addEventListener('click', handleRetry);
    btnErrorReset.addEventListener('click', resetApp);

    // Results Actions (Copy Transcript & Batch Download)
    if (btnCopyTranscript) {
        btnCopyTranscript.addEventListener('click', handleCopyTranscript);
    }
    if (checkSelectAll) {
        checkSelectAll.addEventListener('change', handleToggleSelectAll);
    }
    if (btnDownloadSelected) {
        btnDownloadSelected.addEventListener('click', handleDownloadSelected);
    }

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

        if (quickSelectDuration) quickSelectDuration.value = settings.duration;
        if (quickCheckDeadAir) quickCheckDeadAir.checked = settings.removeDeadAir;

        localStorage.setItem('viralclipper_groq_key', settings.groqKey);
        localStorage.setItem('viralclipper_gemini_key', settings.apiKey);
        localStorage.setItem('viralclipper_duration_v3', settings.duration);
        localStorage.setItem('viralclipper_dead_air', String(settings.removeDeadAir));

        updateBadges();
        settingsModal.classList.add('hidden');
        showToast('Settings saved successfully!', 'success');
    });

    // History Modal
    if (btnOpenHistory) {
        btnOpenHistory.addEventListener('click', () => {
            renderHistoryModal();
            historyModal.classList.remove('hidden');
        });
    }
    if (btnCloseHistory) {
        btnCloseHistory.addEventListener('click', () => {
            historyModal.classList.add('hidden');
        });
    }
    if (historyModal) {
        historyModal.addEventListener('click', (e) => {
            if (e.target === historyModal) historyModal.classList.add('hidden');
        });
    }
    if (btnClearHistory) {
        btnClearHistory.addEventListener('click', () => {
            localStorage.removeItem(HISTORY_STORAGE_KEY);
            updateHistoryBadge();
            renderHistoryModal();
            showToast('History cleared!', 'success');
        });
    }

    // Viral Captions Studio Modal
    if (btnCloseCaptions) {
        btnCloseCaptions.addEventListener('click', () => {
            captionsModal.classList.add('hidden');
        });
    }
    if (captionsModal) {
        captionsModal.addEventListener('click', (e) => {
            if (e.target === captionsModal) captionsModal.classList.add('hidden');
        });
    }
    if (btnCopyBestPick) {
        btnCopyBestPick.addEventListener('click', () => {
            const text = (captionBestPickText && captionBestPickText.textContent || '').trim();
            if (!text || text === 'Generating viral captions...') return;
            navigator.clipboard.writeText(text).then(() => {
                const orig = btnCopyBestPick.textContent;
                btnCopyBestPick.textContent = '✓ Copied!';
                setTimeout(() => { btnCopyBestPick.textContent = orig; }, 2000);
                showToast('Best Pick caption copied!', 'success');
            });
        });
    }
    if (btnCopyAllCaptions) {
        btnCopyAllCaptions.addEventListener('click', () => {
            if (!activeCaptionContext || !activeCaptionContext.clip) return;
            const caps = activeCaptionContext.clip.viral_captions || [];
            const best = activeCaptionContext.clip.best_caption || '';
            if (!caps.length) return;
            const formatted = caps.map((c, i) => `${i + 1}. ${c}`).join('\n') + (best ? `\n\nBest Pick: ${best}` : '');
            navigator.clipboard.writeText(formatted).then(() => {
                const orig = btnCopyAllCaptions.textContent;
                btnCopyAllCaptions.textContent = '✓ Copied!';
                setTimeout(() => { btnCopyAllCaptions.textContent = orig; }, 2000);
                showToast('All viral caption options copied!', 'success');
            });
        });
    }
    if (captionFeedbackPills) {
        captionFeedbackPills.querySelectorAll('.btn-caption-feedback').forEach((btn) => {
            btn.addEventListener('click', () => {
                const fb = btn.getAttribute('data-feedback');
                if (fb) requestViralCaptionsUpdate(fb);
            });
        });
    }
    if (btnSubmitCaptionFeedback) {
        btnSubmitCaptionFeedback.addEventListener('click', () => {
            const val = (inputCaptionFeedback && inputCaptionFeedback.value || '').trim();
            if (!val) {
                showToast('Enter feedback, a name, or style example first.', 'error');
                return;
            }
            requestViralCaptionsUpdate(val);
            inputCaptionFeedback.value = '';
        });
    }
    if (inputCaptionFeedback) {
        inputCaptionFeedback.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                btnSubmitCaptionFeedback.click();
            }
        });
    }

    // Keyboard Escape to close modals
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (captionsModal && !captionsModal.classList.contains('hidden')) {
                captionsModal.classList.add('hidden');
            } else if (settingsModal && !settingsModal.classList.contains('hidden')) {
                settingsModal.classList.add('hidden');
            } else if (historyModal && !historyModal.classList.contains('hidden')) {
                historyModal.classList.add('hidden');
            }
        }
    });
}

function switchInputTab(tab) {
    activeInputTab = tab;

    if (tab === 'upload') {
        tabUpload.className = 'cursor-pointer py-2 px-3.5 rounded-lg text-xs font-semibold transition-colors duration-200 bg-rose-600 text-white shadow-md flex items-center justify-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500';
        tabYoutube.className = 'cursor-pointer py-2 px-3.5 rounded-lg text-xs font-semibold transition-colors duration-200 text-slate-400 hover:text-white flex items-center justify-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500';
        tabUpload.setAttribute('aria-selected', 'true');
        tabYoutube.setAttribute('aria-selected', 'false');

        dropZone.classList.remove('hidden');
        youtubeInputZone.classList.add('hidden');
        btnGenerate.disabled = !selectedFile;
    } else {
        tabYoutube.className = 'cursor-pointer py-2 px-3.5 rounded-lg text-xs font-semibold transition-colors duration-200 bg-rose-600 text-white shadow-md flex items-center justify-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500';
        tabUpload.className = 'cursor-pointer py-2 px-3.5 rounded-lg text-xs font-semibold transition-colors duration-200 text-slate-400 hover:text-white flex items-center justify-center gap-1.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500';
        tabYoutube.setAttribute('aria-selected', 'true');
        tabUpload.setAttribute('aria-selected', 'false');

        dropZone.classList.add('hidden');
        youtubeInputZone.classList.remove('hidden');
        btnGenerate.disabled = true;
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
    dropZone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            fileInput.click();
        }
    });

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
            currentVideoLabel = selectedFile.name;
            btnGenerate.innerHTML = `${ICONS.spinner}<span>Uploading Video...</span>`;
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

            currentVideoLabel = ytUrl;
            btnGenerate.innerHTML = `${ICONS.spinner}<span>Downloading from YouTube...</span>`;
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
        btnGenerate.innerHTML = `<span>Generate Viral Clips</span>${ICONS.bolt}`;
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
            if (res.status === 404) {
                stopPolling();
                stopMessageRotation();
                showError('Processing job was interrupted (the server restarted or timed out). Please try uploading again.');
                return;
            }
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
        transcribing: ICONS.mic,
        analyzing: ICONS.cpu,
        cutting: ICONS.scissors,
        done: ICONS.check,
    };
    stepIcon.innerHTML = stepIcons[status.status] || ICONS.spinner;
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
        saveToHistory(data);
        renderResults(data);
        switchState('results');
    } catch (err) {
        showError(`Failed to load results: ${err.message}`);
    }
}

// ─── Browser History (Captions, Quotes & Clips) ──────────────────────────────

function getHistory() {
    try {
        return JSON.parse(localStorage.getItem(HISTORY_STORAGE_KEY) || '[]');
    } catch {
        return [];
    }
}

function updateHistoryBadge() {
    if (!historyCountBadge) return;
    const list = getHistory();
    if (list.length > 0) {
        historyCountBadge.textContent = String(list.length);
        historyCountBadge.classList.remove('hidden');
    } else {
        historyCountBadge.classList.add('hidden');
    }
}

function saveToHistory(data) {
    try {
        const list = getHistory().filter((item) => item.job_id !== data.job_id);
        list.unshift({
            job_id: data.job_id,
            video_name: currentVideoLabel || `Video (${formatDuration(data.video_duration)})`,
            created_at: new Date().toLocaleString(),
            video_duration: data.video_duration,
            processing_time: data.processing_time,
            total_clips: data.total_clips,
            clips: data.clips,
            transcript_text: data.transcript_text || '',
        });
        // Keep up to 30 past video runs in localStorage
        localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(list.slice(0, 30)));
        updateHistoryBadge();
    } catch (e) {
        console.warn('Could not save history:', e);
    }
}

function getClipTranscript(clip) {
    if (clip && typeof clip.transcript === 'string' && clip.transcript.trim()) {
        return clip.transcript.trim();
    }
    const raw = (clip && clip.description) ? String(clip.description).trim() : '';
    return raw.replace(/^["“]+|["”]+$/g, '').trim();
}

function renderHistoryModal() {
    if (!historyList) return;
    const list = getHistory();
    if (list.length === 0) {
        historyList.innerHTML = `
            <div class="text-center py-12 text-slate-500">
                <div class="mb-3">${ICONS.inbox}</div>
                <p class="text-sm font-semibold text-slate-300">No history yet</p>
                <p class="text-xs text-slate-400 mt-1 max-w-sm mx-auto">Process a video and all its clip transcripts, titles &amp; timestamps will be saved here automatically.</p>
            </div>
        `;
        return;
    }

    historyList.innerHTML = '';
    list.forEach((entry, idx) => {
        const itemEl = document.createElement('div');
        itemEl.className = 'bg-dark-950/90 border border-white/10 rounded-2xl p-4 space-y-3';

        const clipsHtml = (entry.clips || []).map((clip, clipIdx) => {
            const fileLabel = clip.filename || `clip_${String(clip.rank).padStart(2, '0')}_score${clip.virality_score}.mp4`;
            const clipTranscript = getClipTranscript(clip);
            return `
            <div class="bg-dark-800/90 border border-white/5 rounded-xl p-3.5 flex flex-col gap-2">
                <div class="flex flex-wrap items-start justify-between gap-2">
                    <div class="flex flex-wrap items-center gap-2">
                        <span class="px-2 py-0.5 bg-rose-500/20 text-rose-300 font-mono font-bold rounded-md text-[11px]">#${clip.rank} (${clip.virality_score}/100)</span>
                        <span class="inline-flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 font-mono rounded-md text-[11px]">
                            ${ICONS.fileVideo}
                            <span>${escapeHtml(fileLabel)}</span>
                        </span>
                        <span class="font-bold text-white text-xs">${escapeHtml(clip.title)}</span>
                    </div>
                    <span class="text-[11px] font-mono text-slate-400 whitespace-nowrap bg-dark-900 px-2 py-0.5 rounded-md border border-white/5">
                        ${formatDuration(clip.start_time)} - ${formatDuration(clip.end_time)} (${Number(clip.duration || 0).toFixed(1)}s)
                    </span>
                </div>
                <p class="text-[11px] text-slate-300 bg-dark-950/80 p-2.5 rounded-lg border border-white/5 leading-relaxed max-h-28 overflow-y-auto">
                    ${escapeHtml(clipTranscript)}
                </p>
                <div class="flex items-center justify-between pt-1 gap-2 flex-wrap">
                    <span class="text-[11px] text-slate-400 truncate flex-1 min-w-0">${escapeHtml(clip.reason)}</span>
                    <div class="flex items-center gap-1.5">
                        <button type="button" data-entry-idx="${idx}" data-clip-idx="${clipIdx}" class="cursor-pointer btn-hist-captions inline-flex items-center gap-1 px-2.5 py-1.5 bg-indigo-500/15 hover:bg-indigo-500/25 text-indigo-300 border border-indigo-500/30 rounded-lg text-[11px] font-semibold whitespace-nowrap transition-colors duration-200" title="Open 5-10 viral in-video captions">
                            ✨ Viral Captions
                        </button>
                        <button type="button" data-entry-idx="${idx}" data-clip-idx="${clipIdx}" class="cursor-pointer btn-hist-copy inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-500/15 hover:bg-rose-500/25 text-rose-300 border border-rose-500/30 rounded-lg text-[11px] font-semibold whitespace-nowrap transition-colors duration-200" title="Copy clip transcript">
                            ${ICONS.copy}
                            <span>Copy Transcript</span>
                        </button>
                    </div>
                </div>
            </div>
        `;
        }).join('');

        itemEl.innerHTML = `
            <div class="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-white/10">
                <div>
                    <h4 class="font-bold text-sm text-white">${escapeHtml(entry.video_name)}</h4>
                    <p class="text-[11px] font-mono text-slate-400 mt-0.5">${escapeHtml(entry.created_at)} • ${entry.total_clips} clips • Duration: ${formatDuration(entry.video_duration || 0)}</p>
                </div>
                <div class="flex items-center gap-2">
                    ${entry.transcript_text ? `
                        <button type="button" data-idx="${idx}" class="cursor-pointer btn-hist-copy-transcript inline-flex items-center gap-1.5 px-3 py-1.5 bg-dark-700 hover:bg-dark-600 border border-white/10 rounded-xl text-xs text-slate-200 font-semibold transition-colors duration-200" title="Copy full video transcript">
                            ${ICONS.fileText}
                            <span>Full Transcript</span>
                        </button>
                    ` : ''}
                    <button type="button" data-idx="${idx}" class="cursor-pointer btn-hist-open px-3.5 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-semibold transition-colors duration-200">
                        Open Clips View
                    </button>
                </div>
            </div>
            <div class="grid grid-cols-1 gap-2.5">
                ${clipsHtml}
            </div>
        `;

        historyList.appendChild(itemEl);
    });

    // Attach copy clip transcript listeners
    historyList.querySelectorAll('.btn-hist-copy').forEach((btn) => {
        btn.addEventListener('click', () => {
            const entryIdx = parseInt(btn.getAttribute('data-entry-idx'), 10);
            const clipIdx = parseInt(btn.getAttribute('data-clip-idx'), 10);
            const entry = list[entryIdx];
            const clip = entry && entry.clips ? entry.clips[clipIdx] : null;
            const text = getClipTranscript(clip);
            if (!text) {
                showToast('No transcript available for this clip.', 'error');
                return;
            }
            navigator.clipboard.writeText(text).then(() => {
                const origHtml = btn.innerHTML;
                btn.innerHTML = `${ICONS.check}<span>Copied</span>`;
                setTimeout(() => { btn.innerHTML = origHtml; }, 2000);
                showToast('Clip transcript copied to clipboard!', 'success');
            });
        });
    });

    // Attach copy transcript in history
    historyList.querySelectorAll('.btn-hist-copy-transcript').forEach((btn) => {
        btn.addEventListener('click', () => {
            const idx = parseInt(btn.getAttribute('data-idx'), 10);
            const entry = list[idx];
            if (entry && entry.transcript_text) {
                navigator.clipboard.writeText(entry.transcript_text).then(() => {
                    const origHtml = btn.innerHTML;
                    btn.innerHTML = `${ICONS.check}<span>Copied</span>`;
                    setTimeout(() => { btn.innerHTML = origHtml; }, 2000);
                    showToast('Full transcript copied to clipboard!', 'success');
                });
            }
        });
    });

    // Attach "Viral Captions" modal listeners in History
    historyList.querySelectorAll('.btn-hist-captions').forEach((btn) => {
        btn.addEventListener('click', () => {
            const entryIdx = parseInt(btn.getAttribute('data-entry-idx'), 10);
            const clipIdx = parseInt(btn.getAttribute('data-clip-idx'), 10);
            const entry = list[entryIdx];
            const clip = entry && entry.clips ? entry.clips[clipIdx] : null;
            if (!clip) return;
            openCaptionsModal(clip, () => {
                localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(list));
                renderHistoryModal();
            });
        });
    });

    // Attach "Open Clips View" listeners
    historyList.querySelectorAll('.btn-hist-open').forEach((btn) => {
        btn.addEventListener('click', () => {
            const idx = parseInt(btn.getAttribute('data-idx'), 10);
            const entry = list[idx];
            if (entry) {
                historyModal.classList.add('hidden');
                renderResults(entry);
                switchState('results');
            }
        });
    });
}

function renderResults(data) {
    currentResultsData = data;
    selectedClipsSet.clear();
    if (checkSelectAll) checkSelectAll.checked = false;
    updateSelectedCountUI();

    resultsSummary.textContent = `${data.total_clips} viral clips generated from ${formatDuration(data.video_duration)} video • Processed in ${data.processing_time}s`;
    clipsGrid.innerHTML = '';

    data.clips.forEach((clip) => {
        const card = createClipCard(clip, data.job_id);
        clipsGrid.appendChild(card);
    });
}

function handleCopyTranscript() {
    if (!currentResultsData) return;
    const transcript = currentResultsData.transcript_text;
    if (!transcript) {
        const fallback = (currentResultsData.clips || []).map(c => getClipTranscript(c)).filter(Boolean).join('\n\n');
        if (fallback) {
            navigator.clipboard.writeText(fallback).then(() => {
                showToast('Copied clips transcript to clipboard!', 'success');
            });
        } else {
            showToast('No transcript text available.', 'error');
        }
        return;
    }

    navigator.clipboard.writeText(transcript).then(() => {
        if (btnCopyTranscriptText) {
            const originalText = btnCopyTranscriptText.textContent;
            btnCopyTranscriptText.textContent = 'Copied!';
            setTimeout(() => { btnCopyTranscriptText.textContent = originalText; }, 2000);
        }
        showToast('Full transcript copied to clipboard!', 'success');
    }).catch(() => {
        showToast('Failed to copy to clipboard.', 'error');
    });
}

function handleToggleSelectAll() {
    if (!currentResultsData || !currentResultsData.clips) return;
    const isChecked = checkSelectAll.checked;
    selectedClipsSet.clear();

    const checkboxes = clipsGrid.querySelectorAll('.clip-select-check');
    checkboxes.forEach((cb) => {
        cb.checked = isChecked;
        const filename = cb.getAttribute('data-filename');
        const card = cb.closest('.clip-card');
        if (card) {
            card.classList.toggle('is-selected', isChecked);
        }
        if (isChecked && filename) {
            selectedClipsSet.add(filename);
        }
    });

    updateSelectedCountUI();
}

function handleClipCheckboxChange(filename, isChecked, cardEl) {
    if (isChecked) {
        selectedClipsSet.add(filename);
    } else {
        selectedClipsSet.delete(filename);
    }

    if (cardEl) {
        cardEl.classList.toggle('is-selected', isChecked);
    }

    const totalClips = currentResultsData ? currentResultsData.clips.length : 0;
    if (checkSelectAll) {
        checkSelectAll.checked = totalClips > 0 && selectedClipsSet.size === totalClips;
    }

    updateSelectedCountUI();
}

function updateSelectedCountUI() {
    const count = selectedClipsSet.size;
    if (selectedClipsCount) {
        selectedClipsCount.textContent = `${count} selected`;
    }
    if (btnDownloadSelected) {
        btnDownloadSelected.disabled = count === 0;
        btnDownloadSelected.innerHTML = `
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
            <span>Download Selected (${count})</span>
        `;
    }
}

async function downloadClipFile(clipUrl, filename, btnEl = null) {
    let origHtml = null;
    if (btnEl) {
        origHtml = btnEl.innerHTML;
        btnEl.disabled = true;
        btnEl.classList.add('opacity-70', 'pointer-events-none');
        btnEl.innerHTML = `${ICONS.spinner}<span>Starting...</span>`;
    }
    try {
        const downloadUrl = `${clipUrl}?download=true`;
        const headRes = await fetch(downloadUrl, { method: 'HEAD' });
        if (!headRes.ok) {
            if (headRes.status === 404) {
                throw new Error(`Clip file "${filename}" expired on the cloud server after a restart. Re-process the video to download the MP4.`);
            }
            throw new Error(`Download failed (HTTP ${headRes.status})`);
        }
        // Trigger immediate browser-native streaming download via an isolated hidden iframe
        // (starts immediately in the browser download bar without buffering 40MB in JS RAM,
        // and allows multiple simultaneous batch downloads without canceling each other!)
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = downloadUrl;
        document.body.appendChild(iframe);
        setTimeout(() => iframe.remove(), 60000);
        return true;
    } catch (err) {
        showToast(err.message || `Failed to download ${filename}`, 'error');
        return false;
    } finally {
        if (btnEl && origHtml !== null) {
            setTimeout(() => {
                btnEl.disabled = false;
                btnEl.classList.remove('opacity-70', 'pointer-events-none');
                btnEl.innerHTML = origHtml;
            }, 600);
        }
    }
}

async function handleDownloadSelected() {
    if (selectedClipsSet.size === 0 || !currentResultsData) return;
    const filenames = Array.from(selectedClipsSet);
    const jobId = currentResultsData.job_id;

    showToast(`Starting download for ${filenames.length} selected clip(s)...`, 'success');
    if (btnDownloadSelected) btnDownloadSelected.disabled = true;

    let successCount = 0;
    for (let i = 0; i < filenames.length; i++) {
        const fname = filenames[i];
        const clipUrl = `${API_BASE}/api/clips/${jobId}/${fname}`;
        const ok = await downloadClipFile(clipUrl, fname);
        if (ok) successCount++;
        if (i < filenames.length - 1) {
            await new Promise((r) => setTimeout(r, 350));
        }
    }

    updateSelectedCountUI();
}

function updateClipInHistory(jobId, updatedClip) {
    if (!jobId || !updatedClip) return;
    try {
        const list = getHistory();
        const entry = list.find((item) => item.job_id === jobId);
        if (entry && Array.isArray(entry.clips)) {
            const target = entry.clips.find(
                (c) => c.rank === updatedClip.rank || (updatedClip.filename && c.filename === updatedClip.filename)
            );
            if (target) {
                target.viral_captions = updatedClip.viral_captions;
                target.best_caption = updatedClip.best_caption;
                target.title = updatedClip.title;
                localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(list));
            }
        }
    } catch (e) {
        console.warn('Could not sync caption update to history:', e);
    }
}

function setCaptionsModalLoading(isLoading) {
    if (captionsLoadingIndicator) {
        captionsLoadingIndicator.classList.toggle('hidden', !isLoading);
    }
    if (btnSubmitCaptionFeedback) {
        btnSubmitCaptionFeedback.disabled = isLoading;
    }
    if (captionFeedbackPills) {
        captionFeedbackPills.querySelectorAll('.btn-caption-feedback').forEach((b) => {
            b.disabled = isLoading;
            b.classList.toggle('opacity-50', isLoading);
        });
    }
}

function renderCaptionsModalContent() {
    if (!activeCaptionContext || !activeCaptionContext.clip) return;
    const { clip } = activeCaptionContext;
    const captions = Array.isArray(clip.viral_captions) ? clip.viral_captions : [];
    const bestPick = clip.best_caption || captions[0] || clip.title || 'Generating viral captions...';

    if (captionBestPickText) {
        captionBestPickText.textContent = bestPick;
    }
    if (!captionsOptionsList) return;

    if (!captions.length) {
        captionsOptionsList.innerHTML = `
            <div class="p-4 rounded-xl bg-dark-950/70 border border-white/5 text-center text-slate-400">
                Generating 5–10 viral caption ideas...
            </div>
        `;
        return;
    }

    captionsOptionsList.innerHTML = '';
    captions.forEach((cap, i) => {
        const isBest = cap.trim().toLowerCase() === bestPick.trim().toLowerCase();
        const row = document.createElement('div');
        row.className = `flex items-center justify-between gap-3 p-3 rounded-xl border transition-colors ${
            isBest
                ? 'bg-rose-500/10 border-rose-500/35'
                : 'bg-dark-950/70 border-white/5 hover:border-white/15'
        }`;
        row.innerHTML = `
            <div class="flex items-start gap-2.5 min-w-0 flex-1">
                <span class="w-6 h-6 rounded-lg bg-dark-800 border border-white/10 text-[11px] font-mono font-bold text-slate-300 flex items-center justify-center shrink-0">${i + 1}</span>
                <p class="text-xs sm:text-[13px] font-semibold text-white leading-snug break-words pt-0.5">${escapeHtml(cap)}</p>
            </div>
            <button type="button" class="btn-copy-opt cursor-pointer shrink-0 inline-flex items-center gap-1 px-2.5 py-1.5 bg-dark-800 hover:bg-dark-700 border border-white/10 rounded-lg text-[11px] font-semibold text-slate-200 transition-colors">
                ${ICONS.copy}
                <span>Copy</span>
            </button>
        `;
        const copyBtn = row.querySelector('.btn-copy-opt');
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(cap).then(() => {
                const orig = copyBtn.innerHTML;
                copyBtn.innerHTML = `${ICONS.check}<span>Copied</span>`;
                setTimeout(() => { copyBtn.innerHTML = orig; }, 2000);
                showToast(`Caption #${i + 1} copied!`, 'success');
            });
        });
        captionsOptionsList.appendChild(row);
    });
}

async function requestViralCaptionsUpdate(feedback = null) {
    if (!activeCaptionContext || !activeCaptionContext.clip) return;
    const { clip, onUpdate } = activeCaptionContext;
    const transcript = getClipTranscript(clip) || clip.title || '';
    if (!transcript.trim()) {
        showToast('No clip transcript available to generate captions.', 'error');
        return;
    }

    setCaptionsModalLoading(true);
    try {
        const res = await fetch(`${API_BASE}/api/captions/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                transcript,
                feedback: feedback || null,
                previous_captions: clip.viral_captions || [],
                groq_api_key: settings.groqKey || null,
                gemini_api_key: settings.apiKey || null,
            }),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || `Failed (${res.status})`);
        }
        const data = await res.json();
        clip.viral_captions = Array.isArray(data.captions) ? data.captions : [];
        clip.best_caption = data.best_pick || clip.viral_captions[0] || clip.title;
        if (clip.best_caption) {
            clip.title = clip.best_caption;
        }
        renderCaptionsModalContent();
        if (typeof onUpdate === 'function') {
            onUpdate(clip);
        }
        if (feedback) {
            showToast(`Refined captions with: "${feedback}"`, 'success');
        }
    } catch (err) {
        showToast(`Caption generation failed: ${err.message}`, 'error');
    } finally {
        setCaptionsModalLoading(false);
    }
}

function openCaptionsModal(clip, onUpdateCallback) {
    if (!captionsModal || !clip) return;
    activeCaptionContext = { clip, onUpdate: onUpdateCallback };
    const filename = clip.filename || `clip_${String(clip.rank).padStart(2, '0')}_score${clip.virality_score}.mp4`;
    if (captionsModalSubtitle) {
        captionsModalSubtitle.textContent = `#${clip.rank} • ${filename} • ${formatDuration(clip.start_time)} - ${formatDuration(clip.end_time)}`;
    }
    if (inputCaptionFeedback) {
        inputCaptionFeedback.value = '';
    }
    renderCaptionsModalContent();
    captionsModal.classList.remove('hidden');

    if (!Array.isArray(clip.viral_captions) || clip.viral_captions.length === 0) {
        requestViralCaptionsUpdate(null);
    }
}

function createClipCard(clip, jobId) {
    const card = document.createElement('div');
    card.className = 'clip-card fade-in';

    const rankClass = clip.rank <= 3 ? `rank-${clip.rank}` : 'rank-default';
    const viralityClass = clip.virality_score >= 75 ? 'virality-high' : clip.virality_score >= 50 ? 'virality-mid' : 'virality-low';
    const clipUrl = `${API_BASE}/api/clips/${jobId}/${clip.filename}`;
    const filename = clip.filename || `clip_${String(clip.rank).padStart(2, '0')}_score${clip.virality_score}.mp4`;
    const clipTranscript = getClipTranscript(clip);
    const bestCaption = clip.best_caption || clip.title;
    const captionCount = Array.isArray(clip.viral_captions) && clip.viral_captions.length ? clip.viral_captions.length : '5–10';

    card.innerHTML = `
        <div class="relative bg-black">
            <!-- Checkbox selection badge -->
            <label class="absolute top-3 right-3 z-10 bg-dark-950/85 backdrop-blur-md border border-white/15 rounded-lg p-1.5 flex items-center justify-center cursor-pointer hover:border-rose-500 transition-colors shadow-lg" title="Select clip for batch download">
                <input type="checkbox" data-filename="${escapeHtml(filename)}" class="clip-select-check w-4 h-4 rounded text-rose-600 bg-dark-900 border-dark-500 cursor-pointer accent-rose-600">
            </label>
            <div class="rank-badge ${rankClass}">#${clip.rank}</div>
            <video controls preload="metadata" class="w-full">
                <source src="${clipUrl}" type="video/mp4">
                Your browser does not support video playback.
            </video>
        </div>
        <div class="p-4 sm:p-5 flex-1 flex flex-col">
            <div class="flex items-center justify-between gap-2 mb-2.5">
                <span class="inline-flex items-center gap-1.5 px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/25 font-mono rounded-md text-[11px] truncate">
                    ${ICONS.fileVideo}
                    <span class="truncate">${escapeHtml(filename)}</span>
                </span>
                <span class="text-[11px] font-mono text-slate-400 whitespace-nowrap bg-dark-900 px-2 py-0.5 rounded-md border border-white/5">
                    ${formatDuration(clip.start_time)} - ${formatDuration(clip.end_time)}
                </span>
            </div>

            <div class="flex items-start justify-between gap-2 mb-2.5">
                <h3 class="clip-card-title font-bold text-sm sm:text-base text-white flex-1 leading-snug">${escapeHtml(clip.title)}</h3>
            </div>

            <!-- Virality Score Meter -->
            <div class="flex items-center gap-2.5 mb-3">
                <div class="virality-bar flex-1">
                    <div class="virality-bar-fill ${viralityClass}" style="width: ${clip.virality_score}%"></div>
                </div>
                <span class="text-xs font-mono font-extrabold ${clip.virality_score >= 75 ? 'text-emerald-400' : clip.virality_score >= 50 ? 'text-amber-400' : 'text-rose-400'}">
                    ${clip.virality_score}/100
                </span>
            </div>

            <!-- Best Pick In-Video Caption Box -->
            <div class="mb-2.5 bg-gradient-to-br from-rose-500/10 via-dark-950/90 to-indigo-500/10 p-3 rounded-xl border border-rose-500/30">
                <div class="flex items-center justify-between gap-2 mb-1">
                    <span class="text-[10px] font-mono font-bold uppercase tracking-wider text-rose-400">★ Best Pick In-Video Caption</span>
                    <button type="button" class="btn-copy-best-card cursor-pointer inline-flex items-center gap-1 px-2 py-0.5 bg-dark-800 hover:bg-dark-700 border border-white/10 rounded-md text-[10px] font-semibold text-slate-200 transition-colors" title="Copy Best Pick caption">
                        ${ICONS.copy}
                        <span>Copy</span>
                    </button>
                </div>
                <p class="clip-best-caption text-xs font-bold text-white leading-snug mb-2">${escapeHtml(bestCaption)}</p>
                <button type="button" class="btn-open-captions cursor-pointer w-full py-1.5 px-2.5 bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/30 rounded-lg text-[11px] font-semibold text-indigo-300 transition-colors flex items-center justify-center gap-1.5">
                    <span>✨</span>
                    <span class="btn-open-captions-label">${captionCount} Viral Captions &amp; Feedback</span>
                </button>
            </div>

            <!-- Full Clip Transcript -->
            <div class="mb-2.5 bg-dark-950/70 p-2.5 rounded-xl border border-white/5">
                <span class="block text-[10px] font-mono uppercase tracking-wider text-slate-400 mb-1">Clip Transcript</span>
                <p class="text-[11px] text-slate-200 leading-relaxed max-h-24 overflow-y-auto pr-1">
                    ${escapeHtml(clipTranscript)}
                </p>
            </div>

            <!-- Lesson & Value -->
            <p class="text-xs text-slate-400 mb-4 bg-dark-900/70 p-2.5 rounded-xl border border-white/5 leading-relaxed flex-1">
                <span class="text-rose-400 font-semibold">Why It Works:</span> ${escapeHtml(clip.reason)}
            </p>

            <!-- Card Footer Actions -->
            <div class="flex items-center justify-between pt-2 border-t border-white/5 mt-auto">
                <span class="inline-flex items-center gap-1.5 text-[11px] font-mono font-medium px-2.5 py-1 bg-dark-900 border border-white/5 rounded-lg text-slate-400">
                    ${ICONS.clock}
                    <span>${clip.duration.toFixed(1)}s</span>
                </span>
                
                <div class="flex items-center gap-2">
                    <button type="button" class="cursor-pointer btn-copy-transcript inline-flex items-center gap-1.5 px-3 py-1.5 bg-dark-700 hover:bg-dark-600 border border-white/10 rounded-xl text-xs text-slate-200 font-semibold transition-colors duration-200" title="Copy clip transcript to clipboard">
                        ${ICONS.copy}
                        <span>Copy Transcript</span>
                    </button>
                    <a href="${clipUrl}?download=true" download="${filename}" class="btn-download">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                        </svg>
                        <span>Download</span>
                    </a>
                </div>
            </div>
        </div>
    `;

    const checkbox = card.querySelector('.clip-select-check');
    checkbox.checked = selectedClipsSet.has(filename);
    card.classList.toggle('is-selected', checkbox.checked);
    checkbox.addEventListener('change', () => {
        handleClipCheckboxChange(filename, checkbox.checked, card);
    });

    const cardTitleEl = card.querySelector('.clip-card-title');
    const cardBestEl = card.querySelector('.clip-best-caption');
    const cardBtnLabel = card.querySelector('.btn-open-captions-label');

    const btnCopyBestCard = card.querySelector('.btn-copy-best-card');
    btnCopyBestCard.addEventListener('click', () => {
        const text = (clip.best_caption || clip.title || '').trim();
        if (!text) return;
        navigator.clipboard.writeText(text).then(() => {
            const origHtml = btnCopyBestCard.innerHTML;
            btnCopyBestCard.innerHTML = `${ICONS.check}<span>Copied</span>`;
            setTimeout(() => { btnCopyBestCard.innerHTML = origHtml; }, 2000);
            showToast('Best Pick caption copied!', 'success');
        });
    });

    const btnOpenCaptions = card.querySelector('.btn-open-captions');
    btnOpenCaptions.addEventListener('click', () => {
        openCaptionsModal(clip, (updated) => {
            const nextBest = updated.best_caption || updated.title;
            if (cardTitleEl) cardTitleEl.textContent = nextBest;
            if (cardBestEl) cardBestEl.textContent = nextBest;
            if (cardBtnLabel && Array.isArray(updated.viral_captions)) {
                cardBtnLabel.textContent = `${updated.viral_captions.length} Viral Captions & Feedback`;
            }
            updateClipInHistory(jobId, updated);
        });
    });

    const btnCopy = card.querySelector('.btn-copy-transcript');
    btnCopy.addEventListener('click', () => {
        if (!clipTranscript) {
            showToast('No transcript available for this clip.', 'error');
            return;
        }
        navigator.clipboard.writeText(clipTranscript).then(() => {
            const origHtml = btnCopy.innerHTML;
            btnCopy.innerHTML = `${ICONS.check}<span>Copied</span>`;
            setTimeout(() => { btnCopy.innerHTML = origHtml; }, 2000);
            showToast('Clip transcript copied to clipboard!', 'success');
        }).catch(() => {
            showToast('Failed to copy transcript to clipboard.', 'error');
        });
    });

    const btnDownload = card.querySelector('.btn-download');
    if (btnDownload) {
        btnDownload.addEventListener('click', (e) => {
            e.preventDefault();
            downloadClipFile(clipUrl, filename, btnDownload);
        });
    }

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
    btnGenerate.innerHTML = `<span>Generate Viral Clips</span>${ICONS.bolt}`;
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
            ${type === 'error' ? ICONS.alertCircle : ICONS.checkCircle}
            <p class="text-xs font-medium text-slate-200 flex-1 leading-snug">${escapeHtml(message)}</p>
            <button type="button" aria-label="Dismiss notification" class="cursor-pointer text-slate-400 hover:text-white leading-none p-0.5" onclick="this.closest('.toast').remove()">
                <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        </div>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.25s ease-in forwards';
        setTimeout(() => toast.remove(), 250);
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
