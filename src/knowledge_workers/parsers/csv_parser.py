import pandas as pd

from knowledge_workers.parsers.base_parser import BaseParser

SUPPORTED_CONTENT_TYPES = frozenset({"text/csv", "application/csv", ".csv"})


class CsvParser(BaseParser):
    """Parser for CSV files using pandas."""

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
