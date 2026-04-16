/* ============================================================
   J.A.R.V.I.S  —  app.js
   ============================================================
   Flow:
     1. Page loads → SSE connect → fetch greeting → Gemini TTS speaks it
     2. User clicks mic → SpeechRecognition starts
     3. Transcript → POST /api/chat (Gemini 2.5 Flash) → text response
     4. Text response → POST /api/tts (Gemini 2.5 Flash TTS) → play audio
     5. Resume listening
   ============================================================ */

'use strict';

// ------------------------------------------------------------------ //
//  State                                                               //
// ------------------------------------------------------------------ //
const state = {
  listening:     false,
  thinking:      false,
  speaking:      false,
  history:       [],
  apiKey:        '',
  language:      'es-ES',
  ttsVoice:      'Charon',
  volTts:        80,
  volSong:       80,
  recognition:   null,
  currentAudio:  null,   // currently playing AudioBufferSourceNode
  audioCtx:      null,
};

// ------------------------------------------------------------------ //
//  DOM                                                                  //
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
  selTtsVoice:   $('sel-tts-voice'),
  rngVolTts:     $('rng-vol-tts'),
  lblVolTts:     $('lbl-vol-tts'),
  rngVolSong:    $('rng-vol-song'),
  lblVolSong:    $('lbl-vol-song'),
  btnSaludos:    $('btn-open-saludos'),
  btnClear:      $('btn-clear'),
  rngThreshold:  $('rng-threshold'),
  lblThreshold:  $('lbl-threshold'),
  lblSongPath:   $('lbl-song-path'),
};

// ------------------------------------------------------------------ //
//  Clock                                                               //
// ------------------------------------------------------------------ //
function tickClock() {
  const n = new Date();
  els.clock.textContent = n.toLocaleTimeString('en-US', { hour12: false });
}
setInterval(tickClock, 1000);
tickClock();

// ------------------------------------------------------------------ //
//  Status                                                              //
// ------------------------------------------------------------------ //
const STATUSES = {
  ready:     { dot: 'ready',     label: 'READY',      vis: 'STANDBY' },
  listening: { dot: 'listening', label: 'LISTENING',  vis: 'LISTENING' },
  thinking:  { dot: 'thinking',  label: 'PROCESSING', vis: 'PROCESSING...' },
  speaking:  { dot: 'speaking',  label: 'RESPONDING', vis: 'RESPONDING' },
  error:     { dot: 'error',     label: 'ERROR',      vis: 'ERROR' },
};

function setStatus(key) {
  const s = STATUSES[key] || STATUSES.ready;
  els.statusDot.className    = `status-dot ${s.dot}`;
  els.statusLabel.textContent = s.label;
  els.visState.textContent   = s.vis;
}

