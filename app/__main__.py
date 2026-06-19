import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from .core.logging_config import setup_logging  # noqa: E402

setup_logging(service="llm-gateway-api")

from .http_server.ingress import start  # noqa: E402

start()
