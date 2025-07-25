import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
import os
from .config import TEXTURE_RES, GAUSS_SIGMA_PIX, OUT_DIR


class PaintMask:
    """Keeps a floating‑point texture and turns it into PNG frames."""

    def __init__(self):
        # 0 = unpainted, 1 = fully painted
        self.tex = np.zeros((TEXTURE_RES, TEXTURE_RES), dtype=np.float32)

    # ------------------------------------------------------------------
    # public methods used by run_simulation.py
    # ------------------------------------------------------------------
    def apply_hits(self, uv):
        """
        Stamp full‑strength paint at every (u,v) hit, then
        blur for overspray.
        • uv: (N,2) array with values in [0,1].
        """
        ix = (uv[:, 0] * (TEXTURE_RES - 1)).astype(int)
        iy = ((1 - uv[:, 1]) * (TEXTURE_RES - 1)).astype(int)
        self.tex[iy, ix] = 1.0                       # instant full paint
        self.tex = gaussian_filter(self.tex, GAUSS_SIGMA_PIX)
        self.tex = np.clip(self.tex, 0.0, 1.0)

    def save_png(self, idx):
        """
        Export current mask as RGB:
          • white  = unpainted
          • red    = fully painted
          • pink   = partial
        Returns the saved file path.
        """
        mask8 = (self.tex * 255).astype(np.uint8)

        rgb = np.empty((TEXTURE_RES, TEXTURE_RES, 3), dtype=np.uint8)
        rgb[..., 0] = 255                 # start white
        rgb[..., 1] = 255
        rgb[..., 2] = 255
        rgb[..., 1] -= mask8              # remove green as paint rises
        rgb[..., 2] -= mask8              # remove blue

        path = os.path.join(OUT_DIR, f"mask_{idx:04d}.png")
        Image.fromarray(rgb).save(path)
        return path
