# Configuration file for Sphinx documentation

import os
import sys
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("../"))
sys.path.insert(0, os.path.abspath('../..'))

project = 'TradeBot'
copyright = '2024, River Trading'
author = 'River Trading'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode', 
    'sphinx.ext.intersphinx',
    'sphinx_autodoc_typehints',
    'sphinx.ext.todo',
    'sphinx_markdown_tables',
]

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'furo'
html_static_path = ['_static']

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Todo settings
todo_include_todos = True

# Mock modules that might cause import issues
autodoc_mock_imports = ['aiohttp', 'redis', 'aioredis', 'ccxt', 'ccxt.pro', 'dynaconf', 'spdlog', 'nautilus_trader', 'orjson', 'aiosqlite', 'aiolimiter', 'returns', 'picows']


source_parsers = {
    '.md': 'recommonmark.parser.CommonMarkParser',
}

source_suffix = ['.rst', '.md']
