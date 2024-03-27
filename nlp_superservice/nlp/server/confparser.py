import argparse
import os

__all__ = ["createParser"]


def createParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    # GUNICORN
    parser.add_argument(
        "--concurrency",
        type=int,
        help="Serving workers (default=10)",
        default=os.environ.get("CONCURRENCY", 10),
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
            "SWAGGER_PATH", "/usr/src/app/nlp/document/swagger.yaml"
        ),
    )

    # MONGODB
    parser.add_argument(
        "--mongo_uri",
        type=str,
        help="MongoDB host",
        default=os.environ.get("MONGO_HOST", None),
    )

    parser.add_argument(
        "--mongo_port",
        type=int,
        help="MongoDB port",
        default=os.environ.get("MONGO_PORT", None),
    )

    # SERVICE
    parser.add_argument(
        "--service_name",
        type=str,
        help="Service name",
        default=os.environ.get("SERVICE_NAME"),
    )

    parser.add_argument(
        "--language",
        type=str,
        help="Service language, required for some subtasks.",
        default=os.environ.get("LANGUAGE", None),
    )

    parser.add_argument("--debug", action="store_true", help="Display debug logs")

    return parser
