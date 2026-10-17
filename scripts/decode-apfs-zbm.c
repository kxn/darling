// APFS decmpfs algorithm 14: resource-fork offset table, 64 KiB blocks.
// Layout follows sgan81/apfs-fuse ApfsLib/Decmpfs.cpp; codec is libzbitmap.
#define _GNU_SOURCE
#include <endian.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include "libzbitmap.h"

static void fail(const char *message) { fprintf(stderr,"%s\n",message);exit(1); }
int main(int argc,char **argv) {
    if(argc!=4)return 2;
    FILE *meta=fopen(argv[1],"rb");if(!meta)fail("Cannot open decmpfs attribute");
    uint32_t header[4];
    if(fread(header,1,16,meta)!=16)fail("Truncated decmpfs attribute");fclose(meta);
    if(le32toh(header[0])!=0x636d7066 || le32toh(header[1])!=14)fail("Expected decmpfs ZBM resource fork");
    uint64_t size=(uint64_t)le32toh(header[2])|((uint64_t)le32toh(header[3])<<32);
    if(!size || size>2ULL*1024*1024*1024)fail("Unexpected cache file size");
    int fd=open(argv[2],O_RDONLY);struct stat st;
    if(fd<0 || fstat(fd,&st)!=0 || st.st_size<4)fail("Cannot read resource fork");
    const unsigned char *resource=mmap(NULL,st.st_size,PROT_READ,MAP_PRIVATE,fd,0);
    if(resource==MAP_FAILED)fail("Resource fork mmap failed");
    uint64_t count=(size+65535)/65536;
    if((count+1)*4>(uint64_t)st.st_size)fail("Offset table outside resource fork");
    const uint32_t *offsets=(const uint32_t *)resource;
    if(le32toh(offsets[0])<(count+1)*4)fail("Offset table overlaps compressed data");
    FILE *output=fopen(argv[3],"wb");if(!output)fail("Cannot create output");
    unsigned char decoded[65536];uint64_t written=0;
    for(uint64_t i=0;i<count;++i) {
        uint64_t start=le32toh(offsets[i]),end=le32toh(offsets[i+1]);
        if(start>=end || end>(uint64_t)st.st_size || end-start>65537)fail("Invalid resource fork block range");
        size_t expected=size-written>65536?65536:(size_t)(size-written),actual=0;
        if(resource[start]==0xff) {
            actual=end-start-1;if(actual>sizeof(decoded))fail("Oversized uncompressed block");
            memcpy(decoded,resource+start+1,actual);
        } else if(zbm_decompress(decoded,sizeof(decoded),resource+start,end-start,&actual)!=0)fail("Invalid LZBITMAP block");
        if(actual!=expected)fail("Decoded block has incorrect length");
        if(fwrite(decoded,1,actual,output)!=actual)fail("Output write failed");written+=actual;
    }
    if(fclose(output)!=0)fail("Output close failed");
    munmap((void *)resource,st.st_size);close(fd);
    printf("Decoded %llu bytes in %llu blocks\n",(unsigned long long)written,(unsigned long long)count);
    return 0;
}
