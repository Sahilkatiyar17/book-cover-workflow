from app.utils.constants import FeedbackBranch
from app.utils.logger import logging

logger = logging.getLogger(__name__)


class BranchRouter:
    def __call__(self, state: dict) -> str:
        has_image = bool(state.get("user_uploaded_image"))
        has_text = bool(state.get("feedback"))

        if has_image and has_text:
            branch = FeedbackBranch.TEXT_AND_IMAGE
        elif has_image:
            branch = FeedbackBranch.USER_IMAGE_UPLOAD
        elif has_text:
            branch = FeedbackBranch.TEXT_FEEDBACK
        else:
            branch = FeedbackBranch.NO_FEEDBACK

        logger.info(f"Routed to branch: {branch}")
        return branch