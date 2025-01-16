class TradebotError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class EngineBuildError(TradebotError):
    def __init__(self, message: str):
        super().__init__(message)

class SubscriptionError(TradebotError):
    def __init__(self, message: str):
        super().__init__(message)
