"""Build a versioned FAISS index from administrator-approved remote sources."""

import argparse
import hashlib
import ipaddress
import json
import os
import socket
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
MAX_DOWNLOAD_BYTES = int(os.getenv("RAG_MAX_SOURCE_BYTES", str(25 * 1024 * 1024)))
FETCH_TIMEOUT = (5, 30)
MAX_REDIRECTS = 3


def _csv(name):
    return [value.strip() for value in os.getenv(name, "").split(",") if value.strip()]


def load_sources():
    manifest_path = os.getenv("RAG_SOURCE_MANIFEST", "").strip()
    if manifest_path:
        data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        sources = data.get("sources", data) if isinstance(data, dict) else data
    else:
        sources = ([{"type": "pdf", "url": url} for url in _csv("RAG_PDF_URLS")] +
                   [{"type": "website", "url": url} for url in _csv("RAG_WEBSITE_URLS")])
    if not isinstance(sources, list):
        raise ValueError("Source manifest must contain a list or a 'sources' list")
    enabled = [source for source in sources if source.get("enabled", True)]
    if not enabled:
        raise ValueError("No enabled RAG sources were configured")
    return enabled


def _validate_public_url(url, allowed_domains):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"Unsupported source URL: {url}")
    if parsed.username or parsed.password:
        raise ValueError(f"Credentials are not allowed in source URLs: {url}")
    if parsed.scheme == "http" and os.getenv("RAG_ALLOW_HTTP", "false").lower() != "true":
        raise ValueError("Plain HTTP sources require RAG_ALLOW_HTTP=true")
    hostname = parsed.hostname.lower()
    if allowed_domains and hostname not in allowed_domains:
        raise ValueError(f"Source host is not in RAG_ALLOWED_DOMAINS: {hostname}")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    for address in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(address[4][0]).is_global:
            raise ValueError(f"Source resolves to a non-public address: {hostname}")


def fetch(url, allowed_domains):
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        _validate_public_url(current, allowed_domains)
        with requests.get(current, stream=True, timeout=FETCH_TIMEOUT,
                          allow_redirects=False,
                          headers={"User-Agent": "CERC-Knowledge-Ingest/1.0"}) as response:
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                if not location:
                    raise ValueError(f"Redirect without Location from {current}")
                current = urljoin(current, location)
                continue
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_DOWNLOAD_BYTES:
                raise ValueError(f"Source exceeds {MAX_DOWNLOAD_BYTES} bytes: {current}")
            chunks, size = [], 0
            for chunk in response.iter_content(64 * 1024):
                size += len(chunk)
                if size > MAX_DOWNLOAD_BYTES:
                    raise ValueError(f"Source exceeds {MAX_DOWNLOAD_BYTES} bytes: {current}")
                chunks.append(chunk)
            return b"".join(chunks), current, content_type
    raise ValueError(f"Too many redirects while fetching {url}")


def _identity(source, final_url):
    source_id = source.get("source_id") or hashlib.sha256(final_url.encode()).hexdigest()[:16]
    title = source.get("title") or Path(urlparse(final_url).path).name or final_url
    return str(source_id), str(title)


def load_pdf(source, allowed_domains):
    body, final_url, content_type = fetch(source["url"], allowed_domains)
    if not body.startswith(b"%PDF-"):
        raise ValueError(f"Remote source is not a PDF: {final_url} ({content_type})")
    source_id, title = _identity(source, final_url)
    checksum = hashlib.sha256(body).hexdigest()
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            handle.write(body)
            temp_path = handle.name
        documents = PyPDFLoader(temp_path).load()
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)
    for document in documents:
        document.metadata.update({"source_id": source_id, "title": title,
                                  "url": final_url, "source_type": "pdf",
                                  "checksum": checksum})
    return documents, {"source_id": source_id, "type": "pdf", "title": title,
                       "url": final_url, "checksum": checksum,
                       "documents": len(documents)}


def load_website(source, allowed_domains):
    body, final_url, content_type = fetch(source["url"], allowed_domains)
    if "html" not in content_type and not body.lstrip().lower().startswith(b"<!doctype html"):
        raise ValueError(f"Website source did not return HTML: {final_url} ({content_type})")
    soup = BeautifulSoup(body, "html.parser")
    for element in soup(["script", "style", "nav", "footer", "noscript"]):
        element.decompose()
    source_id, fallback_title = _identity(source, final_url)
    page_title = soup.title.get_text(" ", strip=True) if soup.title else fallback_title
    text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    if not text:
        raise ValueError(f"No readable content found at {final_url}")
    checksum = hashlib.sha256(text.encode()).hexdigest()
    metadata = {"source_id": source_id, "title": source.get("title") or page_title,
                "url": final_url, "source_type": "website", "checksum": checksum}
    return [Document(page_content=text, metadata=metadata)], {
        "source_id": source_id, "type": "website", "title": metadata["title"],
        "url": final_url, "checksum": checksum, "documents": 1}


def build_index(output, embedding_model):
    if output.exists():
        raise FileExistsError(f"Output exists: {output}. Use a new versioned directory.")
    sources = load_sources()
    configured_domains = {value.strip().lower() for value in
                          os.getenv("RAG_ALLOWED_DOMAINS", "").split(",") if value.strip()}
    # When no separate allow-list is supplied, the configured source hosts are
    # the allow-list. Redirects to any other host are still rejected.
    allowed_domains = configured_domains or {
        urlparse(source["url"]).hostname.lower() for source in sources
        if urlparse(source.get("url", "")).hostname
    }
    documents, source_records, failures = [], [], []
    for source in sources:
        try:
            if str(source.get("type", "")).lower() == "pdf":
                loaded, record = load_pdf(source, allowed_domains)
            elif str(source.get("type", "")).lower() == "website":
                loaded, record = load_website(source, allowed_domains)
            else:
                raise ValueError(f"Unsupported source type: {source.get('type')!r}")
            documents.extend(loaded)
            source_records.append(record)
            print(f"Loaded {record['type']} source: {record['title']}")
        except Exception as exc:
            failures.append({"url": source.get("url"), "error": str(exc)})
    if failures:
        raise RuntimeError("Index build aborted due to source failures:\n" +
                           json.dumps(failures, indent=2))
    if not documents:
        raise RuntimeError("No documents were extracted")
    splitter = RecursiveCharacterTextSplitter(chunk_size=900, chunk_overlap=150)
    chunks = splitter.split_documents(documents)
    vector_store = FAISS.from_documents(
        chunks, FastEmbedEmbeddings(model_name=embedding_model))
    output.mkdir(parents=True)
    vector_store.save_local(str(output))
    now = datetime.now(timezone.utc)
    manifest = {"index_version": now.strftime("%Y%m%dT%H%M%SZ"),
                "created_at": now.isoformat(), "embedding_model": embedding_model,
                "chunk_size": 900, "chunk_overlap": 150,
                "source_count": len(source_records), "chunk_count": len(chunks),
                "sources": source_records}
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Built {output} with {len(chunks)} chunks from {len(source_records)} sources")


def main():
    parser = argparse.ArgumentParser(description="Build the packaged RAG index")
    parser.add_argument("--output", default=os.getenv("RAG_INDEX_PATH", "ngo_index"))
    parser.add_argument("--embedding-model",
                        default=os.getenv("RAG_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL))
    args = parser.parse_args()
    build_index(Path(args.output), args.embedding_model)


if __name__ == "__main__":
    main()
