

import RPi.GPIO as GPIO
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
latencies = []

GPIO_PINS = {
    "STP_ROT": 17,
    "DIR_ROT": 27,
    "BOT_ROT": 19,
    "STP_HIT": 26,
    "DIR_HIT": 19,
    "EN_HIT": 12,
    "BOT_HIT": 10,
    "BLOW": 9,
}

DELAYS = {
    "ROT_DELAY": 400e-6,
    "REC_DELAY": 3000e-6,
    "HIT_DELAY": 2000e-6,
    "HIT_FAST_DELAY": 800e-6,
    "HIT_REC_DELAY": 3000e-6
}

MICRO_STEP_ANGLE = 0.1125
STEP_ANGLE = 1.8


class HitController:
    def __init__(self):
        self.rotation = 0
        self._setup_gpio()
        self._set_microstep()
        self._prepare_hit()
        logging.info("HitController initialized.")

    def _setup_gpio(self):
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for pin, mode in GPIO_PINS.items():
                if pin.startswith("BOT_"):
                    logging.info(
                        f"Setting up pin {pin} ({mode}) as input with pull-up.")
                    GPIO.setup(mode, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                else:
                    GPIO.setup(mode, GPIO.OUT)
                    logging.info(f"Setting up pin {pin} ({mode}) as output.")
            logging.info("GPIO setup complete.")
            GPIO.output(GPIO_PINS['BLOW'], GPIO.LOW)
        except Exception as e:
            logging.error(f"GPIO setup failed: {e}")

    def _step_motor(self, stp_pin, delay):
        GPIO.output(stp_pin, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(stp_pin, GPIO.LOW)
        time.sleep(delay)

    def _set_microstep(self):
        return

    def _set_fullstep(self):
        return
        GPIO.output(GPIO_PINS["MS1_HIT"], GPIO.LOW)
        GPIO.output(GPIO_PINS["MS2_HIT"], GPIO.LOW)
        GPIO.output(GPIO_PINS["MS3_HIT"], GPIO.LOW)

    def _reset_rotation(self):
        GPIO.output(GPIO_PINS["DIR_ROT"], GPIO.LOW)
        while GPIO.input(GPIO_PINS["BOT_ROT"]) == GPIO.HIGH:
            self._step_motor(GPIO_PINS["STP_ROT"], DELAYS["ROT_DELAY"])
        self.rotation = 0
        logging.info("Rotation reset to 0 degrees.")

    def _set_rotation(self, angle):
        initial_rotation = self.rotation
        delta = angle - self.rotation

        if delta == 0:
            logging.info("Rotation already at target angle.")
            return

        GPIO.output(GPIO_PINS["DIR_ROT"], GPIO.HIGH if delta > 0 else GPIO.LOW)
        steps = abs(int(delta // MICRO_STEP_ANGLE))

        for _ in range(steps):
            self._step_motor(GPIO_PINS["STP_ROT"], DELAYS["ROT_DELAY"])
            self.rotation += MICRO_STEP_ANGLE if delta > 0 else -MICRO_STEP_ANGLE

        rotation_change = abs(self.rotation - initial_rotation)
        logging.info(f"Rotation set to {self.rotation:.2f} degrees.")
        return rotation_change

    def _prepare_hit(self):
        logging.info("Preparing hit")
        GPIO.output(GPIO_PINS["DIR_HIT"], GPIO.LOW)
        GPIO.output(GPIO_PINS["EN_HIT"], GPIO.LOW)
        while GPIO.input(GPIO_PINS["BOT_HIT"]) == GPIO.HIGH:
            self._step_motor(GPIO_PINS["STP_HIT"], DELAYS["HIT_REC_DELAY"])
        time.sleep(0.1)
        GPIO.output(GPIO_PINS["EN_HIT"], GPIO.HIGH)
        logging.info("Hit mechanism prepared.")

    def _execute_hit(self, strength):
        if not (0 <= strength <= 800):
            logging.error("Invalid hit strength. Must be between 0 and 800.")
            return

        GPIO.output(GPIO_PINS["EN_HIT"], GPIO.LOW)
        GPIO.output(GPIO_PINS["DIR_HIT"], GPIO.HIGH)

        step_count = (1000 - strength)

        for _ in range(step_count):
            self._step_motor(GPIO_PINS["STP_HIT"], DELAYS["HIT_DELAY"])

        self._set_fullstep()
        self._set_microstep()
        GPIO.output(GPIO_PINS["EN_HIT"], GPIO.HIGH)
        time.sleep(2)

        self._prepare_hit()
        logging.info(f"Executed hit with strength {strength}.")

    def handle_input(self, command, value):
        start = time.time()
        rotation_change = 0

        if command == "R":
            rotation_change = self._set_rotation(value)
        elif command == "H":
            self._execute_hit(value)
        elif command == "T":
            self._reset_rotation()
        else:
            logging.error(f"Unknown command received: {command}")

        latency = time.time() - start
        latencies.append((latency, rotation_change))

        if len(latencies) % 1 == 0:
            with open("latencies.csv", "a") as latencies_file:
                for lat, rot in latencies[-10:]:
                    latencies_file.write(f"{lat},{rot}\n")

        logging.info(
            f"Command {command} executed in {latency:.6f} seconds. Rotation change: {rotation_change:.2f} degrees.")

    def cleanup(self):
        GPIO.cleanup()
        logging.info("GPIO cleanup performed.")


if __name__ == "__main__":
    controller = HitController()

    ######################
    # Socket IO Listener #
    ######################

    # Create a Socket.IO client instance
    # Docs: https://python-socketio.readthedocs.io/en/latest/client.html#id1
    sio = socketio.Client()

    executing = False

    @sio.event
    def connect():
        """
        Runs when the socket first connects
        Join/subscribe to any rooms we want to listen to
        """
        logging.debug("Connected to server")
        sio.emit("join", "hit")

    @sio.event
    def hit(data: dict[str, str]):
        """When new "hit" command is received"""
        logging.debug(f"Received new command from server: {data}")

        if not "angle" in data:
            logging.error("Could not parse angle from input")
            return

        if not "strength" in data:
            logging.error("Could not parse hit strength from input")
            return

        executing = True
        angle = data["angle"]
        hit_strength = data["strength"]
        if not isinstance(angle, int):
            logging.error(f"Could not parse angle {angle} as a number")
            return
        if not isinstance(hit_strength, int):
            logging.error(
                f"Could not parse hit strength {hit_strength} as a number")
            return

        controller.handle_input("R", int(angle))
        time.sleep(1)
        controller.handle_input("H", int(hit_strength))
        time.sleep(1)
        controller.handle_input("R", 0)

        executing = False
        finishedHit()

    def finishedHit():
        """Called when the hit is finished"""
        sio.emit("finishedHit", "true")
        logging.debug("Sent finishedHit message")

    sio.connect(POOLPAL_URL)
    sio.wait()
