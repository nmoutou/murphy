"""Module `connector` archivé.

Le connecteur HTTP PISTE (`LegiConnector`) n'a jamais été instancié en production.
Le système utilise `LegiFileConnector` pour lire les fichiers XML locaux.

Dépendances obsolètes : httpx, tenacity.
"""

    async def fetch_one(
        self,
        document_id: str,
        owner_id: OwnerId,
    ) -> RawDocument | None:
        token = await self._get_oauth_token()
        resp = await self._request(
            "GET",
            f"{self._settings.api_base_url}/consult/eli/{document_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise RagCoreError(
                f"LEGI fetch_one returned {resp.status_code}: {resp.text}"
            )
        data = resp.json()

        return RawDocument(
            source=SourceName.LEGI,
            source_document_id=document_id,
            payload={"content": data},
            fetched_at=datetime.now(timezone.utc),
            owner_id=owner_id,
        )
