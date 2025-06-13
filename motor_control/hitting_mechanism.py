import RPi.GPIO as GPIO
import time
import logging
import socketio

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

GPIO_PINS = {
    "STP_ROT": 14,
    "DIR_ROT": 15,
    "BOT_ROT": 21,
    "STP_HIT": 4,
    "DIR_HIT": 3,
    "EN_HIT": 17,
    "BOT_HIT": 13
}

DELAYS = {
    "ROT_DELAY": 500e-6,
    "REC_DELAY": 2000e-6,
    "HIT_DELAY": 1000e-6
}

STEP_ANGLE = 0.1125

POOLPAL_URL = "http://poolpal.joshn.uk/"

class HitController:
    def __init__(self):
        self.rotation = 0
        self._setup_gpio()
        self._prepare_hit()
        self._reset_rotation()
        logging.info("HitController initialized.")
    
    def _setup_gpio(self):
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            print(GPIO_PINS)
            for pin, mode in GPIO_PINS.items():
                if pin.startswith("BOT_"):
                    logging.info(f"Setting up pin {pin} ({mode}) as input with pull-up.")
                    GPIO.setup(mode, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                else:
                    GPIO.setup(mode, GPIO.OUT)
                    print(pin)
                    logging.info(f"Setting up pin {pin} ({mode}) as output.")
            logging.info("GPIO setup complete.")
        except Exception as e:
            logging.error(f"GPIO setup failed: {e}")
    
    def _step_motor(self, stp_pin, delay):
        GPIO.output(stp_pin, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(stp_pin, GPIO.LOW)
        time.sleep(delay)
    
    def _reset_rotation(self):
        logging.info("Resetting rotation")
        GPIO.output(GPIO_PINS["DIR_ROT"], GPIO.LOW)
        while GPIO.input(GPIO_PINS["BOT_ROT"]) == GPIO.HIGH:
            self._step_motor(GPIO_PINS["STP_ROT"], DELAYS["ROT_DELAY"])
        self.rotation = 0
        logging.info("Rotation reset to 0 degrees.")
    
    def _set_rotation(self, angle):
        angle = angle % 360
        delta = angle - self.rotation
        
        if delta == 0:
            logging.info("Rotation already at target angle.")
            return
        
        GPIO.output(GPIO_PINS["DIR_ROT"], GPIO.HIGH if delta > 0 else GPIO.LOW)
        steps = abs(int(delta // STEP_ANGLE))
        
        for _ in range(steps):
            if GPIO.input(GPIO_PINS["BOT_ROT"]) == GPIO.LOW:
                self.rotation = 0
                logging.warning("Rotation limit reached.")
                return
            self._step_motor(GPIO_PINS["STP_ROT"], DELAYS["ROT_DELAY"])
            self.rotation += STEP_ANGLE if delta > 0 else -STEP_ANGLE
            self.rotation %= 360
        
        logging.info(f"Rotation set to {self.rotation:.2f} degrees.")
    
    def _prepare_hit(self):
        logging.info("Preparing hit")
        GPIO.output(GPIO_PINS["DIR_HIT"], GPIO.LOW)
        GPIO.output(GPIO_PINS["EN_HIT"], GPIO.LOW)
        while GPIO.input(GPIO_PINS["BOT_HIT"]) == GPIO.HIGH:
            self._step_motor(GPIO_PINS["STP_HIT"], DELAYS["HIT_DELAY"])
        time.sleep(0.1)
        GPIO.output(GPIO_PINS["EN_HIT"], GPIO.HIGH)
        logging.info("Hit mechanism prepared.")
    
    def _execute_hit(self, strength):
        if not (0 <= strength <= 1100):
            logging.error("Invalid hit strength. Must be between 0 and 1100.")
            return
        
        GPIO.output(GPIO_PINS["EN_HIT"], GPIO.LOW)
        GPIO.output(GPIO_PINS["DIR_HIT"], GPIO.HIGH)
        for _ in range(1100 - strength):
            self._step_motor(GPIO_PINS["STP_HIT"], DELAYS["HIT_DELAY"])
        GPIO.output(GPIO_PINS["EN_HIT"], GPIO.HIGH)
        time.sleep(2)
        self._prepare_hit()
        logging.info(f"Executed hit with strength {strength}.")
    
    def handle_input(self, command, value):
        if command == "R":
            self._set_rotation(value)
        elif command == "H":
            self._execute_hit(value)
        else:
            logging.error(f"Unknown command received: {command}")
    
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
        
        angle = data["angle"]
        hit_strength = data["strength"]
        if not isinstance(angle, int):
            logging.error(f"Could not parse angle {angle} as a number")
            return
        if not isinstance(hit_strength, int):
            logging.error(f"Could not parse hit strength {hit_strength} as a number")
            return
        
        controller.handle_input("R", angle)
        controller.handle_input("H", hit_strength)
        finishedHit()
            
    @sio.event
    def finishedHit():
        sio.emit("finishedHit", "true")
        logging.debug("Sent finishedHit message")

    sio.connect(POOLPAL_URL)

    sio.wait()

    sio.disconnect()
  
