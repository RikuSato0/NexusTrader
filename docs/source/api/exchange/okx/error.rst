tradebot.exchange.okx.error
=====================================

.. currentmodule:: tradebot.exchange.okx.error

This module defines custom exception classes for handling OKX exchange-specific errors, including HTTP errors and API request errors.

Exception Classes
-----------------

.. autoclass:: OkxHttpError
   :members:
   :undoc-members:
   :show-inheritance:

   Base exception class for OKX HTTP-specific errors.

   :param status_code: HTTP status code
   :type status_code: int
   :param message: Error message
   :type message: str
   :param headers: HTTP response headers
   :type headers: dict[str, Any]

.. autoclass:: OkxRequestError
   :members:
   :undoc-members:
   :show-inheritance:

   Base exception class for OKX API-specific errors.

   :param error_code: OKX error code
   :type error_code: int
   :param status_code: HTTP status code (optional)
   :type status_code: int | None
   :param message: Error message (optional)
   :type message: str | None

   For a complete list of error codes, see the `OKX API documentation <https://www.okx.com/docs-v5/en/?python#error-code>`_.

