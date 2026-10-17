import Darwin

let arguments=CommandLine.arguments
guard arguments.count>=6 && (arguments.count-3)%2==0 else { exit(2) }
guard let library=arguments[1].withCString({ dlopen($0,RTLD_LAZY|RTLD_LOCAL) }) else {
    if let error=dlerror() { fputs(error,stderr);fputs("\n",stderr) }
    exit(1)
}
guard let symbol=arguments[2].withCString({ dlsym(library,$0) }) else { exit(3) }
var owner=Dl_info()
guard dladdr(symbol,&owner) != 0,let base=owner.dli_fbase else { exit(4) }
var cases=0
for index in stride(from:3,to:arguments.count,by:2) {
    guard let offset=Int(arguments[index],radix:16) else { exit(5) }
    let hex=Array(arguments[index+1].utf8)
    precondition(hex.count%2==0)
    func nibble(_ byte:UInt8)->UInt8 {
        if byte>=48 && byte<=57 { return byte-48 }
        precondition(byte>=97 && byte<=102)
        return byte-87
    }
    let expected=stride(from:0,to:hex.count,by:2).map { nibble(hex[$0])*16+nibble(hex[$0+1]) }
    // Read the original String value from the actually rebased Apple image.
    let value=UnsafeRawPointer(base.advanced(by:offset)).load(as:String.self)
    precondition(Array(value.utf8)==expected)
    precondition(value==String(decoding:expected,as:UTF8.self))
    var copies=[value,value]
    copies[0].append("!")
    precondition(Array(copies[0].utf8)==expected+[33])
    precondition(Array(copies[1].utf8)==expected && Array(value.utf8)==expected)
    cases+=1
}
print("Validated original literal values: \(cases)")
print("ORIGINAL_APPLEKEYSTORE_SWIFT_LITERAL_VALUES_UTF8_COPY_ON_WRITE_OK")
