#!/usr/bin/env python3
"""Build updated Darling client endpoint and unchanged Apple cloud RPC functions.

This is a separate source component, not a securityd/cloud implementation.
Private compilation namespaces the updated endpoint to coexist with the older
endpoint in the original Security binary. Full Darling builds use normal names.
"""
from pathlib import Path
import fcntl,hashlib,json,re,subprocess
root=Path(__file__).resolve().parent.parent
base=root/'vendor/darling/src/external/security/OSX/sec'
build=root/'runtime/security-cloud-rpc';build.mkdir(exist_ok=True)
inc=build/'include';digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
commit='db15acbe6a7f257a859ad9a3bb86097bfe0679d9'
upstream={}
for name in ['OSX/sec/Security/SecItem.m','OSX/sec/Security/SecItemFetchOutOfBand.m','OSX/sec/ipc/securityd_client.h','OSX/sec/ipc/client_endpoint.m','keychain/headers/SecItemPriv.h']:
    upstream[name]=subprocess.check_output(['git','-C',str(root/'vendor/apple-security'),'show',commit+':'+name]).decode()
def function(text,name):
    match=re.search(r'(?m)^void\s+'+name+r'\s*\(',text);assert match,name
    at=text.index('{',match.start())+1;depth=1
    while depth:
        depth+=(text[at]=='{')-(text[at]=='}');at+=1
    return text[match.start():at]
frontend=(base/'Security/SecItemCloudRPC.m').read_text()
for name in ['SecItemUnsetCurrentItemsAcrossAllDevices','SecItemFetchCurrentItemOutOfBand','SecItemFetchPCSIdentityOutOfBand','SecItemFetchCurrentItemDataAcrossAllDevices']:
    origin=upstream['OSX/sec/Security/SecItem.m' if ('Unset' in name or 'ItemData' in name) else 'OSX/sec/Security/SecItemFetchOutOfBand.m']
    assert function(frontend,name)==function(origin,name),name
for pattern,text,original in [
    (r'@interface SecItemCurrentItemData: NSObject.*?@end',(base/'Security/SecItemCloudRPC.h').read_text(),upstream['keychain/headers/SecItemPriv.h']),
    (r'@interface SecItemCurrentItemData \(\).*?@end\n\n@implementation SecItemCurrentItemData.*?@end',frontend,upstream['OSX/sec/Security/SecItem.m'])]:
    assert re.search(pattern,text,re.S).group(0)==re.search(pattern,original,re.S).group(0)
def put(name,text):
    path=inc/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
header=(base/'ipc/securityd_client.h').read_text()
for name in ['secItemUnsetCurrentItemsAcrossAllDevices','secItemFetchCurrentItemOutOfBand','secItemFetchPCSIdentityByKeyOutOfBand','secItemFetchCurrentItemAcrossAllDevices']:
    pattern=r'(?m)^-\s*\(void\)\s*'+name+r':.*?;'
    assert re.search(pattern,header,re.S).group(0)==re.search(pattern,upstream['OSX/sec/ipc/securityd_client.h'],re.S).group(0)
# Preserve the entire source protocol and client/callback declarations.
protocol=header[header.index('@class CKKSCurrentItemQuery'):header.index('#endif // OBJC')]
struct=header[header.index('struct securityd {'):header.index('extern struct securityd *gSecurityd;')]
assert struct.count('(*')==81 and struct.count('CFTypeRef secd_xpc_server;')==1
native=root/'runtime/mdns-native/frameworks/Security.framework/Versions/A/Security'
disassembly=subprocess.check_output(['llvm-objdump-19','-d','--disassemble-symbols=_SecuritydXPCProxyObject',str(native)],text=True)
assert '0x288(%rax)' in disassembly and '<_gSecurityd>' in disassembly
exports=subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(native)],text=True)
assert '_gSecurityd' in exports and '_OBJC_CLASS_$_SecXPCHelper' in exports
# A standalone ABI declaration for the actual existing gSecurityd, not a new
# global or local backend. All preceding 81 fields are function pointers.
put('ipc/securityd_client.h', '#pragma once\n#import <Foundation/Foundation.h>\n#import <dispatch/dispatch.h>\n#import <CoreFoundation/CoreFoundation.h>\n#include <stddef.h>\n'
    'typedef void (^SecBoolNSErrorCallback)(bool,NSError *);\n'
    '#define kSecuritydGeneralServiceName "com.apple.securityd.general"\n'
    'struct securityd { void (*prior_callbacks[81])(void); CFTypeRef secd_xpc_server; };\n'
    '_Static_assert(offsetof(struct securityd,secd_xpc_server)==0x288,"native securityd ABI");\n'
    'extern struct securityd *gSecurityd;\n'+protocol)
