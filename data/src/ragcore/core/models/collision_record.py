"""Une collision, telle que ``MURPHY_META.collisions`` la garde : où la retrouver, jamais
les valeurs en conflit."""

from pydantic import BaseModel, ConfigDict

from .enums import SourceName

__all__ = ["CollisionRecord"]


class CollisionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: SourceName
    reason: str
    """L'une des raisons de ``collision_reasons``."""
    identifier: str
    key: str
    """La clé de métadonnée, ou la racine XML en double."""
    files: tuple[str, ...]
    """Absolus, distincts."""

    def to_detail(self) -> dict[str, object]:
        return {
            "identifier": self.identifier,
            "key": self.key,
            "files": list(self.files),
        }
