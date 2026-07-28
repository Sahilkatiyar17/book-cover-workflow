from langgraph.types import interrupt

from app.utils.logger import logging

logger = logging.getLogger(__name__)


class SelectionNode:
    """
    Pauses the graph and waits for the user to select images and provide feedback.
    This is the actual human-in-the-loop checkpoint — everything computed so far
    (search_results, ranked_results) is already saved by the checkpointer when
    this node halts execution.
    """

    def __call__(self, state: dict) -> dict:
        logger.info("Graph paused at SelectionNode — waiting for human input")

        user_response = interrupt(
            {
                "message": "Select images and provide feedback before generation.",
                "ranked_results": state["ranked_results"],
            }
        )

        logger.info("Resumed from SelectionNode with human input")

        return {
            "selected_images": user_response.get("selected_images", []),
            "feedback": user_response.get("feedback", []),
            "user_uploaded_image": user_response.get("user_uploaded_image"),
        }