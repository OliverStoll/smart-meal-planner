from types import SimpleNamespace

import numpy as np
import pytest

from recommendation.api import generate_embeddings, top_k_recommendation


class EmbeddingsStub:
    def create(self, *, input, model):
        if isinstance(input, str):
            input_list = [input]
        else:
            input_list = input
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=np.ones(768).tolist(), index=i) for i, _ in enumerate(input_list)]
        )


@pytest.fixture
def client_stub(monkeypatch):
    stub = SimpleNamespace(embeddings=EmbeddingsStub())
    monkeypatch.setattr("recommendation.api._client", stub)
    return stub


def test_generate_embeddings(client_stub, cleaned_recipes):
    titles, embeddings = generate_embeddings(cleaned_recipes)
    assert len(titles) == len(cleaned_recipes)
    assert len(embeddings) == len(cleaned_recipes)
    assert set(titles) == set(cleaned_recipes["title"].tolist())


def test_top_k_recommendation(client_stub, cleaned_recipes):
    titles, embeddings = generate_embeddings(cleaned_recipes)
    recommendations = top_k_recommendation(titles=titles, embeddings=embeddings, query="test")
    print(recommendations)
