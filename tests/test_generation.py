# from app.graph.builder import GraphBuilder

# graph = GraphBuilder().build()
# config = {"configurable": {"thread_id": "test-run-1"}}
# result = graph.invoke(
#     {"prompt": "red moon and cat", "dimension_preset": "6x9"},
#     config=config,
# )

# print(len(result["ranked_results"]))
# print(result["ranked_results"][0])

# from app.graph.builder import GraphBuilder, GraphRunner

# runner = GraphRunner(GraphBuilder())
# result = runner.run({"prompt": "night waterfall", "dimension_preset": "6x9"})

# print(len(result["ranked_results"]))
# print(result["ranked_results"][0]['score'])
# print(result["ranked_results"][1]['score'])


from app.graph.builder import GraphBuilder, GraphRunner

runner = GraphRunner(GraphBuilder())

# Step 1: start the run — it should pause at SelectionNode
result = runner.run({"prompt": "night waterfall", "dimension_preset": "6x9"})
print(result["state"])  # should show an '__interrupt__' key with the ranked_results payload
thread_id = result["thread_id"]

# Check the DB here — this thread's rows should still exist, NOT deleted, since it's paused

# Step 2: simulate the user picking images and giving feedback
resumed = runner.resume(thread_id, {
    "selected_images": ["storage/raw_images/unsplash_abc123.jpg"],
    "feedback": [{"image_local_path": "storage/raw_images/unsplash_abc123.jpg", "liked_attributes": "liked the moody lighting"}],
    "user_uploaded_image": None,
})
print(resumed["state"])

# Check the DB again — this thread's rows should now be gone, since it reached END