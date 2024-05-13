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
    
    
    parser.add_argument(
        "--api_base",
        type=str,
        help="OpenAI API Base URL",
        default= "https://api.openai.com/v1/",)
        #default=os.environ.get("OPENAI_API_BASE", "http://localhost:9000/v1"),
        #)

    parser.add_argument(
        "--api_key",
        type=str,
        help="OpenAI API Token",
        default = "sk-proj-XQOQzDwEV3yUoF0lR9bRT3BlbkFJ64ZJpW5DIJ3rz1zRtJgv"#"sk-proj-XQOQzDwEV3yUoF0lR9bRT3BlbkFJ64ZJpW5DIJ3rz1z"   #RtJgv
        #default=os.environ.get("OPENAI_API_TOKEN", "EMPTY"),
    )

    # GUNICORN
    parser.add_argument("--service_port", type=int,
                        help="Service port", default=int(os.environ.get("HTTP_PORT",9000)))
          
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
        default=int(os.environ.get("TIMEOUT", 120)),
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
    
    parser.add_argument("--db_path", type=str, help="Path to the result database", default ="/home/mkeita/llm-gateway/data/results.sqlite")
    

    return parser
#NFO: Namespace(service_name='LLM_Gateway', api_base='http://localhost:9000/v1', api_key='sk-proj-XQOQzDwEV3yUoF0lR9bRT3BlbkFJ64ZJpW5DIJ3rz1zRtJgv', service_port=8000, workers=2, timeout=60, swagger_url='/docs', swagger_prefix='', swagger_path='../document/swagger_llm_gateway.yml', debug=False, db_path='/home/mkeita/llm-gateway/data/results.sqlite')