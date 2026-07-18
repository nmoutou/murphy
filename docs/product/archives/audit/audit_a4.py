"""Audit A4/A1 — vérification empirique de l'identité canonique inter-BDD.

Échantillonnage raisonné : pour chaque préfixe d'identifiant présent dans Qdrant
(eli:LEGI…, decision:JURITEXT/CETATEXT/CONSTEXT…), on prend des chunk_id/identifier
et on vérifie leur présence sous le MÊME identifiant dans MongoDB et Neo4j.
Sortie JSON reproductible.
"""

import asyncio
import json
import os
import random
from collections import Counter

from dotenv import dotenv_values
from qdrant_client import QdrantClient
from pymongo import MongoClient
from neo4j import GraphDatabase

ENV = dotenv_values("/home/eyebrow/Documents/Perso/murphy/.env.dev")
QDRANT_URL = "http://localhost:6333"
COLL = "9424808d1c636d533648bbf4e77f2496"
MONGO_URI = "mongodb://root:changeme@localhost:27017/?authSource=admin"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", ENV.get("NEO4J_PASSWORD") or ENV.get("NEO4J_AUTH", "").split("/")[-1])

random.seed(42)

qc = QdrantClient(url=QDRANT_URL)
mc = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

# 1) Scroll a large sample of Qdrant points
points, offset = [], None
while len(points) < 20000:
    batch, offset = qc.scroll(COLL, limit=1000, offset=offset, with_payload=True, with_vectors=False)
    points.extend(batch)
    if offset is None:
        break

by_prefix = Counter()
doc_ids = set()
for p in points:
    ident = p.payload.get("identifier", "?")
    by_prefix[ident.split(":")[0] + ":" + ident.split(":", 1)[1][:8] if ":" in ident else "?"] += 0
    prefix = ident.split(":", 1)[0]
    sub = ident.split(":", 1)[1][:8] if ":" in ident else "?"
    by_prefix[f"{prefix}:{sub}"] += 1
    doc_ids.add(ident)

print("QDRANT total points scrolled:", len(points))
print("QDRANT distinct documents:", len(doc_ids))
print("QDRANT identifier prefixes:", dict(by_prefix.most_common(10)))

# payload keys sample
sample_payload = points[0].payload
print("QDRANT payload keys (sample):", sorted(sample_payload.keys()))
print("QDRANT sample chunk_id:", sample_payload.get("chunk_id"), "| identifier:", sample_payload.get("identifier"))
print("QDRANT payload has camelCase chunkId?:", "chunkId" in sample_payload)

# 2) Mongo state
db = mc["LEGIFRANCE"]
print("\nMONGO collections LEGIFRANCE:", db.list_collection_names())
meta = mc["MURPHY_META"]
print("MONGO collections MURPHY_META:", meta.list_collection_names())
pointer = meta["meta_published_collection"].find_one({"key": "current"})
if pointer:
    pointer.pop("_id", None)
print("MONGO published pointer:", json.dumps(pointer, default=str))

doc_coll = db["documents"]
print("MONGO documents count:", doc_coll.count_documents({}))
agg = doc_coll.aggregate([{"$group": {"_id": "$source", "n": {"$sum": 1}}}])
print("MONGO documents by source:", {d["_id"]: d["n"] for d in agg})
agg2 = doc_coll.aggregate([
    {"$project": {"p": {"$substrCP": ["$identifier", 0, 12]}}},
    {"$group": {"_id": "$p", "n": {"$sum": 1}}}, {"$sort": {"n": -1}},
])
print("MONGO documents by identifier prefix:", {d["_id"]: d["n"] for d in agg2})
# legacy chunks collection?
if "chunks" in db.list_collection_names():
    ch = db["chunks"]
    print("MONGO legacy 'chunks' count:", ch.count_documents({}))
    one = ch.find_one({}, {"chunkId": 1, "chunk_id": 1, "identifier": 1})
    print("MONGO legacy chunks sample keys:", one)

# 3) Sample per prefix family for cross-DB check
families = {}
for ident in doc_ids:
    fam = ident.split(":", 1)[1][:8] if ":" in ident else "?"
    families.setdefault(fam, []).append(ident)
sample = {fam: sorted(random.sample(ids, min(5, len(ids)))) for fam, ids in families.items()}

drv = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
results = {}
with drv.session() as s:
    total_nodes = s.run("MATCH (n) RETURN count(n) AS c").single()["c"]
    total_rels = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
    labels = s.run("MATCH (n) RETURN labels(n) AS l, count(*) AS c ORDER BY c DESC LIMIT 10").data()
    print("\nNEO4J nodes:", total_nodes, "rels:", total_rels)
    print("NEO4J labels:", labels)
    for fam, ids in sample.items():
        fam_res = []
        for ident in ids:
            in_mongo = doc_coll.count_documents({"identifier": ident}) > 0
            in_neo = s.run("MATCH (n {identifier: $i}) RETURN count(n) AS c", i=ident).single()["c"] > 0
            fam_res.append({"identifier": ident, "mongo": in_mongo, "neo4j": in_neo, "qdrant": True})
        results[fam] = fam_res

print("\nCROSS-DB CHECK (sample, seed=42):")
print(json.dumps(results, indent=1, ensure_ascii=False))

ok = sum(1 for fam in results.values() for r in fam if r["mongo"] and r["neo4j"])
tot = sum(len(f) for f in results.values())
print(f"\nRESULT: {ok}/{tot} sampled identifiers present under the SAME id in all 3 DBs")
drv.close()
