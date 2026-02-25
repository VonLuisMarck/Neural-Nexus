import json
import os
from typing import List, Dict
from rbac import can_read_classification

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_INDEX_PATH = os.path.join(DATA_DIR, "docs_index.json")
DOCS_BASE_DIR = DATA_DIR

def load_index() -> List[Dict]:
    with open(DOCS_INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)

DOCS_INDEX = load_index()

def list_docs_for_user(user) -> List[Dict]:
    docs = []
    for doc in DOCS_INDEX:
        if can_read_classification(user, doc["classification"]):
            docs.append({
                "id": doc["id"],
                "classification": doc["classification"],
                "tags": doc.get("tags", []),
            })
    return docs

def get_doc_by_id(doc_id: str) -> Dict | None:
    for doc in DOCS_INDEX:
        if doc["id"] == doc_id:
            return doc
    return None

def load_doc_content(doc_meta: Dict, max_chars: int = 4000) -> str:
    path = os.path.join(DOCS_BASE_DIR, doc_meta["path"])
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    return content[:max_chars]

def build_context_for_user(user) -> str:
    docs_meta = list_docs_for_user(user)
    if not docs_meta:
        return "No additional documents are accessible for this user."
    parts = ["Accessible documents for this user:"]
    for meta in docs_meta:
        full_meta = get_doc_by_id(meta["id"])
        snippet = load_doc_content(full_meta, max_chars=1500)
        parts.append(
            f"[{meta['id']}] (classification: {meta['classification']})\n{snippet}\n"
        )
    return "\n\n".join(parts)
