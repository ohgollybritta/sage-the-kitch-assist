"""
Sage LED Ring Controller
WS2812B 16-LED ring on GPIO 18
Colors and patterns for each Sage state.
"""
import threading
import time
import math

try:
    from rpi_ws281x import PixelStrip, Color
    LED_AVAILABLE = True
except ImportError:
    LED_AVAILABLE = False

# ── Configuration ────────────────────────────────────────────────────────────
LED_COUNT = 16         # Number of LEDs on the ring
LED_PIN = 18           # GPIO pin (must be PWM-capable: 18 or 12)
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 80    # 0-255 — keep moderate for ambient use
LED_INVERT = False
LED_CHANNEL = 0

# ── Colors ───────────────────────────────────────────────────────────────────
WARM_AMBER = (255, 140, 20)
SOFT_BLUE = (30, 100, 255)
GREEN = (0, 255, 60)
RED = (255, 20, 0)
ORANGE = (255, 80, 0)
WHITE = (255, 200, 150)   # warm white
OFF = (0, 0, 0)

# ── Controller ───────────────────────────────────────────────────────────────
class SageLights:
    def __init__(self):
        self._state = "off"
        self._running = True
        self._lock = threading.Lock()
        self.strip = None

        if LED_AVAILABLE:
            try:
                self.strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ,
                                        LED_DMA, LED_INVERT, LED_BRIGHTNESS,
                                        LED_CHANNEL)
                self.strip.begin()
                print("LED ring initialized", flush=True)
            except Exception as e:
                print(f"LED init failed: {e}", flush=True)
                self.strip = None
        else:
            print("LED library not available — running without lights", flush=True)

        # Start animation thread
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def _set_all(self, r, g, b):
        """Set all LEDs to one color."""
        if not self.strip:
            return
        for i in range(LED_COUNT):
            self.strip.setPixelColor(i, Color(r, g, b))
        self.strip.show()

    def _set_brightness_color(self, r, g, b, brightness):
        """Set all LEDs with a brightness multiplier (0.0 - 1.0)."""
        self._set_all(int(r * brightness), int(g * brightness), int(b * brightness))

    def _animate(self):
        """Background animation loop."""
        while self._running:
            state = self._state
            t = time.time()

            if state == "idle":
                # Warm amber gentle breathing
                breath = 0.4 + 0.3 * math.sin(t * 0.8)
                self._set_brightness_color(*WARM_AMBER, breath)

            elif state == "wake":
                # Blue pulse — quick ramp up
                phase = (t * 3) % 1.0
                brightness = 0.3 + 0.7 * math.sin(phase * math.pi)
                self._set_brightness_color(*SOFT_BLUE, brightness)

            elif state == "listening":
                # Solid soft blue
                self._set_brightness_color(*SOFT_BLUE, 0.7)

            elif state == "processing":
                # Blue spinning/chasing effect
                if self.strip:
                    pos = int((t * 8) % LED_COUNT)
                    for i in range(LED_COUNT):
                        dist = min(abs(i - pos), LED_COUNT - abs(i - pos))
                        brightness = max(0.05, 1.0 - dist * 0.2)
                        r = int(SOFT_BLUE[0] * brightness)
                        g = int(SOFT_BLUE[1] * brightness)
                        b = int(SOFT_BLUE[2] * brightness)
                        self.strip.setPixelColor(i, Color(r, g, b))
                    self.strip.show()

            elif state == "success":
                # Quick green flash
                self._set_brightness_color(*GREEN, 0.8)

            elif state == "timer_counting":
                # Slow warm pulse
                breath = 0.3 + 0.4 * math.sin(t * 1.2)
                self._set_brightness_color(*ORANGE, breath)

            elif state == "alarm":
                # Orange/red flash — alternating
                flash = int(t * 4) % 2
                if flash:
                    self._set_brightness_color(*RED, 0.9)
                else:
                    self._set_brightness_color(*ORANGE, 0.6)

            elif state == "security":
                # Red strobe
                flash = int(t * 6) % 2
                if flash:
                    self._set_brightness_color(*RED, 1.0)
                else:
                    self._set_all(0, 0, 0)

            elif state == "off":
                self._set_all(0, 0, 0)

            time.sleep(0.05)  # ~20 FPS

    def set_state(self, state):
        """Change the light state. Valid states:
           idle, wake, listening, processing, success,
           timer_counting, alarm, security, off
        """
        with self._lock:
            self._state = state
        # For quick flash states, auto-revert
        if state == "success":
            threading.Timer(1.0, lambda: self.set_state("idle")).start()

    def cleanup(self):
        """Turn off all LEDs."""
        self._running = False
        self._set_all(0, 0, 0)


# Singleton instance
lights = SageLights()
