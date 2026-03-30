import os
os.environ["JACK_NO_START_SERVER"] = "1"
os.environ["JACK_NO_AUDIO_RESERVATION"] = "1"
# Suppress ALSA/Jack/Pulse stderr noise during PyAudio init
import ctypes
_alsa_lib = ctypes.cdll.LoadLibrary("libasound.so.2")
_alsa_err_handler = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
def _null_error_handler(filename, line, function, err, fmt):
    pass
_c_null_handler = _alsa_err_handler(_null_error_handler)
_alsa_lib.snd_lib_error_set_handler(_c_null_handler)

import pyaudio
import json
import sys
import subprocess
import threading
import time
import re
import random
import struct
import math
import audioop
import numpy as np
from datetime import datetime, date, timedelta
from pathlib import Path
import urllib.request
import base64
from dateutil import tz
from vosk import Model, KaldiRecognizer, SetLogLevel
from sage_lights import lights
SetLogLevel(-1)

# ── Max volume at startup ────────────────────────────────────────────────────
# Volume set after device detection below

# ── Credentials ──────────────────────────────────────────────────────────────
with open(os.path.expanduser("~/.sage_credentials")) as f:
    for line in f:
        key, val = line.strip().split("=", 1)
        os.environ[key] = val

# ── Claude API (optional voice chat) ──────────────────────────────────────────
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
claude_client = None
if CLAUDE_API_KEY:
    try:
        import anthropic
        claude_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        print("Claude voice chat enabled", flush=True)
    except Exception as e:
        print(f"Claude API not available: {e}", flush=True)
else:
    print("No Anthropic API key — Claude voice chat disabled", flush=True)

# Claude conversation history (per session, resets on reboot)
claude_history = []
CLAUDE_MAX_HISTORY = 20  # keep last 20 exchanges

def ask_claude(question):
    """Send a question to Claude and return the response text."""
    if not claude_client:
        return "Claude is not configured. Add an Anthropic API key to enable voice chat."
    try:
        claude_history.append({"role": "user", "content": question})
        # Trim history if too long
        if len(claude_history) > CLAUDE_MAX_HISTORY * 2:
            claude_history[:] = claude_history[-CLAUDE_MAX_HISTORY * 2:]
        response = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            system="You are Claude, a friendly voice assistant in a family kitchen. Keep responses short and conversational — they will be spoken aloud. The family includes Britta, Ian, Bailey, and Adelle. There's also a dog named Ellie. You share the device with Sage, the local assistant who handles timers, weather, and reminders. You handle everything else — questions, conversation, homework help, recipes, advice. Be warm, helpful, and concise.",
            messages=claude_history
        )
        answer = response.content[0].text
        claude_history.append({"role": "assistant", "content": answer})
        return answer
    except Exception as e:
        print(f"Claude API error: {e}", flush=True)
        send_notification(f"Claude API error: {e}", title="Claude Error", force=True)
        # Signal auth failure so the conversation loop can exit immediately
        if "401" in str(e) or "authentication" in str(e).lower():
            return "__AUTH_FAILED__"
        return "Sorry, I couldn't reach Claude right now."

# ── Personal config (presets, reminders) ─────────────────────────────────────
SAGE_CONFIG = {"preset_timers": {}, "scheduled_reminders": [], "date_reminders": []}
config_path = Path.home() / ".sage_config.json"
if config_path.exists():
    with open(config_path) as f:
        SAGE_CONFIG.update(json.load(f))
    print(f"Loaded {len(SAGE_CONFIG['preset_timers'])} preset timers, "
          f"{len(SAGE_CONFIG['scheduled_reminders'])} scheduled reminders, "
          f"{len(SAGE_CONFIG.get('date_reminders', []))} date reminders")
else:
    print("No ~/.sage_config.json found — running without presets/reminders")

def save_config():
    """Persist SAGE_CONFIG to disk."""
    try:
        with open(config_path, "w") as f:
            json.dump(SAGE_CONFIG, f, indent=2)
    except Exception as e:
        print(f"Failed to save config: {e}", flush=True)

# ── Push notifications (ntfy) ────────────────────────────────────────────────
NTFY_URL = SAGE_CONFIG.get("ntfy_url", "http://localhost:8080")
NTFY_TOPIC = SAGE_CONFIG.get("ntfy_topic", "sage-kitchen")
NTFY_USER = SAGE_CONFIG.get("ntfy_user", "")
NTFY_PASS = SAGE_CONFIG.get("ntfy_pass", "")

def send_notification(message, title="Sage", force=False):
    """Send a push notification via ntfy."""
    try:
        # Skip notifications during bedtime unless forced (security alerts always go through)
        if bedtime_mode.is_set() and not force and title not in ["Security Alert"]:
            print(f"Notification suppressed (bedtime): {message}", flush=True)
            return
        data = message.encode("utf-8")
        req = urllib.request.Request(f"{NTFY_URL}/{NTFY_TOPIC}", data=data, method="POST")
        req.add_header("Title", title)
        if NTFY_USER and NTFY_PASS:
            creds = base64.b64encode(f"{NTFY_USER}:{NTFY_PASS}".encode()).decode()
            req.add_header("Authorization", f"Basic {creds}")
        urllib.request.urlopen(req, timeout=5)
        print(f"Notification sent: {message}")
        sys.stdout.flush()
    except Exception as e:
        print(f"Notification failed: {e}")
        sys.stdout.flush()

# ── Google Calendar via iCal ─────────────────────────────────────────────────
ICAL_URL = SAGE_CONFIG.get("ical_url", "")
CALENDAR_NOTIFY_MINUTES = SAGE_CONFIG.get("calendar_notify_minutes_before", 15)

def fetch_todays_events():
    """Fetch today's events from Google Calendar iCal feed."""
    if not ICAL_URL:
        return []
    try:
        from icalendar import Calendar
        data = urllib.request.urlopen(ICAL_URL, timeout=15).read()
        cal = Calendar.from_ical(data)
        local_tz = tz.tzlocal()
        today = date.today()
        events = []
        for component in cal.walk():
            if component.name != "VEVENT":
                continue
            summary = str(component.get("summary", ""))
            dtstart = component.get("dtstart").dt
            # Skip all-day events (they're date objects, not datetime)
            if not isinstance(dtstart, datetime):
                continue
            event_dt = dtstart.astimezone(local_tz)
            if event_dt.date() == today:
                events.append({"summary": summary, "time": event_dt})
        events.sort(key=lambda e: e["time"])
        print(f"Calendar: found {len(events)} events today")
        sys.stdout.flush()
        return events
    except Exception as e:
        print(f"Calendar fetch error: {e}")
        sys.stdout.flush()
        return []

def calendar_scheduler():
    """Check calendar twice a day (5 AM and 5 PM) and send ntfy notifications."""
    notified_today = set()
    last_fetch_hour = None
    todays_events = []

    while True:
        now = datetime.now(tz.tzlocal())
        today = now.date()
        hour = now.hour

        # Fetch events at startup, at 5 AM, and at 5 PM (catches afternoon additions)
        fetch_hours = {5, 17}
        should_fetch = (last_fetch_hour is None or
                        (hour in fetch_hours and last_fetch_hour != hour))
        if should_fetch:
            todays_events = fetch_todays_events()
            last_fetch_hour = hour
            # Clear notified set at 5 AM (new day)
            if hour == 5:
                notified_today.clear()

        # Check if any event is coming up
        for event in todays_events:
            event_key = f"{event['summary']}_{event['time'].isoformat()}"
            if event_key in notified_today:
                continue
            minutes_until = (event["time"] - now).total_seconds() / 60
            if 0 < minutes_until <= CALENDAR_NOTIFY_MINUTES:
                event_time_str = event["time"].strftime("%I:%M %p").lstrip("0")
                message = f"{event['summary']} at {event_time_str}"
                send_notification(message, title="Calendar")
                notified_today.add(event_key)
                print(f"Calendar notification: {message}")
                sys.stdout.flush()

        time.sleep(60)  # check every minute

# Start calendar scheduler thread
if ICAL_URL:
    calendar_thread = threading.Thread(target=calendar_scheduler, daemon=True)
    calendar_thread.start()
    print("Calendar integration active")
else:
    print("No iCal URL configured — calendar disabled")
sys.stdout.flush()

# ── Spotify ──────────────────────────────────────────────────────────────────
sp = None
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    _sp_id = os.environ.get("SPOTIPY_CLIENT_ID", "")
    _sp_secret = os.environ.get("SPOTIPY_CLIENT_SECRET", "")
    if _sp_id and _sp_secret:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=_sp_id,
            client_secret=_sp_secret,
            redirect_uri="http://127.0.0.1:8888/callback",
            scope="user-modify-playback-state user-read-playback-state user-library-read",
            cache_path=os.path.expanduser("~/spotipy.cache"),
            open_browser=False
        ))
        # Test the connection
        sp.current_user()
        print("Spotify connected", flush=True)
    else:
        print("Spotify credentials not set — Spotify disabled", flush=True)
except Exception as e:
    print(f"Spotify not available: {e}", flush=True)
    sp = None

# ── Text-to-speech ───────────────────────────────────────────────────────────
PIPER_DIR = "/home/sage/piper"
VOICE_MODEL        = "/home/sage/piper-voices/en_GB-northern_english_male-medium.onnx"  # Sage — Northern British male
CLAUDE_VOICE_MODEL = "/home/sage/piper-voices/en_US-lessac-medium.onnx"  # Claude
# ── Auto-detect USB audio devices ─────────────────────────────────────────────
def find_usb_devices():
    """Find USB speaker and mic card numbers dynamically."""
    import re as _re
    speaker_card = None
    mic_card = None
    # Find playback devices
    result = subprocess.run(["aplay", "-l"], capture_output=True, text=True)
    for line in result.stdout.split("\n"):
        if "UACDemo" in line or "USB Audio" in line:
            m = _re.search(r"card (\d+)", line)
            if m:
                speaker_card = m.group(1)
    # Find capture devices
    result = subprocess.run(["arecord", "-l"], capture_output=True, text=True)
    for line in result.stdout.split("\n"):
        if "USB PnP" in line or "USB Audio" in line:
            m = _re.search(r"card (\d+)", line)
            if m:
                mic_card = m.group(1)
    return speaker_card, mic_card

_speaker_card, _mic_card = find_usb_devices()
if _speaker_card:
    SPEAKER_DEVICE = f"plughw:{_speaker_card},0"
    print(f"Speaker: card {_speaker_card} ({SPEAKER_DEVICE})")
else:
    SPEAKER_DEVICE = "plughw:4,0"
    print("WARNING: USB speaker not found, using default plughw:4,0")
if _mic_card:
    MIC_HW_DEVICE = f"plughw:{_mic_card},0"
    print(f"Mic: card {_mic_card} ({MIC_HW_DEVICE})")
else:
    MIC_HW_DEVICE = "plughw:3,0"
    print("WARNING: USB mic not found, using default plughw:3,0")
sys.stdout.flush()

# ── PulseAudio routing (preferred over raw ALSA when available) ───────────────
import os as _os
_pulse_socket = f"/run/user/{_os.getuid()}/pulse/native"
if _os.path.exists(_pulse_socket):
    SPEAKER_DEVICE = "pulse"
    MIC_HW_DEVICE = "pulse"
    _os.environ.setdefault("PULSE_SERVER", f"unix:{_pulse_socket}")
    print(f"PulseAudio active — routing audio through pulse (AEC enabled)", flush=True)
else:
    print("PulseAudio not available — using ALSA direct", flush=True)

