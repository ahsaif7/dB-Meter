import machine, time, math
from neopixel import NeoPixel

# ===== CONFIG =====
MIC_PIN = 26
LED_PIN = 2
NUM_LEDS = 39
SAMPLES = 300
FAST_DELAY = 0.02

ATTACK_SPEED = 0.08     # medium attack
CALIBRATION_TIME = 3
NOISE_MARGIN = 1.05

MIN_DB = 30
MAX_DB = 80

# zone fractions
GREEN_ZONE = 0.33
YELLOW_ZONE = 0.66
RED_TRIGGER = 0.95   # red flash threshold

adc = machine.ADC(MIC_PIN)
np = NeoPixel(machine.Pin(LED_PIN), NUM_LEDS)

# === Gradient Colors ===
def color_from_fraction(f):
    f = max(0.0, min(1.0, f))
    if f <= 0.5:
        t = f / 0.5
        return (int(255 * t), 255, 0)   # Green → Yellow
    else:
        t = (f - 0.5) / 0.5
        return (255, int(255 * (1 - t)), 0)  # Yellow → Red

# === Flash Effect ===
def flash_all(color, duration=0.2):
    for i in range(NUM_LEDS):
        np[i] = color
    np.write()
    time.sleep(duration)

# === RMS Measurement ===
def read_rms(samples=SAMPLES):
    vals = [adc.read_u16() for _ in range(samples)]
    mean = sum(vals) / len(vals)
    sq = sum((v - mean) ** 2 for v in vals) / len(vals)
    return math.sqrt(sq)

# === dB Conversion ===
def rms_to_db(rms, ref=32768):
    if rms <= 0:
        return MIN_DB
    return 20 * math.log10(rms / ref) + 90

# === LED Update ===
def update_leds(level):
    leds_on = int(level * NUM_LEDS)

    # Full bar → solid red
    if leds_on >= NUM_LEDS:
        for i in range(NUM_LEDS):
            np[i] = (255, 0, 0)
        np.write()
        return

    # Otherwise normal gradient bar
    for i in range(NUM_LEDS):
        if i < leds_on:
            frac = i / (NUM_LEDS - 1)
            np[i] = color_from_fraction(frac)
        else:
            np[i] = (0, 0, 0)
    np.write()

# === Main Loop ===
try:
    print("Calibrating... stay quiet.")
    cal_start = time.ticks_ms()
    cal_values = []

    while time.ticks_diff(time.ticks_ms(), cal_start) < CALIBRATION_TIME * 1000:
        cal_values.append(read_rms())
        time.sleep(0.05)

    base_noise = sum(cal_values) / len(cal_values)
    noise_floor = base_noise * NOISE_MARGIN
    print("Calibration done. Noise floor RMS =", noise_floor)

    current_level = 0.0
    last_zone = 0  # 0=below green, 1=green, 2=yellow, 3=red

    while True:
        rms = read_rms()

        if rms <= noise_floor:
            time.sleep(FAST_DELAY)
            continue

        db = rms_to_db(rms)
        norm = (db - MIN_DB) / (MAX_DB - MIN_DB)
        norm = max(0.0, min(1.0, norm))

        # medium attack, no decay
        if norm > current_level:
            current_level += (norm - current_level) * ATTACK_SPEED

        # Zone detection with red at 95%
        if current_level >= RED_TRIGGER and last_zone < 3:
            flash_all((255, 0, 0), 0.3)   # red flash
            last_zone = 3
        elif current_level >= YELLOW_ZONE and last_zone < 2:
            flash_all((255, 255, 0), 0.2) # yellow flash
            last_zone = 2
        elif current_level >= GREEN_ZONE and last_zone < 1:
            flash_all((0, 255, 0), 0.2)   # green flash
            last_zone = 1

        update_leds(current_level)
        time.sleep(FAST_DELAY)

except KeyboardInterrupt:
    for i in range(NUM_LEDS):
        np[i] = (0, 0, 0)
    np.write()

