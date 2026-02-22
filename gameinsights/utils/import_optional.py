"""Optional dependency lazy-import helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd  # noqa: F401


def import_pandas() -> Any:
    """Lazy-import pandas, raising a helpful error if not installed.

    Returns:
        The pandas module.

    Raises:
        ImportError: With installation instructions if pandas is not available.

    Example:
        >>> pd = import_pandas()
        >>> df = pd.DataFrame([{"a": 1}])
    """
    try:
        import pandas as pd_module

        return pd_module
    except ImportError:
        raise ImportError(
            "pandas is required for DataFrame operations. "
            "Install it with: pip install gameinsights[dataframe] "
            "or: poetry install --extras dataframe"
        ) from None


__all__ = ["import_pandas"]