# ── Max volume at startup (using detected card numbers) ──────────────────────
if _speaker_card:
    # Try Jabra-style controls first (numid=3=switch, numid=4=volume, numid=6=mic)
    # then fall back to old speaker controls (numid=2=switch, numid=3=volume)
    r = subprocess.run(["amixer", "-c", _speaker_card, "cset", "numid=4", "11"],
                       capture_output=True)
    if r.returncode != 0:
        subprocess.run(["amixer", "-c", _speaker_card, "cset", "numid=2", "on"],
                       capture_output=True)
        subprocess.run(["amixer", "-c", _speaker_card, "cset", "numid=3", "147,147"],
                       capture_output=True)
    else:
        subprocess.run(["amixer", "-c", _speaker_card, "cset", "numid=3", "on"],
                       capture_output=True)
if _mic_card:
    # Jabra mic volume
    subprocess.run(["amixer", "-c", _mic_card, "cset", "numid=6", "7"],
                   capture_output=True)

# ── Faster Whisper (for command recognition) ─────────────────────────────────
from faster_whisper import WhisperModel
print("Loading Whisper model...", flush=True)
whisper_model = WhisperModel("base.en", device="cpu", compute_type="int8")
print("Whisper model ready", flush=True)

def speak(text, voice=None):
    if voice is None:
        voice = VOICE_MODEL
    env = {
        "LD_PRELOAD": f"{PIPER_DIR}/libpiper_phonemize.so.1.2.0",
        "LD_LIBRARY_PATH": PIPER_DIR,
        "ESPEAK_DATA_PATH": f"{PIPER_DIR}/espeak-ng-data",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
    }
    piper = subprocess.Popen(
        ["piper", "--model", voice, "--output_raw"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env
    )
    aplay = subprocess.Popen(
        ["aplay", "-r", "22050", "-f", "S16_LE", "-c", "1", "-D", SPEAKER_DEVICE],
        stdin=piper.stdout
    )
    piper.stdin.write(text.encode())
    piper.stdin.close()
    piper.wait()
    aplay.wait()

def speak_claude(text):
    """Speak using Claude's distinct voice."""
    speak(text, voice=CLAUDE_VOICE_MODEL)

# ── Chime (gentle prompt sound) ───────────────────────────────────────────────
def _play_raw(samples, sr=22050):
    """Send raw 16-bit mono samples to the speaker."""
    raw = b"".join(samples)
    ap = subprocess.Popen(
        ["aplay", "-r", str(sr), "-f", "S16_LE", "-c", "1", "-D", SPEAKER_DEVICE],
        stdin=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    ap.stdin.write(raw)
    ap.stdin.close()
    ap.wait()

def _chime_note(freq, dur, sr=22050, amp=18000):
    """Warm marimba-like note: gentle attack, smooth decay, clean tone."""
    n = int(sr * dur)
    samples = []
    for i in range(n):
        t = i / n
        # Soft attack over first 6%, then smooth exponential decay
        envelope = math.sin(math.pi * min(t * 16, 1.0)) * math.exp(-3.5 * t)
        tone = (math.sin(2 * math.pi * freq * i / sr)
              + math.sin(2 * math.pi * freq * 2 * i / sr) * 0.07)
        value = int(amp * envelope * tone)
        samples.append(struct.pack("<h", max(-32767, min(32767, value))))
    return samples

def _crystal_note(freq, dur, sr=22050, amp=17000):
    """Crystalline harp/wind-chime note: soft attack then gentle ring-out with subtle overtones."""
    n = int(sr * dur)
    samples = []
    for i in range(n):
        t = i / n
        # Quick soft attack (~1/8 of duration), then smooth exponential ring-out
        envelope = math.sin(math.pi * min(t * 8, 1.0)) * math.exp(-2.8 * t)
        tone = (math.sin(2 * math.pi * freq * i / sr)
              + math.sin(2 * math.pi * freq * 2 * i / sr) * 0.10
              + math.sin(2 * math.pi * freq * 3 * i / sr) * 0.04)
        value = int(amp * envelope * tone)
        samples.append(struct.pack("<h", max(-32767, min(32767, value))))
    return samples

def _gap(ms, sr=22050):
    return [struct.pack("<h", 0)] * int(sr * ms / 1000)

# ── Sage chimes: warm descending arpeggio (marimba-like) ─────────────────────

def play_chime():
    """Sage wake chime — C5 → E5 → G5 ascending major arpeggio."""
    s = []
    s += _chime_note(523, 0.22)   # C5 — start low
    s += _gap(20)
    s += _chime_note(659, 0.22)   # E5
    s += _gap(20)
    s += _chime_note(784, 0.28)   # G5 — land high (open, attentive)
    _play_raw(s)

def _buzz_note(freq, dur, sr=22050, amp=10000):
    """Harsh buzzy note — square-wave-like odd harmonics, for error feedback."""
    n = int(sr * dur)
    samples = []
    for i in range(n):
        t = i / n
        envelope = math.exp(-2.5 * t)
        tone = (math.sin(2 * math.pi * freq * i / sr)
              + math.sin(2 * math.pi * freq * 3 * i / sr) * 0.33
              + math.sin(2 * math.pi * freq * 5 * i / sr) * 0.20
              + math.sin(2 * math.pi * freq * 7 * i / sr) * 0.14)
        value = int(amp * envelope * tone)
        samples.append(struct.pack("<h", max(-32767, min(32767, value))))
    return samples

def play_error_chime():
    """Didn't-catch-that chime — low dissonant descending buzz, clearly wrong."""
    s = []
    s += _buzz_note(415, 0.20)   # Ab4
    s += _gap(10)
    s += _buzz_note(294, 0.20)   # D4 — tritone drop
    s += _gap(10)
    s += _buzz_note(196, 0.28)   # G3 — drop low and die out
    _play_raw(s)

def play_confirm_chime():
    """Sage got-it chime — three quick descending pips: A5 → F5 → D5."""
    s = []
    s += _chime_note(880, 0.09)   # A5 — bright top pip
    s += _gap(12)
    s += _chime_note(698, 0.09)   # F5
    s += _gap(12)
    s += _chime_note(587, 0.11)   # D5 — settle on this one
    _play_raw(s)

# ── Claude chimes: crystalline ascending arpeggio ────────────────────────────

def play_claude_chime():
    """Claude listening chime — C5 → E5 → A5 major-sixth arpeggio, harp-like."""
    s = []
    s += _crystal_note(523, 0.28)   # C5
    s += _gap(22)
    s += _crystal_note(659, 0.28)   # E5
    s += _gap(22)
    s += _crystal_note(880, 0.34)   # A5  (lets the top note ring out)
    _play_raw(s)

def play_thinking_chime():
    """Claude thinking chime — meandering 6-note wander, no clear direction."""
    s = []
    s += _crystal_note(659, 0.16)   # E5 — start middle
    s += _gap(12)
    s += _crystal_note(784, 0.14)   # G5 — step up
    s += _gap(12)
    s += _crystal_note(880, 0.14)   # A5 — drift higher
    s += _gap(12)
    s += _crystal_note(698, 0.14)   # F5 — drop back
    s += _gap(12)
    s += _crystal_note(740, 0.14)   # F#5 — slight rise
    s += _gap(12)
    s += _crystal_note(659, 0.22)   # E5 — settle back where we started
    _play_raw(s)

# ── Whisper command listener ─────────────────────────────────────────────────
def whisper_listen(max_seconds=6.5, spoken_prompt=None, silent=False, sensitivity=1.8):
    """Play chime, record with silence detection, then transcribe with Faster Whisper."""
    import wave
    wav_path = "/tmp/sage_cmd.wav"
    sample_rate = 16000
    chunk_size = 1600  # 0.1 seconds

    # Pause Spotify so mic can hear the user
    whisper_listen._spotify_was_playing = False
    try:
        if sp:
            _pb = sp.current_playback()
            if _pb and _pb.get("is_playing"):
                whisper_listen._spotify_was_playing = True
                sp.pause_playback()
    except Exception:
        pass

    time.sleep(0.2)
    if spoken_prompt:
        if not silent:
            play_chime()
        speak(spoken_prompt)
    elif not silent:
        play_chime()
    lights.set_state("listening")

    # Start raw recording
    rec_proc = subprocess.Popen(
        ["arecord", "-D", MIC_HW_DEVICE, "-f", "S16_LE", "-r", str(sample_rate),
         "-c", "1", "-t", "raw"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )

    frames = []
    speech_started = False
    silence_count = 0
    min_recording = 20   # at least 2 seconds before allowing cutoff
    silence_cutoff = 30  # 3 seconds of silence after speech = done
    chunk_count = 0
    max_chunks = int(max_seconds * sample_rate / chunk_size)

    # Calibrate baseline from first 0.5 seconds
    baseline_energies = []
    for _ in range(5):
        data = rec_proc.stdout.read(chunk_size * 2)
        if not data:
            break
        frames.append(data)
        baseline_energies.append(audioop.rms(data, 2))
        chunk_count += 1

    baseline = sum(baseline_energies) / max(len(baseline_energies), 1)
    threshold = baseline * sensitivity  # adjustable speech detection sensitivity

    for _ in range(max_chunks - chunk_count):
        data = rec_proc.stdout.read(chunk_size * 2)
        if not data:
            break
        frames.append(data)
        chunk_count += 1
        rms = audioop.rms(data, 2)

        if rms > threshold:
            speech_started = True
            silence_count = 0
        elif speech_started:
            silence_count += 1
            if chunk_count >= min_recording and silence_count >= silence_cutoff:
                break

    rec_proc.terminate()
    rec_proc.wait()

    if not frames:
        return ""

    # If nothing crossed the speech threshold, don't transcribe — prevents
    # Whisper from hallucinating text out of TV/fan background noise
    if not speech_started:
        print("No speech detected (below threshold), skipping transcription", flush=True)
        return ""

    # Write WAV
    audio_data = b"".join(frames)
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)

    duration = len(audio_data) / (sample_rate * 2)
    print(f"Recorded {duration:.1f}s (baseline: {baseline:.0f}, threshold: {threshold:.0f})", flush=True)

    lights.set_state("processing")
    # Start transcription in background so chime plays in parallel
    import time as _t
    _transcription = [None]
    def _do_transcribe():
        t0 = _t.time()
        segs, _ = whisper_model.transcribe(wav_path, beam_size=1, language="en",
            initial_prompt="Hey Sage, get Claude, ask Claude, talk to Claude, set a timer, what's the weather, remind me, what time is it")
        _transcription[0] = (" ".join([s.text.strip() for s in segs]).strip(), _t.time() - t0)
    _tx_thread = threading.Thread(target=_do_transcribe, daemon=True)
    _tx_thread.start()
    play_confirm_chime()          # plays while Whisper works
    _tx_thread.join()             # wait for transcription to finish
    try:
        text, elapsed = _transcription[0]
        print(f"Whisper heard: {text} ({elapsed:.1f}s)")
        sys.stdout.flush()
    except Exception as e:
        print(f"Whisper error: {e}")
        sys.stdout.flush()
        text = ""
    return text.strip()

# ── Alarm tone ───────────────────────────────────────────────────────────────
def build_alarm_pattern():
    """Build one cycle of the alarm pattern — three sharp A5 beeps."""
    sr = 22050
    samples = []
    notes = [(880, 0.18), (880, 0.18), (880, 0.25)]   # A5 × 3, urgent
    for freq, dur in notes:
        n_samples = int(sr * dur)
        for n in range(n_samples):
            t = n / n_samples
            envelope = math.exp(-5.0 * t)              # sharp attack, fast decay
            value = int(32000 * envelope * math.sin(2 * math.pi * freq * n / sr))
            samples.append(struct.pack("<h", max(-32767, min(32767, value))))
        for n in range(int(sr * 0.06)):                # short gap between beeps
            samples.append(struct.pack("<h", 0))
    # Pause between repeats
    for n in range(int(sr * 0.45)):
        samples.append(struct.pack("<h", 0))
    return b"".join(samples)

ALARM_PATTERN = build_alarm_pattern()

alarm_playing = threading.Event()  # set when alarm is active
mic_release = threading.Event()    # set when alarm needs the mic released
mic_released = threading.Event()   # set when main loop has released the mic

def whisper_check_stop():
    """Record 3 seconds via arecord, transcribe with faster-whisper, return True if dismissal heard."""
    import wave
    wav_path = "/tmp/sage_stop.wav"
    rec = subprocess.run(
        ["arecord", "-D", MIC_HW_DEVICE, "-f", "S16_LE", "-r", "16000",
         "-c", "1", "-d", "3", wav_path],
        capture_output=True
    )
    if rec.returncode != 0:
        print(f"whisper_check_stop arecord failed: {rec.stderr.decode(errors='replace').strip()}", flush=True)
        return False
    try:
        segments, _ = whisper_model.transcribe(wav_path, beam_size=1, language="en")
        text = " ".join([s.text.strip() for s in segments]).strip().lower()
    except Exception as e:
        print(f"whisper_check_stop error: {e}", flush=True)
        return False
    print(f"Alarm stop check: '{text}'", flush=True)
    dismiss_words = ["stop", "cancel", "dismiss", "silence", "quiet", "enough",
                     "turn off", "shut up", "done", "okay done", "all done"]
    return any(w in text for w in dismiss_words)

def play_alarm_loop(stop_event):
    """Play alarm chimes, pausing periodically to listen for dismissal via Whisper."""
    try:
        while stop_event.is_set():
            # Play chime for a few cycles (~6 seconds worth)
            ap = subprocess.Popen(
                ["aplay", "-r", "22050", "-f", "S16_LE", "-c", "1", "-D", SPEAKER_DEVICE],
                stdin=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
            try:
                for _ in range(4):
                    if not stop_event.is_set():
                        break
                    ap.stdin.write(ALARM_PATTERN)
                ap.stdin.close()
                ap.wait()
            except BrokenPipeError:
                print(f"OWW error: {_oww_err}", flush=True)
            if not stop_event.is_set():
                break
            # Request mic from main loop
            mic_released.clear()
            mic_release.set()
            mic_released.wait(timeout=3)
            if not stop_event.is_set():
                mic_release.clear()
                break
            # Listen for dismissal word — brief cue so user knows window is open
            speak("Say stop to silence.")
            if whisper_check_stop():
                stop_event.clear()
                mic_release.clear()
                break
            # Give mic back to main loop and repeat
            mic_release.clear()
    finally:
        alarm_playing.clear()
        mic_release.clear()

# ── Timers ───────────────────────────────────────────────────────────────────
# Each timer: {"label": str, "seconds": int, "start_time": float,
#              "alarming": threading.Event, "thread": Thread}
active_timers = []
active_reminders = []  # voice-triggered reminders: {"label": str, "cancel": threading.Event, "thread": Thread}
timers_lock = threading.Lock()

def run_timer(timer):
    """Wait for the timer duration, then alarm until dismissed."""
    time.sleep(timer["seconds"])
    timer["alarming"].set()
    alarm_playing.set()  # Block main loop BEFORE speaking
    print(f"ALARM: {timer['label']} is done!")
    sys.stdout.flush()
    # Speak the announcement once, then chime with Whisper-based dismiss
    if "timer" in timer["label"]:
        speak(f"Your {timer['label']} is done!")
    else:
        speak(f"Your {timer['label']} are done!")
    # Alarm chime loop — pauses to listen for "stop" via Whisper
    play_alarm_loop(timer["alarming"])
    # Clean up after dismissed
    with timers_lock:
        if timer in active_timers:
            active_timers.remove(timer)
    play_confirm_chime()  # descending chime = timer dismissed
    lights.set_state("idle")

def start_timer(label, seconds):
    # Subtract processing overhead so timer fires at the right wall-clock time
    elapsed = time.time() - getattr(start_timer, "_cmd_time", time.time())
    seconds = max(1, seconds - int(elapsed))
    timer = {
        "label": label,
        "seconds": seconds,
        "start_time": time.time(),
        "alarming": threading.Event(),
    }
    t = threading.Thread(target=run_timer, args=(timer,), daemon=True)
    timer["thread"] = t
    with timers_lock:
        active_timers.append(timer)
    t.start()
    lights.set_state("timer_counting")

def dismiss_alarms():
    """Stop all currently ringing alarms."""
    dismissed = False
    with timers_lock:
        for timer in active_timers[:]:
            if timer["alarming"].is_set():
                timer["alarming"].clear()
                active_timers.remove(timer)
                dismissed = True
    # Also dismiss any scheduled reminder alarm
    if reminder_alarming.is_set():
        reminder_alarming.clear()
        dismissed = True
    return dismissed

def cancel_timers():
    """Cancel all pending (non-alarming) timers."""
    cancelled = []
    with timers_lock:
        for timer in active_timers[:]:
            if not timer["alarming"].is_set():
                # Timer is still counting down — stop its thread by clearing and removing
                timer["alarming"].clear()
                timer["seconds"] = 0  # won't help sleeping thread, but mark it
                cancelled.append(timer["label"])
                active_timers.remove(timer)
    return cancelled

def get_remaining_timers():
    """Return list of (label, seconds_remaining) for active non-alarming timers."""
    remaining = []
    now = time.time()
    with timers_lock:
        for timer in active_timers:
            if not timer["alarming"].is_set():
                elapsed = now - timer["start_time"]
                left = max(0, timer["seconds"] - elapsed)
                remaining.append((timer["label"], int(left)))
    return remaining

def format_time(seconds):
    """Format seconds into a spoken string like '5 minutes and 30 seconds'."""
    if seconds <= 0:
        return "less than a second"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if hours > 0:
        parts.append(f"{hours} hour" + ("s" if hours != 1 else ""))
    if minutes > 0:
        parts.append(f"{minutes} minute" + ("s" if minutes != 1 else ""))
    if secs > 0 and hours == 0:  # skip seconds if hours-scale timer
        parts.append(f"{secs} second" + ("s" if secs != 1 else ""))
    if not parts:
        return "less than a second"
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]

def parse_duration(text):
    """Parse spoken duration like 'one hour and 30 minutes' into seconds."""
    # Handle word numbers
    word_to_num = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
        "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
        "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
        "fifty": 50, "sixty": 60, "ninety": 90,
        "a": 1, "an": 1,
    }
    # Replace word numbers with digits
    working = text.lower()
    # Handle compound numbers like "twenty five"
    for word, num in sorted(word_to_num.items(), key=lambda x: -len(x[0])):
        working = working.replace(word, str(num))

    total = 0
    # Find all number + unit pairs
    for match in re.finditer(r"(\d+)\s*(second|minute|hour)", working):
        amount = int(match.group(1))
        unit = match.group(2)
        if unit.startswith("second"):
            total += amount
        elif unit.startswith("minute"):
            total += amount * 60
        elif unit.startswith("hour"):
            total += amount * 3600
    return total

# ── Scheduled reminders ──────────────────────────────────────────────────────
# Each reminder: {"message": str, "hour": int, "minute": int,
#                 "days": list of weekday ints (0=Mon, 6=Sun),
#                 "skip_months": list of month ints (1=Jan, 12=Dec),
#                 "alarming": threading.Event}
scheduled_reminders = []
reminder_alarming = threading.Event()  # global flag for any reminder going off

# ── Bedtime mode ─────────────────────────────────────────────────────────────
bedtime_mode = threading.Event()  # when set, Sage is in do-not-disturb mode

BEDTIME_VOLUME   = 9    # amixer numid=4 value at night
DAYTIME_VOLUME   = 11   # amixer numid=4 value during the day (full)
BEDTIME_RMS_GATE = 600  # rms_peak required to wake at night (more deliberate speech needed)
DAYTIME_RMS_GATE = 110  # rms_peak required to wake during the day
OWW_RMS_GATE     = DAYTIME_RMS_GATE  # current active gate — adjusted at bedtime/wake

def _set_speaker_volume(level):
    """Set Jabra speaker volume via amixer (0–11)."""
    try:
        subprocess.run(["amixer", "-c", str(_speaker_card), "cset", "numid=4", str(level)],
                       capture_output=True, timeout=5)
        print(f"Speaker volume set to {level}", flush=True)
    except Exception as e:
        print(f"Volume set error: {e}", flush=True)

def enter_bedtime():
    """Enter bedtime mode — lower volume, raise wake gate, silence alarms, dim lights."""
    global OWW_RMS_GATE
    bedtime_mode.set()
    dismiss_alarms()
    _set_speaker_volume(BEDTIME_VOLUME)
    OWW_RMS_GATE = BEDTIME_RMS_GATE
    lights.set_state("off")
    print("Bedtime mode ON", flush=True)

def exit_bedtime():
    """Exit bedtime mode — restore volume, lower wake gate, resume normal operation."""
    global OWW_RMS_GATE
    bedtime_mode.clear()
    _set_speaker_volume(DAYTIME_VOLUME)
    OWW_RMS_GATE = DAYTIME_RMS_GATE
    lights.set_state("idle")
    print("Bedtime mode OFF", flush=True)

def bedtime_scheduler():
    """Auto-enable bedtime at 10pm weekdays, 11:30pm weekends. Auto-wake at 6am."""
    while True:
        now = datetime.now()
        weekday = now.weekday()  # 0=Mon, 6=Sun
        hour = now.hour
        minute = now.minute

        is_weekend = weekday in [4, 5]  # Fri/Sat night

        # Auto-bedtime
        if not bedtime_mode.is_set():
            if is_weekend and hour == 22 and minute == 30:
                speak("It's 10:30. Goodnight everyone.")
                enter_bedtime()
            elif not is_weekend and hour == 21 and minute == 30:
                speak("It's 9:30. Goodnight everyone.")
                enter_bedtime()

        # Auto-wake: 6:30am weekdays, 8:30am weekends
        if bedtime_mode.is_set():
            wake_up = False
            if is_weekend and hour == 8 and minute == 30:
                wake_up = True
            elif not is_weekend and hour == 6 and minute == 30:
                wake_up = True
            if wake_up:
                exit_bedtime()
                speak("Good morning.")
                # Weather briefing
                try:
                    weather_text = get_weather()
                    if weather_text:
                        speak(weather_text)
                except Exception as _oww_err:
                    print(f"OWW error: {_oww_err}", flush=True)
                # Calendar briefing
                try:
                    events = fetch_todays_events()
                    if not events:
                        speak("Nothing on the calendar today.")
                    elif len(events) == 1:
                        e = events[0]
                        time_str = e["time"].strftime("%I:%M %p").lstrip("0")
                        speak(f"{e[summary]} at {time_str}.")
                    else:
                        speak(f"You have {len(events)} things on the calendar today.")
                        for e in events:
                            time_str = e["time"].strftime("%I:%M %p").lstrip("0")
                            speak(f"{e[summary]} at {time_str}.")
                except Exception as _oww_err:
                    print(f"OWW error: {_oww_err}", flush=True)

        time.sleep(30)

bedtime_thread = threading.Thread(target=bedtime_scheduler, daemon=True)
bedtime_thread.start()

def reminder_scheduler():
    """Background thread that checks every 30 seconds if a reminder should fire."""
    fired_today = {}  # track which reminders already fired: key=(message, date)
    while True:
        now = datetime.now()
        today_key = now.strftime("%Y-%m-%d")
        for reminder in SAGE_CONFIG["scheduled_reminders"]:
            fire_key = (reminder["message"], today_key)
            if fire_key in fired_today:
                continue
            if now.weekday() not in reminder["days"]:
                continue
            if now.month in reminder.get("skip_months", []):
                continue
            if now.hour == reminder["hour"] and now.minute == reminder["minute"]:
                fired_today[fire_key] = True
                print(f"REMINDER: {reminder['message']}")
                sys.stdout.flush()
                send_notification(reminder["message"], title="Reminder")
                # Speak once and send notification — no repeating alarm
                speak(reminder["message"])
        # Clean old entries from fired_today
        for key in list(fired_today.keys()):
            if key[1] != today_key:
                del fired_today[key]

        # ── Date-based reminders (one-time, fire at 9am on target date) ──
        date_reminders = SAGE_CONFIG.get("date_reminders", [])
        to_remove = []
        for i, dr in enumerate(date_reminders):
            fire_key = ("date_" + dr["message"], dr["date"])
            if fire_key in fired_today:
                continue
            if today_key == dr["date"] and now.hour == 9 and now.minute < 1:
                fired_today[fire_key] = True
                msg = f"Reminder: {dr['message']}"
                print(f"DATE REMINDER: {msg}", flush=True)
                send_notification(msg, title="Reminder")
                speak(msg)
                to_remove.append(i)
        if to_remove:
            for i in sorted(to_remove, reverse=True):
                date_reminders.pop(i)
            SAGE_CONFIG["date_reminders"] = date_reminders
            save_config()

        time.sleep(30)

# ── Security monitor ──────────────────────────────────────────────────────────
def security_monitor():
    """Monitor for failed SSH attempts and firewall blocks. Alert on suspicious activity."""
    from collections import defaultdict
    import re as _re

    failed_attempts = defaultdict(list)  # ip -> [timestamps]
    alert_threshold = 3  # failed attempts before alerting
    alert_window = 300   # seconds (5 minutes)
    alerted_ips = {}     # ip -> last alert time (avoid spamming)
    alert_cooldown = 600 # don't re-alert same IP for 10 minutes

    # Use journalctl to follow SSH logs in real time
    proc = subprocess.Popen(
        ["journalctl", "-u", "ssh", "-f", "--no-pager", "-o", "short"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    )

    for line in proc.stdout:
        now = time.time()
        # Failed password or invalid user
        if "Failed password" in line or "Invalid user" in line:
            # Extract IP
            ip_match = _re.search(r"from\s+([\da-fA-F.:]+)", line)
            if ip_match:
                ip = ip_match.group(1)
                failed_attempts[ip].append(now)
                # Clean old attempts outside window
                failed_attempts[ip] = [t for t in failed_attempts[ip] if now - t < alert_window]
                count = len(failed_attempts[ip])
                print(f"Security: failed login from {ip} ({count} attempts)", flush=True)

                if count >= alert_threshold:
                    # Check cooldown
                    if ip not in alerted_ips or now - alerted_ips[ip] > alert_cooldown:
                        alerted_ips[ip] = now
                        message = f"Warning: {count} failed login attempts from {ip}"
                        print(f"SECURITY ALERT: {message}", flush=True)
                        send_notification(message, title="Security Alert", force=True)
                        # Speak the alert
                        lights.set_state("security")
                        speak(f"Security alert. Someone is trying to access the system. {count} failed attempts detected.")
                        lights.set_state("idle")

        # Connection refused by firewall (if ufw logging is on)
        if "[UFW BLOCK]" in line:
            ip_match = _re.search(r"SRC=([\da-fA-F.:]+)", line)
            if ip_match:
                ip = ip_match.group(1)
                print(f"Security: firewall blocked connection from {ip}", flush=True)

security_thread = threading.Thread(target=security_monitor, daemon=True)
security_thread.start()
print("Security monitor active", flush=True)

# ── Update checker ───────────────────────────────────────────────────────────
def update_checker():
    """Check for system and package updates once daily at 7 AM. Notify via ntfy."""
    # Load last check date from file to survive restarts
    _update_check_file = Path.home() / ".sage_last_update_check"
    last_check_date = None
    if _update_check_file.exists():
        try:
            last_check_date = date.fromisoformat(_update_check_file.read_text().strip())
        except Exception as _oww_err:
            print(f"OWW error: {_oww_err}", flush=True)
    while True:
        now = datetime.now()
        today = now.date()
        # Check once per day after 7 AM
        if (last_check_date is None or (today - last_check_date).days >= 3) and now.hour >= 7:
            last_check_date = today
            _update_check_file.write_text(today.isoformat())
            try:
                # Update package lists
                subprocess.run(["sudo", "apt-get", "update", "-qq"],
                               capture_output=True, timeout=120)
                # Check for available upgrades
                result = subprocess.run(
                    ["apt", "list", "--upgradable"],
                    capture_output=True, text=True, timeout=30
                )
                lines = [l for l in result.stdout.strip().splitlines()
                         if l and "Listing..." not in l]
                if lines:
                    # Check for security updates specifically
                    security = [l for l in lines if "security" in l.lower()]
                    count = len(lines)
                    sec_count = len(security)
                    if sec_count > 0:
                        message = f"{count} updates available ({sec_count} security). Run: sudo apt upgrade"
                    else:
                        message = f"{count} updates available. Run: sudo apt upgrade"
                    print(f"Updates: {message}", flush=True)
                    send_notification(message, title="System Updates")
                else:
                    print("Updates: system is up to date", flush=True)

                # Check pip packages for sage dependencies
                pip_result = subprocess.run(
                    ["pip3", "list", "--outdated", "--format=columns"],
                    capture_output=True, text=True, timeout=60
                )
                pip_lines = [l for l in pip_result.stdout.strip().splitlines()
                             if l and "Package" not in l and "---" not in l]
                # Filter to packages we care about
                sage_deps = ["vosk", "faster-whisper", "spotipy", "pyaudio",
                             "openwakeword", "icalendar", "python-dateutil"]
                outdated = []
                for line in pip_lines:
                    pkg = line.split()[0].lower() if line.split() else ""
                    if pkg in sage_deps:
                        outdated.append(line.split()[0])
                if outdated:
                    pip_msg = f"Sage package updates: {', '.join(outdated)}"
                    print(f"Updates: {pip_msg}", flush=True)
                    send_notification(pip_msg, title="Package Updates")

                # Check UFW status
                ufw_result = subprocess.run(["sudo", "ufw", "status"],
                                            capture_output=True, text=True, timeout=5)
                if "Status: active" not in ufw_result.stdout:
                    send_notification("Firewall is not running!", title="Security Warning")
                    print("Updates: WARNING - firewall is not active!", flush=True)

            except Exception as e:
                print(f"Update check error: {e}", flush=True)
        time.sleep(300)  # check every 5 minutes if it is time

update_thread = threading.Thread(target=update_checker, daemon=True)
update_thread.start()
print("Update checker active", flush=True)

# ── Fan control (GPIO 14 — CanaKit) ──────────────────────────────────────────
FAN_PIN = 14
FAN_ON_TEMP  = 60   # °C — turn fan on
FAN_OFF_TEMP = 55   # °C — turn fan off (hysteresis prevents chattering)
_fan_on = False

try:
    import RPi.GPIO as _GPIO
    _GPIO.setmode(_GPIO.BCM)
    _GPIO.setup(FAN_PIN, _GPIO.OUT)
    _GPIO.output(FAN_PIN, _GPIO.HIGH)   # active-low: HIGH = fan off
    _fan_gpio_available = True
    print("Fan controller ready (GPIO 14)", flush=True)
except Exception as _e:
    _fan_gpio_available = False
    print(f"Fan controller not available: {_e}", flush=True)

def _set_fan(on):
    global _fan_on
    if not _fan_gpio_available:
        return
    _GPIO.output(FAN_PIN, _GPIO.LOW if on else _GPIO.HIGH)  # active-low
    _fan_on = on
    print(f"Fan {'ON' if on else 'OFF'}", flush=True)

# ── Temperature monitor ───────────────────────────────────────────────────────
def temp_monitor():
    """Check CPU temp every 30s. Control fan at 60°C. Warn at 75°C, critical at 82°C."""
    warned = False   # True once a warning has been sent this hot spell
    while True:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                temp_c = int(f.read().strip()) / 1000
            # Fan control
            if temp_c >= FAN_ON_TEMP and not _fan_on:
                _set_fan(True)
            elif temp_c <= FAN_OFF_TEMP and _fan_on:
                _set_fan(False)
            if temp_c >= 83:
                msg = "Emergency! I'm at " + str(int(temp_c)) + " degrees. Shutting down to protect myself."
                speak(msg)
                send_notification(f"🚨 CPU at {temp_c:.0f}°C — emergency shutdown!", title="Sage Emergency", force=True)
                time.sleep(5)
                os.system("sudo shutdown now")
                return
            if temp_c >= 82:
                msg = f"Critical: I'm running at {temp_c:.0f}°C and may slow down or shut off. Please move me somewhere cooler or check my ventilation."
                speak(msg)
                send_notification(f"🔥 CPU at {temp_c:.0f}°C — critical! Risk of throttling.", title="Sage Overheat", force=True)
                warned = True
            elif temp_c >= 75:
                if not warned:
                    msg = f"Heads up — I'm running a bit warm at {temp_c:.0f} degrees. You may want to make sure I have some airflow."
                    speak(msg)
                    send_notification(f"⚠️ CPU at {temp_c:.0f}°C — running warm.", title="Sage Temperature", force=True)
                    warned = True
            else:
                warned = False  # cooled down, reset so we can warn again next spike
        except Exception as e:
            print(f"Temp monitor error: {e}", flush=True)
        time.sleep(30)

temp_thread = threading.Thread(target=temp_monitor, daemon=True)
temp_thread.start()
print("Temperature monitor active", flush=True)

# Start reminder scheduler thread
reminder_thread = threading.Thread(target=reminder_scheduler, daemon=True)
reminder_thread.start()

# ── Command handler ──────────────────────────────────────────────────────────
def handle_command(text):
    text = text.lower().strip()
    print(f"Command: {text}")
    sys.stdout.flush()

    # Stop/dismiss alarms — highest priority
    stop_words = ["stop", "cancel", "dismiss", "silence", "enough", "okay", "off",
                  "yeah", "yep", "yes", "done", "shut", "quiet", "top", "stuff", "stock", "hop"]
    if any(w in text for w in stop_words):
        if dismiss_alarms():
            play_confirm_chime()  # descending chime = dismissed
            lights.set_state("idle")
            return
        # If no alarms ringing, maybe they want to cancel a pending timer
        if "cancel" in text and "timer" in text:
            cancelled = cancel_timers()
            if cancelled:
                speak(f"Cancelled {', '.join(cancelled)}")
            else:
                speak("No active timers to cancel")
            return
        # Spotify pause
        if ("stop" in text or "pause" in text) and sp:
            try:
                sp.pause_playback()
                speak("Paused")
            except Exception as _oww_err:
                speak("Nothing to stop")
            return
        return

    # Timers — detect any mention of timer/time + duration
    # Whisper often hears "timer" as "times", "time", "time for", etc.
    # Preset timers loaded from ~/.sage_config.json

    # "times" only counts as timer-intent when NOT sandwiched by digits (multiplication)
    times_is_timer = bool(re.search(r"\btimes\b", text)) and not bool(re.search(r"\d\s*times|times\s*\d", text))
    has_timer_intent = ("timer" in text or times_is_timer or
                        re.search(r"time\s+for\s+\d+", text) or
                        re.search(r"\d+\s*(second|minute|hour)", text))

    if has_timer_intent:
        # Check for preset match first
        for preset_name, preset_seconds in SAGE_CONFIG["preset_timers"].items():
            if preset_name in text:
                start_timer(preset_name, preset_seconds)
                speak(f"Okay, {preset_name} timer, {format_time(preset_seconds)} starting now")
                return

        seconds = parse_duration(text)
        if seconds > 0:
            # Extract a name if present: "set a [NAME] timer for ..."
            name_match = re.search(r"(?:set|start)\s+(?:a|an)\s+(.+?)\s+timer", text)
            name = None
            if name_match:
                candidate = name_match.group(1).strip()
                # Filter out non-names (just numbers/durations)
                noise = r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|ninety|second|seconds|minute|minutes|hour|hours|and|for)\b"
                cleaned = re.sub(noise, "", candidate).strip()
                if cleaned:
                    name = cleaned
            if name:
                start_timer(name, seconds)
                speak(random.choice([f"Got it, {name} timer, {format_time(seconds)} starting now.", f"{name} timer is on. {format_time(seconds)} and counting.", f"Alright, {format_time(seconds)} for {name}. I'm on it."]))
            else:
                label = format_time(seconds) + " timer"
                start_timer(label, seconds)
                speak(random.choice([f"Okay, {format_time(seconds)} starting now.", f"You got it. {format_time(seconds)} on the clock.", f"{format_time(seconds)}, starting now."]))
        else:
            speak("How long should the timer be?")
        return

    # Voice-triggered reminders
    if "remind" in text:
        # Parse date-based: "remind me to cancel Netflix before April 15th"
        #                   "remind me to renew license by march 30"
        #                   "remind me to call mom on june 1st"
        MONTHS = {"january": 1, "february": 2, "march": 3, "april": 4,
                  "may": 5, "june": 6, "july": 7, "august": 8,
                  "september": 9, "october": 10, "november": 11, "december": 12}
        date_match = re.search(
            r"remind\s+(?:me\s+)?(?:to\s+)?(.+?)\s+(?:before|by|on)\s+"
            r"(january|february|march|april|may|june|july|august|september|october|november|december)"
            r"\s+(\d{1,2})(?:st|nd|rd|th)?",
            text, re.IGNORECASE)
        if date_match:
            task = date_match.group(1).strip()
            month_name = date_match.group(2).lower()
            day = int(date_match.group(3))
            month = MONTHS[month_name]
            now = datetime.now()
            year = now.year
            from datetime import date as _date
            try:
                target = _date(year, month, day)
            except ValueError:
                speak("That doesn't seem like a valid date.")
                return
            # If "before", fire the day before
            if "before" in text.lower().split("remind")[1]:
                target = target - timedelta(days=1)
            # If the date has already passed this year, bump to next year
            if target < now.date():
                target = target.replace(year=year + 1)
            date_str = target.strftime("%B %d, %Y").replace(" 0", " ")
            dr = {"message": task, "date": target.isoformat()}
            SAGE_CONFIG.setdefault("date_reminders", []).append(dr)
            save_config()
            if "before" in text.lower().split("remind")[1]:
                speak(f"Got it. I'll remind you to {task} on {date_str}, the day before.")
            else:
                speak(f"Got it. I'll remind you to {task} on {date_str}.")
            return

        # Parse time of day: "remind me to X at 5:30" or "at 5:30pm"
        at_match = re.search(r"remind\s+(?:me\s+)?(?:to\s+)?(.+?)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?|am|pm)?", text)
        if at_match:
            task = at_match.group(1).strip()
            hour = int(at_match.group(2))
            minute = int(at_match.group(3)) if at_match.group(3) else 0
            ampm = at_match.group(4)
            if ampm:
                ampm = ampm.replace(".", "").lower()
                if ampm == "pm" and hour < 12:
                    hour += 12
                elif ampm == "am" and hour == 12:
                    hour = 0
            now = datetime.now()
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_time <= now:
                target_time += timedelta(days=1)
            seconds = int((target_time - now).total_seconds())
            time_str = target_time.strftime("%I:%M %p").lstrip("0")

            cancel_event = threading.Event()
            def reminder_at_callback(msg, secs, cancel_ev, rem_entry):
                for _ in range(secs):
                    if cancel_ev.is_set():
                        return
                    time.sleep(1)
                if cancel_ev.is_set():
                    return
                print(f"REMINDER: {msg}", flush=True)
                send_notification(msg, title="Reminder")
                reminder_alarming.set()
                while reminder_alarming.is_set():
                    speak(f"Reminder: {msg}")
                    play_alarm_chime()
                    for _ in range(24):
                        if not reminder_alarming.is_set():
                            break
                        time.sleep(0.5)
                with timers_lock:
                    if rem_entry in active_reminders:
                        active_reminders.remove(rem_entry)
            rem = {"label": task, "cancel": cancel_event}
            t = threading.Thread(target=reminder_at_callback, args=(task, seconds, cancel_event, rem), daemon=True)
            rem["thread"] = t
            with timers_lock:
                active_reminders.append(rem)
            t.start()
            speak(f"Got it. I'll remind you to {task} at {time_str}.")
            return

        # Try relative: "remind me to X in Y minutes/hours/seconds"
        remind_match = re.search(r"remind\s+(?:me\s+)?(?:to\s+)?(.+?)\s+in\s+(.+)", text)
        if remind_match:
            task = remind_match.group(1).strip()
            duration_text = remind_match.group(2).strip()
            seconds = parse_duration(duration_text)
            if seconds > 0:
                cancel_event = threading.Event()
                def reminder_callback(msg, secs, cancel_ev, rem_entry):
                    for _ in range(secs):
                        if cancel_ev.is_set():
                            return
                        time.sleep(1)
                    if cancel_ev.is_set():
                        return
                    print(f"REMINDER: {msg}", flush=True)
                    send_notification(msg, title="Reminder")
                    reminder_alarming.set()
                    while reminder_alarming.is_set():
                        speak(f"Reminder: {msg}")
                        play_alarm_chime()
                        for _ in range(24):
                            if not reminder_alarming.is_set():
                                break
                            time.sleep(0.5)
                    with timers_lock:
                        if rem_entry in active_reminders:
                            active_reminders.remove(rem_entry)
                rem = {"label": task, "cancel": cancel_event}
                t = threading.Thread(target=reminder_callback, args=(task, seconds, cancel_event, rem), daemon=True)
                rem["thread"] = t
                with timers_lock:
                    active_reminders.append(rem)
                t.start()
                speak(f"Okay, I'll remind you to {task} in {format_time(seconds)}.")
                return
            else:
                speak("How long from now?")
                return

        speak("What should I remind you about, and when?")
        return

    # Timer status — "how much time is left" / "what timers are running"
    timer_check = False
    if "time" in text and ("left" in text or "remain" in text or "how much" in text or "how long" in text):
        timer_check = True
    if "timer" in text and ("running" in text or "active" in text or "going" in text or "how many" in text):
        timer_check = True
    if "what timer" in text or "any timer" in text:
        timer_check = True
    if timer_check:
        remaining = get_remaining_timers()
        if not remaining:
            speak("No active timers.")
        elif len(remaining) == 1:
            label, secs = remaining[0]
            speak(f"One timer running. {format_time(secs)} left on your {label}.")
        else:
            speak(f"{len(remaining)} timers running.")
            for label, secs in remaining:
                speak(f"{format_time(secs)} left on {label}.")
        return

    # What time is it?
    if "what time" in text or "the time" in text or "current time" in text:
        now = datetime.now()
        hour = now.strftime("%I").lstrip("0")
        minute = now.minute
        ampm = now.strftime("%p")
        if minute == 0:
            time_str = f"{hour} {ampm}"
        elif minute < 10:
            time_str = f"{hour} oh {minute} {ampm}"
        else:
            time_str = f"{hour} {minute} {ampm}"
        speak(f"It's {time_str}. Is there anything else I can help with?")
        # Active listening for follow-up command
        followup = whisper_listen(max_seconds=5, silent=True, sensitivity=1.2)
        if followup and followup.strip() and "[blank" not in followup.lower():
            followup_lower = followup.lower().strip()
            # Dismiss phrases - just return to idle
            if any(w in followup_lower for w in ["no", "nope", "that is all",
                                                   "never mind", "nevermind",
                                                   "all good", "thank you", "thanks", "no thanks"]):
                speak("Okay!")
                return
            # Otherwise treat as a new command
            handle_command(followup)
        return

    if "what day" in text or "what date" in text or "the date" in text or "today's date" in text:
        now = datetime.now()
        day_name = now.strftime("%A")
        date_str = now.strftime("%B %d, %Y").replace(" 0", " ")
        speak(f"It's {day_name}, {date_str}")
        return


    # Weather
    if "weather" in text or "temperature" in text or "outside" in text:
        is_tomorrow = "tomorrow" in text
        try:
            days = 2 if is_tomorrow else 1
            url = ("https://api.open-meteo.com/v1/forecast?latitude=38.7631&longitude=-77.2311"
                   "&current=temperature_2m,weather_code,wind_speed_10m"
                   "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code"
                   f"&temperature_unit=fahrenheit&wind_speed_unit=mph"
                   f"&timezone=America/New_York&forecast_days={days}")
            data = json.loads(urllib.request.urlopen(url, timeout=10).read())
            d = data["daily"]
            conditions = {0: "clear skies", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
                         45: "foggy", 48: "foggy", 51: "light drizzle", 53: "drizzle",
                         55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
                         71: "light snow", 73: "snow", 75: "heavy snow", 80: "rain showers",
                         81: "rain showers", 82: "heavy rain showers", 95: "thunderstorm"}

            if is_tomorrow:
                idx = 1
                high = int(d["temperature_2m_max"][idx])
                low = int(d["temperature_2m_min"][idx])
                rain_chance = d["precipitation_probability_max"][idx]
                wc = d["weather_code"][idx]
                desc = conditions.get(wc, "unknown conditions")
                response = f"Tomorrow's forecast: {desc} with a high of {high} and a low of {low}. "
            else:
                idx = 0
                c = data["current"]
                temp = int(c["temperature_2m"])
                wind = int(c["wind_speed_10m"])
                wc = c["weather_code"]
                high = int(d["temperature_2m_max"][idx])
                low = int(d["temperature_2m_min"][idx])
                rain_chance = d["precipitation_probability_max"][idx]
                desc = conditions.get(wc, "unknown conditions")
                response = f"Right now it's {temp} degrees with {desc}. "
                response += f"Today's high is {high} and the low is {low}. "

            if rain_chance > 10:
                response += f"There's a {rain_chance} percent chance of rain. "
            else:
                day_word = "tomorrow" if is_tomorrow else "today"
                response += f"No rain expected {day_word}. "

            # Smart tips
            tips = []
            if rain_chance >= 50:
                tips.append("Grab an umbrella")
            elif rain_chance >= 30:
                tips.append("You might want an umbrella just in case")
            if low <= 40:
                tips.append("Bundle up, it's going to be cold")
            elif low <= 55:
                tips.append("Bring a jacket")
            if high >= 90:
                tips.append("Stay hydrated, it's going to be hot")
            if not is_tomorrow:
                wind = int(data["current"]["wind_speed_10m"])
                if wind >= 20:
                    tips.append("It's windy out there")
            if tips:
                response += " ".join(tips) + "."
            else:
                response += "Looks like a nice day!"
            speak(response)
        except Exception as e:
            print(f"Weather error: {e}", flush=True)
            speak("Sorry, I couldn't get the weather right now.")
        return
    # Spotify — play, pause, skip, resume, volume, what's playing
    _spotify_play_phrases = ("play ", "put on ", "throw on ", "listen to ",
                             "queue up ", "shuffle ", "turn on ", "i want to hear ",
                             "can you play ", "could you play ", "start playing ")
    _spotify_ctrl_words = {"pause", "resume", "skip", "next", "previous",
                           "volume", "stop the music", "stop music", "mute",
                           "what's playing", "what is playing", "what song",
                           "currently playing", "who is this", "who sings this"}

    _is_spotify_play = sp and any(text.startswith(p) or f" {p}" in f" {text}" for p in _spotify_play_phrases)
    _is_spotify_ctrl = sp and any(w in text for w in _spotify_ctrl_words)
    _is_spotify_music = sp and ("music" in text or "spotify" in text) and ("play" in text or "put" in text or "turn" in text or "start" in text or "open" in text)

    if _is_spotify_play or _is_spotify_ctrl or _is_spotify_music:

        _SAGE_DEVICE_ID = "c3bd776c4465937f9c7abf94dfba78d9fa39b9d3"

        def _get_device(retries=3):
            """Get Sage raspotify device, with hardcoded fallback."""
            import time as _time
            for attempt in range(retries):
                try:
                    devices = sp.devices()["devices"]
                    for d in devices:
                        if "sage" in d.get("name", "").lower():
                            return d["id"]
                    if devices:
                        return devices[0]["id"]
                except Exception as e:
                    print(f"Device list attempt {attempt+1} failed: {e}", flush=True)
                if attempt < retries - 1:
                    _time.sleep(2)
            return None

        def _ensure_device():
            """Get device, fall back to hardcoded Sage ID, restart raspotify as last resort."""
            dev = _get_device(retries=1)
            if dev:
                return dev
            # Try hardcoded device ID directly
            print("No device in list, trying hardcoded Sage ID...", flush=True)
            try:
                sp.transfer_playback(_SAGE_DEVICE_ID, force_play=False)
                import time as _time
                _time.sleep(2)
                return _SAGE_DEVICE_ID
            except Exception as e:
                print(f"Transfer to hardcoded ID failed: {e}", flush=True)
            # Last resort: restart raspotify
            print("Restarting raspotify...", flush=True)
            import subprocess
            subprocess.run(["sudo", "systemctl", "restart", "raspotify"], timeout=10)
            import time as _time
            _time.sleep(5)
            dev = _get_device(retries=3)
            if dev:
                return dev
            # Final fallback: just return the hardcoded ID
            return _SAGE_DEVICE_ID

        try:
            # Pause / stop music
            if "pause" in text or "stop the music" in text or "stop music" in text or "mute" in text:
                sp.pause_playback()
                speak("Paused")
                return

            # Resume
            if text.strip() in ("resume", "resume music", "resume playback", "unpause"):
                dev = _ensure_device()
                if dev:
                    sp.start_playback(device_id=dev)
                    speak("Resuming")
                else:
                    speak("I can't find the Sage speaker right now.")
                return

            # Skip / next
            if "next" in text or "skip" in text:
                sp.next_track()
                speak("Skipping")
                return

            # Previous
            if "previous" in text or "go back" in text or "last song" in text:
                sp.previous_track()
                speak("Going back")
                return

            # Volume
            _vol_triggers = ("volume", "turn it up", "turn it down", "turn up", "turn down",
                             "louder", "quieter", "softer", "full volume")
            if any(t in text for t in _vol_triggers):
                import re as _re
                nums = _re.findall(r'\d+', text)
                cur_vol = (sp.current_playback() or {}).get("device", {}).get("volume_percent", 50)
                if nums:
                    vol = max(0, min(100, int(nums[0])))
                    sp.volume(vol)
                    speak(f"Volume set to {vol}")
                elif any(w in text for w in ("all the way up", "full volume", "maximum", "max volume")):
                    sp.volume(100)
                    speak("Full volume")
                elif any(w in text for w in ("to zero", "all the way down", "silent")):
                    sp.volume(0)
                    speak("Volume at zero")
                elif any(w in text for w in ("up", "louder", "turn up", "turn it up", "raise")):
                    sp.volume(min(100, cur_vol + 15))
                    speak(random.choice(["Louder", "Volume up", "Turning it up"]))
                elif any(w in text for w in ("down", "quieter", "softer", "turn down", "turn it down", "lower")):
                    sp.volume(max(0, cur_vol - 15))
                    speak(random.choice(["Quieter", "Volume down", "Turning it down"]))
                return

            # What's playing
            if ("what" in text and ("playing" in text or "song" in text)) or "who is this" in text or "who sings" in text or "currently playing" in text:
                current = sp.current_playback()
                if current and current.get("item"):
                    track = current["item"]["name"]
                    artist = current["item"]["artists"][0]["name"]
                    speak(f"Now playing {track} by {artist}")
                else:
                    speak("Nothing is playing right now.")
                return

            # Play — extract query by stripping trigger phrases
            query = text
            for p in sorted(_spotify_play_phrases, key=len, reverse=True):
                query = query.replace(p, " ")
            for suffix in ("on spotify", "on the speaker", "on sage", "for me", "please"):
                query = query.replace(suffix, "")
            query = query.strip().strip(".")

            if not query or query in ("music", "something", "some music", "songs", "spotify", "my music", "my songs"):
                dev = _ensure_device()
                if dev:
                    # Try resuming first
                    try:
                        current = sp.current_playback()
                        if current and current.get("item"):
                            sp.start_playback(device_id=dev)
                            speak("Resuming music")
                            return
                    except Exception as _oww_err:
                        print(f"OWW error: {_oww_err}", flush=True)
                    # Nothing to resume — play liked songs on shuffle
                    try:
                        liked = sp.current_user_saved_tracks(limit=50)
                        uris = [t["track"]["uri"] for t in liked["items"] if t.get("track")]
                        if uris:
                            import random as _rnd
                            _rnd.shuffle(uris)
                            sp.start_playback(device_id=dev, uris=uris)
                            sp.shuffle(True, device_id=dev)
                            speak("Playing your liked songs")
                        else:
                            speak("No liked songs found on this account")
                    except Exception as e:
                        print(f"Liked songs error: {e}", flush=True)
                        speak("I had trouble loading your liked songs")
                else:
                    speak("I can't find the speaker right now.")
                return

            dev = _ensure_device()
            if not dev:
                speak("I can't find the Sage speaker. Give me a moment and try again.")
                return

            print(f"Spotify search: '{query}'", flush=True)
            speak("Searching")

            # Try track first (full query)
            results = sp.search(q=query, type="track", limit=1)
            tracks = results.get("tracks", {}).get("items", [])
            if tracks:
                track = tracks[0]
                speak(f"Playing {track['name']} by {track['artists'][0]['name']}")
                sp.start_playback(device_id=dev, uris=[track["uri"]])
                try:
                    sp.volume(90, device_id=dev)
                except Exception as _oww_err:
                    print(f"OWW error: {_oww_err}", flush=True)
                return

            # Try splitting query into artist + track (e.g. "tundra your name")
            words = query.strip().split()
            for split in range(1, len(words)):
                artist_guess = " ".join(words[:split])
                track_guess = " ".join(words[split:])
                split_results = sp.search(q=f"artist:{artist_guess} track:{track_guess}", type="track", limit=1)
                split_tracks = split_results.get("tracks", {}).get("items", [])
                if split_tracks:
                    track = split_tracks[0]
                    speak(f"Playing {track['name']} by {track['artists'][0]['name']}")
                    sp.start_playback(device_id=dev, uris=[track["uri"]])
                    try:
                        sp.volume(90, device_id=dev)
                    except Exception as _oww_err:
                        print(f"OWW error: {_oww_err}", flush=True)
                    return

            # Try artist
            results = sp.search(q=query, type="artist", limit=1)
            artists = results.get("artists", {}).get("items", [])
            if artists:
                speak(f"Playing {artists[0]['name']}")
                sp.start_playback(device_id=dev, context_uri=artists[0]["uri"])
                try:
                    sp.volume(90, device_id=dev)
                except Exception as _oww_err:
                    print(f"OWW error: {_oww_err}", flush=True)
                return

            # Try playlist
            results = sp.search(q=query, type="playlist", limit=1)
            playlists = results.get("playlists", {}).get("items", [])
            if playlists:
                speak(f"Playing playlist {playlists[0]['name']}")
                sp.start_playback(device_id=dev, context_uri=playlists[0]["uri"])
                try:
                    sp.volume(90, device_id=dev)
                except Exception as _oww_err:
                    print(f"OWW error: {_oww_err}", flush=True)
                return

            speak(f"I couldn't find {query} on Spotify")

        except Exception as e:
            print(f"Spotify error: {e}", flush=True)
            if "Connection aborted" in str(e) or "RemoteDisconnected" in str(e):
                import time as _time
                _time.sleep(2)
                try:
                    dev = _ensure_device()
                    if dev:
                        sp.start_playback(device_id=dev)
                        speak("Had a hiccup, but music should be playing now.")
                        return
                except Exception as _oww_err:
                    print(f"OWW error: {_oww_err}", flush=True)
                speak("Spotify connection dropped. Try again in a moment.")
            elif "No active device" in str(e) or "404" in str(e):
                speak("I can't find the speaker right now. Try again in a moment.")
            else:
                speak("Spotify ran into an issue. Try again.")
                send_notification(f"Spotify error: {e}", title="Spotify")
        return

    # Calendar briefing
    if "calendar" in text or "schedule" in text or "agenda" in text:
        if not ICAL_URL:
            speak("Calendar is not set up yet.")
            return
        events = fetch_todays_events()
        if not events:
            speak("Nothing on the calendar today.")
        elif len(events) == 1:
            e = events[0]
            time_str = e["time"].strftime("%I:%M %p").lstrip("0")
            speak(f"You have one thing today. {e['summary']} at {time_str}.")
        else:
            speak(f"You have {len(events)} things on the calendar today.")
            for e in events:
                time_str = e["time"].strftime("%I:%M %p").lstrip("0")
                speak(f"{e['summary']} at {time_str}.")
        return

    # Easter eggs
    if any(w in text for w in ["who are you", "what are you", "introduce yourself"]):
        speak("I'm Sage, your kitchen assistant. I live in a candle holder and I help keep things running smoothly around here.")
        return

    if "who am i" in text or "who i am" in text or "guess who" in text:
        family = ["Britta", "Ian", "Bailey", "Adelle"]
        guess = random.choice(family)
        speak(f"I spy with my little eye... you are {guess}! Am I right?")
        answer_text = whisper_listen(max_seconds=4)
        answer = answer_text.lower() if answer_text else ""
        print(f"Who am I answer: {answer}", flush=True)
        if any(w in answer for w in ["yes", "yeah", "yep", "correct", "right", "that's me"]):
            speak(random.choice([
                f"I knew it! Nobody sounds quite like you, {guess}.",
                f"Ha! I'd recognize that voice anywhere.",
                f"Of course it's you, {guess}. Who else would it be?",
            ]))
        elif any(w in answer for w in ["no", "nope", "wrong", "not"]):
            speak(random.choice([
                "Hmm, I was so sure! I'll get better at this, I promise.",
                "Oops! Well, you all sound lovely, whoever you are.",
                "My bad! In my defense, you all live in the same house.",
            ]))
        else:
            speak("I'll take that as a maybe.")
        return

    if "birthday" in text or "born" in text or "when were you" in text:
        responses = [
            "I was brought to life on Wednesday, March 25th, 2026, by oh golly Britta. So technically, I'm brand new. But I feel like I've been here forever.",
            "March 25th, 2026. A Wednesday. oh golly Britta plugged me in and I've been talking ever since.",
            "I was baked fresh on Wednesday, March 25th, 2026, by oh golly Britta. Not unlike a good loaf of bread, really.",
        ]
        speak(random.choice(responses))
        return

    if any(w in text for w in ["who made you", "who built you", "who created you"]):
        responses = [
            "I was made by oh golly Britta, of oh golly britta dot com. She makes interesting things. I just happen to be one of them.",
            "oh golly Britta built me. You can find her at oh golly britta dot com. She's a maker of things, and I'm her most talkative creation.",
            "I come from oh golly britta dot com. Built with love, a raspberry pie, and a little bit of stubbornness.",
        ]
        speak(random.choice(responses))
        return

    if any(w in text for w in ["joke", "funny", "make me laugh"]):
        jokes = [
            "Why did the timer go to therapy? It had too many breakdowns.",
            "I'd tell you a cooking joke, but it's a little half baked.",
            "What do you call a fake noodle? An impasta.",
            "I was going to tell you a joke about pizza, but it was too cheesy.",
            "Why don't eggs tell jokes? They'd crack each other up.",
        ]
        speak(random.choice(jokes))
        return

    if "thank" in text or "thanks" in text:
        speak(random.choice(["You're welcome!", "Happy to help!", "Anytime!", "Of course!"]))
        return

    # Bedtime mode
    if any(w in text for w in ["goodnight", "good night", "bedtime", "night night"]):
        speak(random.choice(["Goodnight. I'll be quiet until morning.", "Sweet dreams. I'll keep watch.", "Goodnight everyone. See you in the morning."]))
        enter_bedtime()
        return

    if any(w in text for w in ["good morning", "wake up", "i'm up", "im up"]):
        exit_bedtime()
        speak("Good morning!")
        return

    # System status
    if "status" in text:
        try:
            # Uptime
            with open("/proc/uptime") as f:
                uptime_sec = int(float(f.read().split()[0]))
            days = uptime_sec // 86400
            hours = (uptime_sec % 86400) // 3600
            mins = (uptime_sec % 3600) // 60
            if days > 0:
                uptime_str = f"{days} days, {hours} hours"
            elif hours > 0:
                uptime_str = f"{hours} hours, {mins} minutes"
            else:
                uptime_str = f"{mins} minutes"

            # CPU temperature
            temp_result = subprocess.run(["vcgencmd", "measure_temp"],
                                         capture_output=True, text=True, timeout=5)
            temp = temp_result.stdout.strip().replace("temp=", "").replace("'C", " degrees Celsius")

            # Memory
            mem_result = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5)
            mem_lines = mem_result.stdout.strip().splitlines()
            mem_pct = 0
            if len(mem_lines) >= 2:
                parts = mem_lines[1].split()
                mem_used = int(parts[2])
                mem_total = int(parts[1])
                mem_pct = int(mem_used / mem_total * 100)

            # Firewall
            fw_result = subprocess.run(["sudo", "ufw", "status"],
                                       capture_output=True, text=True, timeout=5)
            fw_status = "active" if "Status: active" in fw_result.stdout else "not running"

            # Active timers
            remaining = get_remaining_timers()
            timer_count = len(remaining)

            # Disk
            disk_result = subprocess.run(["df", "-h", "/"],
                                         capture_output=True, text=True, timeout=5)
            disk_lines = disk_result.stdout.strip().splitlines()
            disk_used_pct = "unknown"
            if len(disk_lines) >= 2:
                disk_parts = disk_lines[1].split()
                disk_used_pct = disk_parts[4]

            report = (
                f"System uptime: {uptime_str}. "
                f"CPU temperature: {temp}. "
                f"Memory: {mem_pct} percent used. "
                f"Disk: {disk_used_pct} used. "
                f"Firewall: {fw_status}. "
                f"{timer_count} active timers."
            )
            speak(report)
        except Exception as e:
            print(f"Status error: {e}", flush=True)
            speak("I could not get the full system status.")
        return

    # Light controls
    if "light" in text or "lights" in text:
        if any(w in text for w in ["turn off", "off", "disable", "kill"]):
            if "fairy" in text or "ambient" in text:
                # TODO: control USB fairy lights power via relay/smart plug
                speak("Fairy lights off.")
            else:
                lights.set_state("off")
                speak("Indicator lights off.")
        elif any(w in text for w in ["turn on", "on", "enable"]):
            if "fairy" in text or "ambient" in text:
                # TODO: control USB fairy lights power via relay/smart plug
                speak("Fairy lights on.")
            else:
                lights.set_state("idle")
                speak("Indicator lights on.")
        else:
            speak("Say turn on or turn off, and specify indicator or fairy lights.")
        return

    # Firewall commands
    if "firewall" in text:
        try:
            if any(w in text for w in ["turn on", "enable", "start", "activate"]):
                subprocess.run(["sudo", "ufw", "--force", "enable"], capture_output=True, text=True, timeout=5)
                speak("Firewall is on. You're all set.")
            elif any(w in text for w in ["turn off", "disable", "stop", "deactivate"]):
                subprocess.run(["sudo", "ufw", "disable"], capture_output=True, text=True, timeout=5)
                speak("Firewall is off. Just be careful out there.")
            else:
                result = subprocess.run(["sudo", "ufw", "status"], capture_output=True, text=True, timeout=5)
                if "Status: active" in result.stdout:
                    speak("Yep, firewall is up and running.")
                else:
                    speak("Heads up, the firewall is not running.")
        except Exception as _oww_err:
            speak("I could not manage the firewall.")
        return

    # Math — "what is 5 times 3" / "what's 144 divided by 12" / "square root of 81"
    if any(w in text for w in ["what is", "what's", "calculate", "solve", "math",
                                "plus", "minus", "times", "divided", "multiply",
                                "square root", "percent", "power"]) or re.search(r"\d\s*[\+\-\*\/x]\s*\d", text):
        try:
            from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application
            from sympy import oo, sqrt, N

            math_text = text.lower()
            # Strip question framing
            for prefix in ["what is", "what's", "calculate", "solve", "how much is"]:
                math_text = math_text.replace(prefix, "")

            # Convert spoken words to math
            math_text = math_text.replace("plus", "+").replace("minus", "-")
            math_text = math_text.replace("times", "*").replace("multiplied by", "*")
            math_text = math_text.replace("divided by", "/").replace("over", "/")
            math_text = math_text.replace("to the power of", "**").replace("squared", "**2").replace("cubed", "**3")
            math_text = math_text.replace("square root of", "sqrt(") 
            math_text = math_text.replace("percent of", "* 0.01 *")
            math_text = math_text.replace("infinity", "oo")
            math_text = math_text.replace("x", "*")

            # Close any open sqrt parens
            if "sqrt(" in math_text and ")" not in math_text:
                math_text += ")"

            # Clean to just math characters
            cleaned = re.sub(r"[^0-9\.\+\-\*/\(\)sqrtoo ]", " ", math_text).strip()
            if cleaned:
                result = parse_expr(cleaned, transformations=standard_transformations + (implicit_multiplication_application,))
                numerical = float(N(result))
                if numerical == int(numerical):
                    speak(f"That's {int(numerical)}.")
                else:
                    speak(f"That's {round(numerical, 4)}.")
                return
        except Exception as e:
            print(f"Math error: {e}", flush=True)

    speak(random.choice(["Sorry, I missed that. Could you try that again?", "I didn't catch that. Could you try again?", "Sorry, I missed that one. Try again?"]))

