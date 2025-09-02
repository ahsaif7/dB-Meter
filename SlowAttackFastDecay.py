#Slow Attack Fast Decay

import machine, time, math
from neopixel import NeoPixel

# ===== CONFIG =====
MIC_PIN = 26       # ADC0 (GP26)
LED_PIN = 2        # WS2812 Data pin (GP0)
NUM_LEDS = 39
SAMPLES = 150      # number of ADC samples per measurement
FAST_DELAY = 0.01  # 10 ms refresh

RISE_RATE = 0.02   # how fast LEDs rise per frame (0.01=slower, 0.05=faster)
FALL_RATE = 0.15   # how fast LEDs fall per frame (0.1=fast, 0.3=very fast)

adc = machine.ADC(MIC_PIN)
np = NeoPixel(machine.Pin(LED_PIN), NUM_LEDS)

# === Color Gradient: Green → Yellow → Red ===
def color_from_fraction(f):
    f = max(0.0, min(1.0, f))
    if f <= 0.5:  # green to yellow
        t = f / 0.5
        return (int(255 * t), 255, 0)
    else:         # yellow to red
        t = (f - 0.5) / 0.5
        return (255, int(255 * (1 - t)), 0)

# === ADC RMS ===
def read_rms(samples=SAMPLES):
    vals = [adc.read_u16() for _ in range(samples)]
    mean = sum(vals) / len(vals)
    sq = sum((v - mean) ** 2 for v in vals) / len(vals)
    return math.sqrt(sq)

# === Show LEDs ===
def show_bar(level):  # level: 0.0–1.0
    leds_on = int(level * NUM_LEDS)
    for i in range(NUM_LEDS):
        if i < leds_on:
            frac = i / (NUM_LEDS - 1)
            np[i] = color_from_fraction(frac)
        else:
            np[i] = (0, 0, 0)
    np.write()

# === Main Loop ===
try:
    current_level = 0.0
    noise_floor = read_rms(200)  # quick auto-calibration
    max_rms = noise_floor * 3.0  # initial scale

    while True:
        rms = read_rms()
        if rms > max_rms:
            max_rms = rms
        else:
            max_rms *= 0.999  # slow decay of max

        norm = (rms - noise_floor) / (max_rms - noise_floor + 1e-6)
        norm = max(0.0, min(1.0, norm))

        # Slow Rise / Fast Fall
        if norm > current_level:
            current_level += RISE_RATE   # rise slowly
            if current_level > norm:
                current_level = norm
        else:
            current_level -= FALL_RATE   # fall quickly
            if current_level < norm:
                current_level = norm

        show_bar(current_level)
        time.sleep(FAST_DELAY)

except KeyboardInterrupt:
    for i in range(NUM_LEDS):
        np[i] = (0, 0, 0)
    np.write()

