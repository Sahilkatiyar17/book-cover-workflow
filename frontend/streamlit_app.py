import streamlit as st

from app.graph.builder import GraphBuilder, GraphRunner
from app.utils.logger import logging

logger = logging.getLogger(__name__)


class BookCoverApp:
    """
    Minimal test harness for the human-in-the-loop workflow.
    Not the polished frontend (that's Phase 6) — just enough UI to prove
    the four branches actually trigger correctly from real user interaction.
    """

    def __init__(self):
        if "runner" not in st.session_state:
            st.session_state.runner = GraphRunner(GraphBuilder())
        if "thread_id" not in st.session_state:
            st.session_state.thread_id = None
        if "ranked_results" not in st.session_state:
            st.session_state.ranked_results = None
        if "final_result" not in st.session_state:
            st.session_state.final_result = None

    def run(self):
        st.title("Book Cover Workflow — Test Harness")

        if st.session_state.thread_id is None:
            self._render_prompt_stage()
        elif st.session_state.final_result is None:
            self._render_selection_stage()
        else:
            self._render_result_stage()

    def _render_prompt_stage(self):
        prompt = st.text_input("Describe the book cover you want")
        dimension = st.selectbox("Dimension preset", ["5x8", "6x9", "7x10"], index=1)

        if st.button("Search images") and prompt:
            result = st.session_state.runner.run({"prompt": prompt, "dimension_preset": dimension})
            st.session_state.thread_id = result["thread_id"]
            st.session_state.ranked_results = result["state"]["__interrupt__"][0].value["ranked_results"]
            st.rerun()

    def _render_selection_stage(self):
        st.subheader("Select images you like")

        selected_paths = []
        feedback_entries = []

        for i, img in enumerate(st.session_state.ranked_results):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(img["local_path"], width=150)
                checked = st.checkbox("Select", key=f"select_{i}")
            with col2:
                text = st.text_input("What did you like about this one? (optional)", key=f"feedback_{i}")

            if checked:
                selected_paths.append(img["local_path"])
                if text.strip():
                    feedback_entries.append({"image_local_path": img["local_path"], "liked_attributes": text.strip()})

        uploaded_file = st.file_uploader("Or upload your own reference image (optional)", type=["jpg", "jpeg", "png"])
        user_uploaded_path = None
        if uploaded_file:
            user_uploaded_path = f"storage/raw_images/upload_{uploaded_file.name}"
            with open(user_uploaded_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

        if st.button("Proceed"):
            resumed = st.session_state.runner.resume(
                st.session_state.thread_id,
                {
                    "selected_images": selected_paths,
                    "feedback": feedback_entries,
                    "user_uploaded_image": user_uploaded_path,
                },
            )
            st.session_state.final_result = resumed
            st.rerun()

    def _render_result_stage(self):
        st.subheader("Workflow complete")
        branch = st.session_state.final_result["state"].get("feedback_branch", "unknown")
        st.write(f"Routed branch: **{branch}**")
        st.json(st.session_state.final_result["state"])

        if st.button("Start over"):
            st.session_state.thread_id = None
            st.session_state.ranked_results = None
            st.session_state.final_result = None
            st.rerun()


if __name__ == "__main__":
    BookCoverApp().run()