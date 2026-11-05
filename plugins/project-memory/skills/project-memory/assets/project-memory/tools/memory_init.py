"""One initializer for packaged and portable entry points. Standard library only."""
import argparse
from datetime import datetime
from pathlib import Path
import sys
from memory_check import git_state, REQUIRED_RELATIVE
from memory_storage import atomic_write, linked

TOOL_NAMES=('init_memory.py','memory_check.py','memory_close.py','memory_backup.py','memory_storage.py', 'memory_archive_sessions.py','memory_init.py')


def initialize(template_root,tool_root,target):
    template_root=Path(template_root).resolve()
    target=Path(target).resolve()
    if not template_root.is_dir() or not (template_root/'memory').is_dir():
        raise ValueError('Hafıza şablonu bulunamadı')
    # Read only neutral templates; never use the source project's live records.
    for relative in REQUIRED_RELATIVE:
        if not relative.startswith('tools/') and not (template_root/relative).is_file():
            raise ValueError('Paket şablonu eksik: '+relative)
    templates=[template_root/name for name in ('AGENTS.md','README.md','.gitignore')]
    templates+=sorted(path for path in (template_root/'memory').rglob('*') if path.is_file())
    source_pairs=[(path,path.relative_to(template_root)) for path in templates]
    source_pairs += [(Path(tool_root)/name,Path('tools')/name) for name in TOOL_NAMES]
    source_pairs += [(path,Path('tools/project_memory_template')/path.relative_to(template_root)) for path in templates]
    replacements={'{{PROJECT_NAME}}':target.name,
                  '{{TIMESTAMP}}':datetime.now().astimezone().isoformat(sep=' ',timespec='seconds'),
                  '{{GIT_STATUS}}':'KONTROL EDİLEMEDİ'}
    plan=[]
    for source,relative in source_pairs:
        if not source.is_file() or linked(source):
            raise ValueError('Paket dosyası eksik veya bağlantılı: '+source.name)
        path=target/relative
        # Preflight the entire plan before creating even one destination file.
        parent=path.parent
        while parent.is_relative_to(target):
            if (parent.exists() or parent.is_symlink()) and (linked(parent) or not parent.is_dir()):
                raise ValueError('Hedef üst yolu uygun değil: '+relative.as_posix())
            if parent==target:break
            parent=parent.parent
        if path.exists() or path.is_symlink():
            raise FileExistsError('Var olan dosyanın üzerine yazılmadı: '+relative.as_posix())
        raw=source.read_bytes()
        rendered=relative.suffix=='.md' and not relative.is_relative_to('tools/project_memory_template')
        content=raw
        if rendered:
            text=raw.decode('utf-8')
            for old,new in replacements.items():text=text.replace(old,new)
            content=text.encode('utf-8')
        plan.append((path,raw,content,rendered))
    for path,raw,content,rendered in plan:
        path.parent.mkdir(parents=True,exist_ok=True)
        # Exclusive creation also refuses a file introduced after preflight.
        with path.open('xb') as stream:stream.write(content)
    replacements['{{GIT_STATUS}}']=git_state(target)
    for path,raw,content,rendered in plan:
        if rendered and '{{GIT_STATUS}}' in raw.decode('utf-8'):
            if linked(path) or path.read_bytes()!=content:
                raise RuntimeError('Başlatma sırasında dosya değişti; üzerine yazılmadı')
            text=raw.decode('utf-8')
            for old,new in replacements.items():text=text.replace(old,new)
            atomic_write(path,text.encode('utf-8'))


def main(template_root,tool_root):
    parser=argparse.ArgumentParser(description='Mevcut belgeleri koruyarak taşınabilir hafıza oluşturur')
    parser.add_argument('target',type=Path)
    args=parser.parse_args()
    try:
        initialize(template_root,tool_root,args.target)
    except (OSError,ValueError,RuntimeError) as error:
        print('HATA: '+str(error),file=sys.stderr)
        return 1
    print('Proje hafızası oluşturuldu: '+str(args.target.resolve()))
    return 0
