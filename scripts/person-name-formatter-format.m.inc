// Local public-API adaptations to the pinned GNUstep formatter. Full locale
// rules and annotated-name output are deliberately outside this implementation.
- (NSLocale *)locale { return _linuxcodeLocale ?: [NSLocale autoupdatingCurrentLocale]; }
- (void)setLocale:(NSLocale *)locale {
    NSLocale *copy = [locale copy]; [_linuxcodeLocale release]; _linuxcodeLocale = copy;
}
- (void)dealloc { [_linuxcodeLocale release]; [super dealloc]; }
- (id)copyWithZone:(NSZone *)zone {
    NSPersonNameComponentsFormatter *copy = [[[self class] allocWithZone:zone] init];
    copy->_style = _style; copy->_phonetic = _phonetic; copy->_nameOptions = _nameOptions;
    copy.locale = self.locale;
    return copy;
}
- (NSString *)stringFromPersonNameComponents:(NSPersonNameComponents *)components {
    if (![components isKindOfClass:[NSPersonNameComponents class]])
        [NSException raise:NSInvalidArgumentException format:@"Expected person-name components"];
    NSString *language = [self.locale objectForKey:NSLocaleLanguageCode];
    // An empty ICU identifier represents the invariant root locale. Darling's
    // current-locale preferences can select that locale even with LANG set.
    BOOL invariant = self.locale.localeIdentifier.length == 0 || [self.locale.localeIdentifier isEqualToString:@"root"];
    if (!invariant && ![language isEqualToString:@"en"])
        [NSException raise:NSInvalidArgumentException format:@"Person-name locale %@ (language %@) is not supported by this compatibility implementation", self.locale.localeIdentifier, language];
    if (_nameOptions & ~NSPersonNameComponentsFormatterPhonetic)
        [NSException raise:NSInvalidArgumentException format:@"Unsupported person-name formatting option"];
    if (_phonetic || (_nameOptions & NSPersonNameComponentsFormatterPhonetic)) {
        components = components.phoneticRepresentation;
        if (!components)
            [NSException raise:NSInvalidArgumentException format:@"Phonetic components are required"];
    }
    NSMutableArray *parts = [NSMutableArray array];
    switch (_style) {
        case NSPersonNameComponentsFormatterStyleDefault:
        case NSPersonNameComponentsFormatterStyleMedium:
            if (components.givenName.length) [parts addObject:components.givenName];
            if (components.familyName.length) [parts addObject:components.familyName];
            break;
        case NSPersonNameComponentsFormatterStyleShort: {
            NSString *shortName = components.nickname.length ? components.nickname :
                (components.givenName.length ? components.givenName : components.familyName);
            if (shortName.length) [parts addObject:shortName];
            break;
        }
        case NSPersonNameComponentsFormatterStyleLong: {
            NSString *fields[] = {components.namePrefix, components.givenName, components.middleName,
                                  components.familyName, components.nameSuffix};
            for (unsigned i = 0; i < 5; ++i) if (fields[i].length) [parts addObject:fields[i]];
            break;
        }
        case NSPersonNameComponentsFormatterStyleAbbreviated: {
            NSString *fields[] = {components.givenName, components.familyName};
            for (unsigned i = 0; i < 2; ++i) if (fields[i].length)
                [parts addObject:[fields[i] substringWithRange:[fields[i] rangeOfComposedCharacterSequenceAtIndex:0]]];
            return [parts componentsJoinedByString:@""];
        }
        default:
            [NSException raise:NSInvalidArgumentException format:@"Unsupported person-name style"];
    }
    return [parts componentsJoinedByString:@" "];
}
- (NSAttributedString *)annotatedStringFromPersonNameComponents:(NSPersonNameComponents *)components {
    [NSException raise:NSInvalidArgumentException format:@"Person-name component annotations are not implemented"];
    return nil;
}
