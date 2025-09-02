import machine, time
from neopixel import NeoPixel

LED_PIN = 2
NUM_LEDS = 39
np = NeoPixel(machine.Pin(LED_PIN), NUM_LEDS)

def fill(color, delay=0.5):
    for i in range(NUM_LEDS):
        np[i] = color
    np.write()
    time.sleep(delay)

try:
    while True:
        fill((0, 255, 0), 1)     # Green
        fill((255, 255, 0), 1)   # Yellow
        fill((255, 0, 0), 1)     # Red
        fill((0, 0, 255), 1)     # Blue
        fill((255, 255, 255), 1) # White
        fill((0, 0, 0), 1)       # Off

except KeyboardInterrupt:
    # Turn off when stopped
    fill((0, 0, 0), 0)

