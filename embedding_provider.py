"""Embedding adapter supporting a deployment-packaged FastEmbed ONNX model."""

from pathlib import Path


def create_embeddings(model_name: str, local_model_path: str = ""):
    if not local_model_path:
        from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

        return FastEmbedEmbeddings(model_name=model_name)

    model_path = Path(local_model_path)
    if not model_path.is_absolute():
        model_path = Path(__file__).resolve().parent / model_path
    if not model_path.is_dir():
        raise FileNotFoundError(f"Bundled embedding model not found: {model_path}")
    required = {
        "config.json",
        "model_optimized.onnx",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
    }
    missing = sorted(name for name in required if not (model_path / name).is_file())
    if missing:
        raise FileNotFoundError(
            f"Bundled embedding model is incomplete; missing: {', '.join(missing)}"
        )

    from fastembed import TextEmbedding
    from langchain_core.embeddings import Embeddings

    class PackagedFastEmbed(Embeddings):
        def __init__(self):
            self.model = TextEmbedding(
                model_name=model_name,
                specific_model_path=str(model_path),
                local_files_only=True,
            )

        def embed_documents(self, texts):
            return [vector.tolist() for vector in self.model.passage_embed(texts)]

        def embed_query(self, text):
            return next(self.model.query_embed(text)).tolist()

    return PackagedFastEmbed()
