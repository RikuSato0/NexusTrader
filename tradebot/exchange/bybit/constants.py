from tradebot.constants import AccountType

class BybitAccountType(AccountType):
    SPOT = "SPOT"
    LINEAR = "LINEAR"
    INVERSE = "INVERSE"
    OPTION = "OPTION"
    SPOT_TESTNET = "SPOT_TESTNET"
    LINEAR_TESTNET = "LINEAR_TESTNET"
    INVERSE_TESTNET = "INVERSE_TESTNET"
    OPTION_TESTNET = "OPTION_TESTNET"
    
    @property
    def is_testnet(self):
        return self in {
            self.SPOT_TESTNET,
            self.LINEAR_TESTNET,
            self.INVERSE_TESTNET,
            self.OPTION_TESTNET,
        }
    
    @property
    def ws_public_url(self):
        return WS_PUBLIC_URL[self]
    
    @property
    def ws_private_url(self):
        if self.is_testnet:
            return "wss://stream-testnet.bybit.com/v5/private"
        return "wss://stream.bybit.com/v5/private"
    
    @property
    def is_spot(self):
        return self in {self.SPOT, self.SPOT_TESTNET}
    
    @property
    def is_linear(self):
        return self in {self.LINEAR, self.LINEAR_TESTNET}
    
    @property
    def is_inverse(self):
        return self in {self.INVERSE, self.INVERSE_TESTNET}
        
    
WS_PUBLIC_URL = {
    BybitAccountType.SPOT: "wss://stream.bybit.com/v5/public/spot",
    BybitAccountType.LINEAR: "wss://stream.bybit.com/v5/public/linear",
    BybitAccountType.INVERSE: "wss://stream.bybit.com/v5/public/inverse",
    BybitAccountType.OPTION: "wss://stream.bybit.com/v5/public/option",
    BybitAccountType.SPOT_TESTNET: "wss://stream-testnet.bybit.com/v5/public/spot",
    BybitAccountType.LINEAR_TESTNET: "wss://stream-testnet.bybit.com/v5/public/linear",
    BybitAccountType.INVERSE_TESTNET: "wss://stream-testnet.bybit.com/v5/public/inverse",
    BybitAccountType.OPTION_TESTNET: "wss://stream-testnet.bybit.com/v5/public/option",
}