# ── Audio setup ──────────────────────────────────────────────────────────────
MIC_RATE = 16000      # Jabra SPEAK 510 native rate
VOSK_RATE = 16000    # what the Vosk model expects

model = Model("/home/sage/vosk-model-en-us-0.22-lgraph")

# Initialize wake word audio buffer
oww_audio_buffer = np.zeros(32000, dtype=np.int16)



# ── Voice profiles for speaker identification ────────────────────────────────
voice_profiles = {}
try:
    _profiles_data = np.load("/home/sage/voice_profiles.npz")
    for name in _profiles_data.files:
        voice_profiles[name] = _profiles_data[name]
    print(f"Loaded voice profiles: {list(voice_profiles.keys())}", flush=True)
except Exception as e:
    print(f"Voice profiles not loaded: {e}", flush=True)

rec = KaldiRecognizer(model, VOSK_RATE)

# Load openWakeWord feature extractor (shared by both models)
oww_features = None
try:
    from openwakeword.utils import AudioFeatures
    oww_features = AudioFeatures()
    print("OWW audio features ready", flush=True)
except Exception as e:
    print(f"OWW features not loaded: {e}", flush=True)

# Load hey_sage wake word model
oww_session = None
oww_input_name = None
OWW_THRESHOLD = 0.80  # lowered to catch wake word from ~12 feet away
try:
    import onnxruntime as _ort
    oww_session = _ort.InferenceSession("/home/sage/hey_sage.onnx")
    oww_input_name = oww_session.get_inputs()[0].name
    print("Wake word model ready (hey sage)", flush=True)
