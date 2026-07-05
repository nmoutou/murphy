import re
from datetime import datetime, timezone
from typing import Any

import spacy
from spacy.language import Language

from ragcore.core.exceptions import ParseError, ValidationError
from ragcore.core.models import (
    ParsedDocument,
    RawDocument,
    SourceName,
)
from ragcore.core.models.identifiers import ELI
from ragcore.core.services.validation import validate_eli_format

_DEFAULT_SPACY_MODEL = "fr_core_news_sm"


class LegiParser:
    source_name = SourceName.LEGI

    def __init__(self, nlp: Language | None = None) -> None:
        """Charge le pipeline spaCy ``fr_core_news_sm`` pour le nettoyage texte.

        ``parser`` et ``ner`` sont désactivés : seul le tokenizer + tagger +
        lemmatizer sont nécessaires pour filtrer stopwords/ponctuation et
        produire des lemmes.
        """
        self._nlp = nlp or spacy.load(
            _DEFAULT_SPACY_MODEL, disable=["parser", "ner"]
        )

    def parse(self, raw: RawDocument) -> ParsedDocument:
        """Parse un RawDocument LEGI en ParsedDocument.
        
        Lève ValidationError si l'ELI est absent ou invalide (N1+N2 validation).
        """
        try:
            # Étape 1 : extraire le contenu du payload
            content_data = raw.payload.get("content", {})

            # Étape 1b : extraire structure avant aplatissement (dict imbriqué réservé)
            pre_structure: dict = {}
            if isinstance(content_data, dict) and isinstance(
                content_data.get("structure"), dict
            ):
                pre_structure = content_data["structure"]
                content_data = {k: v for k, v in content_data.items() if k != "structure"}

            # Étape 2 : aplatir les champs imbriqués
            fields = self._flatten_fields(content_data)

            # Étape 3 : extraction et validation ELI (N1+N2)
            # Lève ValidationError si absent ou invalide
            identifier = ELI.from_raw_document(raw)

            # Étapes 4-5 : normalisation et nettoyage du texte
            title = self._clean_text(fields.get("title", ""))
            content = self._clean_text(fields.get("content", fields.get("texte", "")))

            # Utiliser la structure pré-extraite (avant aplatissement)
            structure = pre_structure or {}
            if not isinstance(structure, dict):
                structure = {}

            metadata = {
                k: v
                for k, v in fields.items()
                if k not in ("title", "content", "texte", "structure", "eli", "id")
            }

            # Étape 6 : renommage des métadonnées
            metadata = self._rename_metadata(metadata)

            # Étape 7 : construction du ParsedDocument (sans content_hash)
            return ParsedDocument(
                identifier=identifier,
                source=SourceName.LEGI,
                owner_id=raw.owner_id,
                title=title,
                content=content,
                structure=structure,
                metadata=metadata,
                parsed_at=datetime.now(timezone.utc),
            )
        except (ValidationError, ParseError):
            raise
        except Exception as e:
            raise ParseError(f"Erreur lors du parsing LEGI : {e}") from e

    def _flatten_fields(
        self, data: Any, full_name: list[str] | None = None
    ) -> dict[str, Any]:
        """Aplatit récursivement un dict imbriqué.

        full_name est list[str] — jamais str — pour éviter le TypeError list+str.
        """
        if full_name is None:
            full_name = []

        result: dict[str, Any] = {}

        if isinstance(data, dict):
            for key, value in data.items():
                new_path = full_name + [key]
                if isinstance(value, dict):
                    result.update(self._flatten_fields(value, new_path))
                else:
                    field_name = "_".join(new_path) if new_path else key
                    result[field_name] = value
        else:
            field_name = "_".join(full_name) if full_name else "content"
            result[field_name] = data

        return result

    def _clean_text(self, text: str) -> str:
        """Nettoyage en deux passes : suppression balises HTML puis filtrage spaCy.

        spaCy produit des lemmes à partir desquels on retire stopwords,
        ponctuation et espaces. Si le pipeline ne contient pas de lemmatizer
        (ex. ``spacy.blank("fr")`` en test), on retombe sur le texte du token.
        """
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", " ", str(text))
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return ""
        doc = self._nlp(text)
        has_lemma = self._nlp.has_pipe("lemmatizer")
        tokens = [
            (token.lemma_ if has_lemma and token.lemma_ else token.text).lower()
            for token in doc
            if not token.is_stop and not token.is_punct and not token.is_space
        ]
        return " ".join(tokens)

    def _rename_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Renomme les clés selon la convention du domaine."""
        renames = {
            "dateDebut": "date_debut",
            "dateFin": "date_fin",
            "datePublication": "date_publication",
            "etat": "statut",
            "nature": "type_document",
        }
        return {renames.get(k, k): v for k, v in metadata.items()}
