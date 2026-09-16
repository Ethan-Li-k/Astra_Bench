"""Prepare a private RSI data overlay, retaining the verified public archive."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('/home/galbot/lizekai/psi_0_deploy5090/Psi0/third_party/SIMPLE/data')
DEST = ROOT/'data/simple/runtime'
ARCHIVE = ROOT/'data/simple/archives/assets_articulated.zip'
SHA = 'e8e479f6d6d2800f709f443ec022371e04e939aaa8b18f8880ae6e3306f28dd6'
URL = 'https://huggingface.co/datasets/USC-PSI-Lab/SIMPLE/resolve/main/assets_articulated.zip'


def link_existing(source, target):
    target.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        dest = target/path.name
        if not dest.exists() and not dest.is_symlink():
            dest.symlink_to(path, target_is_directory=path.is_dir())
        elif path.is_dir() and dest.is_dir() and not dest.is_symlink():
            link_existing(path, dest)


def main():
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    if not ARCHIVE.exists():
        partial = ARCHIVE.with_suffix('.zip.part')
        with urllib.request.urlopen(URL, timeout=60) as source, partial.open('wb') as dest:
            while chunk := source.read(1024*1024):
                dest.write(chunk)
        if hashlib.sha256(partial.read_bytes()).hexdigest() != SHA:
            raise ValueError('Downloaded archive checksum mismatch; retained partial file')
        partial.rename(ARCHIVE)
    if hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() != SHA:
        raise ValueError('Existing archive checksum mismatch; no overwrite')
    DEST.mkdir(parents=True, exist_ok=True)
    extracted = 0
    with zipfile.ZipFile(ARCHIVE) as archive:
        for info in archive.infolist():
            path = (DEST/info.filename).resolve()
            if DEST.resolve() not in path.parents:
                raise ValueError('Archive member escapes the data overlay')
            if info.is_dir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                content = archive.read(info)
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.exists() and path.read_bytes() != content:
                    raise ValueError(f'Existing extracted file differs: {path}')
                if not path.exists():
                    path.write_bytes(content)
                extracted += 1
    link_existing(SOURCE, DEST)
    required = [DEST/'assets/articulated/003/output_mjcf/003.xml',
                DEST/'assets/articulated/003/output_usd/003.usd']
    result = {'archive': str(ARCHIVE), 'sha256': SHA, 'size_bytes': ARCHIVE.stat().st_size,
              'extracted_files': extracted, 'data_root': str(DEST),
              'door_files': {str(p): p.exists() for p in required},
              'original_environment_modified': False, 'archive_retained': True}
    (ROOT/'artifacts/R018/simple-data-preparation.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
