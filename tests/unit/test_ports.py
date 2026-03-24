import pytest

from knowledge_core.ports.database_repository_port import DatabaseRepositoryPort
from knowledge_core.ports.document_storage_port import DocumentStoragePort


class TestDatabaseRepositoryPort:
    def test_database_repository_port_is_abstract(self):
        with pytest.raises(TypeError, match="abstract"):
            DatabaseRepositoryPort()


class TestDocumentStoragePort:
    def test_document_storage_port_is_abstract(self):
        with pytest.raises(TypeError, match="abstract"):
            DocumentStoragePort()
