import machine, time, math
from neopixel import NeoPixel

# ===== CONFIG =====
MIC_PIN = 26       # ADC0 (GP26)
POT_PIN = 27       # ADC1 (GP27)
LED_PIN = 2        # WS2812 Data pin (GP2)
BTN_PIN = 15       # Push button to reset
NUM_LEDS = 39
SAMPLES = 150
FAST_DELAY = 0.01

RISE_RATE = 0.08   # smooth attack only (no decay)

adc = machine.ADC(MIC_PIN)
pot = machine.ADC(POT_PIN)
np = NeoPixel(machine.Pin(LED_PIN), NUM_LEDS)

button = machine.Pin(BTN_PIN, machine.Pin.IN, machine.Pin.PULL_UP)

# === Color Gradient: Green → Yellow → Red ===
def color_from_fraction(f):
    f = max(0.0, min(1.0, f))
    if f <= 0.5:
        t = f / 0.5
        return (int(255 * t), 255, 0)
    else:
        t = (f - 0.5) / 0.5
        return (255, int(255 * (1 - t)), 0)

# === ADC RMS ===
def read_rms(samples=SAMPLES):
    vals = [adc.read_u16() for _ in range(samples)]
    mean = sum(vals) / len(vals)
    sq = sum((v - mean) ** 2 for v in vals) / len(vals)
    return math.sqrt(sq)

# === Show LEDs ===
def show_bar(level):
    leds_on = int(level * NUM_LEDS)
    for i in range(NUM_LEDS):
        if i < leds_on:
            frac = i / (NUM_LEDS - 1)
            np[i] = color_from_fraction(frac)
        else:
            np[i] = (0, 0, 0)
    np.write()

def clear_strip():
    for i in range(NUM_LEDS):
        np[i] = (0, 0, 0)
    np.write()

# === Main Loop ===
try:
    current_level = 0.0

    while True:
        # Check button
        if button.value() == 0:   # pressed (active low)
            current_level = 0.0
            clear_strip()
            time.sleep(0.3)  # debounce

        rms = read_rms()

        # Potentiometer sets threshold
        pot_val = pot.read_u16() / 65535
        threshold = 1000 + pot_val * 30000  # adjust range for your mic

        # Difference from threshold
        diff = max(0.0, rms - threshold)
        norm = min(1.0, diff / 15000)

        # Smooth attack, no decay
        if norm > current_level:
            current_level += (norm - current_level) * RISE_RATE
            if current_level > norm:
                current_level = norm
        # else: do nothing (hold peak)

        show_bar(current_level)
        time.sleep(FAST_DELAY)

except KeyboardInterrupt:
    clear_strip()

