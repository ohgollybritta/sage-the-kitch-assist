# Sage v1.4 🌿
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

### Music (Spotify)
- 🎵 **Spotify playback** — "Play Fleetwood Mac", "Put on some jazz", "Listen to Taylor Swift"
- 🎵 **Natural phrasing** — understands "play", "put on", "throw on", "listen to", "queue up", "shuffle", "can you play", and more
- 🎵 **Song, artist, or playlist search** — searches tracks first, then artists, then playlists
- 🎵 **Pause/stop** — "Pause", "Stop the music", "Stop", "Mute"
- 🎵 **Resume** — "Resume", "Resume music", "Unpause"
- 🎵 **Skip/previous** — "Skip", "Next", "Previous", "Go back", "Last song"
- 🎵 **Volume control** — "Volume 50", "Volume up", "Volume down"
- 🎵 **Now playing** — "What's playing?", "What song is this?", "Who is this?", "Who sings this?"
- 🎵 **Auto-pause on wake** — Sage pauses Spotify when it hears "Hey Sage" so it can hear your command, then resumes if the command wasn't music-related
- 🎵 **Plays through the Pi** — Raspotify turns the Pi into a Spotify Connect speaker
- 🎵 **Hardcoded device fallback** — if the Spotify API can't find the speaker, Sage falls back to a known device ID and restarts Raspotify automatically

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
LIBRESPOT_DEVICE="plughw:${CARD},0"
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

#### Open firewall for Spotify Connect

Raspotify uses mDNS (Avahi) for device discovery and needs LAN access for Spotify Connect:

```bash
sudo ufw allow 5353/udp comment 'mDNS/Avahi'
sudo ufw allow proto tcp from 192.168.0.0/24 to any port 1:65535 comment 'Spotify Connect LAN'
sudo ufw reload
```

#### Disable PulseAudio (important)

PulseAudio grabs the audio device and blocks direct ALSA access. Sage and Raspotify both need direct access to `plughw`:

```bash
systemctl --user stop pulseaudio.socket pulseaudio.service
systemctl --user disable pulseaudio.socket pulseaudio.service
systemctl --user mask pulseaudio.socket pulseaudio.service
mkdir -p ~/.config/pulse
echo 'autospawn = no' > ~/.config/pulse/client.conf
```

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

Raspotify only appears in the Spotify device list when it has recently been active. After being idle for a while, it becomes invisible to `sp.devices()`. Sage handles this with:

1. **Hardcoded device ID fallback** — if the API can't find the device, Sage uses a known device ID stored in the code
2. **Auto-restart** — if the hardcoded ID also fails, Sage restarts the Raspotify service and retries
3. **`transfer_playback()`** — attempts to wake the device by transferring playback to it directly

To get the device ID for your setup, play something on Sage from the Spotify app, then run:

```python
python3 -c "
import spotipy
from spotipy.oauth2 import SpotifyOAuth
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(...))
for d in sp.devices()['devices']:
    print(f\"{d['name']}: {d['id']}\")
"
```

Copy the Sage device ID into the `_SAGE_DEVICE_ID` variable in `sage.py`.

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
4. Run `python3 ~/spotify_auth.py` — open the URL in a browser, log in, paste the redirect URL back
5. Token is cached at `~/spotipy.cache` — Sage will auto-refresh it

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

The included `hey_sage.onnx` and `hey_claude.onnx` models work out of the box but were trained on one family's voices. For best results, train your own using [openWakeWord](https://github.com/dscripka/openWakeWord). Record 30+ samples per household member saying "hey sage" and retrain.

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
| "Play [song/artist/playlist]" | Play music on Spotify |
| "Put on [artist]" / "Throw on [song]" | Natural play phrases |
| "Listen to [artist]" / "Queue up [song]" | More natural play phrases |
| "Play [song] on Spotify" | Explicit Spotify request |
| "Play music" / "Play something" | Resume or start radio |
| "Pause" / "Stop the music" / "Mute" | Pause playback |
| "Resume" / "Unpause" | Resume playback |
| "Skip" / "Next" | Skip to next track |
| "Previous" / "Go back" / "Last song" | Go to previous track |
| "Volume [0–100]" | Set volume level |
| "Volume up" / "Volume down" | Adjust volume by 15% |
| "What's playing?" / "What song is this?" | Currently playing track + artist |
| "Who is this?" / "Who sings this?" | Identify current artist |

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
- faster-whisper with the base.en model balances speed and accuracy on Pi 4
- Sage calibrates a noise baseline before each recording to filter ambient noise

**"Sorry, I couldn't reach Claude"**
- Check your Anthropic API key in `~/.sage_credentials`
- Verify the model name in sage.py matches available models
- Check your API credit balance at console.anthropic.com

**Speaker not working**
- `sage.py` sets volume to max on startup — verify card numbers match your hardware
- Check with `aplay -l` and update `SPEAKER_DEVICE` in sage.py
- Make sure PulseAudio is disabled — it grabs the audio device and blocks direct ALSA access
- Check `sudo fuser -v /dev/snd/*` to see what's holding the audio devices

**Spotify not playing / "Can't find the speaker"**
- Raspotify and Spotipy must be on the **same Spotify account**
- Check that Raspotify is running: `systemctl status raspotify`
- Check Raspotify logs for crashes: `journalctl -u raspotify -n 20`
- If you see `Unsupported Sample Rate 44100` — your speaker doesn't support 44100 Hz. Use `plughw:X,0` (not `hw:X,0`) in the Raspotify config so ALSA handles rate conversion
- The Spotify device goes idle/invisible after inactivity — play something from the Spotify app to wake it up, then voice commands will work
- Verify firewall allows mDNS: `sudo ufw status` should show port 5353/udp open
- Check `avahi-daemon` is running: `systemctl status avahi-daemon`

**Spotify says "Connection aborted" or "RemoteDisconnected"**
- This is usually a transient network issue — Sage will auto-retry once
- Check the Pi's internet connection: `ping -c 3 spotify.com`
- Token may need refresh — delete `~/spotipy.cache` and re-run `python3 ~/spotify_auth.py`

**Wake word not detected over music**
- This is a hardware limitation of single-mic setups — the mic picks up the speaker output
- A USB conference speakerphone with built-in echo cancellation (e.g., Jabra Speak) significantly improves this
- Sage auto-pauses Spotify when it detects the wake word, but the word must be heard first
- Keeping Spotify volume at 75% or lower helps the mic hear you

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
