# Sage 🌿
### A privacy-first voice assistant for your kitchen, built on a Raspberry Pi.

Sage is an open-source voice assistant that does the everyday things a kitchen assistant should do — play music, set timers, give reminders — without sending a single byte of your voice to the cloud. It runs entirely on a Raspberry Pi.

> "Always-on shouldn't mean always uploading."

---

## Why Sage?

In early 2025, the last remaining opt-out for local voice processing was quietly removed from major commercial smart speakers. The official reason was generative AI — new features need the cloud. The effect was that users lost the ability to keep any part of their voice data on-device, with no alternative offered.

Sage is that alternative. The voice pipeline runs locally. Audio is never stored, never uploaded, never sent anywhere except out your speaker.

---

## Hardware

- **Raspberry Pi 4** (CanaKit)
- **USB microphone**
- **USB speaker**

---

## What it does

- 🎵 **Spotify playback** via voice — "Sage, play Fleetwood Mac"
- ⏱ **Kitchen timers** by voice — "Sage, set a timer for 10 minutes"
- ⏱ **Preset food timers** — "Sage, pasta timer" (customizable via config file)
- ⏱ **Named timers** — "Sage, set a chicken nuggets timer for 13 minutes"
- 🔔 **Scheduled reminders** — recurring alerts at specific times/days (configurable)
- 📅 **Google Calendar** — fetches today's events via iCal and sends push notifications before each one
- 📲 **Push notifications** — reminders and calendar events push to your phone via [ntfy](https://ntfy.sh)
- 🔕 **Persistent alarms** — timers and reminders repeat until you say "Sage, stop"
- 👂 **Wake word detection** — only activates when you say "Sage"
- 🔒 **Zero cloud audio** — voice is processed locally via Vosk
- 🗣 **Natural voice responses** — text-to-speech via Piper (local, no cloud)
- 🌐 **Internet only where needed** — Spotify streams; the voice pipeline does not
- 🚀 **Auto-start on boot** — runs as a systemd service

---

## Setup

### 1. Flash the SD card

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/). Choose **Raspberry Pi OS Lite (64-bit)**. In the settings before flashing, configure:

- Hostname: `sage`
- Enable SSH with password authentication
- Set your username and password
- Configure your WiFi network name and password
- Set WiFi country to `US`

### 2. SSH in

```bash
ssh yourusername@sage.local
```

### 3. Update the system

```bash
sudo apt update && sudo apt upgrade -y
```

### 4. Install Spotify Connect (Raspotify)

```bash
curl -sL https://dtcooper.github.io/raspotify/install.sh | sh
```

Edit the config:

```bash
sudo nano /etc/raspotify/conf
```

Set the following (remove the `#` from each line and update the device to match your speaker):

```
LIBRESPOT_NAME="Sage"
LIBRESPOT_DEVICE="plughw:CARD_NUMBER,0"
```

> Note: Do **not** set username/password — Spotify dropped password auth. Discovery mode works automatically.

Restart the service:

```bash
sudo systemctl daemon-reload
sudo systemctl restart raspotify
```

Open Spotify on any device on the same network — "Sage" will appear in the device list.

### 5. Find your audio device numbers

```bash
aplay -l    # speaker card number
arecord -l  # mic card number
```

