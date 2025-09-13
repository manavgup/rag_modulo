"""Core configuration classes.

This module re-exports device flow configuration to maintain
clean test imports while keeping the main logic in device_flow.py.
"""

from .device_flow import DeviceFlowConfig

__all__ = ["DeviceFlowConfig"]
