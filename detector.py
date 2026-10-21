from typing import Protocol
import numpy as np
from src.contracts import SCHEMA_VERSION, validate_prediction

class Detector(Protocol):
    def predict(self, image: np.ndarray, image_id: str) -> dict: ...

class MockDetector:
    """Synthetic red rectangle detector. No learned weights, no GT access."""
    def predict(self,image,image_id):
        if image.dtype!=np.uint8 or image.ndim!=3 or image.shape[2]!=3:
            raise ValueError('Detector expects RGB uint8 H,W,3')
        mask=(image[:,:,0]>200)&(image[:,:,1]<50)&(image[:,:,2]<50)
        y,x=np.where(mask);detections=[]
        if len(x):
            detections=[{'polygon':[[int(x.min()),int(y.min())],[int(x.max()+1),int(y.min())],[int(x.max()+1),int(y.max()+1)],[int(x.min()),int(y.max()+1)]],'score':.9,'script':None}]
        return validate_prediction({'schema_version':SCHEMA_VERSION,'image_id':image_id,'width':image.shape[1],'height':image.shape[0],'detections':detections})
