import os
import shutil

src_dir = os.path.expanduser('~/.EasyOCR/model')
dst_dir = os.path.join(os.getcwd(), 'easyocr_models', 'model')
os.makedirs(dst_dir, exist_ok=True)

for name in ['craft_mlt_25k.pth', 'latin_g2.pth']:
    src = os.path.join(src_dir, name)
    dst = os.path.join(dst_dir, name)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f'copied {name}')
    else:
        print(f'missing {name}')
