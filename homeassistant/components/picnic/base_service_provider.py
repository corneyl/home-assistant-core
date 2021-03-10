from homeassistant.core import HomeAssistant


class ServiceCallError(Exception):
    """Error indicating a service call failed to execute."""


class ServiceProviderMetaclass(type):

    def __new__(mcs, name, bases, namespace, **kwds):
        """Create a list of service handlers in the class at class (not object!) instantiation."""
        # Create the class definition
        result = type.__new__(mcs, name, bases, dict(namespace))

        # Get a list of functions which have the _is_handler attribute and save it as class variable.
        result._handlers = []
        for value in namespace.values():
            if hasattr(value, 'is_handler'):
                result._handlers += [value]
            # Special case for static methods
            elif hasattr(value, '__func__') and hasattr(value.__func__, 'is_handler'):
                result._handlers += [value.__func__]

        return result


class BaseServiceProvider(metaclass=ServiceProviderMetaclass):
    hass: HomeAssistant = None

    async def register(self, hass: HomeAssistant):
        """Registers all service handlers defined in the class."""
        for handler in self._handlers:
            # Get a function or bound object function
            if isinstance(handler, staticmethod):
                bound_func = handler.__func__
            else:
                bound_func = handler.__get__(self)

            hass.services.async_register(handler.domain, handler.name, bound_func)

        # Save reference to hass
        self.hass = hass

    def fail(self, message: str):
        raise ServiceCallError(message)

    @staticmethod
    def handle_service(name, domain):
        """Provides a decorator to indicate for which domain/service name the method is a handler."""

        def handles_service_decorator(decorated):
            # Decorate method with attributes so we know it's a handler
            decorated.is_handler = True
            decorated.name = name
            decorated.domain = domain

            return decorated

        return handles_service_decorator
