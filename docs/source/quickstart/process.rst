Process Management
====================

In this section, you'll learn: 🎯

- How to manage the process using `pm2` 📦


Install pm2
------------

.. code-block:: bash

    npm install -g pm2

Start the process
------------------

create a process named "trader" and when stopping the process, wait for 10 seconds before killing the process. (need some time to release the resources)

.. code-block:: bash

   pm2 start trader.py --name "trader" --kill-timeout 10000

List all processes
------------------

.. code-block:: bash

   pm2 ls

Stop the process
-----------------

.. code-block:: bash

   pm2 stop trader

More resources
--------------

- `pm2 documentation <https://pm2.keymetrics.io/docs/usage/process-management/>`_
-  `pm2 python <https://pm2.io/blog/2018/09/19/Manage-Python-Processes>`_
- `pm2 github <https://github.com/Unitech/pm2>`_

