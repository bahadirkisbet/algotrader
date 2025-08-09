import threading
from typing import Dict, Any


class Singleton(type):
    """
    Thread-safe singleton metaclass implementation.
    It can be used as a metaclass for a class that should have a single instance.
    """
    _instances: Dict[type, Any] = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                # Double-checked locking pattern
                if cls not in cls._instances:
                    cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

    @classmethod
    def clear_instance(cls, instance_class: type) -> None:
        """Clear a specific singleton instance (useful for testing)"""
        with cls._lock:
            if instance_class in cls._instances:
                del cls._instances[instance_class]

    @classmethod
    def clear_all_instances(cls) -> None:
        """Clear all singleton instances (useful for testing)"""
        with cls._lock:
            cls._instances.clear()
