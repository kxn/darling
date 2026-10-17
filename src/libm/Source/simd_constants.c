// Public SIMD constant ABI: three 16-byte columns, including vector padding.
typedef float darling_simd_float3 __attribute__((ext_vector_type(3)));
typedef struct { darling_simd_float3 columns[3]; } darling_simd_float3x3;
_Static_assert(sizeof(darling_simd_float3x3) == 48, "SIMD matrix ABI");
_Static_assert(_Alignof(darling_simd_float3x3) == 16, "SIMD matrix alignment");
const darling_simd_float3x3 matrix_identity_float3x3 = {
    .columns = {{1.0f, 0.0f, 0.0f}, {0.0f, 1.0f, 0.0f}, {0.0f, 0.0f, 1.0f}}
};
