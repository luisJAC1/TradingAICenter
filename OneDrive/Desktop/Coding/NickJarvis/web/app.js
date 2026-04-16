/* ============================================================
   J.A.R.V.I.S  —  app.js
   ============================================================
   Flow:
     1. Page loads → fetch /api/greeting → speak it → show overlay
     2. User clicks mic (or auto-activates) → SpeechRecognition starts
     3. Transcript finalised → POST /api/chat → display + speak response
     4. Repeat from step 2
   ============================================================ */

'use strict';

// ------------------------------------------------------------------ //
//  State                                                               //
// ------------------------------------------------------------------ //
const state = {
  listening:    false,
  thinking:     false,
  speaking:     false,
  history:      [],          // [{role:'user'|'assistant', content:'...'}]
  apiKey:       '',
  language:     'es-ES',
  selectedVoice: null,
  recognition:  null,
  lastGreeting: '',
};

// ------------------------------------------------------------------ //
//  DOM references                                                      //
// ------------------------------------------------------------------ //
const $ = id => document.getElementById(id);
const els = {
  bgCanvas:      $('bg-canvas'),
  visCanvas:     $('vis-canvas'),
  greetOverlay:  $('greeting-overlay'),
  greetText:     $('greeting-text'),
  clock:         $('clock'),
  statusDot:     $('status-dot'),
  statusLabel:   $('status-label'),
  visState:      $('vis-state'),
  btnMic:        $('btn-mic'),
  micHint:       $('mic-hint'),
  interimBar:    $('interim-bar'),
  chatLog:       $('chat-log'),
  btnSettings:   $('btn-settings'),
  settingsPanel: $('settings-panel'),
  btnCloseSet:   $('btn-close-settings'),
  inpApiKey:     $('inp-apikey'),
  btnSaveKey:    $('btn-save-key'),
  selLang:       $('sel-lang'),
  selVoice:      $('sel-voice'),
  btnSaludos:    $('btn-open-saludos'),
  btnClear:      $('btn-clear'),
  rngThreshold:  $('rng-threshold'),
  lblThreshold:  $('lbl-threshold'),
};

// ------------------------------------------------------------------ //
//  Clock                                                               //
// ------------------------------------------------------------------ //
function tickClock() {
  const now = new Date();
  els.clock.textContent = now.toLocaleTimeString('en-US', { hour12: false });
}
setInterval(tickClock, 1000);
tickClock();

// ------------------------------------------------------------------ //
//  Status helpers                                                      //
// ------------------------------------------------------------------ //
const STATES = {
  ready:     { dot: 'ready',     label: 'READY',      vis: 'STANDBY' },
  listening: { dot: 'listening', label: 'LISTENING',  vis: 'LISTENING' },
  thinking:  { dot: 'thinking',  label: 'PROCESSING', vis: 'PROCESSING...' },
  speaking:  { dot: 'speaking',  label: 'RESPONDING', vis: 'RESPONDING' },
  error:     { dot: 'error',     label: 'ERROR',      vis: 'ERROR' },
};

function setStatus(key) {
  const s = STATES[key] || STATES.ready;
  els.statusDot.className   = `status-dot ${s.dot}`;
  els.statusLabel.textContent = s.label;
  els.visState.textContent  = s.vis;
}

