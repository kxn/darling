#!/usr/bin/env python3
"""Expose genuine bundled Xcode package payloads inside this Darling prefix."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,fcntl,hashlib,json,os
parser=argparse.ArgumentParser(description=__doc__)
selection=parser.add_mutually_exclusive_group();selection.add_argument('--publish-prefix',action='store_true');selection.add_argument('--unpublish-prefix',action='store_true');args=parser.parse_args()
root=Path(__file__).resolve().parent.parent
payload=root/'runtime/xcode-system-resources'
package='runtime/xcode-extract/Xcode.app/Contents/Resources/Packages/XcodeSystemResources.pkg'
digest=lambda n:hashlib.sha256((root/n).read_bytes()).hexdigest()
extraction=json.loads((root/'artifacts/xcode-system-resources-extraction.json').read_text())
assert extraction['member']=='Payload' and extraction['content_sha1']=='3c7861e60d82e641ad4c653524cd0aad768dd8b1'
prefix=root/'runtime/state/prefix';selections=[]
developer=payload/'Library/Developer'
for child in sorted(developer.iterdir()):
    selections.extend(sorted(child.iterdir()) if child.name=='PrivateFrameworks' else [child])
links={str((prefix/child.relative_to(payload)).relative_to(root)):'/Volumes/SystemRoot/workspace/'+str(child.relative_to(root)) for child in selections}
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    if args.publish_prefix or args.unpublish_prefix:
        for name,target in links.items():
            path=root/name
            assert not path.exists() and (not path.is_symlink() or os.readlink(path)==target),name
        for name,target in links.items():
            path=root/name
            if args.unpublish_prefix:
                if path.is_symlink():path.unlink()
            else:
                path.parent.mkdir(parents=True,exist_ok=True)
                if not path.is_symlink():path.symlink_to(target,target_is_directory=True)
published=all((root/name).is_symlink() and os.readlink(root/name)==target for name,target in links.items())
files={str(path.relative_to(root)):digest(str(path.relative_to(root))) for path in sorted(payload.rglob('*')) if path.is_file() and not path.is_symlink()}
symlinks={str(path.relative_to(root)):os.readlink(path) for path in sorted(payload.rglob('*')) if path.is_symlink()}
record={'checked_at':datetime.now(timezone.utc).isoformat(),'package':package,'package_sha256':digest(package),'extraction':extraction,'prefix_links':links,'prefix_links_published':published,'payload_files':files,'payload_symlinks':symlinks,'postinstall_script':'runtime/xcode-system-resources-package-scripts/postinstall_actions/XcodeSystemResources_postinstall.sh','postinstall_script_sha256':digest('runtime/xcode-system-resources-package-scripts/postinstall_actions/XcodeSystemResources_postinstall.sh'),'postinstall_executed':False,'installer_receipts_created':False,'run_first_launch_completed':False,'scope':'Original XcodeSystemResources.pkg payload staging. Publishing to the task prefix is explicit and reversible; default staging does not publish. No script/receipt/state success is synthesized. Original postinstall calls devicectl to update device images; it has not run. No host system library is changed.'}
target=root/'artifacts/xcode-system-resources-stage.json';pending=target.with_suffix('.pending');pending.write_text(json.dumps(record,indent=2)+'\n');pending.replace(target)
print('Staged original package payload:',len(files),'files; prefix links published:',published)