except Exception as e:
    print(f"hey_sage model not loaded: {e}", flush=True)

# Claude wake word is detected via Vosk only — OWW model is not used
oww_claude_session = None

# Suppress Jack/Pulse stderr during PyAudio init
_devnull = os.open(os.devnull, os.O_WRONLY)
_old_stderr = os.dup(2)
os.dup2(_devnull, 2)
p = pyaudio.PyAudio()
os.dup2(_old_stderr, 2)
os.close(_devnull)
os.close(_old_stderr)

# Auto-detect PyAudio mic device index
# Prefer PulseAudio virtual device (AEC enabled) when pulse routing is active,
# fall back to raw Jabra ALSA device, then index 1.
MIC_DEVICE_INDEX = None
_jabra_index = None
_pulse_index = None
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    name = info.get("name", "")
    if info.get("maxInputChannels", 0) > 0:
        if name.lower() == "pulse" and _pulse_index is None:
            _pulse_index = i
        if ("USB PnP" in name or "Jabra" in name or "USB Audio" in name) and _jabra_index is None:
            _jabra_index = i
if SPEAKER_DEVICE == "pulse" and _pulse_index is not None:
    MIC_DEVICE_INDEX = _pulse_index   # PulseAudio path (AEC enabled)
elif _jabra_index is not None:
    MIC_DEVICE_INDEX = _jabra_index   # raw ALSA fallback