// ------------------------------------------------------------------ //
//  Background canvas — animated hex-grid                              //
// ------------------------------------------------------------------ //
(function initBg() {
  const canvas = els.bgCanvas;
  const ctx = canvas.getContext('2d');
  let W, H;
  const dots = [];

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  window.addEventListener('resize', resize);
  resize();

  // Sparse dots
  function buildDots() {
    dots.length = 0;
    const cols = Math.ceil(W / 40);
    const rows = Math.ceil(H / 40);
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        if (Math.random() > 0.55) continue;
        dots.push({
          x: c * 40 + Math.random() * 20,
          y: r * 40 + Math.random() * 20,
          a: Math.random(),
          da: (Math.random() * 0.004 + 0.001) * (Math.random() > 0.5 ? 1 : -1),
        });
      }
    }
  }
  buildDots();
  window.addEventListener('resize', buildDots);

  function drawBg() {
    ctx.clearRect(0, 0, W, H);
    for (const d of dots) {
      d.a += d.da;
      if (d.a > 1 || d.a < 0) d.da *= -1;
      ctx.beginPath();
      ctx.arc(d.x, d.y, 1, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0, 180, 220, ${d.a * 0.6})`;
      ctx.fill();
    }
    requestAnimationFrame(drawBg);
  }
  drawBg();
})();

// ------------------------------------------------------------------ //
//  Visualizer                                                          //
// ------------------------------------------------------------------ //
const Vis = (() => {
  const canvas = els.visCanvas;
  const ctx    = canvas.getContext('2d');
  const W = 440, H = 440, CX = W / 2, CY = H / 2;

  let audioCtx = null, analyser = null, dataArray = null;
  let rotation = 0;
  let idlePhase = 0;

  async function init() {
    try {
      audioCtx  = new (window.AudioContext || window.webkitAudioContext)();
      analyser  = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      dataArray = new Uint8Array(analyser.frequencyBinCount);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      const src = audioCtx.createMediaStreamSource(stream);
      src.connect(analyser);
    } catch (e) {
      console.warn('[Jarvis] Mic access denied or unavailable:', e);
    }
    draw();
  }

  function getRms() {
    if (!dataArray) return 0;
    analyser.getByteFrequencyData(dataArray);
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) sum += dataArray[i] * dataArray[i];
    return Math.sqrt(sum / dataArray.length) / 255;
  }

  function draw() {
    requestAnimationFrame(draw);
    ctx.clearRect(0, 0, W, H);

    const rms      = getRms();
    const isActive = state.listening || state.speaking;
    idlePhase     += 0.012;

    // ---- Outer decorative ring (always rotating) ----
    const outerR = 195;
    ctx.save();
    ctx.translate(CX, CY);
    ctx.rotate(rotation * 0.4);
    for (let i = 0; i < 6; i++) {
      const a0 = (i / 6) * Math.PI * 2;
      const a1 = a0 + Math.PI / 8;
      ctx.beginPath();
      ctx.arc(0, 0, outerR, a0, a1);
      ctx.strokeStyle = 'rgba(0, 120, 180, 0.5)';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }
    ctx.restore();

    ctx.save();
    ctx.translate(CX, CY);
    ctx.rotate(-rotation * 0.6);
    for (let i = 0; i < 4; i++) {
      const a0 = (i / 4) * Math.PI * 2 + 0.3;
      const a1 = a0 + Math.PI / 7;
      ctx.beginPath();
      ctx.arc(0, 0, outerR + 8, a0, a1);
      ctx.strokeStyle = `rgba(0, 200, 255, ${0.3 + rms * 0.5})`;
      ctx.lineWidth = 2;
      ctx.shadowBlur = 10;
      ctx.shadowColor = '#00d4ff';
      ctx.stroke();
    }
    ctx.restore();
    ctx.shadowBlur = 0;

    // ---- Frequency bars arranged in circle ----
    const bars    = dataArray ? dataArray.length / 2 : 64;
    const innerR  = 90;
    const maxBar  = isActive ? 70 : 18;

    for (let i = 0; i < bars; i++) {
      const angle   = (i / bars) * Math.PI * 2 - Math.PI / 2 + rotation;
      const rawVal  = dataArray ? dataArray[i] / 255 : 0;
      const idleVal = (Math.sin(idlePhase + i * 0.35) + 1) * 0.06;
      const val     = isActive ? rawVal : idleVal;
      const barLen  = 4 + val * maxBar;

      const x1 = CX + Math.cos(angle) * innerR;
      const y1 = CY + Math.sin(angle) * innerR;
      const x2 = CX + Math.cos(angle) * (innerR + barLen);
      const y2 = CY + Math.sin(angle) * (innerR + barLen);

      const alpha = 0.35 + val * 0.65;
      const hue   = state.thinking ? 30 + val * 30
                  : state.speaking ? 270 + val * 30
                  : 185 + val * 20;

      ctx.strokeStyle = `hsla(${hue}, 100%, 65%, ${alpha})`;
      ctx.lineWidth   = 2;
      ctx.shadowBlur  = val * 12;
      ctx.shadowColor = `hsla(${hue}, 100%, 65%, 0.6)`;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }
    ctx.shadowBlur = 0;

    // ---- Inner pulse ring ----
    const pulseR = 72 + (isActive ? rms * 28 : Math.sin(idlePhase) * 4 + 4);
    ctx.beginPath();
    ctx.arc(CX, CY, pulseR, 0, Math.PI * 2);
    const ringAlpha = isActive ? 0.55 + rms * 0.4 : 0.25;
    ctx.strokeStyle = `rgba(0, 210, 255, ${ringAlpha})`;
    ctx.lineWidth   = 1.5;
    ctx.shadowBlur  = isActive ? 20 + rms * 20 : 6;
    ctx.shadowColor = '#00d4ff';
    ctx.stroke();
    ctx.shadowBlur = 0;

    // ---- Static inner structural ring ----
    ctx.beginPath();
    ctx.arc(CX, CY, 80, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(0, 80, 120, 0.4)';
    ctx.lineWidth = 1;
    ctx.stroke();

    // ---- Centre dot ----
    const dotR = isActive ? 7 + rms * 5 : 6;
    const grad = ctx.createRadialGradient(CX, CY, 0, CX, CY, dotR * 2);
    grad.addColorStop(0, 'rgba(0, 230, 255, 1)');
    grad.addColorStop(1, 'rgba(0, 100, 200, 0)');
    ctx.beginPath();
    ctx.arc(CX, CY, dotR, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.shadowBlur = 24;
    ctx.shadowColor = '#00d4ff';
    ctx.fill();
    ctx.shadowBlur = 0;

    rotation += 0.006;
  }

  return { init };
})();

// ------------------------------------------------------------------ //
//  Speech Synthesis (TTS)                                              //
// ------------------------------------------------------------------ //
function populateVoices() {
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return;
  els.selVoice.innerHTML = '<option value="">Default system voice</option>';
  voices.forEach((v, i) => {
    const opt = document.createElement('option');
    opt.value = i;
    opt.textContent = `${v.name} (${v.lang})`;
    els.selVoice.appendChild(opt);
  });
}
window.speechSynthesis.onvoiceschanged = populateVoices;
populateVoices();

function speak(text, onEnd) {
  window.speechSynthesis.cancel();
  const utt = new SpeechSynthesisUtterance(text);
  utt.lang  = state.language;

  const voices = window.speechSynthesis.getVoices();
  const idx    = parseInt(els.selVoice.value);
  if (!isNaN(idx) && voices[idx]) utt.voice = voices[idx];

  utt.rate   = 1.05;
  utt.pitch  = 0.95;
  utt.volume = 1;

  state.speaking = true;
  setStatus('speaking');
  els.btnMic.classList.remove('active');

  utt.onend = utt.onerror = () => {
    state.speaking = false;
    if (!state.listening && !state.thinking) setStatus('ready');
    if (onEnd) onEnd();
  };

  window.speechSynthesis.speak(utt);
}

// ------------------------------------------------------------------ //
//  Greeting system                                                     //
// ------------------------------------------------------------------ //
async function showGreeting() {
  try {
    const res = await fetch('/api/greeting');
    const { greeting } = await res.json();
    if (!greeting) return;

    els.greetText.textContent   = greeting;
    els.greetOverlay.classList.add('visible');

    speak(greeting, () => {
      setTimeout(() => {
        els.greetOverlay.classList.remove('visible');
        // Auto-start listening after greeting
        setTimeout(startListening, 600);
      }, 800);
    });
  } catch (e) {
    console.warn('[Jarvis] Could not fetch greeting:', e);
  }
}

// ------------------------------------------------------------------ //
//  Speech Recognition (STT)                                           //
// ------------------------------------------------------------------ //
const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

function startListening() {
  if (!SpeechRec) {
    addMessage('error', 'SYSTEM', 'Speech recognition not available in this browser. Please use Chrome or Edge.');
    return;
  }
  if (state.listening || state.thinking || state.speaking) return;

  const rec = new SpeechRec();
  state.recognition = rec;

  rec.continuous      = false;
  rec.interimResults  = true;
  rec.lang            = state.language;
  rec.maxAlternatives = 1;

  rec.onstart = () => {
    state.listening = true;
    setStatus('listening');
    els.btnMic.classList.add('active');
    els.micHint.textContent = 'Listening...';
    els.interimBar.textContent = '';
  };

  rec.onresult = e => {
    let interim = '', final = '';
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      if (e.results[i].isFinal) final += t;
      else interim += t;
    }
    els.interimBar.textContent = interim || final;
    if (final) handleTranscript(final.trim());
  };

  rec.onerror = e => {
    console.warn('[Jarvis] STT error:', e.error);
    if (e.error === 'not-allowed') {
      addMessage('error', 'SYSTEM', 'Microphone access denied. Please allow mic access and refresh.');
    }
    stopListening();
  };

  rec.onend = () => {
    state.listening = false;
    els.btnMic.classList.remove('active');
    if (!state.thinking && !state.speaking) {
      setStatus('ready');
      els.micHint.textContent = 'Click to speak';
    }
  };

  try { rec.start(); }
  catch (e) { console.warn('[Jarvis] Could not start recognition:', e); }
}

function stopListening() {
  state.listening = false;
  els.btnMic.classList.remove('active');
  els.micHint.textContent = 'Click to speak';
  if (state.recognition) {
    try { state.recognition.stop(); } catch (_) {}
    state.recognition = null;
  }
  if (!state.thinking && !state.speaking) setStatus('ready');
}

// ------------------------------------------------------------------ //
//  Chat                                                                //
// ------------------------------------------------------------------ //
async function handleTranscript(text) {
  if (!text) return;
  stopListening();
  els.interimBar.textContent = '';

  addMessage('user', 'YOU', text);
  state.history.push({ role: 'user', content: text });

  state.thinking = true;
  setStatus('thinking');
  const thinkMsg = addMessage('jarvis', 'JARVIS', '...', true);

  try {
    const res = await fetch('/api/chat', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ message: text, history: state.history.slice(-10) }),
    });
    const data = await res.json();

    state.thinking = false;

    if (data.error) {
      thinkMsg.remove();
      if (data.error === 'no_api_key') {
        const msg = 'No Gemini API key configured. Open Settings and paste your key.';
        addMessage('error', 'SYSTEM', msg);
        speak(msg);
      } else {
        addMessage('error', 'SYSTEM', `Error: ${data.error}`);
      }
      return;
    }

    const reply = data.response;
    thinkMsg.querySelector('.msg-body').textContent = reply;
    thinkMsg.classList.remove('thinking-msg');
    state.history.push({ role: 'assistant', content: reply });

    speak(reply, () => {
      // Resume listening after response
      setTimeout(startListening, 400);
    });

  } catch (e) {
    state.thinking = false;
    thinkMsg.remove();
    addMessage('error', 'SYSTEM', `Network error: ${e.message}`);
    setStatus('error');
    setTimeout(() => setStatus('ready'), 3000);
  }
}

function addMessage(type, role, text, isThinking = false) {
  const div = document.createElement('div');
  div.className = `msg ${type}${isThinking ? ' thinking-msg' : ''}`;
  div.innerHTML = `
    <span class="msg-role">${role}</span>
    <span class="msg-body">${escHtml(text)}</span>
  `;
  els.chatLog.appendChild(div);
  els.chatLog.scrollTop = els.chatLog.scrollHeight;
  return div;
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ------------------------------------------------------------------ //
//  Config loading                                                      //
// ------------------------------------------------------------------ //
async function loadConfig() {
  try {
    const res  = await fetch('/api/config');
    const data = await res.json();
    state.apiKey   = data.api_key  || '';
    state.language = data.language || 'es-ES';

    if (data.api_key) els.inpApiKey.value = data.api_key;
    els.selLang.value = state.language;

    const songLabel = document.getElementById('lbl-song-path');
    if (songLabel) {
      songLabel.textContent = data.song_name
        ? `Current song: ${data.song_name}`
        : 'No song configured.';
    }
  } catch (e) {
    console.warn('[Jarvis] Could not load config:', e);
  }
}

// ------------------------------------------------------------------ //
//  Event listeners                                                     //
// ------------------------------------------------------------------ //

// Mic button
els.btnMic.addEventListener('click', () => {
  if (state.speaking) {
    window.speechSynthesis.cancel();
    state.speaking = false;
  }
  if (state.listening) {
    stopListening();
  } else {
    startListening();
  }
});

// Settings panel
els.btnSettings.addEventListener('click', () => {
  els.settingsPanel.classList.toggle('hidden');
});
els.btnCloseSet.addEventListener('click', () => {
  els.settingsPanel.classList.add('hidden');
});

// Save API key
els.btnSaveKey.addEventListener('click', async () => {
  const key = els.inpApiKey.value.trim();
  if (!key) return;
  await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ gemini_api_key: key }),
  });
  state.apiKey = key;
  els.btnSaveKey.textContent = 'SAVED!';
  setTimeout(() => els.btnSaveKey.textContent = 'SAVE', 2000);
});

// Language change
els.selLang.addEventListener('change', async () => {
  state.language = els.selLang.value;
  await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ language: state.language }),
  });
});

// Open saludos.txt
els.btnSaludos.addEventListener('click', () => {
  fetch('/api/open-saludos', { method: 'POST' });
});

// Clear chat
els.btnClear.addEventListener('click', () => {
  els.chatLog.innerHTML = '';
  state.history = [];
});

// Threshold slider
els.rngThreshold.addEventListener('input', () => {
  els.lblThreshold.textContent = parseFloat(els.rngThreshold.value).toFixed(2);
});

// Keyboard shortcut: Space = toggle mic (when not in a text field)
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.code === 'Space') {
    e.preventDefault();
    els.btnMic.click();
  }
});

// ------------------------------------------------------------------ //
//  Boot                                                                //
// ------------------------------------------------------------------ //
async function boot() {
  setStatus('ready');
  await Vis.init();
  await loadConfig();
  await showGreeting();
}

boot();
