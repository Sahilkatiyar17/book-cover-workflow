from app.graph.builder import GraphBuilder, GraphRunner

runner = GraphRunner(GraphBuilder())

# Step 1: start — pauses at selection
result = runner.run({"prompt": "night waterfall", "dimension_preset": "6x9"})
thread_id = result["thread_id"]
print("Paused. Ranked results:", len(result["state"]["__interrupt__"][0].value["ranked_results"]))

# Step 2: resume with selections + feedback — should now flow through
# understanding -> summarization -> generation automatically
resumed = runner.resume(thread_id, {
    "selected_images": [
        "storage/raw_images/unsplash_abc123.jpg",
        "storage/raw_images/pexels_def456.jpg",
    ],
    "feedback": [
        {"image_local_path": "storage/raw_images/unsplash_abc123.jpg", "liked_attributes": "the moody blue tones"}
    ],
    "user_uploaded_image": None,
})

print("Image descriptions:", resumed["state"].get("image_descriptions"))
print("Summarized prompt:", resumed["state"].get("summarized_prompt"))
print("Final generation prompt:", resumed["state"].get("generation_prompt"))
print("Generated covers:", resumed["state"].get("generated_covers"))