nexustrader.exchange.okx.ems
=====================================

.. currentmodule:: nexustrader.exchange.okx.ems

This module implements the Execution Management System (EMS) for OKX exchange, handling order submission and management across different account types.

Class Overview
-----------------

.. autoclass:: OkxExecutionManagementSystem
   :members:
   :undoc-members:
   :show-inheritance:

   .. rubric:: Account Type Priority

   The system prioritizes account types in the following order:
    1. Demo Account
    2. AWS Account
    3. Live Account

   .. rubric:: Key Features

   * Asynchronous order submission queue management
   * Support for multiple account types
   * Automatic account type selection based on priority
   * Order validation and minimum amount checks


