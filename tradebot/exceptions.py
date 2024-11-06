class OrderError(Exception):
    def __init__(self, original_error: Exception, params: dict):
        self.original_error = original_error
        self.params = params
        super().__init__(str(original_error))

    def __str__(self):
        context_str = "\n".join(f"  {k}: {v}" for k, v in self.params.items())
        return (f"OrderResponseError: {self.original_error}\n"
                f"Params:\n{context_str}")

    def __repr__(self):
        return self.__str__()

class ExchangeResponseError(Exception):
    def __init__(self, message, data, method, url):
        self.data = data
        self.method = method
        self.url = url
        
        super().__init__(message)
    
    def __str__(self):
        return f"Exchange {self.method} {self.url}: {self.data}"
    
    def __repr__(self):
        return self.__str__()
