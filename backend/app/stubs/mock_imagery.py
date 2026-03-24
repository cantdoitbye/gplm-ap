"""
Mock Imagery Generator

Generates synthetic satellite imagery for testing without
real satellite data.
"""

import os
import random
import tempfile
from typing import Optional, Tuple
from datetime import datetime


class MockImageryGenerator:
    """
    Generates mock satellite imagery for testing.
    
    Creates synthetic images that simulate satellite data:
    - Sentinel-2 style images (10m resolution)
    - Bhuvan/ISRO style images
    - NRSC high-resolution images
    """
    
    def __init__(self):
        self.output_dir = os.environ.get("MOCK_IMAGERY_DIR", tempfile.gettempdir())
        self._ensure_numpy_pil()
    
    def _ensure_numpy_pil(self):
        """Check if numpy and PIL are available."""
        try:
            import numpy
            import PIL
            self.numpy = numpy
            self.PIL = PIL
        except ImportError:
            self.numpy = None
            self.PIL = None
    
    def generate_sentinel_image(
        self,
        scene_id: str,
        width: int = 256,
        height: int = 256,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate a mock Sentinel-2 style image.
        
        Sentinel-2 has 13 bands, but we generate a simple RGB preview.
        """
        if output_path is None:
            output_path = os.path.join(self.output_dir, f"sentinel_{scene_id}.tif")
        
        self._create_synthetic_image(
            output_path,
            width,
            height,
            bands=3,
            pattern="sentinel",
        )
        
        return output_path
    
    def generate_bhuvan_image(
        self,
        scene_id: str,
        satellite: str = "Resourcesat-2",
        sensor: str = "LISS-IV",
        resolution: float = 5.8,
        output_path: Optional[str] = None,
    ) -> str:
        """Generate a mock Bhuvan/ISRO style image."""
        if output_path is None:
            output_path = os.path.join(self.output_dir, f"bhuvan_{scene_id}.tif")
        
        self._create_synthetic_image(
            output_path,
            width=512,
            height=512,
            bands=4 if "LISS" in sensor else 1,
            pattern="bhuvan",
        )
        
        return output_path
    
    def generate_nrsc_image(
        self,
        scene_id: str,
        resolution: float = 0.5,
        output_path: Optional[str] = None,
    ) -> str:
        """Generate a mock NRSC high-resolution image."""
        if output_path is None:
            output_path = os.path.join(self.output_dir, f"nrsc_{scene_id}.tif")
        
        self._create_synthetic_image(
            output_path,
            width=1024,
            height=1024,
            bands=3,
            pattern="highres",
        )
        
        return output_path
    
    def generate_preview_image(
        self,
        scene_id: str,
        source: str = "sentinel",
        output_path: Optional[str] = None,
    ) -> str:
        """Generate a preview/thumbnail image."""
        if output_path is None:
            output_path = os.path.join(self.output_dir, f"preview_{source}_{scene_id}.png")
        
        self._create_synthetic_image(
            output_path,
            width=256,
            height=256,
            bands=3,
            pattern="preview",
        )
        
        return output_path
    
    def generate_change_pair(
        self,
        before_date: datetime,
        after_date: datetime,
        change_type: str = "construction",
        output_dir: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Generate a pair of images with simulated changes.
        
        Returns paths to before and after images.
        """
        if output_dir is None:
            output_dir = self.output_dir
        
        before_path = os.path.join(output_dir, f"change_before_{before_date.strftime('%Y%m%d')}.tif")
        after_path = os.path.join(output_dir, f"change_after_{after_date.strftime('%Y%m%d')}.tif")
        
        self._create_change_images(before_path, after_path, change_type)
        
        return before_path, after_path
    
    def _create_synthetic_image(
        self,
        output_path: str,
        width: int,
        height: int,
        bands: int,
        pattern: str,
    ):
        """Create a synthetic satellite-like image."""
        if self.numpy is None:
            with open(output_path, 'wb') as f:
                f.write(b"MOCK_SATELLITE_IMAGE_" + pattern.encode() + b"\n")
                f.write(f"Dimensions: {width}x{height}x{bands}\n".encode())
                f.write(f"Generated: {datetime.utcnow().isoformat()}\n".encode())
            return
        
        np = self.numpy
        
        if pattern == "sentinel":
            data = self._generate_sentinel_pattern(width, height, bands)
        elif pattern == "bhuvan":
            data = self._generate_bhuvan_pattern(width, height, bands)
        elif pattern == "highres":
            data = self._generate_highres_pattern(width, height, bands)
        else:
            data = np.random.randint(0, 255, (height, width, bands), dtype=np.uint8)
        
        if output_path.endswith('.png'):
            from PIL import Image
            img = Image.fromarray(data[:, :, :3] if data.shape[2] > 3 else data)
            img.save(output_path)
        else:
            np.save(output_path.replace('.tif', '.npy'), data)
    
    def _generate_sentinel_pattern(self, width: int, height: int, bands: int):
        """Generate Sentinel-2 style pattern (vegetation, urban, water)."""
        np = self.numpy
        
        data = np.zeros((height, width, bands), dtype=np.uint8)
        
        data[:height//3, :] = [34, 139, 34]
        
        data[height//3:2*height//3, :width//2] = [128, 128, 128]
        
        data[height//3:2*height//3, width//2:] = [169, 169, 169]
        
        data[2*height//3:, :] = [65, 105, 225]
        
        noise = np.random.randint(-20, 20, (height, width, bands))
        data = np.clip(data.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        return data
    
    def _generate_bhuvan_pattern(self, width: int, height: int, bands: int):
        """Generate Bhuvan/ISRO style pattern."""
        np = self.numpy
        
        data = np.zeros((height, width, min(bands, 3)), dtype=np.uint8)
        
        for i in range(0, height, 64):
            for j in range(0, width, 64):
                color = random.choice([
                    [34, 139, 34],
                    [139, 90, 43],
                    [128, 128, 128],
                    [65, 105, 225],
                ])
                data[i:i+64, j:j+64] = color
        
        noise = np.random.randint(-15, 15, (height, width, min(bands, 3)))
        data = np.clip(data.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        return data
    
    def _generate_highres_pattern(self, width: int, height: int, bands: int):
        """Generate high-resolution imagery pattern with buildings/roads."""
        np = self.numpy
        
        data = np.ones((height, width, bands), dtype=np.uint8) * 200
        
        for _ in range(random.randint(20, 50)):
            x1, y1 = random.randint(0, width-50), random.randint(0, height-50)
            x2, y2 = x1 + random.randint(20, 100), y1 + random.randint(20, 100)
            color = random.choice([[100, 80, 80], [120, 100, 100], [80, 60, 60]])
            data[y1:y2, x1:x2] = color
        
        for _ in range(5):
            y = random.randint(0, height-1)
            data[y, :] = [50, 50, 50]
        
        noise = np.random.randint(-10, 10, (height, width, bands))
        data = np.clip(data.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        return data
    
    def _create_change_images(self, before_path: str, after_path: str, change_type: str):
        """Create before/after images with simulated changes."""
        np = self.numpy
        
        if np is None:
            for path in [before_path, after_path]:
                with open(path, 'wb') as f:
                    f.write(b"MOCK_CHANGE_IMAGE\n")
            return
        
        width, height, bands = 512, 512, 3
        
        before = self._generate_sentinel_pattern(width, height, bands)
        after = before.copy()
        
        if change_type == "construction":
            x, y = width//2, height//2
            size = 50
            after[y:y+size, x:x+size] = [128, 128, 128]
        elif change_type == "demolition":
            x, y = width//4, height//4
            size = 40
            after[y:y+size, x:x+size] = [34, 139, 34]
        elif change_type == "vegetation_loss":
            after[:height//3, :] = [139, 90, 43]
        
        if before_path.endswith('.png'):
            from PIL import Image
            Image.fromarray(before).save(before_path)
            Image.fromarray(after).save(after_path)
        else:
            np.save(before_path.replace('.tif', '.npy'), before)
            np.save(after_path.replace('.tif', '.npy'), after)
