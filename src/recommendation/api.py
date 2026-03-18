import os
import numpy as np
from logs.logs import create_logger
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from dotenv import load_dotenv

from database.engine import recipes_from_sql

load_dotenv()

try:
    _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception:
    _client = None

log = create_logger("Recommendation Engine")


def generate_embeddings(recipes: pd.DataFrame | None = None):
    if not _client:
        raise RuntimeError("OpenAI client not initialized. Check your environment variables.")
    if recipes is None:
        recipes = recipes_from_sql()
    recipe_titles = recipes["title"]
    recipes["ingredient_names"] = recipes["ingredients"].apply(
        lambda row: ", ".join(ingredient["name"] for ingredient in row)
    )
    recipes["representation"] = "title: " + recipes["title"] + "; ingredients: " + recipes["ingredient_names"]
    embedding_input = recipes["representation"].tolist()
    response = _client.embeddings.create(input=embedding_input, model="text-embedding-3-small")
    log.info("Generated title embeddings")
    log.debug(response)
    recipes["embedding"] = [data.embedding for data in response.data]
    embeddings = np.array(recipes["embedding"].tolist())
    return recipe_titles, embeddings


def top_k_recommendation(titles, embeddings, query, k=20):
    if not _client:
        raise RuntimeError("OpenAI client not initialized. Check your environment variables.")
    q = _client.embeddings.create(model="text-embedding-3-small", input=query).data[0].embedding
    scores = cosine_similarity([q], embeddings)[0]
    idx = np.argsort(scores)[-k:][::-1]
    return [titles[i] for i in idx]


if __name__ == "__main__":
    titles, embeddings = generate_embeddings()
    recommendations = top_k_recommendation(titles=titles, embeddings=embeddings, query="quick vegan dinner")
    print(recommendations)
