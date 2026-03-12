from core.config import ATLAS_MODEL_INSTANCE_ID, MOLMO_MODEL_INSTANCE_ID, logger
from infra.http_utils import async_request, request_gcp


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ModelIPStorage(metaclass=Singleton):
    def __init__(self):
        self._model_ip_atlas = None
        self._model_ip_molmo = None

    async def initialize(self):
        self._model_ip_atlas = await self.check_instance(ATLAS_MODEL_INSTANCE_ID, "ATLAS")
        self._model_ip_molmo = await self.check_instance(MOLMO_MODEL_INSTANCE_ID, "MOLMO")


    async def check_instance(self, instance_id, name):
        ip = None
        status_code, response = await request_gcp("check", {"instance_id": instance_id})
        if status_code != 200:
            logger.info(f"{name=} {instance_id=} {ip=}")
            return ip
        if isinstance(response, list):
            ip = response[0].get('PublicIpAddress', None)

        if ip:
            status, _ = await async_request(f"http://{ip}:8001/health", method='get', timeout=10)
            if status != 200:
                ip = None

        logger.info(f"{name=} {instance_id=} {ip=}")
        return ip

    def set_model_ip_atlas(self, ip: str):
        if not ip:
            ip = None
        self._model_ip_atlas = ip
        logger.info(f"New model_ip: {self._model_ip_atlas}")

    def set_model_ip_molmo(self, ip: str):
        if not ip:
            ip = None
        self._model_ip_molmo = ip
        logger.info(f"New model_ip molmo: {self._model_ip_molmo}")

    async def get_model_ip_atlas(self) -> str:
        self._model_ip_atlas = await self.check_instance(ATLAS_MODEL_INSTANCE_ID, "ATLAS")
        return self._model_ip_atlas

    async def get_model_ip_molmo(self) -> str:
        self._model_ip_molmo = await self.check_instance(MOLMO_MODEL_INSTANCE_ID, "MOLMO")
        return self._model_ip_molmo

    @property
    def model_ip_atlas(self) -> str:
        return self._model_ip_atlas

    @property
    def model_ip_molmo(self) -> str:
        return self._model_ip_molmo


model_ip_store = ModelIPStorage()
