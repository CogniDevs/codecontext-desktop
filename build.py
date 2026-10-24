import os
import sys
import shutil
import subprocess


def ensure_windows_ico(icon_ico, icon_png):
    if os.path.exists(icon_ico):
        return icon_ico
    if os.path.exists(icon_png):
        try:
            from PIL import Image
            img = Image.open(icon_png)
            img.save(icon_ico, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
            return icon_ico
        except Exception:
            pass
    return None


def build():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, 'backend')
    dist_path = os.path.join(root_dir, 'dist')
    build_path = os.path.join(root_dir, 'build')
    resources_src = os.path.join(root_dir, 'resources')
    icon_ico = os.path.join(resources_src, 'icons', 'icon.ico')
    icon_png = os.path.join(resources_src, 'icons', 'icon.png')
    main_entry = os.path.join(root_dir, 'main.py')

    print('--- Packaging Desktop Binary with PyInstaller ---')

    add_data_sep = ';' if sys.platform == 'win32' else ':'
    pyinstaller_args = [
        main_entry,
        '--onefile',
        '--noconsole',
        '--name=CodeContext',
        f'--distpath={dist_path}',
        f'--workpath={build_path}',
        f'--paths={root_dir}',
        f'--paths={backend_dir}',
        '--clean',
    ]

    if os.path.exists(resources_src):
        pyinstaller_args.append(f'--add-data={resources_src}{add_data_sep}resources')

    dist_ui_candidates = [
        os.path.join(root_dir, 'dist_ui'),
        os.path.join(root_dir, 'dist', 'browser'),
        os.path.join(root_dir, 'frontend', 'dist', 'codecontext-web', 'browser')
    ]
    ui_folder = next((d for d in dist_ui_candidates if os.path.exists(d)), None)
    if ui_folder:
        print(f'Embedding Web UI from: {ui_folder}')
        pyinstaller_args.append(f'--add-data={ui_folder}{add_data_sep}dist_ui')

    if sys.platform == 'win32':
        sys32_dir = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32')
        for dll_name in ['vcruntime140.dll', 'vcruntime140_1.dll']:
            dll_path = os.path.join(sys32_dir, dll_name)
            if os.path.exists(dll_path):
                pyinstaller_args.append(f'--add-binary={dll_path};.')

        valid_ico = ensure_windows_ico(icon_ico, icon_png)
        if valid_ico:
            pyinstaller_args.append(f'--icon={valid_ico}')
    elif sys.platform == 'darwin':
        if os.path.exists(icon_png):
            pyinstaller_args.append(f'--icon={icon_png}')

    import PyInstaller.__main__
    PyInstaller.__main__.run(pyinstaller_args)

    print('\n--- Build finished successfully! Binary is in dist/ ---')


if __name__ == '__main__':
    build()