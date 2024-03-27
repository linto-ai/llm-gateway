""" The serviceresolve module implements Resolving Policy, resolving exception and the serviceResolver class used to resolve requested services depending on available micro-services."""

import logging
import os

from nlp.broker.discovery import (SERVICE_TYPES, list_available_services)


class ResolveException(Exception):
    """Resolve exception parent class."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class NoServiceSpecified(ResolveException):
    """Exception raised in STRICT mode when no service is specified"""

    def __init__(self, service_type: str) -> None:
        self.message = f"No service name provided for {service_type}. Not specifying serviceName in STRICT mode will raise an error."
        logging.error(self.message)
        super().__init__(self.message)


class FailedToResolve(ResolveException):
    """Exception raised when the requested service is unresolvable."""

    def __init__(self, service_name: str, policy: str) -> None:
        self.message = f"The required service {service_name} could not be resolved. (Policy={policy})."
        logging.error(self.message)
        super().__init__(self.message)


class ServiceUnavailable(ResolveException):
    """Exception raised when the requested service_name does not exist."""

    def __init__(self, service_name: str, policy: str) -> None:
        self.message = f"The required service {service_name} could not be resolved. (Policy={policy})."
        logging.error(self.message)
        super().__init__(self.message)


class NoServiceAvailable(ResolveException):
    """Exception raised when not service for the specified service type is available."""

    def __init__(self, service_type: str) -> None:
        self.message = f"No service {service_type} available."
        logging.error(self.message)
        super().__init__(self.message)


class NoDefaultDeclared(ResolveException):
    """Exception raised when policy is set to default but no default service has been declared."""

    def __init__(self, service_type: str, policy: str) -> None:
        self.message = (
            f"The default service for {service_type} is not set (Policy={policy})."
        )
        logging.error(self.message)
        super().__init__(self.message)


class DefaultUnavailable(ResolveException):
    def __init__(self, service_name: str, service_type: str, policy: str) -> None:
        self.message = f"The default service for {service_type} -> {service_name} could not be found(Policy={policy})."
        logging.error(self.message)
        super().__init__(self.message)


class ServicePolicy:
    """Enumeration of service resolve policies."""

    ANY = "any"  # If the asked service is not available, chooses any other similar service instead
    DEFAULT = "default"  # If the asked service is not available, uses the default service instead. If the default service is not available, throws an error.
    STRICT = "error"  # If the asked service is not available, throws an error.

    @classmethod
    def from_env(cls) -> str:
        """Returns environement defined resolve policy.

        Returns:
            str: Environement defined resolve policy (default ANY)
        """
        env_policy = os.environ.get("RESOLVE_POLICY", "any").lower()
        return {"default": cls.DEFAULT, "any": cls.ANY, "strict": cls.STRICT}.get(
            env_policy, cls.ANY
        )


class ServiceResolver:
    """The ServiceResolver class is used to fetch available services and resolve service queues from requests."""

    def __init__(self):
        self.subservices_list = list_available_services(ensure_alive=True)
        self.service_policy = ServicePolicy.from_env()
        self.default_services = {}
        if self.service_policy == ServicePolicy.DEFAULT:
            self.default_services = {
                service_type: os.environ.get(f"{service_type.upper()}_DEFAULT", None)
                for service_type in SERVICE_TYPES
            }

    def resolve_task(self, task_config: "TaskConfig") -> bool:
        """Resolve a service config using available services and declared policy.

        Args:
            task_config (ServiceConfig): Service configuration to resolve.

        Raises:
            NoServiceAvailable: No service exist to resolve this configuration.
        """
        service_type = task_config.service_type
        av_service_list = self.subservices_list[service_type]

        resolving_service = None

        # Not enabled
        if not task_config.isEnabled:
            logging.debug(
                f"Service {task_config.task_name} is not enabled, no resolve necessary."
            )
            return True

        # No service available
        if not av_service_list:
            raise NoServiceAvailable(service_type)

        # No service_name specified
        if task_config.serviceName is None:
            if self.service_policy == ServicePolicy.STRICT:
                raise NoServiceSpecified(service_type)
            if self.service_policy == ServicePolicy.DEFAULT:
                resolving_service = self._resolve_default(service_type)
            else:
                resolving_service = self._resolve_any(service_type)

        # Service match
        if task_config.serviceName in av_service_list:
            resolving_service = av_service_list[task_config.serviceName]

        if resolving_service is None:
            raise ServiceUnavailable(task_config.serviceName, self.service_policy)

        task_config.setService(
            resolving_service.service_name, resolving_service.queue_name
        )

    def _resolve_any(self, service_type: str) -> "Service":
        """Pick any of compatible running intance of the service_type

        Args:
            service_type (str): Type of service specified in SERVICE_TYPES

        Raises:
            NoServiceAvailable: No running instance exist for the service_type

        Returns:
            Service: Instance of Service
        """
        if self.subservices_list[service_type]:
            return list(self.subservices_list[service_type].items())[0][1]
        else:
            raise NoServiceAvailable(service_type=service_type)

    def _resolve_default(self, service_type: str) -> "Service":
        default_service_name = self.default_services.get(service_type, False)
        if default_service_name:
            if default_service_name in self.subservices_list[service_type]:
                return self.subservices_list[service_type][default_service_name]
            else:
                raise DefaultUnavailable(
                    default_service_name, service_type, self.service_policy
                )
        else:
            raise NoDefaultDeclared(
                service_type=service_type, policy=self.service_policy
            )
