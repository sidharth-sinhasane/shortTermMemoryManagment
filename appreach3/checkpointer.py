from __future__ import annotations

import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

from langchain_core.runnables import RunnableConfig
from psycopg import Connection, Pipeline
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from langgraph.checkpoint.base import (
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.serde.base import SerializerProtocol


class CustomPostgresSaver:
    """Custom wrapper around PostgresSaver that delegates all calls to the underlying PostgresSaver."""

    def __init__(
        self,
        conn: Connection | ConnectionPool,
        pipe: Pipeline | None = None,
        serde: SerializerProtocol | None = None,
    ) -> None:
        self._postgres_saver = PostgresSaver(conn, pipe, serde)

    @classmethod
    @contextmanager
    def from_conn_string(
        cls, conn_string: str, *, pipeline: bool = False
    ) -> Iterator['CustomPostgresSaver']:
        """Create a new CustomPostgresSaver instance from a connection string."""
        with Connection.connect(
            conn_string, autocommit=True, prepare_threshold=0, row_factory=dict_row
        ) as conn:
            if pipeline:
                with conn.pipeline() as pipe:
                    yield cls(conn, pipe)
            else:
                yield cls(conn)

    def setup(self) -> None:
        """Set up the checkpoint database."""
        return self._postgres_saver.setup()

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        """List checkpoints from the database."""
        return self._postgres_saver.list(config, filter=filter, before=before, limit=limit)

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """Get a checkpoint tuple from the database."""
        return None

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        """Save a checkpoint to the database."""
        # Pseudo-code
        channel_values = checkpoint.get("channel_values", {})

        if not channel_values.get("user"):
            return  # Skip - no user information
            
        if not channel_values.get("response"):
            return  # Skip - no AI response
            
        if not channel_values.get("messages"):
            return  # Skip - no conversation messages
            
        # Additional check: must have session_id for thread identification
        if not channel_values.get("session_id"):
            return  # Skip - no session ID


        # for k, v in checkpoint["channel_values"].items():
        #     if k == "user":
        #         checkpoint["channel_values"][k] = dict(v) if hasattr(v, '__dict__') else v
        #     elif k == "messages":
        #         checkpoint["channel_values"][k] = [msg.content for msg in v]
        print(checkpoint)
        return self._postgres_saver.put(config, checkpoint, metadata, new_versions)

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """Store intermediate writes linked to a checkpoint."""
        # return self._postgres_saver.put_writes(config, writes, task_id, task_path)
        return None

    def delete_thread(self, thread_id: str) -> None:
        """Delete all checkpoints and writes associated with a thread ID."""
        return self._postgres_saver.delete_thread(thread_id)

    def get_next_version(self, current: str | float | None, channel: str) -> str | float:
        """Get the next version for a channel."""
        return self._postgres_saver.get_next_version(current, channel)

    def __getattr__(self, name):
        """Delegate any missing attributes to the underlying PostgresSaver."""
        return getattr(self._postgres_saver, name)

    # Context manager support
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # PostgresSaver doesn't seem to have explicit cleanup, but we can pass through
        if hasattr(self._postgres_saver, '__exit__'):
            return self._postgres_saver.__exit__(exc_type, exc_val, exc_tb)
        return None