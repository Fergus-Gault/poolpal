import socketio
import serial
import time
from dotenv import load_dotenv
import os
import logging
import time


def send_command(ser: serial.Serial, x: int, y: int):
    ser.write(f"{x} {y}\n".encode())
    print(ser.readline().decode())


########
# Init #
########
load_dotenv()
ser = serial.Serial("COM3", 115200)
time.sleep(1)
logging.basicConfig(level=logging.DEBUG)

POOLPAL_URL = "http://poolpal.joshn.uk"

WRITE_STATS = False

moving = False


def send_command(ser: serial.Serial, x: int, y: int):
    global moving
    if moving:
        return

    moving = True
    start_time = time.time()
    ser.write(f"{x} {y}\n".encode())
    moving_response = ser.readline().decode()

    logging.debug(f"Moving response 1: {moving_response}")

    # Move started, wait to finish moving
    moving_response = ser.readline().decode()

    logging.debug(f"Moving response 2: {moving_response}")
    if moving_response:
        end_time = time.time()
        duration = end_time - start_time
        if WRITE_STATS:
            with open("stats.csv", "a") as stats_file:
                stats_file.write(f"{x},{y},{duration}\n")
        logging.debug(f"Finished moving in {duration} seconds")
        finishedMove()

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
    sio.emit("join", "move")


@sio.event
def move(data: dict[str, str]):
    """When new "move" command is received"""
    logging.debug(f"Received new command from server: {data}")
    try:
        send_command(ser, int(data["x"]), int(data["y"]))
    except Exception as e:
        logging.error(f"Failed to execute move command {data}\n {repr(e)}")


def finishedMove():
    global moving
    moving = False
    sio.emit("finishedMove", "true")
    logging.debug("Finished move")


sio.connect(POOLPAL_URL)

sio.wait()

sio.disconnect()
ser.close()
