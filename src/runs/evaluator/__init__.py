"""
PRS Evaluator - 3-Layer Waterfall 평가 시스템

Format → Semantic → Logic → Pass (fail-fast)
"""

from .format_layer import check_format

__all__ = ["check_format"]
