from dataclasses import dataclass
from src.contracts import number

@dataclass(frozen=True)
class ResizePad:
    scale_x: float
    scale_y: float
    pad_x: float = 0
    pad_y: float = 0
    def __post_init__(self):
        if number(self.scale_x)<=0 or number(self.scale_y)<=0:
            raise ValueError('Scale must be positive')
        number(self.pad_x);number(self.pad_y)
    def forward(self,polygon):
        return [[number(x)*self.scale_x+self.pad_x,number(y)*self.scale_y+self.pad_y] for x,y in polygon]
    def inverse(self,polygon):
        return [[(number(x)-self.pad_x)/self.scale_x,(number(y)-self.pad_y)/self.scale_y] for x,y in polygon]
