from dataclasses import dataclass, asdict, field
from typing import Dict, List, Tuple
from urllib.parse import urlencode
from . import variables as var

@dataclass
class Item:
    title: str = 'Unknown Title'
    type: str = 'item'
    mode: str = ''
    link: str = ''
    thumbnail: str = var.addon_icon
    fanart: str = var.addon_fanart
    summary: str = ''
    infolabels = None
    cast = None
    contextmenu: List[Tuple[str]] = field(default_factory=list)
    title2: str = ''
    
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v}
    
    def full_dict(self) -> Dict:
        return asdict(self)
    
    def url_encode(self) -> str:
        return urlencode(self.to_dict())