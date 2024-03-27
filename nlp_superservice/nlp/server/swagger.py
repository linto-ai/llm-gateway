import os

import yaml
from flask_swagger_ui import get_swaggerui_blueprint


def setupSwaggerUI(app, args):
    """Setup Swagger UI within the app"""
    swagger_yml = yaml.load(open(args.swagger_path, "r"), Loader=yaml.Loader)

    # Setup additionnal servers
    if os.environ.get("SWAGGER_URLS", None):
        server_urls = os.environ.get("SWAGGER_URLS").split(",")
        swagger_yml["servers"] = [
            {"url:": url, "description": url} for url in server_urls
        ]

    swaggerui = get_swaggerui_blueprint(
        # Swagger UI static files will be mapped to '{SWAGGER_URL}/dist/'
        args.swagger_prefix + args.swagger_url,
        args.swagger_path,
        config={  # Swagger UI config overrides
            "app_name": "API Documentation",
            "spec": swagger_yml,
        },
    )
    app.register_blueprint(swaggerui, url_prefix=args.swagger_url)
