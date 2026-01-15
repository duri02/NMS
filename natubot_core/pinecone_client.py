from __future__ import annotations

from typing import Any, Dict, Optional

from pinecone import Pinecone
from pinecone.grpc import PineconeGRPC as PineconeGRPC

class PineconeClients:
    def __init__(self, api_key: str, index_name: str, index_host: str = ""):
        self.ctrl = Pinecone(api_key=api_key)
        self.index_name = index_name
        self.index_host = index_host
        self.grpc = PineconeGRPC(api_key=api_key)
        self.index = self.grpc.Index(host=self.resolve_host())

    def resolve_host(self) -> str:
        if self.index_host:
            return self.index_host
        desc = self.ctrl.describe_index(self.index_name)
        host = None
        if isinstance(desc, dict):
            host = desc.get("host") or desc.get("status", {}).get("host")
        else:
            host = getattr(desc, "host", None) or getattr(getattr(desc, "status", None), "host", None)
        if not host:
            raise RuntimeError(
                "Could not resolve PINECONE_INDEX_HOST. "
                "Set it manually from Pinecone Console (Index -> Host)."
            )
        return host

    def stats(self, namespace: str) -> Any:
        return self.index.describe_index_stats(namespace=namespace)

    def query(self, *, namespace: str, vector, top_k: int, include_metadata: bool = True,
              include_values: bool = False, filter: Optional[Dict[str, Any]] = None) -> Any:
        kwargs: Dict[str, Any] = dict(
            namespace=namespace,
            vector=vector,
            top_k=top_k,
            include_metadata=include_metadata,
            include_values=include_values,
        )
        if filter:
            kwargs["filter"] = filter
        return self.index.query(**kwargs)
