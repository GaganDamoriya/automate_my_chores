"""Agents package.

The ADK agent objects live in the submodules and require `google-adk`. We import
them lazily so the pure-Python tools (agents.tools.*) stay importable even when
ADK isn't installed (e.g. in lightweight test/CI contexts).
"""
try:
    from .root_agent import root_agent, discovery_pipeline  # noqa: F401
    from .rework import rework_agent  # noqa: F401
except ModuleNotFoundError:  # google-adk not installed
    root_agent = discovery_pipeline = rework_agent = None
