from pathlib import Path

from internal_assistant.constants import PROJECT_ROOT_PATH


def _absolute_or_from_project_root(path: str) -> Path:
    if path.startswith("/"):
        return Path(path)
    return PROJECT_ROOT_PATH / path


models_path: Path = PROJECT_ROOT_PATH / "models"
models_cache_path: Path = models_path / "cache"
docs_path: Path = PROJECT_ROOT_PATH / "docs"

def _get_local_data_path() -> Path:
    """Lazy initialization of local_data_path to avoid circular import."""
    from internal_assistant.settings.settings import settings
    return _absolute_or_from_project_root(settings().data.local_data_folder)

# Use a property-like access pattern to delay settings() call
class _LocalDataPath:
    def __init__(self):
        self._path = None
    
    def __truediv__(self, other):
        if self._path is None:
            self._path = _get_local_data_path()
        return self._path / other
    
    @property
    def path(self) -> Path:
        if self._path is None:
            self._path = _get_local_data_path()
        return self._path
    
    def __str__(self) -> str:
        return str(self.path)

local_data_path = _LocalDataPath()
