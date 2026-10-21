# Third-party notices

This repository redistributes the unmodified binaries listed below. Each is
the property of its author and is used under the licence stated here.

## texconv.exe

- **Project:** DirectXTex — https://github.com/microsoft/DirectXTex
- **Author:** Microsoft Corporation
- **File:** `texconv.exe` (DirectXTex texture conversion command-line tool)
- **Used for:** DDS conversion in the sprite viewer
  (`texconv_convert()` in `BZCC_SpriteViewer.py`, bundled into the EXE by
  `build_exe.py`).
- **Licence:** MIT

```
MIT License

Copyright (c) Microsoft Corporation.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Game content

This tool reads `sprite.txt` tables and the textures they reference from a
Battlezone: Combat Commander installation the user supplies. No game assets
are redistributed here.
