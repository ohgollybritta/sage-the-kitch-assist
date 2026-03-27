# Sage 🌿
### A privacy-first voice assistant for your kitchen, built on a Raspberry Pi.

Sage is an open-source voice assistant that does the everyday things a kitchen assistant should do — set timers, give weather reports, manage reminders, chat with Claude AI — without sending your voice to the cloud. The voice pipeline runs entirely on a Raspberry Pi.

> "Always-on shouldn't mean always uploading."

---

## Why Sage?

In early 2025, the last remaining opt-out for local voice processing was quietly removed from major commercial smart speakers. The official reason was generative AI — new features need the cloud. The effect was that users lost the ability to keep any part of their voice data on-device, with no alternative offered.

Sage is that alternative. The voice pipeline runs locally. Audio is never stored, never uploaded, never sent anywhere except out your speaker.

---

## Hardware

- **Raspberry Pi 4** (CanaKit or equivalent)
- **USB microphone**
- **USB speaker** (or Bluetooth soundbar)
- **WS2812B LED ring** (optional — 24-bit, for visual indicators)
- **Female-to-female jumper wires** (3 needed for LED ring)

---

## What it does

### Kitchen
- ⏱ **Kitchen timers** — "Set a timer for 10 minutes"
- ⏱ **Named timers** — "Set a chicken nuggets timer for 13 minutes"
- ⏱ **Preset food timers** — 23 built-in presets, say "pasta timer" and it auto-sets
- ⏱ **Multiple simultaneous timers** — "What timers are running?"
- 🔔 **Persistent alarms** — repeating chime until you say "stop"

