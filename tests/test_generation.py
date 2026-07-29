# from app.services.generation import GeminiProvider

# provider = GeminiProvider()
# result = provider.generate(
#     prompt="Image 1: use as reference for mood and lighting. Create a moody fantasy book cover.",
#     reference_image_paths=["storage/raw_images/serpapi_7840891ebf6d.jpg"],  # use a real path from your storage folder
#     output_path="storage/generated_covers/test_gemini.jpg",
# )
# print(result)


# from app.services.generation import QwenEditProvider

# provider = QwenEditProvider()
# result = provider.generate(
#     prompt="Transform into a moody fantasy book cover style.",
#     reference_image_paths=["storage/raw_images/serpapi_7840891ebf6d.jpg"],
#     output_path="storage/generated_covers/test_qwen.jpg",
# )
# print(result)

# from google import genai
# import os

# client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# for model in client.models.list():
#     print(model.name)


from app.services.generation import HuggingFaceProvider

result = HuggingFaceProvider().generate(
    prompt="Create a moody fantasy book cover provided image.",
    reference_image_paths=["storage/raw_images/serpapi_7840891ebf6d.jpg","storage/raw_images/upload_be3dd733-b6ec-4ccf-b83c-151f6cfe1e69.png"],
    output_path="storage/generated_covers/test_hf.jpg",
)
print(result)