Set speaker volume to max (replace `CARD` with your speaker's card number):

```bash
amixer -c CARD cset numid=2 on
amixer -c CARD cset numid=3 147,147
```

Boost mic capture volume (replace `CARD` with your mic's card number):

```bash
amixer -c CARD cset numid=3 16
```

> **Note:** These settings reset on reboot. They are automatically set by `/etc/rc.local` and by `sage.py` on startup — just make sure the card numbers are correct in both files.

### 6. Install Vosk (local speech-to-text)

```bash
sudo apt install -y python3-pip python3-pyaudio
pip3 install vosk --break-system-packages
```

For the small model (faster, less accurate):
```bash
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
```

For the medium model (recommended — better accuracy, fits in Pi 4 memory):
```bash
wget https://alphacephei.com/vosk/models/vosk-model-en-us-0.22-lgraph.zip
unzip vosk-model-en-us-0.22-lgraph.zip
```

> **Note:** The full model (`vosk-model-en-us-0.22`, ~1.8GB) is too large for the Pi 4's memory. Use the lgraph variant instead.

Update the model path in `sage.py` to match whichever you installed.

### 7. Install Piper (local text-to-speech)

Download the Piper binary:

```bash
wget https://github.com/rhasspy/piper/releases/latest/download/piper_linux_aarch64.tar.gz
tar xzf piper_linux_aarch64.tar.gz
sudo mv piper/piper /usr/local/bin/
sudo cp ~/piper/*.so* /usr/local/lib/
sudo ldconfig
```

Download the voice model:

```bash
mkdir -p ~/piper-voices
wget -O ~/piper-voices/en_US-lessac-medium.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget -O ~/piper-voices/en_US-lessac-medium.onnx.json \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

Install the espeak-ng library (required by Piper):

```bash
sudo apt install -y libespeak-ng1
```

### 8. Set up Spotify API credentials

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create an app with redirect URI `http://127.0.0.1:8888/callback`
3. Under **User Management**, add your Spotify account email
4. Note your **Client ID** and **Client Secret**

Install Spotipy:

```bash
pip3 install spotipy --break-system-packages
```

Create a credentials file at `~/.sage_credentials` (this file is gitignored):

```
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
```

> Never commit your credentials to GitHub. The `.sage_credentials` file is listed in `.gitignore`.

### 9. Authorize Spotify (one-time, run on your laptop)

Because the Pi is headless, the OAuth flow needs to run on a machine with a browser.

Copy `spotify_auth.py` to your laptop, create `~/.sage_credentials` there with your credentials, and run:

```bash
python3 spotify_auth.py
```

It will print a Spotify URL. Open it in your browser, log in, then paste the redirect URL back into the terminal. It will save `~/spotipy.cache`. Copy that to the Pi:

```bash
scp ~/spotipy.cache sage@sage.local:~/spotipy.cache
```

### 10. Configure device indices in sage.py

Before running Sage, check that the mic's PyAudio device index is correct:

```bash
python3 -c "import pyaudio; p=pyaudio.PyAudio(); [print(i, p.get_device_info_by_index(i)['name']) for i in range(p.get_device_count())]"
```

Update `MIC_DEVICE_INDEX` and `SPEAKER_DEVICE` in `sage.py` to match your hardware.

### 11. Personal config (optional)

Create `~/.sage_config.json` to add preset food timers, scheduled reminders, and push notifications. This file is gitignored so your personal settings stay private.

```json
{
    "preset_timers": {
        "pasta": 720,
        "rice": 420,
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

- **preset_timers**: food name mapped to seconds. Say "Sage, pasta timer" and it auto-sets.
- **scheduled_reminders**: recurring alerts. `days` uses 0=Monday through 6=Sunday. `skip_months` uses 1=January through 12=December. Reminders also push to your phone via ntfy.
- **ical_url**: your Google Calendar secret iCal address. Go to Google Calendar Settings → your calendar → "Secret address in iCal format". Events are fetched once daily; notifications push via ntfy before each event.
- **ntfy_url / ntfy_topic**: push notification settings. Install the [ntfy app](https://ntfy.sh) on your phone and subscribe to your topic to receive reminder and calendar notifications anywhere. Use a long random topic name for privacy.

### 12. Run Sage

Manually:
```bash
python3 ~/sage.py
```

Or enable the systemd service to auto-start on boot:
```bash
sudo systemctl enable sage
sudo systemctl start sage
```

Manage the service:
```bash
sudo systemctl status sage      # check if running
sudo systemctl restart sage     # restart after changes
sudo systemctl stop sage        # stop
journalctl -u sage -f           # watch live logs
```

Say **"Sage"** — she'll respond "Yes?" and listen for your command.

---

## How it works

```
Mic → PyAudio (44100Hz) → Downsample (16000Hz) → Vosk (local STT)
                                                        |
                                            Wake word detected → "Yes?"
                                                        |
                                            Listen for command → Action taken
                                                        |
                                      Timer / Preset / Reminder / Spotify
                                                        |
                                          Piper TTS → Speaker (response)
                                                        |
                               Scheduled reminders ─┐
                               Calendar events ─────┤→ ntfy push → Phone
```

All speech processing happens on-device. The only outbound network traffic is Spotify streaming, Spotify API calls, and ntfy push notifications for scheduled reminders — and only when you trigger it or at times you configure.

---

## Voice commands

| Command | Example |
|---|---|
| Wake word | "Sage" |
| Set a timer | "Set a timer for 10 minutes" |
| Named timer | "Set a chicken nuggets timer for 13 minutes" |
| Preset timer | "Pasta timer" |
| Check timers | "How much time is left?" |
| Cancel timer | "Cancel the timer" |
| Stop alarm | "Stop" |
| Play music | "Play Fleetwood Mac" |
| Pause music | "Stop" or "Pause" |
| Skip track | "Next" or "Skip" |

---

## Troubleshooting

**Sage hangs on startup / aplay error 524**
- Something else has the speaker locked (usually PulseAudio or Raspotify)
- Check with `fuser /dev/snd/*` and `ps aux | grep <pid>`
- Stop Raspotify before running Sage if they conflict: `sudo systemctl stop raspotify`
- If PulseAudio is running, kill it: `pulseaudio --kill`

**Raspotify won't start**
- Make sure username/password are commented out in `/etc/raspotify/conf`
- Use `plughw:CARD,0` not `hw:CARD,0` for the device

**Spotify shows "Sage" but won't connect**
- Run `sudo systemctl daemon-reload && sudo systemctl restart raspotify`
- Force-close and reopen Spotify on your phone
- Make sure your phone is on the same WiFi network as the Pi

**Mic not picking up voice**
- Mic capture volume defaults to 0 after reboot — `sage.py` sets it at startup
- Verify with `amixer -c CARD contents`

**Wake word not triggering**
- Vosk mishears "sage" as "age", "ames", or "page" at distance — all are included as wake words
- Speak clearly and pause after the wake word
- Use the lgraph model for better accuracy

**Vosk model too large for Pi 4**
- The full model (`vosk-model-en-us-0.22`, ~1.8GB) exceeds Pi 4 RAM
- Use `vosk-model-en-us-0.22-lgraph` (~128MB) instead — nearly as accurate

**Spotify auth "invalid client" error**
- Make sure your Spotify account email is added under User Management in the Developer Dashboard
- Redirect URI must be exactly `http://127.0.0.1:8888/callback` (not localhost)

**Piper symbol lookup error**
- Use `LD_PRELOAD=/home/sage/piper/libpiper_phonemize.so.1.2.0`

**Piper espeak data not found**
- Set `ESPEAK_DATA_PATH=/home/sage/piper/espeak-ng-data`

---

## Roadmap

- [x] Raspberry Pi setup
- [x] Spotify Connect via Raspotify
- [x] Local wake word detection via Vosk
- [x] Mic input + gain configuration
- [x] Text-to-speech responses via Piper
- [x] Sage talks back on wake word
- [x] Listen for command after wake word
- [x] Kitchen timers by voice
- [x] Named timers
- [x] Preset food timers (configurable)
- [x] Persistent alarms (repeat until dismissed)
- [x] Scheduled reminders
- [x] Auto-start on boot (systemd)
- [x] Audio downsampling for better STT accuracy
- [x] Max volume on boot
- [x] Push notifications for reminders (ntfy)
- [ ] Spotify voice control (in progress — auth being resolved)
- [ ] Voice-triggered reminders ("remind me to X in Y minutes")
- [x] Google Calendar integration (iCal)
- [ ] Tighten wake word accuracy

---

## Privacy

- Voice is processed by [Vosk](https://alphacephei.com/vosk/) running locally on the Pi
- Text-to-speech is handled by [Piper](https://github.com/rhasspy/piper) running locally on the Pi
- No audio is ever sent to an external server
- No audio is stored anywhere
- Internet is used only for Spotify streaming, Spotify API calls, Google Calendar iCal fetches, and ntfy push notifications
- Push notifications use a private, unguessable topic name — no account required
- Personal config (presets, reminders, calendar URL, ntfy topic) stays in `~/.sage_config.json` and is gitignored
- Credentials stay in `~/.sage_credentials` and are gitignored

---

## License

MIT — free to use, fork, and adapt.

---

*Built by [oh golly britta](https://ohgollybritta.com)*