### Reminders
- 📋 **Voice reminders (relative)** — "Remind me to check the laundry in 20 minutes"
- 📋 **Voice reminders (time-of-day)** — "Remind me to pick up the kids at 3:30 PM"
- 📋 **Scheduled reminders** — recurring alerts at specific times/days (configurable)
- 📲 **Push notifications** — all reminders push to your phone via [ntfy](https://ntfy.sh)

### Weather
- 🌤 **Today's weather** — "What's the weather?" with smart outfit suggestions
- 🌤 **Tomorrow's forecast** — "What's the weather tomorrow?"
- 🧥 Smart tips — umbrella, jacket, hydration based on conditions

### Calendar
- 📅 **Google Calendar** — "What's on the calendar today?"
- 📅 Fetches events via iCal (no API key needed)
- 📅 Push notifications 15 minutes before each event

### Claude AI (optional)
- 🤖 **Voice chat with Claude** — "Hey Claude, what's a good recipe for banana bread?"
- 🤖 **Conversation mode** — back-and-forth conversation, no need to repeat the wake word
- 🤖 **Smart handoff** — ask Claude to set a timer and it seamlessly passes to Sage
- 🤖 Requires an [Anthropic API key](https://console.anthropic.com) — completely optional

### Time & Date
- 🕐 "What time is it?"
- 📆 "What day is it?" / "What's the date?"

### Security & System
- 🔒 **Firewall control** — "Is the firewall running?" / "Turn on the firewall"
- 📊 **System status** — "System status" (uptime, CPU temp, memory, disk, firewall)
- 🚨 **Intrusion detection** — voice + push alert on failed SSH login attempts
- 🔄 **Update checker** — notifies every 3 days if system or package updates are available

### Bedtime & Morning
- 😴 **Bedtime mode** — "Goodnight" silences alerts, dims lights
- ☀️ **Morning briefing** — "Good morning" triggers weather + calendar
- ⏰ Auto bedtime: 10 PM weekdays, 11:30 PM weekends
- ⏰ Auto wake: 6:30 AM weekdays, 8:30 AM weekends with full briefing

### Music
- 🎵 **Spotify playback** — "Play Fleetwood Mac" (requires Spotify API setup)
- 🎵 Pause, skip, stop by voice

### Personality
- 🎭 Varied responses — Sage doesn't repeat the same phrase
- 😄 Easter eggs — "Tell me a joke", "Who are you?", "Who made you?", "When is your birthday?"
- 🙏 Says "you're welcome" when you say thanks
- 👤 **Voice identification** — "Who am I?" (guesses who's talking from voice profiles)

### Visual Indicators (LED ring)
- 🟢 **Green** — Sage is idle/listening
- 🔵 **Blue pulse** — wake word detected
- 🔵 **Blue solid** — recording your command
- 🔵 **Blue spin** — processing
- 🟢 **Green flash** — command understood
- 🟠 **Orange pulse** — timer counting down
- 🔴 **Red flash** — alarm going off
- 🟠 **Reddish-orange** — Claude is active
- 🔴 **Red strobe** — security alert

---

## Setup

### 1. Flash the SD card

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/). Choose **Raspberry Pi OS Lite (64-bit)**. Configure:

- Hostname: `sage`
- Enable SSH with password authentication
- Set your username and password
- Configure your WiFi

### 2. SSH in

```bash
ssh yourusername@sage.local
```

### 3. Update the system

```bash
sudo apt update && sudo apt upgrade -y
```

### 4. Install dependencies

```bash
sudo apt install -y python3-pip python3-pyaudio git cmake
pip3 install vosk faster-whisper spotipy openwakeword python-dateutil icalendar --break-system-packages
```

### 5. Install Vosk model (wake word detection)

```bash
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
```

### 6. Install Piper (local text-to-speech)

```bash
wget https://github.com/rhasspy/piper/releases/latest/download/piper_linux_aarch64.tar.gz
tar xzf piper_linux_aarch64.tar.gz
sudo mv piper/piper /usr/local/bin/
sudo cp ~/piper/*.so* /usr/local/lib/
sudo ldconfig
sudo apt install -y libespeak-ng1

mkdir -p ~/piper-voices
wget -O ~/piper-voices/en_US-lessac-medium.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget -O ~/piper-voices/en_US-lessac-medium.onnx.json \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

### 7. Find your audio devices

```bash
aplay -l    # speaker card number
arecord -l  # mic card number
```

Update `MIC_DEVICE_INDEX` and `SPEAKER_DEVICE` in `sage.py` to match your hardware.

### 8. Create credentials file

Create `~/.sage_credentials` (gitignored):

```
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
ANTHROPIC_API_KEY=your_anthropic_api_key
```

> Spotify and Anthropic keys are optional. Sage works fully without them — you just won't have music or Claude chat.

### 9. Personal config (optional)

Create `~/.sage_config.json` for presets, reminders, calendar, and notifications:

```json
{
    "preset_timers": {
        "pasta": 720,
        "rice": 420,
        "chicken nuggets": 780,
        "eggs": 600
    },
    "scheduled_reminders": [
        {
            "message": "Time for your meeting!",
            "hour": 9,
            "minute": 0,
            "days": [0, 1, 2, 3, 4],
            "skip_months": []
        }
    ],
    "ical_url": "your-google-calendar-secret-ical-url",
    "calendar_notify_minutes_before": 15,
    "ntfy_url": "https://ntfy.sh",
    "ntfy_topic": "your-secret-topic-name"
}
```

### 10. Set up the systemd service

```bash
sudo tee /etc/systemd/system/sage.service << EOF
[Unit]
Description=Sage Voice Assistant
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
User=sage
WorkingDirectory=/home/sage
ExecStart=/usr/bin/python3 /home/sage/sage.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable sage
sudo systemctl start sage
```

### 11. Firewall (recommended)

```bash
sudo apt install -y ufw
sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw --force enable
```

### 12. Train your wake word (optional)

The included `hey_sage.onnx` and `hey_claude.onnx` models work out of the box but were trained on one family's voices. For best results, train your own using [openWakeWord](https://github.com/dscripka/openWakeWord). Record 30 samples per household member saying "hey sage" and retrain.

---

## How it works

```
Wake word detection (openWakeWord + Vosk)
              |
     "Hey Sage" detected → Chime → Record audio
              |                         |
              |              Faster Whisper (local STT)
              |                         |
              |                  Command parsed
              |                    /        \
              |            Sage command    "Hey Claude"
              |           (local)          (API call)
              |              |                |
              |         handle_command    Claude responds
              |              |                |
              └──── Piper TTS → Speaker ──────┘
                              |
              Scheduled reminders ─┐
              Calendar events ─────┤→ ntfy push → Phone
              Security alerts ─────┘
```

All speech processing happens on-device. Outbound network traffic is limited to: Spotify streaming, ntfy push notifications, weather API (Open-Meteo), Google Calendar iCal fetches, and Claude API calls (only when you say "Hey Claude").

---

## Voice commands

### Sage commands (all local, no cloud)

| Command | What it does |
|---|---|
| "Hey Sage" | Wake word — activates Sage |
| "Set a timer for 10 minutes" | Starts a countdown timer |
| "Set a pasta timer for 12 minutes" | Named timer |
| "Chicken nuggets" | Preset timer (13 min) |
| "What timers are running?" | Lists active timers |
| "How much time is left?" | Time remaining on timers |
| "Stop" / "Stop the timer" | Dismisses ringing alarm |
| "Cancel all timers" | Cancels pending timers |
| "Cancel all reminders" | Cancels pending reminders |
| "Cancel everything" | Cancels all timers + reminders |
| "Remind me to X in 20 minutes" | Voice reminder (relative) |
| "Remind me to X at 5:30 PM" | Voice reminder (time-of-day) |
| "What's the weather?" | Today's conditions + tips |
| "What's the weather tomorrow?" | Tomorrow's forecast |
| "What's on the calendar?" | Today's events |
| "What time is it?" | Current time |
| "What day is it?" | Day and date |
| "Is the firewall running?" | Firewall status |
| "Turn on/off the firewall" | Enable/disable firewall |
| "System status" | Full system report |
| "Goodnight" | Enter bedtime mode |
| "Good morning" | Exit bedtime + briefing |
| "Tell me a joke" | Random kitchen joke |
| "Who are you?" | Self-introduction |
| "Who made you?" | Credits |
| "Thank you" | You're welcome! |

### Claude commands (requires API key)

| Command | What it does |
|---|---|
| "Hey Claude" | Activates Claude conversation mode |
| Ask anything | Open-ended Q&A, recipes, homework help, advice |
| "Goodbye" / "Thanks Claude" | Exit conversation, return to Sage |
| Ask for a timer/weather/etc. | Claude hands off to Sage automatically |

---

## LED ring wiring (optional)

If using a WS2812B LED ring (24-bit recommended):

| LED ring pin | Pi GPIO pin |
|---|---|
| 5V | Pin 2 or 4 |
| GND | Pin 6 |
| DIN | Pin 12 (GPIO 18) |

No soldering required — use female-to-female jumper wires.

---

## Troubleshooting

**Wake word not triggering**
- The included wake word models may not match your voice — retrain with your own samples
- Vosk fallback is enabled with common mishearings
- Move the mic away from the Pi's fan if possible (USB extension cable helps)

**Whisper recognition is poor**
- Fan noise is the most common issue — a USB extension cable for the mic helps significantly
- faster-whisper with the tiny.en model balances speed and accuracy on Pi 4

**"Sorry, I couldn't reach Claude"**
- Check your Anthropic API key in `~/.sage_credentials`
- Verify the model name in sage.py matches available models
- Check your API credit balance at console.anthropic.com

**Speaker not working**
- `sage.py` sets volume to max on startup — verify card numbers match your hardware
- Check with `aplay -l` and update `SPEAKER_DEVICE` in sage.py

**Service won't start**
- Check logs: `journalctl -u sage -f`
- Common issue: mic or speaker device busy from another process

---

## Privacy

- Voice is processed by [Vosk](https://alphacephei.com/vosk/) and [Faster Whisper](https://github.com/SYSTRAN/faster-whisper) running locally on the Pi
- Text-to-speech is handled by [Piper](https://github.com/rhasspy/piper) running locally on the Pi
- Wake word detection uses [openWakeWord](https://github.com/dscripka/openWakeWord) running locally
- No audio is ever sent to an external server or stored
- Claude AI chat is **opt-in** — only activates when you say "Hey Claude" and requires your own API key
- Internet is used only for: Spotify, weather (Open-Meteo), calendar (iCal), push notifications (ntfy), and Claude API
- All personal config, credentials, and voice profiles are gitignored

---

## License

**GPL v3** with commercial use restriction.

- Free to use, fork, and modify for personal and non-commercial use
- Commercial use requires written permission from the copyright holder
- Attribution required: **Britta Davis / [oh golly britta](https://ohgollybritta.com)**

See [LICENSE](LICENSE) for full terms.

---

*Built by [oh golly britta](https://ohgollybritta.com)*
