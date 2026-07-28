import sys
import uuid

from langgraph.graph import StateGraph, END
from langgraph.types import Command

from app.db.checkpointer import CheckpointerFactory
from app.graph.edges import BranchRouter
from app.graph.nodes import SelectionNode
from app.graph.state import GraphState
from app.services.image_search import ImageSearchNode
from app.services.ranking import RankingNode
from app.utils.constants import FeedbackBranch
from app.utils.exception import AgentException
from app.utils.logger import logging

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Owns graph construction: node registration, edges, and checkpointer wiring."""

    def __init__(self):
        self.image_search_node = ImageSearchNode()
        self.ranking_node = RankingNode()
        self.selection_node = SelectionNode()
        self.branch_router = BranchRouter()
        self.checkpointer = CheckpointerFactory.get_sqlite_checkpointer()

    def build(self):
        try:
            graph = StateGraph(GraphState)

            graph.add_node("image_search", self.image_search_node)
            graph.add_node("ranking", self.ranking_node)
            graph.add_node("selection", self.selection_node)

            graph.set_entry_point("image_search")
            graph.add_edge("image_search", "ranking")
            graph.add_edge("ranking", "selection")

            graph.add_conditional_edges(
                "selection",
                self.branch_router,
                {
                    FeedbackBranch.NO_FEEDBACK: END,
                    FeedbackBranch.TEXT_FEEDBACK: END,
                    FeedbackBranch.USER_IMAGE_UPLOAD: END,
                    FeedbackBranch.TEXT_AND_IMAGE: END,
                },
            )

            compiled = graph.compile(checkpointer=self.checkpointer)
            logger.info("Graph compiled successfully with SQLite checkpointer")
            return compiled
        except Exception as e:
            raise AgentException(e, sys) from e


class GraphRunner:
    """
    Owns a single request's lifecycle: fresh thread_id per run, invoke, resume
    after human input, and checkpoint cleanup only on genuine completion.
    """

    def __init__(self, builder: GraphBuilder):
        self.builder = builder
        self.graph = builder.build()

    def run(self, initial_state: dict) -> dict:
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        try:
            result = self.graph.invoke(initial_state, config=config)
            self._cleanup_if_complete(thread_id, config)
            return {"thread_id": thread_id, "state": result}
        except Exception as e:
            logger.warning(f"Run failed for thread {thread_id} — checkpoint preserved for resume: {e}")
            raise AgentException(e, sys) from e

    def resume(self, thread_id: str, resume_payload: dict) -> dict:
        config = {"configurable": {"thread_id": thread_id}}

        try:
            result = self.graph.invoke(Command(resume=resume_payload), config=config)
            self._cleanup_if_complete(thread_id, config)
            return {"thread_id": thread_id, "state": result}
        except Exception as e:
            logger.warning(f"Resume failed for thread {thread_id} — checkpoint preserved: {e}")
            raise AgentException(e, sys) from e

    def _cleanup_if_complete(self, thread_id: str, config: dict) -> None:
        snapshot = self.graph.get_state(config)
        if not snapshot.next:
            CheckpointerFactory.clear_thread(self.builder.checkpointer, thread_id)
        else:
            logger.info(f"Thread {thread_id} paused (human-in-the-loop) — checkpoint preserved")