put('Foundation/NSXPCConnection_Private.h', '#pragma once\n// The compiled endpoint uses only public NSXPCConnection methods.\n')
put('utilities/debugging.h', '#pragma once\n#import <Foundation/Foundation.h>\n#define secerror(format,...) NSLog(@format, ##__VA_ARGS__)\n')
put('Security/SecXPCHelper.h', (root/'vendor/darling/src/external/security/OSX/utilities/SecXPCHelper.h').read_text())
sdk=root/'runtime/state/prefix/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
names=['SecuritydXPCClient','SecuritydXPCCallback','SecuritydXPCProtocol','SecuritydXPCCallbackProtocol','SecuritydXPCProxyObject']
flags=['-D'+name+'=DarlingModern'+name for name in names]
flags+=['-DSecItemFetchCurrentItemAcrossAllDevices=DarlingModernSecItemFetchCurrentItemAcrossAllDevices']
legacy=build/'legacy-api.m'
legacy.write_text('#import "SecItemCloudRPC.h"\n#import <ipc/securityd_client.h>\n#import <os/activity.h>\n'+function((base/'Security/SecItem.m').read_text(),'SecItemFetchCurrentItemAcrossAllDevices')+'\n')
sources=[base/'ipc/client_endpoint.m',base/'Security/SecItemCloudRPC.m',legacy]
objects=[]
for source in sources:
    obj=build/(source.stem+'.o');objects.append(str(obj))
    subprocess.run(['clang-19','-target','x86_64-apple-macos11','-isysroot',str(sdk),'-I'+str(inc),'-I'+str(base/'Security'),'-DOCTAGON=0',*flags,'-fobjc-arc','-O2','-c',str(source),'-o',str(obj)],check=True)
library=build/'libDarlingSecurityCloudRPC.dylib';pending=library.with_suffix('.pending')
subprocess.run(['ld64.lld-19','-dylib','-arch','x86_64','-platform_version','macos','11','11','-syslibroot',str(sdk),'-F'+str(native.parents[3]),'-framework','Security','-framework','Foundation','-framework','CoreFoundation','-L'+str(root/'runtime/security-out-of-band-values'),'-lDarlingSecurityOutOfBandValues','-lobjc','-lSystem','-install_name','/usr/lib/libDarlingSecurityCloudRPC.dylib',*objects,'-o',str(pending)],check=True)
with (root/'runtime/session.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);pending.replace(library)
exports=re.findall(r'^0x[0-9A-Fa-f]+\s+(\S+)',subprocess.check_output(['llvm-objdump-19','--macho','--exports-trie',str(library)],text=True),re.M)
sources += [base/'Security/SecItemCloudRPC.h',base/'Security/SecItem.m',base/'ipc/server_xpc.m',base/'ipc/securityd_client.h',base.parent/'CMakeLists.txt',base.parents[1]/'Security.exp-in']
report={'library':str(library.relative_to(root)),'library_sha256':digest(library),'sources':{str(p.relative_to(root)):digest(p) for p in sources},'upstream_commit':commit,'upstream_source_sha256':{n:hashlib.sha256(s.encode()).hexdigest() for n,s in upstream.items()},'three_upstream_function_bodies_unchanged':True,'three_upstream_protocol_declarations_unchanged':True,'four_upstream_function_bodies_unchanged':True,'modern_current_item_protocol_matches_upstream':True,'result_class_matches_upstream':True,'generated_headers':{str(p.relative_to(root)):digest(p) for p in inc.rglob('*') if p.is_file()},'compiler_namespace_flags':flags,'source_client_endpoint_build':True,'OCTAGON_backend_enabled':False,'public_RPCs':['_SecItemUnsetCurrentItemsAcrossAllDevices','_SecItemFetchCurrentItemOutOfBand','_SecItemFetchPCSIdentityOutOfBand','_SecItemFetchCurrentItemDataAcrossAllDevices'],'public_value_class_exports':['_OBJC_CLASS_$_SecItemCurrentItemData','_OBJC_METACLASS_$_SecItemCurrentItemData'],'legacy_API_alias':'_DarlingModernSecItemFetchCurrentItemAcrossAllDevices','native_result_layout':json.loads((root/'config/security-current-item-native-layout.json').read_text()),'exports':exports,'native_existing_global':'_gSecurityd','native_secd_xpc_server_offset':648,'native_security_sha256':digest(native),'runtime_execution_verified':False,'cloud_backend_implemented':False,'full_Security_build':False,'full_xcode_build_ready':False}
(root/'artifacts/security-cloud-rpc-build.json').write_text(json.dumps(report,indent=2)+'\n')
print('Built source client endpoint and four actual Apple RPC functions plus current-item result class; backend not implemented')
