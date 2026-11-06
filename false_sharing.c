#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
#define N 100000000L
int main(int argc, char **argv) {
    int stride = (argc > 1 && argv[1][0] == 'p') ? 8 : 1; /* p = padded: 8 longs = 64 bytes */
    int nt = omp_get_max_threads();
    size_t bytes = ((size_t)nt * stride * sizeof(long) + 63) / 64 * 64;
    long *cnt = aligned_alloc(64, bytes);
    memset(cnt, 0, bytes);
    double t0 = omp_get_wtime();
    #pragma omp parallel
    {
        volatile long *p = &cnt[omp_get_thread_num() * stride];
        for (long i = 0; i < N / nt; i++) (*p)++;      /* read-modify-write own counter */
    }
    double t = omp_get_wtime() - t0;
    long total = 0;
    for (int i = 0; i < nt; i++) total += cnt[i * stride];
    printf("%s | threads=%d | total=%ld | time=%.4f s\n",
           stride == 1 ? "adjacent" : "padded ", nt, total, t);
    return 0;
}
