# dB_meter_neopixel_39.py
import machine
import time
import math
from neopixel import NeoPixel

# ====== CONFIG ======
MIC_PIN = 26        # ADC0 (GP26)
LED_PIN = 2        # Data pin for WS2812 (GP0)
NUM_LEDS = 39
SAMPLES = 300       # number of ADC samples per measurement (adjust for speed/smoothness)
SAMPLE_DELAY = 0    # microdelay between samples; 0 means tight loop
SMOOTH_ALPHA = 0.2  # exponential smoothing (0-1): higher -> less smoothing
PEAK_HOLD_TIME = 0.8  # seconds peak remains
MIN_RMS = None      # will be set on startup (noise floor)
CALIBRATE_SECONDS = 2  # time to sample for noise floor calibration

# ====== SETUP ======
adc = machine.ADC(MIC_PIN)
np = NeoPixel(machine.Pin(LED_PIN), NUM_LEDS)

# ====== HELPERS ======
def read_rms(samples=SAMPLES):
    vals = []
    # fast sampling
    for _ in range(samples):
        v = adc.read_u16()
        vals.append(v)
        if SAMPLE_DELAY:
            time.sleep_us(SAMPLE_DELAY)
    mean = sum(vals) / len(vals)
    sq = sum((v-mean)**2 for v in vals) / len(vals)
    rms = math.sqrt(sq)
    return rms

def clamp(x, a, b):
    return max(a, min(b, x))

def db_from_rms(rms, ref=1.0):
    # Not real SPL unless calibrated; useful for relative scale
    return 20 * math.log10(rms / (ref+1e-9) + 1e-9)

def color_from_fraction(f):  # f: 0.0..1.0
    # green (0.0) -> yellow (0.5) -> red (1.0)
    f = clamp(f, 0.0, 1.0)
    if f <= 0.5:
        # green to yellow: (0,255,0) -> (255,255,0)
        t = f / 0.5
        r = int(255 * t)
        g = 255
        b = 0
    else:
        # yellow to red: (255,255,0) -> (255,0,0)
        t = (f - 0.5) / 0.5
        r = 255
        g = int(255 * (1 - t))
        b = 0
    return (r, g, b)

def show_bar(normalized):  # normalized 0.0..1.0
    leds_on = int(round(normalized * NUM_LEDS))
    for i in range(NUM_LEDS):
        if i < leds_on:
            # use gradient across the bar so lower LEDs are greener
            frac = i / (NUM_LEDS - 1) if NUM_LEDS>1 else 0
            # mix base color with fraction of normalized
            color = color_from_fraction(frac)
            np[i] = color
        else:
            np[i] = (0,0,0)
    np.write()

# ====== BOOT CALIBRATION: measure noise floor ======
print("Calibrating noise floor for {} seconds... stay quiet".format(CALIBRATE_SECONDS))
t0 = time.ticks_ms()
samples = []
while time.ticks_diff(time.ticks_ms(), t0) < CALIBRATE_SECONDS*1000:
    samples.append(read_rms(80))
    time.sleep(0.05)
MIN_RMS = sum(samples)/len(samples)
print("Calibration done. Noise floor RMS ~ {:.2f}".format(MIN_RMS))

# We'll also track a sliding top (max) to auto-scale
max_rms_seen = MIN_RMS * 3.0  # initial guess
smoothed = 0.0
peak_value = 0.0
peak_time = time.time()

# ====== MAIN LOOP ======
try:
    while True:
        rms = read_rms()
        # update observed maximum slowly for auto-ranging
        if rms > max_rms_seen:
            max_rms_seen = rms
        else:
            # decay the max slowly so it adapts down
            max_rms_seen *= 0.9995

        # normalize rms between MIN_RMS and max_rms_seen
        if max_rms_seen <= MIN_RMS:
            norm = 0.0
        else:
            norm = (rms - MIN_RMS) / (max_rms_seen - MIN_RMS)
            norm = clamp(norm, 0.0, 1.0)

        # smoothing
        smoothed = (SMOOTH_ALPHA * norm) + ((1 - SMOOTH_ALPHA) * smoothed)

        # peak hold
        if smoothed > peak_value:
            peak_value = smoothed
            peak_time = time.time()
        else:
            if time.time() - peak_time > PEAK_HOLD_TIME:
                # decay the peak slowly
                peak_value *= 0.995
                if peak_value < smoothed:
                    peak_value = smoothed

        # display: we use peak_value for max LED, and smoothed for current bar
        show_bar(peak_value)  # simple: light up according to peak (change to smoothed for other behavior)

        # small delay to control refresh
        time.sleep(0.05)

except KeyboardInterrupt:
    # turn off LEDs on exit
    for i in range(NUM_LEDS):
        np[i] = (0,0,0)
    np.write()
    print("Stopped.")


