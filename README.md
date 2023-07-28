# Meal planner

Select recipes from a variety of sites, and place orders for ingredients in aggregate.

## Roadmap

- [ ] Collect recipes from a whole buncha sites via deploying a crawler that writes recipes to Kafka, and dedupes links in Redis. Use `pip install recipe-scrapers` for parsing the html.
- [ ] Dump each unique recipe into a more structured SQL schema in Postgres, for persistence.
- [ ] Once the db is ready, clean up the structure a bit more into retrievable data (may need some sorta text-based AI model here) for an ingredient aggregation sub-app.
- [ ] Build a Django app (or whatever) to serve a frontend that lets you select recipes, and then render an aggregated list of ingredients.
- [ ] Integrate Instacart API for checkout of the list of ingredients.
