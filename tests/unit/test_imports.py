def test_import_knowledge_core():
    import knowledge_core

    assert knowledge_core is not None


def test_import_knowledge_api():
    import knowledge_api

    assert knowledge_api is not None


def test_import_knowledge_workers():
    import knowledge_workers

    assert knowledge_workers is not None


def test_import_config():
    from knowledge_core.config import settings

    assert settings is not None
    assert settings.app_name == "Knowledge"


def test_import_exceptions():
    from knowledge_core.exceptions import DocumentProcessingError, KnowledgeError

    assert issubclass(DocumentProcessingError, KnowledgeError)
