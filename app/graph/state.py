from typing import TypedDict, Optional


class ImageResult(TypedDict):
    """Shape of a single image as it flows through the graph."""
    url: str
    source: str
    metadata: dict
    local_path: str
    score: Optional[float]


class UserFeedback(TypedDict):
    """One image's worth of user annotation from the selection step."""
    image_local_path: str
    liked_attributes: str  # free text: "liked the font", "liked the color", etc.


class GraphState(TypedDict):
    """
    The single shared state object that flows through every node in the graph.
    LangGraph passes this dict between nodes; each node reads what it needs
    and returns a partial dict to merge back in.
    """
    # User input
    prompt: str
    dimension_preset: str  # e.g. "6x9", matches BookDimensions.PRESETS keys

    # Search + ranking stage
    search_results: list[ImageResult]
    ranked_results: list[ImageResult]

    # Selection + feedback stage (human-in-the-loop)
    selected_images: list[str]  # local_paths of images the user picked
    feedback: list[UserFeedback]
    user_uploaded_image: Optional[str]  # local_path if user provided their own reference image
    feedback_branch: str  # one of FeedbackBranch constants — set by edges.py routing logic

    # Generation stage
    generation_prompt: str  # the final merged prompt sent to the image model
    generated_cover_path: Optional[str]

    # Error/status tracking
    error: Optional[str]
    
    image_descriptions: Optional[dict]  # {local_path: caption_text}
    summarized_prompt: Optional[str]