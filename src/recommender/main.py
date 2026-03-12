import os
import ast
import numpy as np
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from dotenv import load_dotenv

from data_ingestion import CLEANED_RECIPES_TABLE

# from database.engine import engine

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

df = pd.read_csv("../../data/temp_data/cleaned.csv")
titles = df["title"].tolist()
print(titles)


def generate_embeddings():
    # recipies = pd.read_sql_table(CLEANED_RECIPES_TABLE, con=engine)
    recipes = pd.read_csv("../../data/temp_data/cleaned.csv")
    recipes = recipes.head(1000)
    recipes["ingredient_names"] = (
        df["ingredients"].apply(ast.literal_eval).apply(lambda row: ", ".join(ingredient["name"] for ingredient in row))
    )
    recipes["representation"] = "title: " + recipes["title"] + "; ingredients: " + recipes["ingredient_names"]
    embedding_input = recipes["representation"].tolist()
    response = client.embeddings.create(input=embedding_input, model="text-embedding-3-small")
    print("Generated title embeddings")
    print(response)
    recipes["embedding"] = [data.embedding for data in response.data]
    return np.array(recipes["embedding"].tolist())


def top20(embeddings, query):
    q = client.embeddings.create(model="text-embedding-3-small", input=query).data[0].embedding
    scores = cosine_similarity([q], embeddings)[0]
    idx = np.argsort(scores)[-20:][::-1]
    return [titles[i] for i in idx]


if __name__ == "__main__":
    embeddings = generate_embeddings()
    print(top20(embeddings=embeddings, query="quick vegan dinner"))
