from app.services.summarization import GroqSummarizerProvider, SummarizationNode

# # Step 1: test the provider alone on plain text
# provider = GroqSummarizerProvider()
# summary = provider.summarize(
#     "Summarize the following into a single, concise, vivid book cover generation prompt "
#     "under 100 words. Preserve the theme, mood, and specific user preferences:\n\n"
#     "Book cover theme: night waterfall\n"
#     "Reference image 1: A long-exposure photo of a waterfall at night under a starry sky, "
#     "deep blues and silvery whites, serene and ethereal mood.\n"
#     "(User specifically liked: the moody blue tones)"
# )
# print(summary)

# Step 2: test the full node with mock state
node = SummarizationNode()
mock_state = {
    "prompt": "night waterfall",
    "image_descriptions": {
        "storage/raw_images/unsplash_abc123.jpg": (
            "A long-exposure photo of a waterfall at night under a starry sky, "
            "deep blues and silvery whites, serene and ethereal mood."
        ),
    },
    "feedback": [
        {"image_local_path": "storage/raw_images/unsplash_abc123.jpg", "liked_attributes": "the moody blue tones"}
    ],
}
result = node(mock_state)
print(result["summarized_prompt"])