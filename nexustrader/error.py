class NexusTraderError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class EngineBuildError(NexusTraderError):
    def __init__(self, message: str):
        super().__init__(message)

class SubscriptionError(NexusTraderError):
    def __init__(self, message: str):
        super().__init__(message)
