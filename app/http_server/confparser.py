import argparse
import os

__all__ = ["createParser"]


def createParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    # SERVICE
    parser.add_argument(
        "--service_name",
        type=str,
        help="Service Name",
        default=os.environ.get("SERVICE_NAME", "LLM_Gateway"),
    )

    # GUNICORN
    parser.add_argument("--service_port", type=int,
                        help="Service port", default=int(os.environ.get("HTTP_PORT",8000)))
          
    parser.add_argument(
        "--workers",
        type=int,
        help="Number of Gunicorn workers (default=CONCURRENCY + 1)",
        default=int(os.environ.get("CONCURRENCY", 1)) + 1,
    )

    parser.add_argument(
        "--timeout",
        type=int,
        help="Request timeout",
        default=int(os.environ.get("TIMEOUT", 30)),
    )

    # SWAGGER
    parser.add_argument(
        "--swagger_url", type=str, help="Swagger interface url", default="/docs"
    )
    parser.add_argument(
        "--swagger_prefix",
        type=str,
        help="Swagger prefix",
        default=os.environ.get("SWAGGER_PREFIX", ""),
    )
    parser.add_argument(
        "--swagger_path",
        type=str,
        help="Swagger file path",
        default=os.environ.get(
            "SWAGGER_PATH", "../document/swagger_llm_gateway.yml"),
    )

    # MISC
    parser.add_argument("--debug", action="store_true",
                        help="Display debug logs")

    return parser
