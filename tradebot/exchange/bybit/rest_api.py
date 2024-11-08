import hmac
import hashlib
from tradebot.base import ApiClient




class BybitApiClient(ApiClient):
    def __init__(
        self,
        api_key: str = None,
        secret: str = None,
        testnet: bool = False,
        timeout: int = 10,
    ):
        super().__init__(
            api_key=api_key,
            secret=secret,
            testnet=testnet,
            timeout=timeout,
        )
        
        self._testnet = testnet
    
    def _generate_signature(self, query: str) -> str:
        signature = hmac.new(
            bytes(self._secret, "utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _auth(self, payload, recv_window: int = 5000):
        if self._api_key is None or self._secret is None:
            raise PermissionError("API Key and Secret must be set")
        
        timestamp = self._clock.timestamp_ms()
        query = f"{timestamp}{self._api_key}{recv_window}{payload}"
        return self._generate_signature(query)
        
    
    
