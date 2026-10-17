#include <cassert>
#include <charconv>
#include <cinttypes>
#include <cmath>
#include <cfloat>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <system_error>
#ifdef __APPLE__
#include <dlfcn.h>
#ifndef LINUXCODE_LIBCXX_EXPECTED_PROVIDER
#define LINUXCODE_LIBCXX_EXPECTED_PROVIDER "/native-library-stage/libc++.1.dylib"
#endif
#endif

template<class Float,class Bits> static void check(char kind,Bits bits,int mode=0,int precision=-1) {
    Float value;static_assert(sizeof(value)==sizeof(bits));memcpy(&value,&bits,sizeof(value));
    if (!std::isfinite(value))return;
    char storage[1026];memset(storage,0x5a,sizeof(storage));
    std::chars_format formats[]={std::chars_format::general,std::chars_format::scientific,
        std::chars_format::fixed,std::chars_format::hex};
    auto convert=[&](char *first,char *last) {
        if (mode==0)return std::to_chars(first,last,value);
        if (precision<0)return std::to_chars(first,last,value,formats[mode-1]);
        return std::to_chars(first,last,value,formats[mode-1],precision);
    };
    auto result=convert(storage+1,storage+1025);
    assert(result.ec==std::errc{} && result.ptr>storage+1 && result.ptr<storage+1025);
    size_t length=(size_t)(result.ptr-(storage+1));
    assert(storage[0]==0x5a && *result.ptr==0x5a && storage[1025]==0x5a);
    char text[1025];memcpy(text,storage+1,length);text[length]=0;
    char parseText[1030];const char *parse=text;
    if (mode==4) {
        if (text[0]=='-')snprintf(parseText,sizeof(parseText),"-0x%s",text+1);
        else snprintf(parseText,sizeof(parseText),"0x%s",text);
        parse=parseText;
    }
    char *end=nullptr;Float parsed;
    if constexpr(sizeof(Float)==4)parsed=strtof(parse,&end);else parsed=strtod(parse,&end);
    Bits restored;memcpy(&restored,&parsed,sizeof(parsed));
    assert(end==parse+strlen(parse));if (precision<0)assert(restored==bits);
    char exact[1026];memset(exact,0x5a,sizeof(exact));
    auto fit=convert(exact+1,exact+1+length);
    assert(fit.ec==std::errc{} && fit.ptr==exact+1+length && !memcmp(exact+1,text,length));
    assert(exact[0]==0x5a && *fit.ptr==0x5a);
    for (size_t capacity: {size_t(0),length-1}) {
        char shortBuffer[1026];memset(shortBuffer,0x5a,sizeof(shortBuffer));
        auto shortResult=convert(shortBuffer+1,shortBuffer+1+capacity);
        assert(shortResult.ec==std::errc::value_too_large && shortResult.ptr==shortBuffer+1+capacity);
        assert(shortBuffer[0]==0x5a && shortBuffer[1+capacity]==0x5a);
    }
    printf("%c%dP%d %016" PRIx64 " %s\n",kind,mode,precision,(uint64_t)bits,text);
}

int main() {
#ifdef __APPLE__
    Dl_info owner;auto function=static_cast<std::to_chars_result(*)(char*,char*,double)>(&std::to_chars);
    assert(dladdr((void *)function,&owner));
    assert(strstr(owner.dli_fname,LINUXCODE_LIBCXX_EXPECTED_PROVIDER));
#endif
    uint64_t fixed[]={0,UINT64_C(0x8000000000000000),1,UINT64_C(0xfffffffffffff),
        UINT64_C(0x10000000000000),UINT64_C(0x3fb999999999999a),UINT64_C(0x3ff0000000000000),
        UINT64_C(0x7fefffffffffffff),UINT64_C(0xffefffffffffffff),UINT64_C(0x3eb0c6f7a0b5ed8d)};
    for (uint64_t bits:fixed)for (int mode=0;mode<5;mode++)check<double>('D',bits,mode);
    uint64_t state=UINT64_C(0x43c6a7b13290feda);
    for (unsigned i=0;i<4096;i++) {
        state^=state<<13;state^=state>>7;state^=state<<17;
        check<double>('D',state);check<float>('F',(uint32_t)(state>>19));
        if (i<256)for (int mode=1;mode<5;mode++) {
            check<double>('D',state,mode);check<float>('F',(uint32_t)(state>>19),mode);
        }
        if (i<32)for (int mode=1;mode<=3;mode++)for (int precision:{0,1,6,17,100,400}) {
            check<double>('D',state,mode,precision);check<float>('F',(uint32_t)(state>>19),mode,precision);
        }
    }
    // Native Apple Intel libc++ also narrows these overloads to double.
    // Verify that exact observed behavior, without asserting 80-bit precision.
    long double extended[]={1.0L+0x1p-60L,LDBL_MAX,LDBL_MIN,-0.0L,0x1p-16400L};
    for (unsigned i=0;i<sizeof(extended)/sizeof(extended[0]);i++) {
        char actual[1024],expected[1024];
        for (int mode=0;mode<3;mode++) {
            std::to_chars_result a,b;
#ifdef __APPLE__
            if (mode==0)a=std::to_chars(actual,actual+sizeof(actual),extended[i]);
            else if (mode==1)a=std::to_chars(actual,actual+sizeof(actual),extended[i],std::chars_format::scientific);
            else a=std::to_chars(actual,actual+sizeof(actual),extended[i],std::chars_format::scientific,6);
#else
            if (mode==0)a=std::to_chars(actual,actual+sizeof(actual),(double)extended[i]);
            else if (mode==1)a=std::to_chars(actual,actual+sizeof(actual),(double)extended[i],std::chars_format::scientific);
            else a=std::to_chars(actual,actual+sizeof(actual),(double)extended[i],std::chars_format::scientific,6);
#endif
            if (mode==0)b=std::to_chars(expected,expected+sizeof(expected),(double)extended[i]);
            else if (mode==1)b=std::to_chars(expected,expected+sizeof(expected),(double)extended[i],std::chars_format::scientific);
            else b=std::to_chars(expected,expected+sizeof(expected),(double)extended[i],std::chars_format::scientific,6);
            assert(a.ec==std::errc{} && b.ec==std::errc{} && a.ptr-actual==b.ptr-expected);
            assert(!memcmp(actual,expected,(size_t)(a.ptr-actual)));
            printf("L%d %u %.*s\n",mode,i,(int)(a.ptr-actual),actual);
        }
    }
    puts("REAL_LIBCXX_TO_CHARS_FINITE_ROUNDTRIP_EXACT_FIT_SHORT_BUFFER_GUARDS_OK");
    return 0;
}
