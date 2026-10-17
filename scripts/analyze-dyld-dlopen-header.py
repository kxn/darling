#!/usr/bin/env python3
"""Pin the real source contract for the next missing loader SPI."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,subprocess
root=Path(__file__).resolve().parent.parent
config=json.loads((root/'config/dyld-cache-introspection.json').read_text())
modern=root/'vendor/apple-dyld';legacy=root/config['legacy_backend']['root']
for repo,expected in [(modern,config['source_commit']),(legacy,config['legacy_backend']['commit'])]:
    assert subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()==expected
def function(repo,relative,signature):
    path=repo/relative;data=path.read_bytes()
    assert data==subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+relative])
    text=data.decode();match=re.search(re.escape(signature)+r'\s*\{',text);assert match
    begin=match.start();start=text.index('{',begin);depth=1;cursor=start+1
    while depth:
        if text[cursor]=='{':depth+=1
        elif text[cursor]=='}':depth-=1
        cursor+=1
    body=text[begin:cursor]
    return dict(path=str(path.relative_to(root)),file_sha256=hashlib.sha256(data).hexdigest(),
        function_sha256=hashlib.sha256(body.encode()).hexdigest(),line=text[:begin].count('\n')+1,body=body)
api=function(modern,'dyld/DyldAPIs.cpp','const mach_header* APIs::_dyld_get_dlopen_image_header(void* handle)')
assert 'RTLD_SELF' in api['body'] and 'RTLD_MAIN_ONLY' in api['body'] and '!validLoader(ldr)' in api['body']
validation=function(legacy,'src/dyldAPIs.cpp','inline ImageLoader* NSModuleToImageLoader(NSModule module)')
assert 'dyld::validImage(image)' in validation['body']
lookup=function(legacy,'src/dyldAPIs.cpp','int _dyld_func_lookup(const char* name, void** address)')
shared=legacy/'src/dyldAPIsInLibSystem.cpp'
baseline_shared=subprocess.check_output(['git','-C',str(legacy),'show','HEAD:src/dyldAPIsInLibSystem.cpp'],text=True)
assert '_dyld_get_dlopen_image_header' not in baseline_shared
assert '__dyld_get_dlopen_image_header' not in (legacy/'src/dyldAPIs.cpp').read_text()
report=dict(checked_at=datetime.now(timezone.utc).isoformat(),native_execution=False,
    source_implementation_added='_dyld_get_dlopen_image_header' in shared.read_text(),
    current_source_libdyld_SPI_sha256=hashlib.sha256(shared.read_bytes()).hexdigest(),
    actual_execution_report='artifacts/dyld-dlopen-header-source.json',
    source_implementation_form='Complete source libdyld selects the pinned dyld2 loader. Under the shared recursive loader lock it validates the untagged ImageLoader via the existing NSModule registry API and invokes the declared C++ machHeader interface. The main loader binary is not rebuilt; exact source interface and packaged loader hashes are checked by the build and launcher. No path scan, guessed symbol, private-field offset or vtable patch.',
    modern_source_commit=config['source_commit'],
    legacy_source_commit=config['legacy_backend']['commit'],original_API=api,
    existing_legacy_module_validation=validation,existing_legacy_function_lookup=lookup,
    official_reference='https://github.com/apple-oss-distributions/dyld/blob/main/dyld/DyldAPIs.cpp',
    public_signature='const struct mach_header* _dyld_get_dlopen_image_header(void* handle)',
    implementation_requirements=[
        'Use actual loader-registered handles and return that image header, including when its exports are reexported by dependencies.',
        'Preserve the original caller for RTLD_SELF, and return the actual main executable header for RTLD_MAIN_ONLY.',
        'Validate invalid handles without reading arbitrary caller memory; invalid inputs return NULL.',
        'Coordinate with the existing global loader lock and real dlopen/dlclose lifetime; no fabricated handle registry.',
        'Preserve all existing libdyld exports. The source libdyld implementation reuses the existing pinned dyld2 registry and C++ interface; other loader ABIs and dyld3 are not supported by this path.',
        'Verify multiple dlopen references, RTLD_FIRST, reexport-only images, no-export images, caller/main selection, invalid handles and concurrent load/unload on Linux.'
    ],
    pitfalls=['dladdr resolves an address, not an opaque dlopen handle.',
        'Looking up __mh_dylib_header through dlsym can fail or find a dependency header; it is not the required image identity.',
        'A handle-to-path-to-image scan can be ambiguous for modules with duplicate names; do not return another image header.',
        'No private ImageLoader field offset, vtable patch, header guess or success stub was added.'],
    current_xcode_probe='artifacts/quartzcore-native-source-dyld-probe.json')
(root/'artifacts/dyld-dlopen-header-source-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print('Pinned modern ABI, baseline source and new source libdyld registry/C++ implementation; runtime results remain separate')
