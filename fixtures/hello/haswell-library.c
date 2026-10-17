#include <immintrin.h>
void haswell_add_seven(const int *input,int *output) {
    __m256i values=_mm256_loadu_si256((const __m256i *)input);
    values=_mm256_add_epi32(values,_mm256_set1_epi32(7));
    _mm256_storeu_si256((__m256i *)output,values);
}
