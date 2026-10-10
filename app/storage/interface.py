from abc import ABC, abstractmethod

class StorageInterface(ABC):
    @abstractmethod
    def save_file(self, content: bytes, filename: str) -> str:
        """Save a file and return its path/URI."""
        pass
        
    @abstractmethod
    def get_file_path(self, filename: str) -> str:
        """Returns the absolute or reachable path of the file."""
        pass
