# Sage v2.0.0 🌿
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
- **USB microphone** — any USB mic works out of the box
- **USB speaker** — any USB speaker works out of the box
- **WS2812B LED ring** (optional — 24-bit, for visual indicators)
- **Female-to-male jumper wires** (3 needed — red, black, green — for LED ring)

### Recommended: USB speakerphone (optional upgrade)

A **USB conference speakerphone** like the **Jabra SPEAK 510** is optional but highly recommended if you want to use voice commands while music is playing. It combines mic and speaker into one USB device and includes hardware acoustic echo cancellation (AEC), which lets Sage hear "Hey Sage" even while audio is playing through it.

**Jabra SPEAK 510 benefits:**
- Single USB device = both mic and speaker on one card (e.g. `plughw:1,0`) — no separate detection needed
- Hardware AEC cancels speaker output from the mic signal — Sage can hear you over music
- Omnidirectional mic array designed for voice pickup across a room
- Works at the Pi's native 16000 Hz sample rate with no conversion needed
- Max volume: ALSA numid=4 (playback, 0–11), numid=6 (mic, 0–7)

> Sage is hardware-agnostic — it auto-detects your USB mic and speaker on startup. No manual configuration needed for standard setups. If you're using a Jabra SPEAK 510, see [`jabra_config.py`](jabra_config.py) for device-specific settings and notes.

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
- 📊 **System status** — "System status" (uptime, CPU usage, CPU temp, memory, disk, firewall)
- 🚨 **Intrusion detection** — voice + push alert on failed SSH login attempts
- 🔄 **Update checker** — notifies every 3 days if system or package updates are available

### Bedtime & Morning
- 😴 **Bedtime mode** — "Goodnight" silences alerts, dims lights
- ☀️ **Morning briefing** — "Good morning" triggers weather + calendar
- ⏰ Auto bedtime: 9:30 PM weekdays, 10:30 PM weekends
- ⏰ Auto wake: 6:30 AM weekdays, 8:30 AM Sat/Sun with full briefing

### Music (Spotify)
- 🎵 **Spotify playback** — "Play Fleetwood Mac", "Put on some jazz", "Listen to Taylor Swift"
- 🎵 **Natural phrasing** — understands "play", "put on", "throw on", "listen to", "queue up", "shuffle", "can you play", and more
- 🎵 **Song, artist, or playlist search** — searches tracks first, then artists, then playlists
- 🎵 **Play Spotify / Play music** — resumes where you left off, or shuffles liked songs if nothing was previously playing
- 🎵 **Pause/stop** — "Pause", "Stop the music", "Stop", "Mute"
- 🎵 **Resume** — "Resume", "Resume music", "Unpause"
- 🎵 **Skip/previous** — "Skip", "Next", "Previous", "Go back", "Last song"
- 🎵 **Volume control** — "Volume 50", "Turn up the volume", "Turn down the volume", "Full volume", "All the way down", "Turn your volume to zero"
- 🎵 **Default playback volume** — 90% when a song starts
- 🎵 **Now playing** — "What's playing?", "What song is this?", "Who is this?", "Who sings this?"
- 🎵 **Auto-pause on wake** — Sage pauses Spotify when it hears "Hey Sage" so it can hear your command, then resumes if the command wasn't music-related
- 🎵 **Plays through the Pi** — Raspotify turns the Pi into a Spotify Connect speaker
- 🎵 **Dynamic device discovery** — Sage finds the Spotify Connect speaker by name ("Sage"), caches the device ID, and restarts Raspotify as a last resort if the device disappears
- 🎵 **Liked songs shuffle** — "Play Spotify" or "Play music" with nothing active shuffles your saved/liked songs

### Speaker Volume
- 🔊 **Turn yourself up/down** — adjusts Sage's hardware speaker volume (separate from Spotify)
- 🔊 **Talk louder / Talk quieter** — natural phrasing for volume control
- 🔊 **Speaker volume up/down** — explicit speaker volume commands
- 🔊 Works through PulseAudio or ALSA depending on your setup