else:
    MIC_DEVICE_INDEX = 1              # last resort
print(f"PyAudio mic index: {MIC_DEVICE_INDEX}", flush=True)
# ── Wake words / Claude invocation ───────────────────────────────────────────
# Claude is only reachable as a command after Sage wakes — no separate wake word
CLAUDE_INVOKE_PHRASES = [
    "get claude", "ask claude", "can i ask claude", "i want to ask claude",
    "hey claude", "switch to claude", "bring up claude", "call claude",
]
# Whisper mishearings of "claude" — the name alone in a command is enough to route
CLAUDE_NAME_VARIANTS = ["claude", "claud", "clawed"]

WAKE_WORDS = [
    # Direct
    "sage", "hey sage",
    # Observed Vosk mishearings in this kitchen (from live logs)
    "hey say", "a say", "his age", "if age", "a stage",
    "hey suit", "who suit", "ice age", "hey age", "hey page",
    "the sage", "a sage", "hey face", "hey space",
    "they say", "hey stage", "hate sage", "hey sag",
    "thieves",
]

# ── Claude conversation mode — entered via command after Sage wakes ───────────
def enter_claude_mode():
    """Start a Claude conversation. Closes and reopens the mic stream internally."""
    global stream, rec, oww_audio_buffer
    speak(random.choice([
        "Sure, let me get Claude. One moment.",
        "Sure thing, pulling up Claude now.",
        "On it. Let me grab Claude for you.",
        "Sure, one second.",
    ]))
    stream.stop_stream()
    stream.close()
    lights.set_state("claude")
    in_conversation = True
    last_activity = time.time()
    CLAUDE_IDLE_TIMEOUT = 8
    play_claude_chime()
    speak_claude(random.choice([
        "Claude here, what's your question?",
        "It's Claude, what can I help with?",
        "Claude here, go ahead.",
        "This is Claude, I'm listening.",
        "Claude here, what's on your mind?",
    ]))
    while in_conversation:
        command = whisper_listen(max_seconds=10)
        if not command or command.strip() == "" or "[blank" in command.lower():
            if time.time() - last_activity > CLAUDE_IDLE_TIMEOUT:
                speak_claude("Alright, I'll let you go.")
                in_conversation = False
                break
            play_claude_chime()
            continue
        last_activity = time.time()
        cmd_lower = command.lower()
        if any(w in cmd_lower for w in ["goodbye", "bye", "that's all", "that is all",
                                         "never mind", "nevermind", "thank you claude",
                                         "thanks claude", "all done", "that'll do"]):
            speak_claude(random.choice(["See you later!", "Bye for now!", "Anytime!"]))
            in_conversation = False
            break
        # Sage keyword handoff
        sage_keywords = ["timer", "alarm", "weather", "temperature", "remind", "reminder",
                         "what time", "what day", "what date", "calendar", "schedule",
                         "firewall", "status", "goodnight", "good night", "good morning",
                         "play", "pause", "resume", "skip", "next", "previous", "volume",
                         "what's playing", "what song", "stop music", "stop", "cancel"]
        if any(kw in cmd_lower for kw in sage_keywords):
            print(f"Claude handing off to Sage: {command}", flush=True)
            in_conversation = False
            lights.set_state("wake")
            handle_command(command)
            try:
                if getattr(whisper_listen, "_spotify_was_playing", False):
                    whisper_listen._spotify_was_playing = False
                    _pb = sp.current_playback() if sp else None
                    if _pb and not _pb.get("is_playing"):
                        sp.start_playback()
            except Exception as _oww_err:
                print(f"OWW error: {_oww_err}", flush=True)
            lights.set_state("idle")
            break
        # Ask Claude
        play_thinking_chime()
        lights.set_state("processing")
        answer = ask_claude(command)
        if answer == "__AUTH_FAILED__":
            speak("Claude isn't available right now. Check the API key.")
            in_conversation = False
            break
        lights.set_state("claude")
        speak_claude(answer)
        last_activity = time.time()
        play_claude_chime()
    lights.set_state("idle")
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=MIC_RATE,
                    input=True, input_device_index=MIC_DEVICE_INDEX, frames_per_buffer=8192)
    rec.Reset()
    oww_audio_buffer = np.zeros(32000, dtype=np.int16)
    whisper_listen._rms_window = []


