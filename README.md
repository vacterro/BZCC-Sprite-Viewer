# *** THIS CONTENT IS AI GENERATED ***
<img width="1434" height="857" alt="clipboard_20260527_011935_4cbba4fc" src="https://github.com/user-attachments/assets/fc53d9a0-c598-48fe-8b9f-5e6f8dfaaace" />



Optional clipboard support on Windows:

pip install pywin32

Place texconv.exe next to the script if you want automatic conversion support for formats Pillow cannot read directly.
<img width="1434" height="857" alt="clipboard_20260527_012528_cfcb7a69" src="https://github.com/user-attachments/assets/c6793775-45d4-49bc-9cab-de7b3f9a99e0" />

Folder Setup

The program expects a resource folder containing sprite.txt and the corresponding image files.

Typical layout:

bz2r_res/
├─ interface/
│  └─ sprite.txt
├─ textures/
│  └─ ...
└─ ...

The viewer can search recursively for texture files inside the selected resource directory.
<img width="1434" height="857" alt="clipboard_20260527_012531_82dd05ca" src="https://github.com/user-attachments/assets/353510d5-e854-4946-8d34-4ea2e62a158e" />

Usage

Run the script:

python BZ2_SpriteViewer_Improved.py

On launch, select the resource folder that contains sprite.txt.
<img width="1434" height="857" alt="clipboard_20260527_012135_7a0198fd" src="https://github.com/user-attachments/assets/a5810e53-2c6d-4795-b6dd-23d64f4d1370" />

Main workflow
Select a sprite in the tree
Adjust U / V / W / H / TW / TH / Flags if needed
Use the Adjust tab for image effects
Export the current crop, save a raw crop, or batch export multiple sprites
Save a modified sprite.txt copy when your changes are ready
Toolbar Controls
In / Out: zoom the preview
Fit: fit the sprite into the viewport
100%: view at native scale
Ctr: center the preview
AA: enable or disable antialiasing
Grid: toggle checkerboard background
BG: choose a solid background color
Export / Raw / Batch: quick access to saving tools
Save Tab

The Save tab groups all save-related actions in one place:
<img width="1434" height="857" alt="clipboard_20260527_012541_57c9be0e" src="https://github.com/user-attachments/assets/c54f1955-3819-4d75-a391-e3d4bee133ec" />

Export with adjustments
Save raw crop without adjustments
Copy image to clipboard
Save one modified entry to the table
Save a full modified table copy
Batch export visible sprites
Batch export the current file group
Keyboard Shortcuts
Ctrl + F - focus filter
Ctrl + O - open image file
Ctrl + Shift + O - open file location
Ctrl + 0 - zoom 100%
Ctrl + + - zoom in
Ctrl + - - zoom out
Ctrl + E - export with adjustments
Ctrl + S - save modified table copy
Ctrl + B - batch export visible sprites
F5 - refresh tree
Ctrl + Shift + F - change resource folder
What Gets Saved
Save Raw Crop
<img width="1434" height="857" alt="clipboard_20260527_012710_f1c45b89" src="https://github.com/user-attachments/assets/29e2ea45-169c-42f0-8032-6f39fab40451" />

Exports the sprite crop exactly as defined by the table entry, with no visual adjustments applied.

Export with Adjustments
<img width="1434" height="857" alt="clipboard_20260527_012715_a0144098" src="https://github.com/user-attachments/assets/8e122b2d-d0ca-4055-9c4c-5519035d227b" />

Exports the sprite crop after applying brightness, contrast, saturation, gamma, hue, and invert settings.

Save Modified Table Copy
<img width="1434" height="857" alt="clipboard_20260527_012723_64d664a4" src="https://github.com/user-attachments/assets/abd0f0b2-ca89-475e-ba2a-34445198c2dc" />

Creates a new sprite.txt copy containing your edited values for:

U
V
W
H
TW
TH
Flags
Batch Export

Exports multiple sprites as PNG files, either:
<img width="1434" height="857" alt="clipboard_20260527_012735_a0fe88f8" src="https://github.com/user-attachments/assets/ffa3405d-ee78-49c9-9a81-b2993f61f80c" />

only the entries currently visible under the filter, or
all entries from the current source file group
Notes
Modified sprites are highlighted in yellow in the tree.
The program avoids false modification records while loading properties.
If an image format is not readable directly, the app can try texconv.exe as a fallback.
Clipboard support is best on Windows with pywin32 installed.
Troubleshooting
"Image not found or unsupported format"
Check whether the texture file exists in the resource folder
Verify the filename matches the entry in sprite.txt
For DDS/TGA files, make sure texconv.exe is present if Pillow cannot read the file directly
Clipboard copy does nothing on Windows
Install pywin32
Run the app with normal desktop permissions
Use the fallback temp-file path if native clipboard access is unavailable
Modified entry is not highlighted
The entry must be edited through the Properties fields
Refresh the tree if needed

<img width="1434" height="857" alt="clipboard_20260527_012750_97a0e2ec" src="https://github.com/user-attachments/assets/5f33324e-442e-4bff-a4ef-777798c4a36c" />
<img width="1434" height="857" alt="clipboard_20260527_012743_13588147" src="https://github.com/user-attachments/assets/107414a4-31bb-4d65-94b1-5d8c808f18a7" />
