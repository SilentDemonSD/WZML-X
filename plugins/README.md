# WZML-X Plugins

This directory contains plugins for the WZML-X bot system.

## Structure

```
plugins/
├── __init__.py
├── speedtest/
│   ├── __init__.py
│   ├── wzml_plugin.yml
│   ├── requirements.txt
│   └── speedtest.py
└── [other_plugins]/
    ├── __init__.py
    ├── wzml_plugin.yml
    ├── requirements.txt
    └── [plugin_files].py
```

## Plugin Requirements

Each plugin must contain:
- `wzml_plugin.yml` - Plugin manifest
- `requirements.txt` - Python dependencies
- Main plugin file (.py)
- `__init__.py` - Python package file

## Available Plugins

### Speedtest Plugin
- **Path**: `plugins/speedtest/`
- **Commands**: `/speedtest`, `/speedtest_servers`
- **Description**: Network speed testing with multiple servers
- **Dependencies**: speedtest-cli, pillow

## Installation

Plugins are automatically loaded during bot startup if enabled in their manifest.
