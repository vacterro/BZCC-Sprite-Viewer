<div align="center">

# BZCC Sprite Viewer

**Inspect, adjust, export, and edit Battlezone-style `sprite.txt` texture entries from one compact desktop tool.**

![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white)
![UI](https://img.shields.io/badge/UI-Tkinter-6B5A2B?style=flat-square)
![Images](https://img.shields.io/badge/images-Pillow-D4B86A?style=flat-square)
![Game](https://img.shields.io/badge/game-BZCC-332E22?style=flat-square)

<img width="1100" alt="BZCC Sprite Viewer main interface" src="https://github.com/user-attachments/assets/f8941d3d-f845-4f68-bbc9-c3a0072b9f53" />

</div>

## What it does

BZCC Sprite Viewer reads sprite-table entries from `sprite.txt`, resolves their referenced texture files, and gives you a visual workspace for inspecting and editing the resulting crops.

It is useful when a sprite definition is technically valid but painful to reason about from coordinates alone.

## Quick start

Requirements: **Windows**, **Python 3**, and Pillow.

```powershell
pip install Pillow
python BZCC_SpriteViewer.py
```

The bundled `texconv.exe` is used when DDS conversion is required.

## Highlights

- compact sprite tree plus two-column property editor;
- recursive texture resolution from sprite-table entries;
- live adjustment preview;
- raw-crop save and adjusted export as separate actions;
- batch export for visible sprites or the current file group;
- save a modified sprite-table copy instead of silently rewriting the source;
- modified-entry highlighting;
- image-size and zoom information in the UI;
- Windows clipboard integration with a safe temp-file fallback;
- persistent configuration in `sprite_viewer_config.json`.

## Repository

| Path | Purpose |
|---|---|
| `BZCC_SpriteViewer.py` | current viewer/editor |
| `BZCC_SpriteViewer_01.py` | retained alternate/older implementation |
| `sprite_viewer_config.json` | persisted viewer configuration |
| `build_exe.py` | executable build helper |
| `texconv.exe` | DDS conversion backend |

## Screenshots

<details>
<summary><b>Open interface gallery</b></summary>

<br>

<table>
<tr>
<td width="50%"><img alt="Sprite Viewer interface view 2" src="https://github.com/user-attachments/assets/59316efa-fd81-4f63-9e2b-db40ce710be8" /></td>
<td width="50%"><img alt="Sprite Viewer interface view 3" src="https://github.com/user-attachments/assets/90071c43-cf4a-4cf1-85fc-53710f63433d" /></td>
</tr>
<tr>
<td width="50%"><img alt="Sprite Viewer interface view 4" src="https://github.com/user-attachments/assets/9cae44a9-3712-4fdf-8ef9-7baaded226c5" /></td>
<td width="50%"><img alt="Sprite Viewer interface view 5" src="https://github.com/user-attachments/assets/98f40f6b-ec63-4721-bf1c-6dc62e7150bf" /></td>
</tr>
<tr>
<td width="50%"><img alt="Sprite Viewer interface view 6" src="https://github.com/user-attachments/assets/43b2725b-2e1e-464c-8674-484735f4cc9a" /></td>
<td width="50%"><img alt="Sprite Viewer interface view 7" src="https://github.com/user-attachments/assets/a7974bd3-7f22-4937-a14a-5dfd891d9e3f" /></td>
</tr>
</table>

</details>


## Project network

Part of the broader **SAIPEN / vacterro** project ecosystem.

[**Author hub**](https://github.com/vacterro) · [**SAIPEN HQ**](https://github.com/saipenhq) · [**SAIPEN Core**](https://github.com/vacterro/saipen) · [**ZAICODE**](https://github.com/vacterro/zaicode) · [**FastPrompter**](https://github.com/vacterro/FastPrompter) · [**SAIPEN Community**](https://discord.gg/SEYaYkuVgN)

For reproducible bugs and durable feature requests, use [GitHub Issues](https://github.com/vacterro/BZCC-Sprite-Viewer/issues).

<!-- VACTERRO_SUPPORT:BEGIN -->
---
<sub>If BZCC Sprite Viewer is useful to you, optional support: [Buy Me a Coffee](https://buymeacoffee.com/vacuum34) · [Boosty](https://boosty.to/vacuum34/donate) · [PayPal](https://paypal.me/AlexNelin) · [other ways](https://github.com/vacterro/vacterro/blob/main/SUPPORT.md)</sub>
<!-- VACTERRO_SUPPORT:END -->
