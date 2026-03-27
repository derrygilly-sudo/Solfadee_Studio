import os, shutil

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

KEEP_FILES = [
    'tonic_solfa_studio_v5.py',
    'requirements.txt',
    'README.md'
]

def ensure_clean_dist():
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    os.makedirs(DIST_DIR)

def copy_files():
    for fname in KEEP_FILES:
        src = os.path.join(BASE_DIR, fname)
        if os.path.exists(src):
            shutil.copy(src, DIST_DIR)
    if os.path.exists(TEMPLATE_DIR):
        shutil.copytree(TEMPLATE_DIR, os.path.join(DIST_DIR, 'templates'))

if __name__ == '__main__':
    print('Preparing minimal distribution package...')
    ensure_clean_dist()
    copy_files()
    print('Minimal dist package created at', DIST_DIR)
    print('Contents:', os.listdir(DIST_DIR))
