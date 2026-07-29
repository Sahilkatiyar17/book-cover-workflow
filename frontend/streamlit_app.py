import streamlit as st

from app.graph.builder import GraphBuilder, GraphRunner
from app.utils.logger import logging

logger = logging.getLogger(__name__)

STEP_LABELS = {
    "image_search": "Searching for images...",
    "ranking": "Ranking images by relevance...",
    "understanding": "Analyzing your selected images...",
    "summarization": "Composing the final prompt...",
    "generation": "Generating your book cover...",
}


class BookCoverApp:
    def __init__(self):
        if "runner" not in st.session_state:
            st.session_state.runner = GraphRunner(GraphBuilder())
        if "thread_id" not in st.session_state:
            st.session_state.thread_id = None
        if "ranked_results" not in st.session_state:
            st.session_state.ranked_results = None
        if "final_result" not in st.session_state:
            st.session_state.final_result = None
        # persists reference images + choices across the generation step, for side-by-side comparison
        if "reference_snapshot" not in st.session_state:
            st.session_state.reference_snapshot = None

    def run(self):
        st.title("Book Cover Workflow")

        if st.session_state.thread_id is None:
            self._render_prompt_stage()
        elif st.session_state.final_result is None:
            self._render_selection_stage()
        else:
            self._render_side_by_side_result()

    def _render_prompt_stage(self):
        prompt = st.text_input("Describe the book cover you want")
        dimension = st.selectbox("Dimension preset", ["5x8", "6x9", "7x10"], index=1)

        if st.button("Search images") and prompt:
            result = st.session_state.runner.run({"prompt": prompt, "dimension_preset": dimension})
            st.session_state.thread_id = result["thread_id"]
            st.session_state.ranked_results = result["state"]["__interrupt__"][0].value["ranked_results"]
            st.rerun()

    def _render_selection_stage(self):
        st.subheader("Select images you like (max 5)")

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

        remaining_slots = 5 - len(selected_paths)
        uploaded_file = None
        if remaining_slots > 0:
            uploaded_file = st.file_uploader(
                f"Or upload your own reference image ({remaining_slots} slot(s) left, optional)",
                type=["jpg", "jpeg", "png"],
            )
        else:
            st.info("You've selected 5 images — deselect one if you want to upload your own instead.")

        user_uploaded_path = None
        if uploaded_file:
            user_uploaded_path = f"storage/raw_images/upload_{uploaded_file.name}"
            with open(user_uploaded_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

        if st.button("Generate cover"):
            total_references = len(selected_paths) + (1 if user_uploaded_path else 0)
            if total_references > 5:
                st.error("You can use a maximum of 5 references total (selected images + upload). Please deselect one.")
                return

            # snapshot the chosen references now, before generation overwrites/loses this context
            st.session_state.reference_snapshot = {
                "selected_images": selected_paths,
                "feedback": feedback_entries,
                "user_uploaded_image": user_uploaded_path,
            }

            self._run_with_progress(st.session_state.reference_snapshot)

    def _run_with_progress(self, resume_payload: dict):
        status = st.status("Starting generation...", expanded=True)
        final_state = {}

        for node_name, update in st.session_state.runner.resume_stream(st.session_state.thread_id, resume_payload):
            label = STEP_LABELS.get(node_name, f"Running: {node_name}")
            status.update(label=label)
            status.write(f"✓ {label}")
            final_state.update(update)

        status.update(label="Done!", state="complete", expanded=False)
        st.session_state.final_result = {"thread_id": st.session_state.thread_id, "state": final_state}
        st.rerun()

    def _render_side_by_side_result(self):
        left, right = st.columns(2)
        ref = st.session_state.reference_snapshot
        state = st.session_state.final_result["state"]

        with left:
            st.subheader("References used")
            for path in ref["selected_images"]:
                st.image(path, width=200)
                note = next((f["liked_attributes"] for f in ref["feedback"] if f["image_local_path"] == path), None)
                if note:
                    st.caption(f"Liked: {note}")
            if ref["user_uploaded_image"]:
                st.image(ref["user_uploaded_image"], width=200)
                st.caption("Your uploaded reference")

        with right:
            st.subheader("Generated cover")
            cover_path = state.get("generated_cover_path")
            if cover_path:
                st.image(cover_path, width=350)
            else:
                st.warning("Generation did not produce an image. Check logs for details.")

            with st.expander("Generation prompt used"):
                st.write(state.get("generation_prompt", "N/A"))
            with st.expander("Image descriptions (captions)"):
                st.json(state.get("image_descriptions", {}))

        st.divider()
        if st.button("Start over"):
            st.session_state.thread_id = None
            st.session_state.ranked_results = None
            st.session_state.final_result = None
            st.session_state.reference_snapshot = None
            st.rerun()


if __name__ == "__main__":
    BookCoverApp().run()