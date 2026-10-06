"""Opt-in local voice research, separate from the JARVIS runtime."""

from .lab import LabResult, run_voice_lab
from .lab_batch import BatchLabResult, run_voice_lab_batch

__all__ = ["LabResult", "run_voice_lab", "BatchLabResult", "run_voice_lab_batch"]
