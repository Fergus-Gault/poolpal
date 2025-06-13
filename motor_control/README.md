# Motor-Control

# Installation
- Run `pip install -r requirements.txt` to install the Python dependencies
- Create a `.env` file with the following entries:
  - `POOLPAL_URL` = base URL to host the server on (including "https://") <br>
    e.g. `https://pool-pal.serveo.net`
  - `WRITE_STATS` = set to "true" if you want movement latency statistics
    writing to a file. Otherwise, do not include

# Usage
`python3 controller.py` starts the Python client for the Pub/Sub server
to allow the motors to be controlled from the web

All Arduino code is in the `main` folder. To develop with this, use the
Arduino IDE and open `main.ino`
