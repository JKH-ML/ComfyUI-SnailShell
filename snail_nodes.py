import torch
import numpy as np
from PIL import Image
import io
import os
import tempfile
try:
    import folder_paths
except:
    folder_paths = None

# MoviePy Import
ImageSequenceClip = None
VideoFileClip = None
try:
    from moviepy.editor import ImageSequenceClip as ISC, VideoFileClip as VFC
    ImageSequenceClip, VideoFileClip = ISC, VFC
except ImportError:
    try:
        from moviepy.video.io.ImageSequenceClip import ImageSequenceClip as ISC2
        from moviepy.video.io.VideoFileClip import VideoFileClip as VFC2
        ImageSequenceClip, VideoFileClip = ISC2, VFC2
    except ImportError:
        pass

from .snail_utils import (
    _build_file_header, 
    _embed_snail_lsb,
    _extract_snail_lsb,
    _parse_snail_header
)

def _tensor_to_pil(image: torch.Tensor) -> Image.Image:
    if image.dim() == 4: image = image[0]
    image = image.detach().cpu().numpy()
    image = np.clip(image * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(image).convert("RGB")

def _pil_to_tensor(image: Image.Image) -> torch.Tensor:
    arr = np.array(image.convert("RGB")).astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None, ...]

class SnailEncoder:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "password": ("STRING", {"default": ""}),
            },
            "optional": {
                "snail_image": ("IMAGE",), # Restored for compatibility
                "snail_images": ("IMAGE",), # Restored for compatibility
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("shell_image",)
    FUNCTION = "encode"
    CATEGORY = "SnailShell"

    def encode(self, password, snail_image=None, snail_images=None):
        # Determine which input to use (Priority: Batch > Single)
        active_snail = snail_images if snail_images is not None else snail_image
        if active_snail is None: raise ValueError("No input image or images provided.")
        
        raw_bytes = b""
        ext = "png"

        # Auto-detect if it's a video or image based on tensor shape
        if active_snail.shape[0] > 1:
            if ImageSequenceClip is None: raise ImportError("moviepy required.")
            fd, temp_path = tempfile.mkstemp(suffix=".mp4"); os.close(fd)
            try:
                frames = (active_snail.detach().cpu().numpy() * 255).astype(np.uint8)
                clip = ImageSequenceClip(list(frames), fps=24) # Fixed 24 FPS
                clip.write_videofile(temp_path, codec="libx264", audio=False, logger=None)
                with open(temp_path, "rb") as f: raw_bytes = f.read()
                ext = "mp4"
            finally:
                if os.path.exists(temp_path): os.remove(temp_path)
        else:
            snail_pil = _tensor_to_pil(active_snail)
            byte_io = io.BytesIO(); snail_pil.save(byte_io, format="PNG")
            raw_bytes = byte_io.getvalue()
            ext = "png"
        
        file_header = _build_file_header(raw_bytes, password, ext=ext)
        dummy_img = Image.new("RGB", (64, 64)) 
        encoded_img = _embed_snail_lsb(dummy_img, file_header)
        return (_pil_to_tensor(encoded_img),)

class SnailDecoder:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "shell_image": ("IMAGE",),
                "password": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING")
    RETURN_NAMES = ("image", "images", "status")
    FUNCTION = "decode"
    CATEGORY = "SnailShell"

    def decode(self, shell_image, password):
        img = _tensor_to_pil(shell_image)
        empty_img = torch.zeros((1, 64, 64, 3))
        try:
            payload = _extract_snail_lsb(img)
            data, ext = _parse_snail_header(payload, password)
            
            if ext == "png":
                snail_pil = Image.open(io.BytesIO(data)).convert("RGB")
                tensor = _pil_to_tensor(snail_pil)
                return (tensor, tensor, f"v2.7: Extracted Image")
            elif ext == "mp4":
                if VideoFileClip is None: raise ImportError("moviepy required.")
                fd, temp_path = tempfile.mkstemp(suffix=".mp4"); os.close(fd)
                with open(temp_path, "wb") as f: f.write(data)
                try:
                    clip = VideoFileClip(temp_path)
                    frames = [frame.astype(np.float32) / 255.0 for frame in clip.iter_frames()]
                    clip.close()
                    video_tensor = torch.from_numpy(np.stack(frames))
                    return (video_tensor[0:1], video_tensor, f"v2.7: Extracted Video ({len(frames)} frames)")
                finally:
                    if os.path.exists(temp_path): os.remove(temp_path)
            else: return (empty_img, empty_img, f"v2.7: Unknown Format")
        except Exception as e:
            return (empty_img, empty_img, f"v2.7 Error: {str(e)}")

NODE_CLASS_MAPPINGS = {
    "SnailEncoder": SnailEncoder,
    "SnailDecoder": SnailDecoder
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SnailEncoder": "Snail in the Shell (Encoder) v2.7",
    "SnailDecoder": "Flip the Shell (Decoder) v2.7"
}