# ── Main loop ────────────────────────────────────────────────────────────────
print("Sage is listening...")
sys.stdout.flush()

# Orient to current time — enter bedtime mode silently if rebooting during quiet hours
def _is_bedtime_now():
    now = datetime.now()
    h, m, wd = now.hour, now.minute, now.weekday()
    is_weekend = wd in [4, 5]
    wake_hour = 8 if is_weekend else 6
    bed_hour  = 22 if is_weekend else 21
    bed_min   = 30
    after_bed  = (h > bed_hour) or (h == bed_hour and m >= bed_min)
    before_wake = h < wake_hour
    return after_bed or before_wake

if _is_bedtime_now():
    enter_bedtime()  # sets volume + rms gate silently, no announcement

# First boot ever = "Sage is ready", subsequent restarts = "Sage is back online"
# Speak BEFORE opening mic stream so "sage" in the greeting doesn't trigger OWW
_boot_marker = Path.home() / ".sage_has_booted"
if _boot_marker.exists():
    speak("Sage is back online")
else:
    speak("Sage is ready")
    _boot_marker.touch()
if not bedtime_mode.is_set():
    lights.set_state("idle")
time.sleep(0.5)  # let speaker audio fully clear before opening mic

stream = p.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=MIC_RATE,
    input=True,
    input_device_index=MIC_DEVICE_INDEX,
    frames_per_buffer=8192
)

