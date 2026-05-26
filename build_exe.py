# build_exe.py
import os, sys, shutil, subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_SCRIPT = "BZCC_SpriteViewer.py"   # измените при необходимости

def ensure_pyinstaller():
    try:
        import PyInstaller
    except ImportError:
        print("Устанавливаю PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def make_onefile():
    main = os.path.join(SCRIPT_DIR, MAIN_SCRIPT)
    if not os.path.isfile(main):
        print(f"Файл '{MAIN_SCRIPT}' не найден.")
        sys.exit(1)

    add_data = []
    texconv = os.path.join(SCRIPT_DIR, "texconv.exe")
    if os.path.isfile(texconv):
        add_data.append(f"--add-data=texconv.exe;.")
    else:
        print("texconv.exe не найден – поддержка DDS будет недоступна.")

    icon = os.path.join(SCRIPT_DIR, "icon.ico")
    icon_arg = [f"--icon={icon}"] if os.path.isfile(icon) else []

    for folder in ["build", "dist"]:
        path = os.path.join(SCRIPT_DIR, folder)
        if os.path.exists(path):
            shutil.rmtree(path)

    print("Собираю EXE...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name=BZ2_Sprite_Viewer",
        main,
    ] + add_data + icon_arg

    subprocess.check_call(cmd)
    print("\nГотово! EXE лежит в папке dist/")

if __name__ == "__main__":
    ensure_pyinstaller()
    make_onefile()