### Personality
- 🎭 Varied responses — Sage doesn't repeat the same phrase
- 😄 Easter eggs — "Tell me a joke", "Who are you?", "Who made you?", "When is your birthday?"
- 🙏 Says "you're welcome" when you say thanks
- 👤 **Voice identification** — "Who am I?" (guesses who's talking from voice profiles)
- 🗣️ **Self-identification on wake** — Sage and Claude both announce who they are when activated (e.g. "Sage here, what's up?" / "Claude here, what's your question?") so you always know who you're talking to
- ❌ **Dismiss on false wake** — say "nevermind", "cancel", "nothing", "forget it", or "nope" after a false trigger and Sage stands down gracefully

### Safety
- 🌡️ **Temperature monitoring** — checks CPU temp every 3 minutes
- 🌡️ **Fan control** — fan on GPIO 14 activates at 60°C, off at 55°C
- ⚠️ **Warm warning** — speaks and sends notification at 75°C
- 🔥 **Critical warning** — speaks and sends notification at 82°C
- 🚨 **Emergency shutdown** — automatic shutdown at 83°C to protect hardware

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
pip3 install vosk faster-whisper spotipy python-dateutil icalendar onnxruntime --break-system-packages
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

### 7. Install Raspotify (optional — for Spotify playback through the Pi)

```bash
curl -sL https://dtcooper.github.io/raspotify/install.sh | sh
```

#### Auto-detect speaker script

Create `/usr/local/bin/setup-raspotify.sh` to auto-detect your USB speaker on every boot:

```bash
sudo tee /usr/local/bin/setup-raspotify.sh << 'EOF'
#!/bin/bash
CARD=$(aplay -l 2>/dev/null | grep -i 'USB Audio\|UACDemo' | head -1 | sed 's/card \([0-9]*\).*/\1/')
if [ -z "$CARD" ]; then
    CARD=4
fi
cat > /etc/raspotify/conf << CONF
LIBRESPOT_NAME="Sage"
LIBRESPOT_BACKEND="pulseaudio"
CONF
EOF
sudo chmod +x /usr/local/bin/setup-raspotify.sh
```

Create a systemd service to run this before Raspotify starts:

```bash
sudo tee /etc/systemd/system/setup-raspotify.service << EOF
[Unit]
Description=Auto-detect USB speaker for Raspotify
Before=raspotify.service
Wants=sound.target
After=sound.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/setup-raspotify.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable setup-raspotify.service
```

#### PulseAudio override for Raspotify

Raspotify runs as root by default, which can't access the user's PulseAudio session. Create a systemd override so it runs as the `sage` user with PulseAudio access:

```bash
sudo mkdir -p /etc/systemd/system/raspotify.service.d
sudo tee /etc/systemd/system/raspotify.service.d/override.conf << EOF
[Service]
User=sage
Group=sage
Environment=PULSE_SERVER=unix:/run/user/1000/pulse/native
ProtectHome=false
PrivateUsers=false
EOF
sudo systemctl daemon-reload
sudo systemctl restart raspotify
```

This allows Sage's TTS and Spotify to share the same speaker through PulseAudio without device-busy conflicts.

#### Open firewall for Spotify Connect

Raspotify uses mDNS (Avahi) for device discovery and needs LAN access for Spotify Connect:

```bash
sudo ufw allow 5353/udp comment 'mDNS/Avahi'
sudo ufw allow proto tcp from 192.168.0.0/24 to any port 1:65535 comment 'Spotify Connect LAN'
sudo ufw reload
```

#### Set up PulseAudio for echo cancellation (recommended)

Sage routes audio through PulseAudio's software echo cancellation (AEC) when PulseAudio is available. This lets Sage hear "Hey Sage" even while music is playing through the same speaker — the AEC removes the speaker output from the mic signal in real time.

**Enable PulseAudio user service:**

```bash
# Enable linger so PulseAudio starts at boot without a login session
sudo loginctl enable-linger $USER

# Unmask and enable the PulseAudio user service
systemctl --user unmask pulseaudio pulseaudio.socket
systemctl --user enable --now pulseaudio
```

**Create the Jabra AEC config snippet** (or adapt for your hardware):

```bash
sudo tee /etc/pulse/default.pa.d/jabra-aec.pa << 'EOF'
### Sage - USB speakerphone with Echo Cancellation

# Speaker output
load-module module-alsa-sink device=plughw:1,0 sink_name=jabra_sink rate=48000

# Mic input (native 16kHz mono)
load-module module-alsa-source device=plughw:1,0 source_name=jabra_source rate=16000 channels=1

# Echo cancellation virtual devices (webrtc AEC)
load-module module-echo-cancel source_master=jabra_source sink_master=jabra_sink source_name=jabra_ec_source sink_name=jabra_ec_sink

# Make AEC devices the default
set-default-sink jabra_ec_sink
set-default-source jabra_ec_source
EOF
```

> Replace `plughw:1,0` with your actual speaker/mic card number if needed (check `aplay -l`). The card number must match your hardware — see the note on dynamic card numbers below.

**Update sage.service to connect to PulseAudio:**

```bash
sudo tee /etc/systemd/system/sage.service << 'EOF'
[Unit]
Description=Sage Voice Assistant
After=network.target sound.target pulseaudio.service
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=simple
User=sage
WorkingDirectory=/home/sage
ExecStartPre=/bin/sleep 5
Environment=JACK_NO_START_SERVER=1
Environment=PULSE_LOG=0
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=PULSE_SERVER=unix:/run/user/1000/pulse/native
ExecStart=/usr/bin/python3 /home/sage/sage.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
```

Sage auto-detects the PulseAudio socket at startup. When PulseAudio is running, Sage routes all audio (`aplay`, `arecord`, PyAudio) through the `jabra_ec_source`/`jabra_ec_sink` virtual devices, engaging AEC. When PulseAudio is not available, Sage falls back to direct ALSA without AEC.

#### Verify

```bash
sudo systemctl restart raspotify
journalctl -u raspotify -n 10   # should see "Published zeroconf service"
```

Raspotify makes the Pi a Spotify Connect speaker called "Sage". The auto-detect script ensures the correct speaker card is used even if USB device order changes across reboots.

### How Spotify works on Sage

Spotify on Sage involves three separate components that must all be on the **same Spotify account**:

1. **Raspotify (librespot)** — a Spotify Connect client that runs as a system service. It registers the Pi as a speaker called "Sage" on your local network, receives audio streams from Spotify, and plays them through the USB speaker.

2. **Spotipy (Python API client)** — runs inside `sage.py`. It handles voice commands: searching for songs, starting/pausing playback, controlling volume, and checking what's playing. It communicates with Spotify's Web API.

3. **Spotify Connect discovery** — uses mDNS/Avahi (port 5353) so the Pi appears as a speaker in Spotify's device list on your phone, computer, or the web player.

#### Dedicated Spotify account recommended

**We strongly recommend using a separate, dedicated Spotify account for Sage** rather than your personal account. Here's why:

- Raspotify and Spotipy must be logged into the **same account** for voice commands to work. If they're on different accounts, `sp.devices()` can't see the Raspotify speaker.
- If Sage uses your personal account, playing music on your phone will conflict with the Pi — Spotify only allows one active stream per account (unless you have a Family/Duo plan).
- A dedicated account keeps your personal listening history, recommendations, and playlists separate from Sage's activity.
- A Spotify Free account works, though playback may include ads. A second Premium account on a Family plan is ideal.

#### How voice commands flow

```
"Hey Sage, play Fleetwood Mac"
        |
   Wake word detected → Spotify paused (if playing) → Chime
        |
   Whisper transcribes: "play fleetwood mac"
        |
   Phrase matched → query extracted: "fleetwood mac"
        |
   Spotipy searches Spotify API (track → artist → playlist)
        |
   Sage speaks: "Playing Fleetwood Mac"
        |
   Spotipy calls start_playback(device_id=SAGE_DEVICE_ID)
        |
   Raspotify receives the stream → plays through USB speaker
```

#### Device discovery and the idle problem

Raspotify only appears in the Spotify device list when it has recently been active. After being idle for a while, it becomes invisible to `sp.devices()`. Sage handles this automatically with dynamic device discovery:

1. **Name-based lookup** — Sage searches `sp.devices()` for a device named "Sage" (the Raspotify device name)
2. **Cached device ID** — once found, the device ID is cached to avoid repeated API calls
3. **`transfer_playback()`** — attempts to wake the device by transferring playback to it directly
4. **Auto-restart** — if all else fails, Sage restarts the Raspotify service and retries

No hardcoded device IDs needed — Sage discovers the speaker automatically on every boot and after every Raspotify restart.

### 8a. Find your audio devices

```bash
aplay -l    # speaker card number
arecord -l  # mic card number
```

Update `MIC_DEVICE_INDEX` and `SPEAKER_DEVICE` in `sage.py` to match your hardware.

### 8b. Create credentials file

Create `~/.sage_credentials` (gitignored):

```
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REFRESH_TOKEN=
ANTHROPIC_API_KEY=your_anthropic_api_key
```

> Spotify and Anthropic keys are optional. Sage works fully without them — you just won't have music or Claude chat.

### 8c. Spotify authentication (if using Spotify)

1. Create a [Spotify Developer App](https://developer.spotify.com/dashboard)
2. Set the Redirect URI to `http://127.0.0.1:8888/callback` in your app settings
3. Add your Client ID and Secret to `~/.sage_credentials`
4. Run `python3 ~/spotify_auth.py` — open the URL in a browser, log in with the **Sage/group account**, paste the redirect URL back
5. Token is cached at `~/spotipy.cache` — Sage will auto-refresh it

> **Required scopes:** `user-modify-playback-state user-read-playback-state user-library-read` — the `user-library-read` scope is needed for "Play Spotify / Play my liked songs" to work. If you need to re-auth to add this scope, delete `~/spotipy.cache` and re-run `spotify_auth.py`.

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

### 12. Wake word tuning

Wake word detection uses a **dual-detector** approach:

1. **MFCC wake word model** (primary) — a custom GradientBoosting classifier trained on temporal MFCC features. Extracts 362-dimensional feature vectors from 2-second audio clips, dividing frames into 8 temporal segments to preserve *when* sounds happen, not just what. Exported as an ONNX model (`hey_sage_mfcc_v5.onnx`). Runs inference every 2 audio chunks when audio energy exceeds the RMS gate.

2. **Vosk** (fallback) — local speech recognition that listens for "hey sage" and common mishearings ("they sage", "hey stage"). Always running as a safety net.

Either detector can trigger the wake word. Both run entirely on-device.

#### Tuning sensitivity

- `DAYTIME_RMS_GATE` — minimum audio energy to trigger during the day (default: 80). Lower = more sensitive, higher = requires louder speech.
- `BEDTIME_RMS_GATE` — minimum audio energy to trigger at night (default: 100). Slightly higher to avoid accidental triggers from sleep-talking or ambient noise.
- `WW_THRESHOLD` — MFCC model confidence threshold (default: 0.92). Higher = fewer false triggers but may require more attempts.
- `WW_COOLDOWN` — minimum seconds between MFCC wake triggers (default: 5). Prevents rapid re-triggering.
- All values are in `sage.py`. Adjust based on your mic distance and environment.

---

## How it works

```
Wake word detection (MFCC model + Vosk fallback)
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
| "Play [song/artist/playlist]" | Play music on Spotify |
| "Put on [artist]" / "Throw on [song]" | Natural play phrases |
| "Listen to [artist]" / "Queue up [song]" | More natural play phrases |
| "Play [song] on Spotify" | Explicit Spotify request |
| "Play music" / "Play Spotify" / "Play something" | Resume where left off, or shuffle liked songs |
| "Pause" / "Stop the music" / "Mute" | Pause playback |
| "Resume" / "Unpause" | Resume playback |
| "Skip" / "Next" | Skip to next track |
| "Previous" / "Go back" / "Last song" | Go to previous track |
| "Volume [0–100]" | Set exact volume level |
| "Volume up" / "Turn up the volume" / "Louder" | Increase volume by 15% |
| "Volume down" / "Turn down the volume" / "Quieter" / "Softer" | Decrease volume by 15% |
| "Full volume" / "All the way up" / "Maximum" | Set volume to 100% |
| "Turn your volume to zero" / "All the way down" / "Silent" | Set volume to 0% |
| "What's playing?" / "What song is this?" | Currently playing track + artist |
| "Who is this?" / "Who sings this?" | Identify current artist |
| "Turn yourself up/down" | Adjust Sage's speaker volume |
| "Speaker volume up/down" | Adjust Sage's speaker volume |
| "Talk louder" / "Talk quieter" | Adjust Sage's speaker volume |
| "Nevermind" / "Cancel" / "Forget it" / "Nope" | Dismiss a false wake trigger |

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
| DIN | Pin 19 (GPIO 10 / SPI) |

Soldering required to attach jumper wires to the LED ring pads (PWR, GND, DIN). Use female-to-male jumper wires from the ring to the Pi GPIO header.

> **Note:** GPIO 18 (PWM) conflicts with the Pi's onboard audio driver (`snd_bcm2835`). GPIO 10 (SPI) avoids this conflict. SPI must be enabled: `sudo raspi-config nonint do_spi 0`.

---

## Troubleshooting

**Wake word not triggering**
- Sage uses dual detection: MFCC model (primary) + Vosk (fallback)
- The MFCC model requires sufficient audio energy (`RMS_GATE * 2`) and buffer energy (`_buf_rms > 150`) to run inference
- Lower `DAYTIME_RMS_GATE` in `sage.py` if Sage consistently misses you (default: 80)
- Lower `WW_THRESHOLD` (default: 0.92) if the MFCC model isn't triggering — but too low causes false positives
- Move the mic away from the Pi's fan if possible (USB extension cable helps)

**Whisper recognition is poor**
- Fan noise is the most common issue with generic microphones — a USB extension cable helps separate the mic from the fan
- faster-whisper with the base.en model balances speed and accuracy on Pi 4
- Sage calibrates a noise baseline before each recording to filter ambient noise

**"Sorry, I couldn't reach Claude"**
- Check your Anthropic API key in `~/.sage_credentials`
- Verify the model name in sage.py matches available models
- Check your API credit balance at console.anthropic.com

**Speaker not working**
- `sage.py` sets volume to max on startup — verify card numbers match your hardware
- Check with `aplay -l` and `arecord -l` to confirm the correct ALSA card number
- If PulseAudio is running, Sage routes through it automatically — check `XDG_RUNTIME_DIR=/run/user/1000 pactl info` to verify PulseAudio is up
- Check `sudo fuser -v /dev/snd/*` to see what's holding the audio devices
- If PulseAudio fails to load the Jabra source: the raw device may already be held by another process — ensure sage.service is stopped before debugging PulseAudio device loading

**Spotify not playing / "Can't find the speaker"**
- Raspotify and Spotipy must be on the **same Spotify account**
- Check that Raspotify is running: `systemctl status raspotify`
- Check Raspotify logs for crashes: `journalctl -u raspotify -n 20`
- If you see `Unsupported Sample Rate 44100` — your speaker doesn't support 44100 Hz. Use `plughw:X,0` (not `hw:X,0`) in the Raspotify config so ALSA handles rate conversion
- The Spotify device goes idle/invisible after inactivity — Sage automatically restarts Raspotify and retries when this happens
- Verify firewall allows mDNS: `sudo ufw status` should show port 5353/udp open
- Check `avahi-daemon` is running: `systemctl status avahi-daemon`

**Spotify says "Connection aborted" or "RemoteDisconnected"**
- This is usually a transient network issue — Sage will auto-retry once
- Check the Pi's internet connection: `ping -c 3 spotify.com`
- Token may need refresh — delete `~/spotipy.cache` and re-run `python3 ~/spotify_auth.py`

**Wake word not detected over music**
- With PulseAudio AEC enabled (see setup), Sage uses the echo-cancelled mic signal — this is the most effective approach
- A USB conference speakerphone like the **Jabra SPEAK 510** is also recommended — hardware AEC provides a second layer of echo cancellation
- Sage auto-pauses Spotify when it detects the wake word, but the word must be heard first
- With a single-mic setup and no AEC, keeping Spotify volume at 75% or lower helps
**Too many false wake triggers (TV, ambient noise)**
- Raise `WW_THRESHOLD` (default: 0.92) to require higher MFCC model confidence
- Raise `DAYTIME_RMS_GATE` in `sage.py` (default: 80) to require louder speech
- Increase `WW_COOLDOWN` (default: 5 seconds) to prevent rapid re-triggering
- The MFCC model was trained on 1,800 real ambient clips — if your environment differs significantly, retraining may help

**Service won't start**
- Check logs: `journalctl -u sage -f`
- Common issue: mic or speaker device busy from another process

---

## Privacy

- Voice is processed by [Vosk](https://alphacephei.com/vosk/) and [Faster Whisper](https://github.com/SYSTRAN/faster-whisper) running locally on the Pi
- Text-to-speech is handled by [Piper](https://github.com/rhasspy/piper) running locally on the Pi
- Wake word detection uses a custom MFCC model (ONNX) + [Vosk](https://alphacephei.com/vosk/) fallback, both running locally
- No audio is ever sent to an external server or stored
- Claude AI chat is **opt-in** — only activates when you say "Hey Claude" and requires your own API key
- Internet is used only for: Spotify, weather (Open-Meteo), calendar (iCal), push notifications (ntfy), and Claude API


---

## License

**GPL v3** with commercial use restriction.

- Free to use, fork, and modify for personal and non-commercial use
- Commercial use requires written permission from the copyright holder
- Attribution required: **Britta Davis / [ohgollybritta](https://ohgollybritta.com)**

See [LICENSE](LICENSE) for full terms.

---

*Built by [ohgollybritta](https://ohgollybritta.com)*
