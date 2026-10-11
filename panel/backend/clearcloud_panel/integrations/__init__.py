"""Integration kinds. Importing this package registers all of them."""

from . import grafana, home_assistant, mqtt, omada, proxmox, truenas  # noqa: F401
from .base import REGISTRY, IntegrationType, TestResult

__all__ = ["REGISTRY", "IntegrationType", "TestResult"]
