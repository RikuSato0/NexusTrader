Setting up Keys
======================

Create a ``.keys`` directory in the root directory of the project and add the following files:

- ``.secrets.toml``: Contains the api keys for the exchanges.

.. code-block:: bash

   mkdir .keys
   touch .keys/.secrets.toml

Example:

.. code-block:: toml


   [BYBIT.ACCOUNT1]
   api_key = "your_api_key"
   secret = "your_secret_key"

Then you can access the api key and secret by using the following code:

.. code-block:: python

   from nexustrader.constants import settings
   print(settings.BYBIT.ACCOUNT1.api_key)
   print(settings.BYBIT.ACCOUNT1.secret)
