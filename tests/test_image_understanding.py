from app.services.image_understanding import GroqVLProvider, ImageUnderstandingNode

# # Step 1: test the provider alone on one image
# provider = GroqVLProvider()
# description = provider.describe(
#     "storage/raw_images/serpapi_66d2f56c8cd2.jpg",  # use a real path from your storage folder
#     "Describe this image in detail, including subject, mood, color palette, and composition.",
# )
# print(description)

# Step 2: test the full node with mock state, 3+ images to confirm the cap works
node = ImageUnderstandingNode()
mock_state = {
    "selected_images": [
        "storage/generated_covers/test_hf.jpg",
        "storage/raw_images/serpapi_7840891ebf6d.jpg",
        
        "storage/raw_images/pexels_7683a02bca30.jpg",
        "storage/raw_images/serpapi_66d2f56c8cd2.jpg", # 4th image — should be dropped by the cap
    ],
    "user_uploaded_image": None,
}
result = node(mock_state)
print(len(result["image_descriptions"]))  # should print 3, not 4
print(result["image_descriptions"])