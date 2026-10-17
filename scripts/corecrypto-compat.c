// Real group-size accessors present in Darling source but absent in its release.
#include <corecrypto/ccdh.h>

cc_size cczp_n(cczp_const_t zp) {
    return CCZP_CONST_T_ZP(zp)->n;
}

size_t ccdh_ccn_size(ccdh_const_gp_t gp) {
    return ccn_sizeof_n(cczp_n(CCDH_CONST_GP_T_ZP(gp)));
}
cc_size ccdh_gp_n(ccdh_const_gp_t gp) {
    return cczp_n(CCDH_CONST_GP_T_ZP(gp));
}
