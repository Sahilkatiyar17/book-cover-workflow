from app.services.image_understanding import GroqVLProvider, ImageUnderstandingService

def test_single_image():
    provider = GroqVLProvider()
    service = ImageUnderstandingService()

    image_path = "storage/raw_images/serpapi_7840891ebf6d.jpg"  # replace with a real path
    prompt = service.build_analysis_prompt()

    result = provider.describe(image_path=image_path, prompt=prompt)

    if result:
        print("--- Description ---")
        print(result)
    else:
        print("Provider returned None — check logs for the actual error.")

if __name__ == "__main__":
    test_single_image()