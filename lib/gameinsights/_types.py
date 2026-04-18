"""Shared type aliases for the gameinsights package."""

from typing import Literal, TypeAlias

ReturnFormat: TypeAlias = Literal["list", "dataframe"]
Scope: TypeAlias = Literal["id", "name"]
HttpMethod: TypeAlias = Literal["GET", "POST"]