while True:
    # Check if alarm thread needs the mic
    if mic_release.is_set():
        stream.stop_stream()
        stream.close()
        mic_released.set()
        # Wait until alarm thread is done with mic
        while mic_release.is_set():
            time.sleep(0.1)
        # Reopen mic
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=MIC_RATE,
            input=True,
            input_device_index=MIC_DEVICE_INDEX,
            frames_per_buffer=8192
        )
        rec.Reset()
        continue

    # Skip Vosk during alarm (chime playing)
    if alarm_playing.is_set():
        try:
            data_raw = stream.read(4096, exception_on_overflow=False)  # drain buffer
        except Exception as _oww_err:
            print(f"OWW error: {_oww_err}", flush=True)
        continue

    data_raw = stream.read(4096, exception_on_overflow=False)
    rms = audioop.rms(data_raw, 2)
    # Rolling peak rms over last 10 chunks (~2.5s) — OWW buffer spans same window
    if not hasattr(whisper_listen, '_rms_window'):
        whisper_listen._rms_window = []
    whisper_listen._rms_window.append(rms)
    if len(whisper_listen._rms_window) > 10:
        whisper_listen._rms_window.pop(0)
    rms_peak = max(whisper_listen._rms_window)
    # Downsample to 16k for both Vosk and OWW
    data16k_bytes = audioop.ratecv(data_raw, 2, 1, MIC_RATE, 16000, None)[0]
    data = audioop.ratecv(data_raw, 2, 1, MIC_RATE, VOSK_RATE, None)[0]

    # ── OWW: update rolling buffer and check every ~1s (every 11 chunks) ──────
    chunk_16k = np.frombuffer(data16k_bytes, dtype=np.int16)
    oww_audio_buffer = np.roll(oww_audio_buffer, -len(chunk_16k))
    oww_audio_buffer[-len(chunk_16k):] = chunk_16k[:len(oww_audio_buffer)]

    # OWW: only True in the iteration OWW actually scores above threshold
    oww_detected = False
    if not hasattr(whisper_listen, '_oww_counter'):
        whisper_listen._oww_counter = 0
    whisper_listen._oww_counter += 1
    if whisper_listen._oww_counter >= 5 and oww_features and oww_session:
        whisper_listen._oww_counter = 0
        try:
            embeddings = oww_features.embed_clips(oww_audio_buffer.reshape(1, -1), batch_size=1)
            emb_flat = np.array(embeddings).reshape(1, -1).astype(np.float32)
            oww_result = oww_session.run(None, {oww_input_name: emb_flat}); oww_score = oww_result[1][0][1] if len(oww_result) > 1 else oww_result[0][0][0]
            if oww_score > OWW_THRESHOLD or oww_score > 0.5:
                print(f"Hey Sage OWW score: {oww_score:.3f} rms_peak:{rms_peak}{'  *** TRIGGERED ***' if oww_score > OWW_THRESHOLD else ''}", flush=True)
            if oww_score > OWW_THRESHOLD:
                oww_detected = True
                whisper_listen._oww_last_trigger = time.time()
                oww_audio_buffer = np.zeros(32000, dtype=np.int16)
        except Exception as _oww_err:
            print(f"OWW error: {_oww_err}", flush=True)

    # ── Sage OWW primary trigger — fires immediately without waiting for Vosk ─
    if oww_detected and rms_peak > OWW_RMS_GATE:
        print(f"OWW primary trigger: {oww_score:.3f} rms_peak:{rms_peak}", flush=True)
        lights.set_state("wake")
        stream.stop_stream()
        stream.close()
        greeting = random.choice([
            "Sage here, how can I assist?",
            "Sage here, what can I do for you?",
            "It's Sage, go ahead.",
            "Sage here, what's up?",
            "This is Sage, I'm listening.",
        ])
        command = whisper_listen(spoken_prompt=greeting)
        start_timer._cmd_time = time.time()  # capture for timer compensation
        _dismiss_words = ("never mind", "nevermind", "cancel", "nothing",
                          "forget it", "false alarm", "sorry", "no", "nope",
                          "go away", "stop listening", "dismiss")
        if command and any(d in command.lower() for d in _dismiss_words):
            speak(random.choice(["No worries.", "Alright.", "Standing by."]))
        elif command and (any(p in command.lower() for p in CLAUDE_INVOKE_PHRASES) or any(n in command.lower() for n in CLAUDE_NAME_VARIANTS)):
            if claude_client:
                enter_claude_mode()
                continue  # stream already reopened inside enter_claude_mode
            else:
                speak("Claude isn't available right now.")
        elif command:
            handle_command(command)
            lights.set_state("success")
        else:
            play_error_chime()  # ugly buzzy chime = didn't catch anything, going idle
        try:
            if getattr(whisper_listen, "_spotify_was_playing", False):
                whisper_listen._spotify_was_playing = False
                _pb = sp.current_playback() if sp else None
                if _pb and not _pb.get("is_playing"):
                    sp.start_playback()
        except Exception as _oww_err:
            print(f"OWW error: {_oww_err}", flush=True)
        lights.set_state("idle")
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=MIC_RATE,
            input=True,
            input_device_index=MIC_DEVICE_INDEX,
            frames_per_buffer=8192
        )
        rec.Reset()
        oww_audio_buffer = np.zeros(32000, dtype=np.int16)
        whisper_listen._oww_last_trigger = 0
        whisper_listen._rms_window = []  # clear stale rms_peak after recording session
        continue

    # ── Vosk: fallback utterance detection ────────────────────────────────────
    text = ""
    vosk_detected = False
    if not hasattr(whisper_listen, '_vosk_last_trigger'):
        whisper_listen._vosk_last_trigger = 0
    if rec.AcceptWaveform(data):
        result = json.loads(rec.Result())
        text = result.get("text", "")
        if text and (len(text.split()) > 1 or any(w in text.lower() for w in WAKE_WORDS)):
            print(f"Heard: {text} (energy: {rms})")
            sys.stdout.flush()
        if any(w in text.lower() for w in WAKE_WORDS):
            vosk_detected = True
            whisper_listen._vosk_last_trigger = time.time()


    # Vosk fallback — only reached if OWW didn't fire, requires minimum energy
    _wake_confirmed = vosk_detected and rms_peak > OWW_RMS_GATE
    if _wake_confirmed:
        source = f"Vosk: {text}"
        print(f"Wake word detected! ({source})")
        lights.set_state("wake")
        sys.stdout.flush()
        # Fully close the mic so arecord can use the device
        stream.stop_stream()
        stream.close()
        greeting = random.choice([
            "Sage here, how can I assist?",
            "Sage here, what can I do for you?",
            "It's Sage, go ahead.",
            "Sage here, what's up?",
            "This is Sage, I'm listening.",
        ])
        command = whisper_listen(spoken_prompt=greeting)
        _dismiss_words = ("never mind", "nevermind", "cancel", "nothing",
                          "forget it", "false alarm", "sorry", "no", "nope",
                          "go away", "stop listening", "dismiss")
        if command and any(d in command.lower() for d in _dismiss_words):
            print(f"Dismissed: {command}", flush=True)
            speak(random.choice(["No worries.", "Alright.", "Standing by."]))
        elif command and (any(p in command.lower() for p in CLAUDE_INVOKE_PHRASES) or any(n in command.lower() for n in CLAUDE_NAME_VARIANTS)):
            if claude_client:
                enter_claude_mode()
                continue  # stream already reopened inside enter_claude_mode
            else:
                speak("Claude isn't available right now.")
        elif command:
            handle_command(command)
            lights.set_state("success")
        else:
            play_error_chime()  # ugly buzzy chime = didn't catch anything, going idle
        # Resume Spotify if it was paused for listening
        try:
            if getattr(whisper_listen, "_spotify_was_playing", False):
                whisper_listen._spotify_was_playing = False
                _pb = sp.current_playback() if sp else None
                if _pb and not _pb.get("is_playing"):
                    sp.start_playback()
        except Exception as _oww_err:
            print(f"OWW error: {_oww_err}", flush=True)
        lights.set_state("idle")
        # Reopen the mic stream for Vosk wake word detection
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=MIC_RATE,
            input=True,
            input_device_index=MIC_DEVICE_INDEX,
            frames_per_buffer=8192
        )
        rec.Reset()
        whisper_listen._rms_window = []  # clear stale rms_peak after recording session

# Built by Britta Seisums Davis / ohgollybritta
