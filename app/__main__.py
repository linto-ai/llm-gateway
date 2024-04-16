import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import logging
from .http_server.ingress import start

logging.basicConfig(
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S",
)
logger = logging.getLogger("__llm_gateway__")
logger.setLevel(logging.INFO)
start()
