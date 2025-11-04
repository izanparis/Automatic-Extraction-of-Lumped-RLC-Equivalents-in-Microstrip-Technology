
from pathlib import Path
from omegaconf import OmegaConf
from pydantic import BaseModel

class Processing(BaseModel):
    ref_frequency_hz: float
    window_band_hz: float

class ModelCfg(BaseModel):
    rlc_topology: str
    class Initial(BaseModel):
        R: float
        L: float
        C: float
    initial: Initial

class RootCfg(BaseModel):
    processing: Processing
    model: ModelCfg

def load_config(path: Path) -> RootCfg:
    cfg = OmegaConf.load(path)
    return RootCfg.model_validate(OmegaConf.to_container(cfg, resolve=True))
