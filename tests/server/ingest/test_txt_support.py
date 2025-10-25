"""Test to verify .txt files are properly supported."""

from pathlib import Path

from internal_assistant.components.ingest.ingest_helper import (
    FILE_READER_CLS,
    IngestionHelper,
)


def test_txt_extension_is_supported() -> None:
    """Verify .txt extension is in supported file types.

    This prevents the "No reader found for extension=.txt" warning
    that was occurring before the fix.

    See: ingest_helper.py:57-71
    Fix: Added .txt to FILE_READER_CLS dictionary
    """
    assert ".txt" in FILE_READER_CLS, (
        ".txt extension should be in FILE_READER_CLS to avoid fallback warnings. "
        "Check internal_assistant/components/ingest/ingest_helper.py"
    )


def test_txt_reader_loads_content(tmp_path: Path) -> None:
    """Verify .txt reader actually loads text content correctly."""
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_content = (
        "This is a test document with some content.\nIt has multiple lines.\n"
    )
    test_file.write_text(test_content, encoding="utf-8")

    # Transform using IngestionHelper
    documents = IngestionHelper.transform_file_into_documents(
        file_name="test.txt", file_data=test_file
    )

    assert len(documents) == 1, "Should create one document from .txt file"
    assert test_content in documents[0].text, "Document should contain file content"
    assert "file_name" in documents[0].metadata, "Should have file_name metadata"
    assert (
        documents[0].metadata["file_name"] == "test.txt"
    ), "Filename should be preserved"


def test_txt_reader_handles_unicode(tmp_path: Path) -> None:
    """Verify .txt reader handles Unicode characters correctly."""
    test_file = tmp_path / "unicode_test.txt"
    test_content = "Unicode test: 你好 🎉 Привет مرحبا"
    test_file.write_text(test_content, encoding="utf-8")

    documents = IngestionHelper.transform_file_into_documents(
        file_name="unicode_test.txt", file_data=test_file
    )

    assert len(documents) == 1
    assert test_content in documents[0].text, "Unicode characters should be preserved"


def test_txt_reader_handles_empty_file(tmp_path: Path) -> None:
    """Verify .txt reader handles empty files gracefully."""
    test_file = tmp_path / "empty.txt"
    test_file.write_text("", encoding="utf-8")

    documents = IngestionHelper.transform_file_into_documents(
        file_name="empty.txt", file_data=test_file
    )

    assert len(documents) == 1, "Should create document even for empty file"
    assert documents[0].text == "", "Document text should be empty string"
