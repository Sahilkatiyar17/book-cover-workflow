import sqlite3
import sys

from langgraph.checkpoint.sqlite import SqliteSaver

from app.utils.constants import GraphConfig
from app.utils.exception import AgentException
from app.utils.logger import logging

logger = logging.getLogger(__name__)


class CheckpointerFactory:
    """
    Owns creation and lifecycle management of the LangGraph checkpointer.
    Opens the SQLite connection directly (check_same_thread=False) rather than
    relying on SqliteSaver.from_conn_string()'s context-manager behavior, so the
    connection stays alive for the lifetime of the app process.
    """

    @staticmethod
    def get_sqlite_checkpointer(db_path: str = GraphConfig.CHECKPOINT_DB_PATH):
        try:
            conn = sqlite3.connect(db_path, check_same_thread=False)
            checkpointer = SqliteSaver(conn)
            logger.info(f"SQLite checkpointer initialized at {db_path}")
            return checkpointer
        except Exception as e:
            raise AgentException(e, sys) from e

    @staticmethod
    def clear_thread(checkpointer, thread_id: str) -> None:
        """
        Deletes all checkpoints for a completed thread.
        Call ONLY when a run has genuinely reached END — never for a
        paused (human-in-the-loop) or errored thread, since that data
        must persist for resume.
        """
        try:
            checkpointer.delete_thread(thread_id)
            logger.info(f"Cleared checkpoint data for completed thread: {thread_id}")
        except Exception as e:
            logger.warning(f"Failed to clear checkpoint for thread {thread_id}: {e}")