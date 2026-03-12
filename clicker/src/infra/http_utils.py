import aiohttp
from aiohttp import ClientConnectorError

from core.config import GCP_ENDPOINT, logger


async def request_gcp(command: str, params: dict = None):
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as client:
        url = f"{GCP_ENDPOINT}/{command}"
        try:
            async with client.get(url, params=params) as resp:
                response = await resp.json()
                return resp.status, response
        except ClientConnectorError as e:
            logger.error(e, exc_info=True)
            return 503, {"error": "Service unavailable"}
        except Exception as e:
            logger.error(e, exc_info=True)
            return 500, {"error": f"Unexpected error occurred: {str(e)}"}


async def async_request(url: str, params: dict = None,
                        method: str = 'get', timeout: int = 30, to=None):
    tm = aiohttp.ClientTimeout(total=timeout)
    async with aiohttp.ClientSession(timeout=tm) as client:
        try:
            if method == 'post':
                to = 'json' if to is None else to
                async with client.post(url, json=params) as resp:
                    response = await resp.json() if to == 'json' else await resp.text()

            else:
                to = 'text' if to is None else to
                async with client.get(url, params=params) as resp:
                    response = await resp.json() if to == 'json' else await resp.text()
            return resp.status, response

        except aiohttp.ClientConnectorError as er:
            logger.error(er, exc_info=True)
            return None, None
        except aiohttp.ClientError as er:
            logger.error(er, exc_info=True)
            return None, None
        except Exception as er:
            logger.error(er, exc_info=True)
            return None, None