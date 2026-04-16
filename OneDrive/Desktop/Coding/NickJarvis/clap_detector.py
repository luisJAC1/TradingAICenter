"""
clap_detector.py
Listens to the microphone 24/7 and fires a callback when two consecutive claps
are detected within ~800 ms with at least 150 ms between them.

Algorithm
---------
* Samples audio in ~30 ms windows via sounddevice.
* Maintains a rolling RMS baseline of the last ~600 ms of audio.
* A "clap" is declared when the current window's RMS exceeds both a hard floor
  (MIN_FLOOR) AND is SPIKE_RATIO times the rolling average -- this filters out
  sustained loud noise (music, speech) while catching sharp transients.
* State machine: IDLE -> FIRST_CLAP -> TRIGGERED, with a COOLDOWN after trigger.
"""

import threading
import time
from collections import deque

import numpy as np
import sounddevice as sd

# ----- tunable constants --------------------------------------------------- #
SAMPLE_RATE   = 44100
BLOCK_SIZE    = int(SAMPLE_RATE * 0.030)   # 30 ms per callback
HISTORY_BINS  = 20                          # rolling baseline window (~600 ms)
SPIKE_RATIO   = 4.0                         # must be 4x above rolling average
MIN_FLOOR     = 0.04                        # absolute minimum RMS to count
MIN_GAP_S     = 0.15                        # min seconds between two clap events
MAX_GAP_S     = 0.80                        # max seconds between two clap events
COOLDOWN_S    = 3.0                         # silence after successful trigger
# --------------------------------------------------------------------------- #


class ClapDetector:
    def __init__(self, callback):
        self._callback = callback
        self._running = False
        self._stream = None

        # test-calibration mode
        self._test_mode = False
        self._test_cb = None

        # detection state
        self._history = deque(maxlen=HISTORY_BINS)
        self._state = "IDLE"            # IDLE | FIRST_CLAP
        self._first_clap_t = 0.0
        self._last_trigger_t = 0.0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def set_test_mode(self, enabled, test_callback=None):
        self._test_mode = enabled
        self._test_cb = test_callback

    def start(self):
        """Block until stop() is called. Call from a daemon thread."""
        self._running = True
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=1,
            dtype="float32",
            callback=self._audio_callback,
        ):
            while self._running:
                time.sleep(0.1)

    def stop(self):
        self._running = False

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #

    def _audio_callback(self, indata, frames, time_info, status):
        audio = indata[:, 0]
        rms = float(np.sqrt(np.mean(audio ** 2)))

        with self._lock:
            # Compute rolling baseline BEFORE adding current bin
            baseline = float(np.mean(self._history)) if self._history else 0.0
            self._history.append(rms)

            now = time.time()

            # Cooldown guard
            if now - self._last_trigger_t < COOLDOWN_S:
                return

            is_spike = rms >= MIN_FLOOR and rms >= baseline * SPIKE_RATIO

            if not is_spike:
                # Reset if the first clap window has expired
                if self._state == "FIRST_CLAP" and (now - self._first_clap_t) > MAX_GAP_S:
                    self._state = "IDLE"
                return

            # --- spike detected ---
            if self._state == "IDLE":
                self._state = "FIRST_CLAP"
                self._first_clap_t = now

            elif self._state == "FIRST_CLAP":
                gap = now - self._first_clap_t
                if MIN_GAP_S <= gap <= MAX_GAP_S:
                    # Valid double-clap!
                    self._state = "IDLE"
                    self._last_trigger_t = now
                    self._fire()
                elif gap > MAX_GAP_S:
                    # Too slow — treat this spike as the new first clap
                    self._first_clap_t = now
                # else: gap < MIN_GAP_S => too fast, ignore (same clap echo)

    def _fire(self):
        if self._test_mode and self._test_cb:
            threading.Thread(target=self._test_cb, daemon=True).start()
        elif not self._test_mode:
            threading.Thread(target=self._callback, daemon=True).start()
