# Sage 🌿

**A privacy-first voice assistant for your kitchen, built on a Raspberry Pi.**

Sage is an open-source voice assistant that does the everyday things a kitchen assistant should do — set timers, give weather reports, manage reminders, chat with Claude AI — without sending your voice to the cloud. The voice pipeline runs entirely on a Raspberry Pi.

> "Always-on shouldn't mean always uploading."

---

## Features

### Voice Commands (all processed locally)

| Category | Commands | What Sage Does |
|----------|----------|----------------|
| **Timers** | "Set a timer for 10 minutes" | Countdown with alarm chime |
| | "Set a pasta timer for 12 minutes" | Named timer |
| | Say a preset name (e.g., "pasta") | Starts preset timer with saved duration |
| | "What timers are running?" | Lists active timers |
| | "How much time is left?" | Time remaining |
| | "Stop" / "Stop the timer" | Dismiss alarm |
| | "Cancel the pasta" | Cancel specific timer |
| | "Cancel everything" | Cancel all timers + reminders |
| **Reminders** | "Remind me to check the laundry in 20 minutes" | Speaks + push notification |
| | "Remind me to call mom at 5:30 PM" | Time-of-day reminder |
| **Weather** | "What's the weather?" | Current conditions + outfit tips |
| | "What's the weather tomorrow?" | Tomorrow's forecast |
| **Calendar** | "What's on the calendar today?" | Reads today's events |
| | "What's my schedule?" | Same as above |
| **Time** | "What time is it?" | Speaks current time |
| | "What day is it?" | Day and full date |
| **System** | "System status" | Uptime, CPU temp, memory, disk, firewall |
| | "Is the firewall running?" | Firewall check |
| | "Turn on/off the firewall" | Manage firewall |
| **Bedtime** | "Goodnight" | Enters sleep mode — mic off, notifications silenced |
| | "Good morning" | Wakes up with weather + calendar briefing |
| **Spotify** | "Play [artist]" | Plays on Spotify (requires API setup) |
| | "Pause" / "Next" | Playback control |
| **Fun** | "Tell me a joke" | Kitchen-themed jokes |
| | "Who are you?" | Introduces itself |
| | "Who made you?" | Credits the creator |
| | "Thank you" | Responds warmly |

### Claude AI Voice Chat (optional, requires API key)

Say **"Hey Claude"** to start an open-ended conversation powered by Anthropic's Claude API. Ask anything — recipes, homework help, general knowledge, advice. Claude knows when to hand off to Sage for timers and local commands.

- Separate wake word and chime from Sage
- Conversation mode — back-and-forth without repeating the wake word
- Seamless handoff: ask Claude for a timer and Sage handles it automatically
- Completely optional — Sage works fully standalone without it

### Background Features (automatic)

- **Push notifications** via ntfy — works on your phone even away from home
- **Google Calendar** integration via iCal — notifications before events
- **Scheduled reminders** — configurable daily/weekly reminders
- **Security monitoring** — alerts on failed SSH login attempts
- **System update checker** — notifies every 3 days if updates are available
- **Bedtime/wake schedule** — auto-sleep at 10 PM weekdays / 11:30 PM weekends, auto-wake with morning briefing
- **Firewall** — UFW enabled on boot, SSH only

### LED Indicator Ring (optional, WS2812B)

Visual status indicators when an LED ring is connected:

| State | Color |
|-------|-------|
| Idle | Warm amber glow |
| Sage listening | Green |
| Processing | Blue spin |
| Claude listening | Reddish-orange |
| Timer counting | Slow warm pulse |
| Alarm | Orange/red flash |
| Security alert | Red strobe |
| Bedtime | Off |

---

## Hardware

- **Raspberry Pi 4** (4GB recommended)
- **USB microphone**
- **USB speaker** (or Bluetooth soundbar)
- **Optional:** WS2812B 24-LED ring + 3 jumper wires for visual indicators
- **Optional:** USB extension cable to move mic away from Pi fan

---

## Setup

### 1. Install dependencies

