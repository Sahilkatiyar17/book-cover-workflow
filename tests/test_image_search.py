# from app.services.image_search import ImageSearchAggregator
# results = ImageSearchAggregator().run("night waterfall")
# print(len(results), results[0])

# from app.services.image_search import PinterestProvider
# results = PinterestProvider().fetch("night waterfall", 2)
# print(results)

# from app.services.image_search import ImageDownloader
# path = ImageDownloader().download(
#     "https://i.pinimg.com/originals/69/52/c3/6952c3d69a600aee4a4e4050070322d5.jpg",
#     "pinterest"
# )
# print(path)

from app.services.image_search import ImageSearchAggregator
results = ImageSearchAggregator().run("night waterfall")
print(len(results))