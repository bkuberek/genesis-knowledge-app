import re
from typing import Any

import numpy as np
import pandas as pd

from knowledge_workers.parsers.base_parser import BaseParser

SUPPORTED_CONTENT_TYPES = frozenset({"text/csv", "application/csv", ".csv"})

NAME_COLUMN_PATTERNS = (
    re.compile(r"^(company[_\s]?name|name|title|label)$", re.IGNORECASE),
    re.compile(r"(^name$|_name$|_title$)", re.IGNORECASE),
)

ENTITY_TYPE_HINTS: dict[str, str] = {
    "company": "company",
    "person": "person",
    "product": "product",
    "organization": "organization",
    "user": "user",
    "employee": "employee",
    "customer": "customer",
}


class CsvParser(BaseParser):
    """Parser for CSV files using pandas.

    Supports two modes:
    - Structured extraction: returns entity dicts for direct ingestion
    - Text parsing: returns text representation for LLM extraction (legacy)
    """

    async def parse(self, file_path: str) -> str:
        """Parse a CSV file and return structured text with column info."""
        dataframe = pd.read_csv(file_path)
        row_count = len(dataframe)
        column_count = len(dataframe.columns)
        column_names = ", ".join(dataframe.columns.tolist())

        lines = [
            f"CSV Data with {row_count} rows and {column_count} columns",
            f"Columns: {column_names}",
            "",
            dataframe.to_string(index=False),
        ]
        return "\n".join(lines)

    def supports(self, content_type: str) -> bool:
        """Check if this parser supports the given content type."""
        return content_type in SUPPORTED_CONTENT_TYPES

    def extract_entities(self, file_path: str) -> list[dict[str, Any]]:
        """Parse CSV rows directly into entity dicts for ingestion.

        Each row becomes one entity. The first name-like column becomes
        the entity name; remaining columns become properties with proper
        numeric types preserved.
        """
        dataframe = pd.read_csv(file_path)
        if dataframe.empty:
            return []

        columns = dataframe.columns.tolist()
        name_column = _detect_name_column(columns)
        entity_type = _infer_entity_type(columns)
        property_columns = [col for col in columns if col != name_column]

        entities: list[dict[str, Any]] = []
        for _, row in dataframe.iterrows():
            name_value = str(row[name_column]).strip()
            if not name_value or name_value.lower() == "nan":
                continue

            properties = _build_properties(row, property_columns)
            entities.append(
                {
                    "name": name_value,
                    "type": entity_type,
                    "properties": properties,
                }
            )

        return entities


def _detect_name_column(columns: list[str]) -> str:
    """Find the column most likely to contain entity names."""
    for pattern in NAME_COLUMN_PATTERNS:
        for col in columns:
            if pattern.search(col):
                return col
    return columns[0]


def _infer_entity_type(columns: list[str]) -> str:
    """Infer entity type from column names."""
    joined = " ".join(columns).lower()
    for keyword, entity_type in ENTITY_TYPE_HINTS.items():
        if keyword in joined:
            return entity_type
    return "record"


def _build_properties(row: pd.Series, columns: list[str]) -> dict[str, Any]:
    """Build a properties dict preserving numeric types."""
    properties: dict[str, Any] = {}
    for col in columns:
        value = row[col]
        properties[col] = _coerce_value(value)
    return properties


def _coerce_value(value: Any) -> Any:
    """Coerce pandas/numpy values to native Python types."""
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return round(float(value), 4) if not np.isnan(value) else None
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, str):
        return value.strip()
    return value
