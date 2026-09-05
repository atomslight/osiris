import os
import time
import ctypes
import logging
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRIGGER_FILE = os.path.join(BASE_DIR, "greet_trigger.flag")
LOG_FILE = os.path.join(BASE_DIR, "greeter.log")
AGENT_FILE = os.path.join(BASE_DIR, "agent.py")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def is_session_unlocked():
    DESKTOP_SWITCHDESKTOP = 0x0100
    handle = ctypes.windll.user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
    if handle:
        ctypes.windll.user32.CloseDesktop(handle)
        return True
    return False

def trigger_agent():
    logging.info("Launching agent.py")
    subprocess.Popen(["uv", "run", "agent.py", "console"], cwd=BASE_DIR)

if os.path.exists(TRIGGER_FILE):
    os.remove(TRIGGER_FILE)

try:
    if not is_session_unlocked():
        logging.info("Locked — waiting for unlock trigger.")
        while not os.path.exists(TRIGGER_FILE):
            time.sleep(1)
        os.remove(TRIGGER_FILE)
        logging.info("Unlock trigger received.")

    trigger_agent()
except Exception:
    logging.exception("Fatal error in session.py:")
