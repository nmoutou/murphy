"""Custom dataset for reading XML files directly from source directory."""

from kedro.io import AbstractDataset
from pathlib import Path
from typing import Dict, Any
import os
import re


class XMLSourceDataset(AbstractDataset):
    """Dataset qui liste et lit les fichiers XML directement depuis le chemin source.
    
    Ce dataset parcourt récursivement un dossier source et retourne un dictionnaire
    {uid: filepath} pour tous les fichiers XML trouvés.
    
    Le uid est déterminé à partir du nom de fichier :
    - Si le nom est un ELI valide (8 lettres majuscules + 12 chiffres), l'ELI est utilisé
    - Sinon, le chemin relatif depuis la source est utilisé
    
    Attributes:
        _source_path: Chemin vers le dossier source contenant les fichiers XML
    """
    
    def __init__(self, source_path: str):
        """Initialise le dataset.
        
        Args:
            source_path: Chemin vers le dossier racine contenant les fichiers XML
        """
        self._source_path = Path(source_path)
        if not self._source_path.exists():
            raise ValueError(f"Source path does not exist: {source_path}")
        if not self._source_path.is_dir():
            raise ValueError(f"Source path is not a directory: {source_path}")
    
    def _load(self) -> Dict[str, str]:
        """Liste tous les fichiers XML dans le dossier source.
        
        Parcourt récursivement le dossier source et collecte tous les fichiers
        avec l'extension .xml.
        
        Returns:
            Dictionnaire mappant uid (ELI ou chemin relatif) vers
            le chemin absolu du fichier XML
        """
        xml_files = {}
        
        # Parcourir récursivement le dossier source
        for root, dirs, files in os.walk(self._source_path):
            for file in files:
                if file.endswith('.xml'):
                    fullpath = os.path.join(root, file)
                    uid = self._get_uid(fullpath)
                    xml_files[uid] = fullpath
        
        return xml_files
    
    def _get_uid(self, fullpath: str) -> str:
        """
        """
        
        rel_path = Path(fullpath).relative_to(self._source_path)
        path = str(rel_path.with_suffix(''))
        path = path.replace("/","\\")
        # Utiliser le chemin sans extension comme uid
        return path
    
    def _save(self, data: Any) -> None:
        """Ce dataset est en lecture seule.
        
        Raises:
            NotImplementedError: Toujours levée car ce dataset ne supporte pas l'écriture
        """
        raise NotImplementedError(
            "XMLSourceDataset is read-only dataset"
        )
    
    def _describe(self) -> Dict[str, Any]:
        """Retourne une description du dataset.
        
        Returns:
            Dictionnaire contenant les métadonnées du dataset
        """
        return {
            "source_path": str(self._source_path),
            "type": "XMLSourceDataset",
            "read_only": True
        }
