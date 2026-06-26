"""Pipeline embedding archivé.

Le système d'embedding legacy (package `data` v0.1) a été remplacé par
`ragcore` v0.2.0 avec orchestration Kedro.

Voir `ragcore/adapters/embedding/` pour les adaptateurs d'embedding actuels.
"""
                "text_chunks": "textChunks",
                "parameters": "params:embedding.embedding",
            },
            outputs="embeddedChunks",
            name="embedChunks",
        ),
    ])
