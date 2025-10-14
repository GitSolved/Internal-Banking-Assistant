import hashlib
import logging
from pathlib import Path

from llama_index.core.readers import StringIterableReader
from llama_index.core.readers.base import BaseReader
from llama_index.core.readers.json import JSONReader
from llama_index.core.schema import Document

logger = logging.getLogger(__name__)


# Inspired by the `llama_index.core.readers.file.base` module
def _try_loading_included_file_formats() -> dict[str, type[BaseReader]]:
    try:
        from llama_index.readers.file.docs import (  # type: ignore
            DocxReader,
            HWPReader,
            PDFReader,
        )
        from llama_index.readers.file.epub import EpubReader  # type: ignore
        from llama_index.readers.file.image import ImageReader  # type: ignore
        from llama_index.readers.file.ipynb import IPYNBReader  # type: ignore
        from llama_index.readers.file.markdown import MarkdownReader  # type: ignore
        from llama_index.readers.file.mbox import MboxReader  # type: ignore
        from llama_index.readers.file.slides import PptxReader  # type: ignore
        from llama_index.readers.file.tabular import PandasCSVReader  # type: ignore
        from llama_index.readers.file.video_audio import (  # type: ignore
            VideoAudioReader,
        )
    except ImportError as e:
        raise ImportError("`llama-index-readers-file` package not found") from e

    default_file_reader_cls: dict[str, type[BaseReader]] = {
        ".hwp": HWPReader,
        ".pdf": PDFReader,
        ".docx": DocxReader,
        ".pptx": PptxReader,
        ".ppt": PptxReader,
        ".pptm": PptxReader,
        ".jpg": ImageReader,
        ".png": ImageReader,
        ".jpeg": ImageReader,
        ".mp3": VideoAudioReader,
        ".mp4": VideoAudioReader,
        ".csv": PandasCSVReader,
        ".epub": EpubReader,
        ".md": MarkdownReader,
        ".mbox": MboxReader,
        ".ipynb": IPYNBReader,
    }
    return default_file_reader_cls


# Patching the default file reader to support other file types
FILE_READER_CLS = _try_loading_included_file_formats()
FILE_READER_CLS.update(
    {
        ".json": JSONReader,
        # Text files should use StringIterableReader for consistent handling
        # This prevents the "No reader found" warning for .txt files
        ".txt": type("TextFileReader", (BaseReader,), {
            "load_data": lambda self, file: [
                Document(
                    text=file.read_text(encoding='utf-8'),
                    metadata={"file_path": str(file)}
                )
            ]
        }),
    }
)


class IngestionHelper:
    """Helper class to transform a file into a list of documents.

    This class should be used to transform a file into a list of documents.
    These methods are thread-safe (and multiprocessing-safe).
    """

    @staticmethod
    def _get_file_hash(file_path: Path) -> str:
        """Generate SHA-256 hash of file content for duplicate detection."""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.warning(f"Could not compute hash for {file_path}: {e}")
            return ""

    @staticmethod
    def transform_file_into_documents(
        file_name: str, file_data: Path
    ) -> list[Document]:
        documents = IngestionHelper._load_file_to_documents(file_name, file_data)
        content_hash = IngestionHelper._get_file_hash(file_data)

        # Get file metadata
        try:
            file_size = file_data.stat().st_size
            creation_time = file_data.stat().st_ctime
            creation_date = Path(file_data).stat().st_ctime
        except Exception as e:
            logger.warning(f"Could not get file metadata for {file_data}: {e}")
            file_size = 0
            creation_date = ""

        for document in documents:
            document.metadata["file_name"] = file_name
            document.metadata["file_size"] = file_size
            document.metadata["creation_date"] = (
                str(creation_date) if creation_date else ""
            )
            if content_hash:
                document.metadata["content_hash"] = content_hash

        IngestionHelper._exclude_metadata(documents)
        return documents

    @staticmethod
    def _load_file_to_documents(file_name: str, file_data: Path) -> list[Document]:
        logger.debug("Transforming file_name=%s into documents", file_name)
        extension = Path(file_name).suffix.lower()
        reader_cls = FILE_READER_CLS.get(extension)

        if reader_cls is None:
            logger.warning(
                f"No reader found for extension={extension}, file={file_name}. "
                f"Supported extensions: {list(FILE_READER_CLS.keys())}. "
                f"Using default string reader."
            )
            # Read as a plain text
            try:
                string_reader = StringIterableReader()
                return string_reader.load_data([file_data.read_text()])
            except Exception as e:
                logger.error(f"Failed to read file {file_name} as text: {e}")
                raise

        logger.debug("Specific reader found for extension=%s", extension)
        try:
            documents = reader_cls().load_data(file_data)
            logger.info(
                f"Successfully loaded {len(documents)} documents from {file_name}"
            )
        except Exception as e:
            logger.error(
                f"Failed to load file {file_name} with {reader_cls.__name__}: {e}"
            )
            raise

        # Sanitize NUL bytes in text which can't be stored in Postgres
        for i in range(len(documents)):
            documents[i].text = documents[i].text.replace("\u0000", "")

        return documents

    @staticmethod
    def _exclude_metadata(documents: list[Document]) -> None:
        logger.debug("Excluding metadata from count=%s documents", len(documents))
        for document in documents:
            document.metadata["doc_id"] = document.doc_id
            # We don't want the Embeddings search to receive this metadata
            document.excluded_embed_metadata_keys = ["doc_id"]
            # We don't want the LLM to receive these metadata in the context
            # Note: content_hash is kept for duplicate detection but not sent to LLM
            document.excluded_llm_metadata_keys = [
                "file_name",
                "doc_id",
                "page_label",
                "content_hash",
            ]
