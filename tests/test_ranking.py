from app.services.ranking import RankingEngine
from app.services.image_search import ImageSearchAggregator

images = ImageSearchAggregator().run("horror photography movies text and cute little dog")
ranked = RankingEngine().rank("horror photography movies text and cute little dog", images)
for r in ranked:
    print(r["score"], r["source"], r["local_path"])