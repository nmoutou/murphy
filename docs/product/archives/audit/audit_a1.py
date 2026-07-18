"""Audit A1 — volumétrie fine, couverture vectorielle, ECLI, remplissage réel."""

import json
from collections import Counter

from qdrant_client import QdrantClient
from pymongo import MongoClient

COLL = "9424808d1c636d533648bbf4e77f2496"
qc = QdrantClient(url="http://localhost:6333", check_compatibility=False)
mc = MongoClient("mongodb://root:changeme@localhost:27017/?authSource=admin", serverSelectionTimeoutMS=5000)
db = mc["LEGIFRANCE"]
docs = db["documents"]

# Qdrant : documents distincts + présence ecli + type_document
points, offset = [], None
while True:
    batch, offset = qc.scroll(COLL, limit=1000, offset=offset, with_payload=True, with_vectors=False)
    points.extend(batch)
    if offset is None:
        break

qdrant_docs = set(p.payload["identifier"] for p in points)
ecli_stats = Counter()
type_doc = Counter()
for p in points:
    pl = p.payload
    if pl["identifier"].startswith("decision:"):
        ecli_stats["decision_chunk_with_ecli" if pl.get("ecli") else "decision_chunk_no_ecli"] += 1
    type_doc[pl.get("type_document", "«absent»")] += 1

print("Qdrant chunks:", len(points), "| docs distincts:", len(qdrant_docs))
print("ECLI sur chunks decision:", dict(ecli_stats))
print("type_document:", dict(type_doc.most_common(10)))

# Mongo : docs sans vecteurs, par préfixe
mongo_ids = {}
for d in docs.find({}, {"identifier": 1, "source": 1, "content": 1, "title": 1, "metadata": 1}):
    mongo_ids[d["identifier"]] = d

missing = [i for i in mongo_ids if i not in qdrant_docs]
missing_by_prefix = Counter(i.split(":", 1)[1][:8] for i in missing)
empty_content = sum(1 for i in missing if not (mongo_ids[i].get("content") or "").strip())
print("\nMongo docs:", len(mongo_ids), "| absents de Qdrant:", len(missing), "| par préfixe:", dict(missing_by_prefix))
print("dont contenu vide/blanc:", empty_content)
nonempty_missing = [i for i in missing if (mongo_ids[i].get("content") or "").strip()][:10]
print("exemples absents avec contenu NON vide:", nonempty_missing)

# extra qdrant docs not in mongo (should be 0)
extra = [i for i in qdrant_docs if i not in mongo_ids]
print("docs Qdrant absents de Mongo (attendu 0):", len(extra), extra[:5])

# Remplissage réel : taux de champs metadata non vides par source (échantillon complet, petit corpus)
fill = {}
for d in docs.find({}, {"source": 1, "metadata": 1, "title": 1}):
    src = d["source"]
    meta = d.get("metadata") or {}
    f = fill.setdefault(src, Counter())
    f["_docs"] += 1
    if (d.get("title") or "").strip():
        f["title"] += 1
    for k, v in meta.items():
        if v not in (None, "", [], {}):
            f[k] += 1
print("\nRemplissage (champ: docs non vides / total) par source:")
for src, f in sorted(fill.items()):
    n = f.pop("_docs")
    top = {k: v for k, v in sorted(f.items())}
    print(f"  {src} ({n} docs): {json.dumps(top, ensure_ascii=False)}")

# ECLI dans les metadata Mongo des décisions
with_ecli = docs.count_documents({"identifier": {"$regex": "^decision:"}, "metadata.ecli": {"$nin": [None, ""]}})
total_dec = docs.count_documents({"identifier": {"$regex": "^decision:"}})
print(f"\nMongo décisions avec metadata.ecli non vide: {with_ecli}/{total_dec}")
