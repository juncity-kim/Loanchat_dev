# src/orchestration/ports.py
from typing import Protocol, Dict, Any, List

class Compute(Protocol):
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]: ...

class Retriever(Protocol):
    def search(self, query: str) -> List[Dict[str, Any]]: ...
