# Configuration file for the Sphinx documentation builder.

import os
import sys
sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -----------------------------------------------------

project = 'TradeBot'
copyright = '2024, Your Name'
author = 'Your Name'
release = '0.1.0'

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
]

templates_path = ['_templates']
exclude_patterns = []

# Enable TODO
todo_include_todos = True

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_material'
html_theme_options = {
    'base_url': 'https://tradebot.readthedocs.io/',
    'repo_url': 'https://github.com/yourusername/tradebot/',
    'repo_name': 'TradeBot',
    'globaltoc_depth': 2,
    'color_primary': 'blue-grey',
    'color_accent': 'indigo',
    'features': [
        'navigation.expand',
        'navigation.tabs',
        'toc.integrate',
        'navigation.sections',
        'navigation.instant',
        'header.autohide',
    ],
    'palette': [
        {
            'scheme': 'default',
            'primary': 'blue-grey',
            'accent': 'indigo',
            'toggle': {
                'icon': 'material/weather-night',
                'name': 'Switch to dark mode',
            }
        },
        {
            'scheme': 'slate',
            'primary': 'blue-grey',
            'accent': 'indigo',
            'toggle': {
                'icon': 'material/weather-sunny',
                'name': 'Switch to light mode',
            }
        }
    ],
}

html_sidebars = {
    '**': ['logo-text.html', 'globaltoc.html', 'localtoc.html', 'searchbox.html']
}

html_static_path = ['_static'] 
