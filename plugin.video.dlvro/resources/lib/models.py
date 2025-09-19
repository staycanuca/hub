from dataclasses import dataclass, asdict
from typing import Dict
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
    title2: str = ''
    
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v}
    
    def full_dict(self) -> Dict:
        return asdict(self)
    
    def url_encode(self) -> str:
        return urlencode(self.to_dict())
