#import <Foundation/Foundation.h>
#include <assert.h>
#include <stdio.h>

int main(void) {
    @autoreleasepool {
        NSPersonNameComponents *name = [NSPersonNameComponents new];
        assert(name && !name.givenName && !name.familyName && !name.phoneticRepresentation);
        NSMutableString *given = [NSMutableString stringWithString:@"小明"];
        name.givenName = given; name.familyName = @"王"; name.namePrefix = @"Dr.";
        name.middleName = @"Middle"; name.nameSuffix = @"Jr."; name.nickname = @"Ming";
        [given appendString:@"-changed"];
        assert([name.givenName isEqualToString:@"小明"]);
        NSPersonNameComponents *phonetic = [NSPersonNameComponents new]; phonetic.givenName = @"Xiao Ming";
        name.phoneticRepresentation = phonetic; phonetic.givenName = @"changed";
        assert([name.phoneticRepresentation.givenName isEqualToString:@"Xiao Ming"]);
        NSPersonNameComponents *copy = [name copy];
        assert(copy != name && [copy isEqual:name] && [copy hash] == [name hash]);
        copy.phoneticRepresentation.givenName = @"independent";
        assert(![copy isEqual:name] && [name.phoneticRepresentation.givenName isEqualToString:@"Xiao Ming"]);
        assert([NSPersonNameComponents supportsSecureCoding]);
        NSError *error = nil;
        NSData *data = [NSKeyedArchiver archivedDataWithRootObject:name requiringSecureCoding:YES error:&error];
        assert(data && !error);
        NSKeyedUnarchiver *decoder = [[NSKeyedUnarchiver alloc] initForReadingWithData:data];
        decoder.requiresSecureCoding = YES;
        NSPersonNameComponents *roundtrip = [decoder decodeObjectOfClass:[NSPersonNameComponents class] forKey:NSKeyedArchiveRootObjectKey];
        assert(roundtrip && [roundtrip isEqual:name]);
        [decoder finishDecoding];
        assert([[name description] rangeOfString:@"小明"].location != NSNotFound);
        name.givenName = nil; assert(!name.givenName && [roundtrip.givenName isEqualToString:@"小明"]);
        [decoder release]; [copy release]; [phonetic release]; [name release];
        puts("PERSON_NAME_COMPONENTS_COPY_UTF8_PHONETIC_SECURE_ARCHIVE_ROUNDTRIP_OK");
    }
}