// ------------------------------------------------------------------ //
//  Background canvas                                                   //
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

  function buildDots() {
    dots.length = 0;
    const cols = Math.ceil(W / 40), rows = Math.ceil(H / 40);
    for (let r = 0; r < rows; r++)
      for (let c = 0; c < cols; c++) {
        if (Math.random() > 0.55) continue;
        dots.push({ x: c*40+Math.random()*20, y: r*40+Math.random()*20,
                    a: Math.random(), da: (Math.random()*0.004+0.001)*(Math.random()>.5?1:-1) });
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
      ctx.arc(d.x, d.y, 1, 0, Math.PI*2);
      ctx.fillStyle = `rgba(0,180,220,${d.a*0.6})`;
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
  const W = 440, H = 440, CX = W/2, CY = H/2;
  let analyser = null, dataArray = null, rotation = 0, idlePhase = 0;

  async function init() {
    try {
      if (!state.audioCtx) state.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      analyser = state.audioCtx.createAnalyser();
      analyser.fftSize = 256;
      dataArray = new Uint8Array(analyser.frequencyBinCount);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      state.audioCtx.createMediaStreamSource(stream).connect(analyser);
    } catch (e) {
      console.warn('[Jarvis] Mic access denied:', e);
    }
    draw();
  }

  function getRms() {
    if (!dataArray) return 0;
    analyser.getByteFrequencyData(dataArray);
    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) sum += dataArray[i]*dataArray[i];
    return Math.sqrt(sum / dataArray.length) / 255;
  }

  function draw() {
    requestAnimationFrame(draw);
    ctx.clearRect(0, 0, W, H);

    const rms      = getRms();
    const isActive = state.listening || state.speaking;
    idlePhase     += 0.012;

    // Outer rotating arcs
    ctx.save(); ctx.translate(CX,CY); ctx.rotate(rotation*0.4);
    for (let i = 0; i < 6; i++) {
      const a0 = (i/6)*Math.PI*2, a1 = a0+Math.PI/8;
      ctx.beginPath(); ctx.arc(0,0,195,a0,a1);
      ctx.strokeStyle='rgba(0,120,180,0.5)'; ctx.lineWidth=1.5; ctx.stroke();
    }
    ctx.restore();
    ctx.save(); ctx.translate(CX,CY); ctx.rotate(-rotation*0.6);
    for (let i = 0; i < 4; i++) {
      const a0 = (i/4)*Math.PI*2+0.3, a1 = a0+Math.PI/7;
      ctx.beginPath(); ctx.arc(0,0,203,a0,a1);
      ctx.strokeStyle=`rgba(0,200,255,${0.3+rms*0.5})`; ctx.lineWidth=2;
      ctx.shadowBlur=10; ctx.shadowColor='#00d4ff'; ctx.stroke();
    }
    ctx.restore(); ctx.shadowBlur=0;

    // Frequency bars in circle
    const bars = dataArray ? dataArray.length/2 : 64;
    const innerR = 90, maxBar = isActive ? 70 : 18;
    for (let i = 0; i < bars; i++) {
      const angle  = (i/bars)*Math.PI*2 - Math.PI/2 + rotation;
      const rawVal = dataArray ? dataArray[i]/255 : 0;
      const idleV  = (Math.sin(idlePhase+i*0.35)+1)*0.06;
      const val    = isActive ? rawVal : idleV;
      const barLen = 4 + val*maxBar;
      const x1=CX+Math.cos(angle)*innerR, y1=CY+Math.sin(angle)*innerR;
      const x2=CX+Math.cos(angle)*(innerR+barLen), y2=CY+Math.sin(angle)*(innerR+barLen);
      const hue = state.thinking ? 30+val*30 : state.speaking ? 270+val*30 : 185+val*20;
      ctx.strokeStyle=`hsla(${hue},100%,65%,${0.35+val*0.65})`;
      ctx.lineWidth=2; ctx.shadowBlur=val*12; ctx.shadowColor=`hsla(${hue},100%,65%,0.6)`;
      ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2); ctx.stroke();
    }
    ctx.shadowBlur=0;

    // Inner pulse ring
    const pulseR = 72 + (isActive ? rms*28 : Math.sin(idlePhase)*4+4);
    ctx.beginPath(); ctx.arc(CX,CY,pulseR,0,Math.PI*2);
    ctx.strokeStyle=`rgba(0,210,255,${isActive?0.55+rms*0.4:0.25})`;
    ctx.lineWidth=1.5; ctx.shadowBlur=isActive?20+rms*20:6; ctx.shadowColor='#00d4ff';
    ctx.stroke(); ctx.shadowBlur=0;

    // Static inner ring
    ctx.beginPath(); ctx.arc(CX,CY,80,0,Math.PI*2);
    ctx.strokeStyle='rgba(0,80,120,0.4)'; ctx.lineWidth=1; ctx.stroke();

    // Centre dot
    const dotR = isActive ? 7+rms*5 : 6;
    const g = ctx.createRadialGradient(CX,CY,0,CX,CY,dotR*2);
    g.addColorStop(0,'rgba(0,230,255,1)'); g.addColorStop(1,'rgba(0,100,200,0)');
    ctx.beginPath(); ctx.arc(CX,CY,dotR,0,Math.PI*2);
    ctx.fillStyle=g; ctx.shadowBlur=24; ctx.shadowColor='#00d4ff'; ctx.fill(); ctx.shadowBlur=0;

    rotation += 0.006;
  }

  return { init };
})();

