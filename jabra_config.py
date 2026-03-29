"""
jabra_config.py — Hardware configuration for Jabra SPEAK 510 USB

This file documents the Jabra-specific settings used in Sage v1.4.
The Jabra SPEAK 510 replaces the separate USB mic + USB speaker setup
with a single device that handles both input and output, and includes
built-in acoustic echo cancellation (AEC).

How to use:
    The values below override the defaults in sage.py.
    If you are using a Jabra SPEAK 510 (or similar USB speakerphone),
    apply these settings to your sage.py installation.

--------------------------------------------------------------------
DEVICE DETECTION
--------------------------------------------------------------------
The Jabra SPEAK 510 shows up on the same card for both mic and speaker:

    aplay -l   → card 1: USB [Jabra SPEAK 510 USB], device 0
    arecord -l → card 1: USB [Jabra SPEAK 510 USB], device 0

sage.py auto-detects this via find_usb_devices(), which searches
aplay/arecord output for "USB Audio". No manual card number needed.

--------------------------------------------------------------------
SAMPLE RATE
--------------------------------------------------------------------
The Jabra SPEAK 510 natively operates at 16000 Hz (16 kHz).
This is also the native rate for Vosk and Whisper — no resampling needed.

    MIC_RATE = 16000      # Jabra SPEAK 510 native rate

Old USB mic/speaker combo used 44100 Hz, requiring ratecv() downsampling.
With the Jabra, that downsampling is a no-op (same rate in and out).

--------------------------------------------------------------------
ALSA MIXER CONTROLS (card 1)
--------------------------------------------------------------------
Run `amixer -c 1 contents` to verify on your system.

    numid=3  PCM Playback Switch   → set to 'on'
    numid=4  PCM Playback Volume   → range 0–11, max = 11  (8.00 dB)
    numid=5  Mic Capture Switch    → set to 'on'
    numid=6  Mic Capture Volume    → range 0–7,  max = 7   (9.00 dB)

Commands to max out volume manually:
    amixer -c 1 cset numid=3 on
    amixer -c 1 cset numid=4 11
    amixer -c 1 cset numid=5 on
    amixer -c 1 cset numid=6 7

sage.py applies these automatically at startup via the
"Max volume at startup" block using the detected card number.

--------------------------------------------------------------------
RASPOTIFY
--------------------------------------------------------------------
Raspotify (librespot) should be configured to use the Jabra:

    /etc/raspotify/conf:
        LIBRESPOT_NAME="Sage"
        LIBRESPOT_DEVICE="plughw:1,0"

The auto-detect script (setup-raspotify.sh) handles this automatically
by scanning aplay -l for "USB Audio" and writing the correct card number.

--------------------------------------------------------------------
PYAUDIO MIC INDEX
--------------------------------------------------------------------
sage.py scans PyAudio devices and selects the first one matching
"USB PnP", "Jabra", or "USB Audio" with input channels > 0.

    MIC_DEVICE_INDEX = 1   (auto-detected — do not hardcode)

--------------------------------------------------------------------
WHY A SPEAKERPHONE?
--------------------------------------------------------------------
A standard USB mic placed near a speaker suffers from acoustic feedback:
the mic picks up the speaker output, causing false wake word triggers
and poor transcription. The Jabra SPEAK 510 solves this with:

    - Hardware acoustic echo cancellation (AEC)
    - Full-duplex audio (can hear you while playing audio)
    - Single USB connection for both mic and speaker
    - Omnidirectional mic designed to hear across a room

This allows Sage to hear "Hey Sage" even while music is playing —
something a single-mic setup cannot reliably do.

--------------------------------------------------------------------
ENCLOSURE NOTE (Sage v1.4 build)
--------------------------------------------------------------------
The Sage v1.4 prototype uses a perforated metal candle holder canister
as its enclosure. The Raspberry Pi 4 sits at the bottom, the Jabra
SPEAK 510 sits on top, and an LED ring will be added inside the canister
to glow through the perforations. The perforations allow both sound and
light to pass through while keeping the build self-contained.
"""

# ── Jabra SPEAK 510 settings reference ───────────────────────────────────────

JABRA_MIC_RATE        = 16000   # Hz — Jabra native sample rate
JABRA_PLAYBACK_NUMID  = 4       # amixer numid for PCM Playback Volume
JABRA_PLAYBACK_MAX    = 11      # max value (8.00 dB)
JABRA_MIC_NUMID       = 6       # amixer numid for Mic Capture Volume
JABRA_MIC_MAX         = 7       # max value (9.00 dB)
JABRA_DEVICE_NAME     = "Jabra SPEAK 510 USB"
JABRA_ALSA_DEVICE     = "plughw:1,0"   # adjust card number if needed

# Built by Britta Seisums Davis / ohgollybritta
