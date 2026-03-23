# 🐌 ComfyUI-SnailShell (v2.7)

**ComfyUI-SnailShell** is a professional steganography suite for ComfyUI. It allows you to discreetly hide "Snails" (secret images or video sequences) inside an automatically generated "Shell" (a carrier image with a unique snail spiral pattern).

This project is designed for content protection, hidden metadata sharing, and creative privacy.

---

## ✨ Key Features

- **🚀 Zero-Config Steganography**: Automatically determines the optimal bit-depth (2, 4, or 8 bits) and canvas size based on your data size.
- **🎬 Video Batch Support**: Directly hide a sequence of images (video frames). The node automatically compresses them into an MP4 and embeds them into the shell.
- **🔒 Password Protection**: Secure your hidden snails using high-standard SHA-256 encryption.
- **🖼️ Universal Format**: Works with single images (PNG) and video batches (MP4).
- **🌐 Web Integration**: Designed to be compatible with the **Flip the Shell** Chrome extension for instant decoding.

---

## 🛠 Nodes Included

### 1. Snail in the Shell (Encoder)
- **Inputs**: 
  - `snail_image`: A single image to hide.
  - `snail_images`: A batch of images (video frames) to hide.
  - `password`: (Optional) Encryption key.
- **Output**: 
  - `shell_image`: The generated carrier image containing your hidden snail.

### 2. Flip the Shell (Decoder)
- **Inputs**: 
  - `shell_image`: The image containing a hidden snail.
  - `password`: (Required if encrypted) The key to unlock the snail.
- **Outputs**: 
  - `image`: The revealed single image (or the first frame of a video).
  - `images`: The full sequence of revealed frames (for video).
  - `status`: Decoding information and version logs.

---

## 💻 Installation

1. Open your terminal and navigate to the ComfyUI `custom_nodes` folder:
   ```bash
   cd ComfyUI/custom_nodes
   ```
2. Clone this repository:
   ```bash
   git clone https://github.com/JKH-ML/ComfyUI-SnailShell.git
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Restart ComfyUI.

---

## 🔍 Chrome Extension: Flip the Shell (Work in Progress)

The **Flip the Shell** companion extension is currently in development. It will allow users to:
- Hover over any Snail Shell image on the web.
- Instantly reveal hidden images or videos in a high-quality overlay.
- *Note: The extension is currently available for manual installation from the source for developers.*

---

## ☁️ RunningHub Support
This node is fully optimized for **RunningHub**. It uses standard `requirements.txt` for automatic dependency management and follows ComfyUI best practices for port naming and data handling.

## 📝 License
MIT License - Feel free to use and contribute!
