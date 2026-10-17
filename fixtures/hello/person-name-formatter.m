#import <Foundation/Foundation.h>
#include <assert.h>
#include <stdio.h>

int main(void) {
    @autoreleasepool {
        NSPersonNameComponents *n = [NSPersonNameComponents new];
        n.namePrefix = @"Dr."; n.givenName = @"Charles"; n.middleName = @"Robert";
        n.familyName = @"Darwin"; n.nameSuffix = @"FRS"; n.nickname = @"Charlie";
        assert([[NSPersonNameComponentsFormatter localizedStringFromPersonNameComponents:n
            style:NSPersonNameComponentsFormatterStyleDefault options:0] isEqualToString:@"Charles Darwin"]);
        NSPersonNameComponentsFormatter *f = [NSPersonNameComponentsFormatter new];
        f.locale = [[[NSLocale alloc] initWithLocaleIdentifier:@"en_US"] autorelease];
        assert([[f stringFromPersonNameComponents:n] isEqualToString:@"Charles Darwin"]);
        f.style = NSPersonNameComponentsFormatterStyleLong;
        assert([[f stringFromPersonNameComponents:n] isEqualToString:@"Dr. Charles Robert Darwin FRS"]);
        f.style = NSPersonNameComponentsFormatterStyleShort;
        assert([[f stringFromPersonNameComponents:n] isEqualToString:@"Charlie"]);
        f.style = NSPersonNameComponentsFormatterStyleAbbreviated;
        assert([[f stringFromPersonNameComponents:n] isEqualToString:@"CD"]);
        n.givenName = @"e\u0301mile"; n.familyName = @"Darwin";
        assert([[f stringFromPersonNameComponents:n] isEqualToString:@"e\u0301D"]);
        NSPersonNameComponentsFormatter *copy = [f copy]; copy.style = NSPersonNameComponentsFormatterStyleMedium;
        assert(f.style == NSPersonNameComponentsFormatterStyleAbbreviated);
        n.namePrefix = nil; n.middleName = nil; n.nameSuffix = nil; n.familyName = nil;
        copy.style = NSPersonNameComponentsFormatterStyleLong;
        assert([[copy stringFromPersonNameComponents:n] isEqualToString:@"e\u0301mile"]);
        n.givenName = nil;
        assert([[copy stringFromPersonNameComponents:n] isEqualToString:@""]);
        NSPersonNameComponents *phonetic = [NSPersonNameComponents new];
        phonetic.givenName = @"Xiao Ming"; phonetic.familyName = @"Wang"; n.phoneticRepresentation = phonetic;
        copy.phonetic = YES; copy.style = NSPersonNameComponentsFormatterStyleMedium;
        assert([[copy stringFromPersonNameComponents:n] isEqualToString:@"Xiao Ming Wang"]);
        copy.locale = [[[NSLocale alloc] initWithLocaleIdentifier:@"zh_CN"] autorelease];
        BOOL unsupported = NO;
        @try { [copy stringFromPersonNameComponents:n]; }
        @catch(NSException *e) { unsupported = [e.name isEqualToString:NSInvalidArgumentException]; }
        assert(unsupported);
        unsupported = NO;
        @try { [f annotatedStringFromPersonNameComponents:n]; }
        @catch(NSException *e) { unsupported = [e.name isEqualToString:NSInvalidArgumentException]; }
        assert(unsupported);
        [phonetic release]; [copy release]; [f release]; [n release];
        puts("PERSON_NAME_FORMATTER_SELECTED_ENGLISH_STYLES_COPY_PHONETIC_GRAPHEME_AND_UNSUPPORTED_REJECTION_OK");
    }
}
