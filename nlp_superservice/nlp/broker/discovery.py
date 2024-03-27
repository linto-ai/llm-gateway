""" The discovery submodule contains methods and function to list and fetch informations relative to subtasks."""
import json
import os

import redis
from nlp.broker.celeryapp import celery

__all__ = ["Service", "list_available_services", "SERVICE_TYPES"]

SERVICE_DISCOVERY_DB = 0  # RedisJSON only allow json indexing on DB 0
SERVICE_TYPES = [
    #"keyword_extraction",
    "language_modeling"
]  # If you intend to add other subservice, add their service's type here

LANGUAGE = os.environ.get("LANGUAGE")


def list_available_services(ensure_alive: bool = False, as_json: bool = False) -> dict:
    """Fetch available services, filter by language and sort by type

    Args:
        ensure_alive (bool, optional): If true, check if the registered service still exist. Defaults to False.

    Returns:
        dict: A dictionary containing types as primary key. Each type containing available service informations.
    """
    services = dict()

    # Connect to the service registry DB
    host, port = os.environ.get("SERVICES_BROKER").split("//")[1].split(":")
    redis_client = redis.Redis(
        host=host,
        port=int(port),
        db=SERVICE_DISCOVERY_DB,
        password=os.environ.get("BROKER_PASS", "password"),
    )

    if ensure_alive:
        worker_names = set(
            k.split("@")[1] for k in celery.control.inspect().active_queues().keys()
        )

    # Listing services
    for service_type in SERVICE_TYPES:
        services[service_type] = {}
        service_l_doc = redis_client.ft().search(service_type).docs
        # Filter and check services
        for service_doc in service_l_doc:
            service_id = service_doc.id
            service_info = json.loads(service_doc.json)
            print(service_info)
            # Ensure service type
            if service_info["service_type"] != service_type:
                continue
            # Filter by language
            if _is_compatible_language(LANGUAGE, service_info["service_language"]):
                # Check if the service is up
                if ensure_alive:
                    if not service_id.split(":")[1] in worker_names:
                        redis_client.ft().delete_document(service_id)
                        print(
                            f"Service host {service_id} is registered but do not exist. Removing entry from registry."
                        )
                if service_info["service_name"] in services.keys():
                    services[service_type][service_info["service_name"]].add_instance(
                        service_info, service_id
                    )
                else:
                    services[service_type][
                        service_info["service_name"]
                    ] = Service.from_service_info(service_info, service_id)
    return prettyfy(services) if as_json else services


def prettyfy(services_dict: dict) -> dict:
    """Present the service list to be returned to the consumer

    Args:
        services_dict (dict): Services dictionary as returned by list_available_services()

    Returns:
        dict: Dictionnary ready to be consumed / serialized.
    """
    pretty_dict = {}
    for service_type in services_dict:
        pretty_dict[service_type] = []
        for service_name, service in services_dict[service_type].items():
            pretty_dict[service_type].append(service.to_dict())
    return pretty_dict


def _is_compatible_language(target_lang: str, provided_lang: str) -> bool:
    """Check if provided language is compatible with target language.
    Either the language match, or it is included or a wildcard is provided.

    Args:
        target_lang (str): The system declared lang
        provided_lang (str): The service registered language(s).

    Returns:
        bool: _description_
    """
    return (
        provided_lang.lower() == target_lang.lower()
        or target_lang.lower() in provided_lang.lower()
        or provided_lang == "*"
    )


class Service:
    """The Service class hold service informations for services sharing the same service_name"""

    def __init__(
        self,
        service_name: str,
        service_type: str,
        service_language: str,
        queue_name: str,
        info: str,
    ):
        self.service_name = service_name
        self.service_type = service_type
        self.service_language = service_language
        self.queue_name = queue_name
        self.info = info
        self.instances = []

    def add_instance(self, service_info: dict, service_id: str) -> None:
        """Add instance to existing service

        Args:
            service_info (dict): service information as dictionnary
            service_id (str): service unique's id
        """
        instance_info = {
            "host_name": service_id.split(":")[1],
            "last_alive": service_info["last_alive"],
            "version": service_info["version"],
            "concurrency": service_info["concurrency"],
        }
        self.instances.append(instance_info)

    @classmethod
    def from_service_info(cls, service_info: dict, service_id: str) -> "Service":
        service = Service(
            service_info["service_name"],
            service_info["service_type"],
            service_info["service_language"],
            service_info["queue_name"],
            service_info["info"],
        )
        service.add_instance(service_info, service_id)
        return service

    def to_dict(self) -> dict:
        return {
            "service_name": self.service_name,
            "service_type": self.service_type,
            "service_language": self.service_language,
            "queue_name": self.queue_name,
            "info": self.info,
            "instances": self.instances,
        }
