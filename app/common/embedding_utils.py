from __future__ import annotations

from collections.abc import Sequence
from typing import Any, List


class EmbeddingUtils:
    """Utility helpers for normalizing embedding payloads."""

    @staticmethod
    def to_vector(value: Any) -> List[float]:
        """
        임베딩 표현의 형식들을 List[float]로 변환하기 (임베딩 형식 반환 너무 더러워서)
        """
        if value is None:
            raise ValueError("Embedding value cannot be None.")

        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                stripped = stripped[1:-1]

            if not stripped:
                return []

            components = [
                component.strip()
                for component in stripped.split(",")
                if component.strip()
            ]
            return [float(component) for component in components]

        if isinstance(value, Sequence):
            # list, tuple, numpy arrays, etc.
            return [float(component) for component in value]

        raise TypeError(f"Unsupported embedding value type: {type(value)!r}")