// ------------------------------------------------------------------ //
//  Gemini TTS  (with browser SpeechSynthesis fallback)                //
// ------------------------------------------------------------------ //
async function speak(text, onEnd) {
  if (!text) { if (onEnd) onEnd(); return; }

  stopAudio();
  state.speaking = true;
  setStatus('speaking');
  els.btnMic.classList.remove('active');

  try {
    const ctrl  = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 40000);

    const res = await fetch('/api/tts', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ text, voice: state.ttsVoice }),
      signal:  ctrl.signal,
    });
    clearTimeout(timer);

    if (!res.ok) throw new Error(`TTS HTTP ${res.status}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    const { audio_b64 } = data;

    // Decode base64 → ArrayBuffer
    const raw = atob(audio_b64);
    const buf = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) buf[i] = raw.charCodeAt(i);

    if (!state.audioCtx) state.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const audioBuf = await state.audioCtx.decodeAudioData(buf.buffer);

    const src  = state.audioCtx.createBufferSource();
    const gain = state.audioCtx.createGain();
    gain.gain.value = state.volTts / 100;
    src.buffer = audioBuf;
    src.connect(gain);
    gain.connect(state.audioCtx.destination);

    state.currentAudio = src;
    src.onended = () => {
      state.speaking = false;
      state.currentAudio = null;
      if (!state.listening && !state.thinking) setStatus('ready');
      if (onEnd) onEnd();
    };
    src.start(0);

  } catch (err) {
    console.warn('[Jarvis] Gemini TTS failed — using browser fallback:', err.message);
    _speakFallback(text, onEnd);
  }
}

/** Browser SpeechSynthesis fallback — always works, no API key needed */
function _speakFallback(text, onEnd) {
  window.speechSynthesis.cancel();
  const utt   = new SpeechSynthesisUtterance(text);
  utt.lang    = state.language;
  utt.rate    = 0.95;
  utt.pitch   = 0.85;
  utt.volume  = state.volTts / 100;

  // Pick best available voice: prefer male, English, or match language
  const voices = window.speechSynthesis.getVoices();
  const pick = (
    voices.find(v => /guy|mark|david/i.test(v.name) && v.lang.startsWith('en')) ||
    voices.find(v => v.lang === state.language) ||
    voices.find(v => v.lang.startsWith(state.language.split('-')[0])) ||
    null
  );
  if (pick) utt.voice = pick;

  const finish = () => {
    state.speaking = false;
    state.currentAudio = null;
    if (!state.listening && !state.thinking) setStatus('ready');
    if (onEnd) onEnd();
  };
  utt.onend = finish;
  utt.onerror = finish;
  window.speechSynthesis.speak(utt);
}

function stopAudio() {
  if (state.currentAudio) {
    try { state.currentAudio.stop(); } catch (_) {}
    state.currentAudio = null;
  }
  state.speaking = false;
}

// ------------------------------------------------------------------ //
//  Greeting                                                            //
// ------------------------------------------------------------------ //
async function showGreeting() {
  try {
    const res = await fetch('/api/greeting');
    const { greeting } = await res.json();
    if (!greeting) return;

    els.greetText.textContent = greeting;
    els.greetOverlay.classList.add('visible');

    speak(greeting, () => {
      setTimeout(() => {
        els.greetOverlay.classList.remove('visible');
        setTimeout(startListening, 600);
      }, 800);
    });
  } catch (e) {
    console.warn('[Jarvis] Greeting fetch failed:', e);
  }
}

// ------------------------------------------------------------------ //
//  Speech Recognition (STT)                                           //
// ------------------------------------------------------------------ //
const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

function startListening() {
  if (!SpeechRec) {
    addMessage('error', 'SYSTEM', 'Speech recognition not available. Use Chrome or Edge.');
    return;
  }
  if (state.listening || state.thinking || state.speaking) return;

  const rec = new SpeechRec();
  state.recognition = rec;
  rec.continuous     = false;
  rec.interimResults = true;
  rec.lang           = state.language;

  rec.onstart = () => {
    state.listening = true;
    setStatus('listening');
    els.btnMic.classList.add('active');
    els.micHint.textContent   = 'Listening...';
    els.interimBar.textContent = '';
  };

  rec.onresult = e => {
    let interim = '', final = '';
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      if (e.results[i].isFinal) final += t; else interim += t;
    }
    els.interimBar.textContent = interim || final;
    if (final) handleTranscript(final.trim());
  };

  rec.onerror = e => {
    if (e.error === 'not-allowed')
      addMessage('error', 'SYSTEM', 'Microphone access denied. Allow it in browser settings.');
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

  try { rec.start(); } catch (e) { console.warn('[Jarvis] STT start failed:', e); }
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
  const placeholder = addMessage('jarvis', 'JARVIS', '...', true);

  try {
    const ctrl  = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 50000);

    const res = await fetch('/api/chat', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ message: text, history: state.history.slice(-12) }),
      signal:  ctrl.signal,
    });
    clearTimeout(timer);
    const data = await res.json();
    state.thinking = false;

    if (data.error) {
      placeholder.remove();
      const msg = data.error === 'no_api_key'
        ? 'No API key set. Open Settings and paste your Gemini key.'
        : `Gemini error: ${data.error}`;
      addMessage('error', 'SYSTEM', msg);
      speak(msg);
      return;
    }

    const reply = data.response;
    placeholder.querySelector('.msg-body').textContent = reply;
    placeholder.classList.remove('thinking-msg');
    state.history.push({ role: 'assistant', content: reply });

    speak(reply, () => setTimeout(startListening, 400));

  } catch (err) {
    state.thinking = false;
    placeholder.remove();
    const msg = err.name === 'AbortError' ? 'Request timed out. Check your internet connection.' : `Error: ${err.message}`;
    addMessage('error', 'SYSTEM', msg);
    setStatus('error');
    setTimeout(() => setStatus('ready'), 4000);
  }
}

function addMessage(type, role, text, isThinking = false) {
  const div = document.createElement('div');
  div.className = `msg ${type}${isThinking ? ' thinking-msg' : ''}`;
  div.innerHTML = `<span class="msg-role">${role}</span><span class="msg-body">${escHtml(text)}</span>`;
  els.chatLog.appendChild(div);
  els.chatLog.scrollTop = els.chatLog.scrollHeight;
  return div;
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ------------------------------------------------------------------ //
//  SSE — single instance                                               //
// ------------------------------------------------------------------ //
function connectSSE() {
  const es = new EventSource('/api/stream');
  es.onmessage = e => {
    if (e.data === 'activate') {
      window.focus();
      // Re-trigger greeting so the page feels fresh on each clap
      stopAudio();
      stopListening();
      state.history = [];
      els.chatLog.innerHTML = '';
      showGreeting();
    }
  };
  es.onerror = () => setTimeout(connectSSE, 3000);
}

// ------------------------------------------------------------------ //
//  Config                                                              //
// ------------------------------------------------------------------ //
async function loadConfig() {
  try {
    const res  = await fetch('/api/config');
    const data = await res.json();

    state.apiKey   = data.api_key   || '';
    state.language = data.language  || 'es-ES';
    state.ttsVoice = data.tts_voice || 'Charon';
    state.volTts   = data.vol_tts   ?? 80;
    state.volSong  = data.vol_song  ?? 80;

    if (data.api_key)     els.inpApiKey.value  = data.api_key;
    els.selLang.value     = state.language;
    els.selTtsVoice.value = state.ttsVoice;
    els.rngVolTts.value   = state.volTts;
    els.lblVolTts.textContent  = `${state.volTts}%`;
    els.rngVolSong.value  = state.volSong;
    els.lblVolSong.textContent = `${state.volSong}%`;

    if (els.lblSongPath) {
      els.lblSongPath.textContent = data.song_name
        ? `Current: ${data.song_name}` : 'No song configured.';
    }
  } catch (e) {
    console.warn('[Jarvis] Config load failed:', e);
  }
}

async function saveConfig(patch) {
  await fetch('/api/config', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(patch),
  });
}

// ------------------------------------------------------------------ //
//  Event listeners                                                     //
// ------------------------------------------------------------------ //

els.btnMic.addEventListener('click', () => {
  if (state.speaking) { stopAudio(); return; }
  state.listening ? stopListening() : startListening();
});

els.btnSettings.addEventListener('click', () => els.settingsPanel.classList.toggle('hidden'));
els.btnCloseSet.addEventListener('click', () => els.settingsPanel.classList.add('hidden'));

els.btnSaveKey.addEventListener('click', async () => {
  const key = els.inpApiKey.value.trim();
  if (!key) return;
  await saveConfig({ gemini_api_key: key });
  state.apiKey = key;
  els.btnSaveKey.textContent = 'SAVED!';
  setTimeout(() => els.btnSaveKey.textContent = 'SAVE', 2000);
});

els.selLang.addEventListener('change', () => {
  state.language = els.selLang.value;
  saveConfig({ language: state.language });
});

els.selTtsVoice.addEventListener('change', () => {
  state.ttsVoice = els.selTtsVoice.value;
  saveConfig({ tts_voice: state.ttsVoice });
});

els.rngVolTts.addEventListener('input', () => {
  state.volTts = parseInt(els.rngVolTts.value);
  els.lblVolTts.textContent = `${state.volTts}%`;
  saveConfig({ vol_tts: state.volTts });
});

els.rngVolSong.addEventListener('input', () => {
  state.volSong = parseInt(els.rngVolSong.value);
  els.lblVolSong.textContent = `${state.volSong}%`;
  saveConfig({ vol_song: state.volSong });
});

els.btnSaludos.addEventListener('click', () => fetch('/api/open-saludos', { method: 'POST' }));

els.btnClear.addEventListener('click', () => {
  els.chatLog.innerHTML = '';
  state.history = [];
});

els.rngThreshold.addEventListener('input', () => {
  els.lblThreshold.textContent = parseFloat(els.rngThreshold.value).toFixed(2);
});

document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.code === 'Space') { e.preventDefault(); els.btnMic.click(); }
});

// ------------------------------------------------------------------ //
//  Boot                                                                //
// ------------------------------------------------------------------ //
async function boot() {
  setStatus('ready');
  connectSSE();
  await Vis.init();
  await loadConfig();
  await showGreeting();
}

boot();
