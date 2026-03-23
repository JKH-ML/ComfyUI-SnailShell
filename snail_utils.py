# Snail Shell Utils v2.0 - Zero Config (Auto Bit-Depth)
import os
import hashlib
import struct
from typing import Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont

WATERMARK_SKIP_W_RATIO = 0.40
WATERMARK_SKIP_H_RATIO = 0.08
SHELL_CHANNELS = 3
MAGIC_SIGNATURE = b"SNAIL"

def _generate_key_stream(password: str, salt: bytes, length: int) -> bytes:
    key_material = (password + salt.hex()).encode("utf-8")
    out = bytearray()
    counter = 0
    while len(out) < length:
        combined = key_material + str(counter).encode("utf-8")
        out.extend(hashlib.sha256(combined).digest())
        counter += 1
    return bytes(out[:length])

def _encrypt_with_password(data: bytes, password: str):
    if not password: return data, b"", b"", False
    salt = os.urandom(16)
    key_stream = _generate_key_stream(password, salt, len(data))
    cipher = bytes(a ^ b for a, b in zip(data, key_stream))
    pwd_hash = hashlib.sha256((password + salt.hex()).encode("utf-8")).digest()
    return cipher, salt, pwd_hash, True

def _build_file_header(raw: bytes, password: str, ext: str = "png") -> bytes:
    cipher, salt, pwd_hash, has_pwd = _encrypt_with_password(raw, password)
    payload = cipher if has_pwd else raw
    ext_bytes = ext.encode("utf-8")
    header = bytearray()
    header.extend(MAGIC_SIGNATURE)
    header.append(1 if has_pwd else 0)
    if has_pwd:
        header.extend(pwd_hash)
        header.extend(salt)
    header.append(len(ext_bytes))
    header.extend(ext_bytes)
    header.extend(struct.pack(">I", len(payload)))
    header.extend(payload)
    return bytes(header)

def _build_shell_image(size: int = 640, title: str = "") -> Image.Image:
    bg = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    draw = ImageDraw.Draw(bg)
    center = (size // 2, size // 2)
    for i in range(0, 1500, 2):
        angle = i * 0.1
        radius = (i**1.1) * (size / 4000)
        x = center[0] + radius * np.cos(angle)
        y = center[1] + radius * np.sin(angle)
        r = int(139 + (210-139) * (i/1500))
        g = int(69 + (180-69) * (i/1500))
        b = int(19 + (140-19) * (i/1500))
        draw.ellipse([x-radius/8, y-radius/8, x+radius/8, y+radius/8], fill=(r, g, b, 255))
    return bg.convert("RGB")

def _determine_best_config(bit_len: int) -> Tuple[int, int]:
    # Returns (lsb_bits, side_size)
    for k in [2, 4, 8]:
        for side in [512, 768, 1024, 1536, 2048]:
            skip_w, skip_h = int(side * WATERMARK_SKIP_W_RATIO), int(side * WATERMARK_SKIP_H_RATIO)
            usable_pixels = (side * side) - (skip_w * skip_h)
            if usable_pixels * SHELL_CHANNELS * k >= bit_len + 2048:
                return k, side
    raise ValueError("Snail data is way too large even for max shell size!")

def _embed_snail_lsb(img_base: Image.Image, file_header: bytes) -> Image.Image:
    bit_len = (len(file_header) + 4) * 8
    lsb_bits, side = _determine_best_config(bit_len)
    
    # Re-build shell with correct size
    img = _build_shell_image(side, title=f"Snail Shell v2.0 (k={lsb_bits})")
    arr = np.array(img).astype(np.uint8).copy()
    h, w, c = arr.shape
    
    # Encode bit-depth info in the very first pixel (0,0) Red channel
    # 2->0, 4->1, 8->2
    bit_mode = {2: 0, 4: 1, 8: 2}[lsb_bits]
    arr[0, 0, 0] = (arr[0, 0, 0] // 4) * 4 + bit_mode
    
    skip_w, skip_h = int(w * WATERMARK_SKIP_W_RATIO), int(h * WATERMARK_SKIP_H_RATIO)
    mask = np.ones((h, w, c), dtype=bool)
    mask[:skip_h, :skip_w, :] = False
    mask[0, 0, 0] = False # Don't overwrite our bit_mode pixel
    
    payload = struct.pack(">I", len(file_header)) + file_header
    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8), bitorder='big')
    
    if len(bits) % lsb_bits != 0:
        bits = np.concatenate([bits, np.zeros(lsb_bits - (len(bits) % lsb_bits), dtype=np.uint8)])
    
    vals = np.sum(bits.reshape(-1, lsb_bits) * (2 ** np.arange(lsb_bits - 1, -1, -1, dtype=np.uint8)), axis=1).astype(np.uint8)
    
    idxs = np.flatnonzero(mask)
    flat = arr.ravel()
    divisor = int(2**lsb_bits)
    flat[idxs[:len(vals)]] = (flat[idxs[:len(vals)]] // divisor) * divisor + vals
    
    return Image.fromarray(flat.reshape(h, w, c))

def _extract_snail_lsb(img: Image.Image) -> bytes:
    arr = np.array(img.convert("RGB")).astype(np.uint8)
    
    # Read bit-depth info from first pixel
    bit_mode = arr[0, 0, 0] % 4
    lsb_bits = {0: 2, 1: 4, 2: 8}.get(bit_mode, 4)
    
    h, w, c = arr.shape
    skip_w, skip_h = int(w * WATERMARK_SKIP_W_RATIO), int(h * WATERMARK_SKIP_H_RATIO)
    mask = np.ones((h, w, c), dtype=bool)
    mask[:skip_h, :skip_w, :] = False
    mask[0, 0, 0] = False
    
    idxs = np.flatnonzero(mask)
    divisor = int(2**lsb_bits)
    vals = (arr.ravel()[idxs] % divisor).astype(np.uint8)
    
    bits = np.unpackbits(vals, bitorder='big').reshape(-1, 8)[:, -lsb_bits:].ravel()
    header_len = struct.unpack(">I", np.packbits(bits[:32], bitorder='big').tobytes())[0]
    return bytes(np.packbits(bits[32:32 + header_len * 8], bitorder='big'))

def _parse_snail_header(header: bytes, password: str):
    idx = 0
    if header[idx:idx+5] != MAGIC_SIGNATURE: raise ValueError("Magic mismatch")
    idx += 5
    has_pwd = header[idx] == 1; idx += 1
    if has_pwd:
        pwd_hash, salt = header[idx:idx+32], header[idx+32:idx+48]
        if not password or hashlib.sha256((password + salt.hex()).encode("utf-8")).digest() != pwd_hash:
            raise ValueError("Wrong password")
        idx += 48
    ext_len = header[idx]; idx += 1
    ext = header[idx:idx+ext_len].decode("utf-8", errors="ignore"); idx += ext_len
    data_len = struct.unpack(">I", header[idx:idx+4])[0]; idx += 4
    data = header[idx:idx+data_len]
    if has_pwd:
        ks = _generate_key_stream(password, salt, len(data))
        data = bytes(a ^ b for a, b in zip(data, ks))
    return data, ext
