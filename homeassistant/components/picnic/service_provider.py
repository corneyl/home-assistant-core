import dataclasses
import logging

from python_picnic_api import PicnicAPI

from homeassistant.core import ServiceCall
from homeassistant.helpers import device_registry
from .base_service_provider import BaseServiceProvider
from .const import CONF_API, DOMAIN


class PicnicServiceProvider(BaseServiceProvider):
    @dataclasses.dataclass
    class Product:
        id: str
        name: str
        price: float
        quantity: str

    # @staticmethod
    # def handle(call: ServiceCall):
    #     """Handle a Picnic service call."""
    #     # Create an instance of this service provider
    #     service_provider = PicnicServiceProvider(call.data)
    #
    #     # Call the service handler if available
    #     handler = getattr(service_provider, f"handle_{call.service}")
    #     if callable(handler):
    #         handler()

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)

    async def get_api_client(self, device_id: str = None):
        if device_id is None:
            default_config_id = list(self.hass.data[DOMAIN].keys())[0]
            return self.hass.data[DOMAIN][default_config_id][CONF_API]

        # Get device from registry
        registry = await device_registry.async_get_registry(self.hass)
        device = registry.async_get(device_id)

        # Get Picnic API client for the config entry id
        try:
            config_entry_id = next(iter(device.config_entries))
            return self.hass.data[DOMAIN][config_entry_id][CONF_API]
        except (AttributeError, StopIteration, KeyError) as error:
            self.fail(f"Device with id {device_id} not found!")

    @BaseServiceProvider.handle_service("add_product", DOMAIN)
    async def handle_add_product(self, call: ServiceCall):
        # Get the picnic API client
        api_client: PicnicAPI = await self.get_api_client(call.data.get('device_id'))

        product_id = call.data.get('product_id')
        if not product_id:
            search_results = await self.hass.async_add_executor_job(
                self.search, api_client, call.data.get('product_name')
            )
            if search_results:
                product_id = search_results[0].id

        if not product_id:
            self.fail("No product found or no product ID given!")

        await self.hass.async_add_executor_job(
            api_client.add_product, product_id, call.data.get('amount', 1)
        )

    @BaseServiceProvider.handle_service("search", DOMAIN)
    async def handle_search(self, call: ServiceCall):
        # Get the picnic API client
        api_client: PicnicAPI = await self.get_api_client(call.data.get('device_id'))
        products = await self.hass.async_add_executor_job(
            self.search, api_client, call.data.get('product_name')
        )

        products_dict = {p.id: dataclasses.asdict(p) for p in products[:5]}
        self.hass.bus.async_fire("picnic_search_result", products_dict)

    def search(self, api_client, product_name):
        # Get the search result
        search_result = api_client.search(product_name)

        # Curate a list of Product objects
        products = []
        for item in search_result[0]['items']:
            if 'name' in item:
                products += [self.Product(
                    id=item['id'], name=item['name'], price=item['display_price'] / 100, quantity=item['unit_quantity']
                )]

        return products