```bash
sudo apt update && sudo apt install -y python3-pip python3-pyaudio ufw
pip3 install vosk faster-whisper openwakeword spotipy python-dateutil icalendar --break-system-packages
```

### 2. Install speech engine (Piper TTS)

Download [Piper](https://github.com/rhasspy/piper) and a voice model (en_US-lessac-medium recommended).

### 3. Install Vosk model

```bash
cd ~
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
```

### 4. Create credentials file

```bash
cat > ~/.sage_credentials << EOF
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
ANTHROPIC_API_KEY=your_anthropic_key_optional
EOF
chmod 600 ~/.sage_credentials
```

### 5. Create config file

```bash
cat > ~/.sage_config.json << 'EOF'
{
  "preset_timers": {
    "pasta": 720,
    "rice": 420,
    "hard boiled eggs": 660
  },
  "scheduled_reminders": [],
  "ntfy_url": "https://ntfy.sh",
  "ntfy_topic": "your-random-topic-name",
  "ical_url": ""
}
EOF
```

### 6. Enable firewall

```bash
sudo ufw allow 22/tcp
sudo ufw --force enable
```

### 7. Set up auto-start

```bash
sudo tee /etc/systemd/system/sage.service << EOF
[Unit]
Description=Sage Voice Assistant
After=network.target sound.target

[Service]
User=sage
WorkingDirectory=/home/sage
ExecStart=/usr/bin/python3 /home/sage/sage.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable sage
sudo systemctl start sage
```

### 8. (Optional) Claude AI voice chat

Get an API key from [console.anthropic.com](https://console.anthropic.com) and add it to `~/.sage_credentials`. If no key is present, Sage works fully without it.

### 9. (Optional) Push notifications

Install the [ntfy app](https://ntfy.sh) on your phone and subscribe to your topic.

---

## Architecture

```
Microphone → Vosk (wake word) → "Hey Sage" detected
                                      ↓
                               Whisper (command STT)
                                      ↓
                               Command handler
                                      ↓
                              Piper TTS → Speaker

Microphone → Vosk (wake word) → "Hey Claude" detected
                                      ↓
                               Whisper (question STT)
                                      ↓
                               Claude API (cloud)
                                      ↓
                              Piper TTS → Speaker
```

All voice processing (wake word detection, speech-to-text) happens locally on the Pi. Only Claude conversations are sent to the cloud, and only when explicitly invoked with "Hey Claude."

---

## Files

| File | Description |
|------|-------------|
| `sage.py` | Main application — voice loop, commands, timers, reminders, Claude |
| `sage_lights.py` | LED ring controller (WS2812B) |
| `spotify_auth.py` | Spotify OAuth setup helper |
| `hey_sage.onnx` | Custom trained "hey sage" wake word model |
| `hey_claude.onnx` | Custom trained "hey claude" wake word model |
| `.gitignore` | Keeps credentials and personal config out of the repo |

### Not in repo (private per-installation)

| File | Description |
|------|-------------|
| `~/.sage_credentials` | API keys and passwords |
| `~/.sage_config.json` | Preset timers, reminders, ntfy settings, calendar URL |
| `~/voice_profiles.npz` | Family voice profiles for "who am I?" feature |

---

## Privacy

- **Wake word detection**: local (openWakeWord)
- **Speech-to-text**: local (Vosk + Whisper)
- **Text-to-speech**: local (Piper)
- **Timers, weather, calendar, reminders**: local processing
- **Claude AI chat**: sent to Anthropic API only when you say "Hey Claude" — completely optional
- **Push notifications**: sent via ntfy (self-hosted option available)
- **No telemetry, no analytics, no accounts required**

---

## License

**GPL v3** with commercial use restriction.

- Free to use, fork, and modify for personal and non-commercial use
- Commercial use requires written permission from the copyright holder
- Attribution required: **Britta Davis / [ohgollybritta.com](https://ohgollybritta.com)**

See [LICENSE](LICENSE) for full terms.

---

Made by [ohgollybritta.com](https://ohgollybritta.com)
