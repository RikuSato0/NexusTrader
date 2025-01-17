Installation
============

Prerequisites
-------------

- Python 3.11+
- Redis
- Poetry (recommended)

Install from PyPI
-----------------

.. code-block:: bash

   pip install nexustrader

Install from source
-------------------

.. code-block:: bash

   git clone https://github.com/RiverTrading/NexusTrader
   cd NexusTrader
   poetry install 


Install Redis
-------------

First, create a ``.env`` file in the root directory of the project and add the following environment variables:

.. code-block:: bash

   NEXUS_REDIS_HOST=127.0.0.1
   NEXUS_REDIS_PORT=6379
   NEXUS_REDIS_DB=0
   NEXUS_REDIS_PASSWORD=your_password

Then, run the following command to start the Redis container:

.. code-block:: bash

   docker-compose up -d redis

.. note::

   Currently, NexusTrader only tested on Linux and MacOS. Windows is not supported yet.
