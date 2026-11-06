# Experiment 4: Cache Coherence (MSI, MESI, MOESI) and NUMA Memory Access Performance


A hands-on study of how cache coherence protocols keep multi-core caches consistent, and how **false sharing** and **NUMA memory placement** affect performance. One simple example is used throughout: **two threads, each incrementing its own counter**, with the two counters placed either on the **same cache line** (adjacent) or on **separate cache lines** (padded).

---

## Table of Contents

1. [Objective](#1-objective)
2. [Software Requirements](#2-software-requirements)
3. [Theory](#3-theory)
4. [Installation and Setup](#4-installation-and-setup)
5. [Repository Structure](#5-repository-structure)
6. [Programs and Compilation](#6-programs-and-compilation)
7. [Comparison Program](#7-comparison-program-scalability--execution-time)
8. [Results](#8-results)
9. [Observation](#9-observation)
10. [Conclusion](#10-conclusion)
11. [Appendix A: coherence_sim.py](#appendix-a-coherence_simpy)

---

## 1. Objective

To study how cache coherence protocols (**MSI**, **MESI** and **MOESI**) keep the caches of a multi-core processor consistent, and to evaluate the performance effect of:

- **Coherence traffic** (false sharing), and
- **NUMA memory placement** (local vs remote memory).

The experiment measures **correctness**, **execution time** and **scalability** as the number of threads increases.

---

## 2. Software Requirements

| S.No. | Software / Tool | Purpose |
|:-----:|-----------------|---------|
| 1 | VMware Workstation Pro | Virtualization software to host the Ubuntu guest OS |
| 2 | Ubuntu 22.04 LTS | Guest operating system used for compiling and running the programs |
| 3 | GCC Compiler (`build-essential`) | Compiles the C programs |
| 4 | OpenMP (`libgomp`, bundled with GCC) | Provides `#pragma omp` directives for parallel regions and timing (`omp_get_wtime`) |
| 5 | `numactl` and `hwloc` | Shows NUMA topology and binds threads and memory to a node (`numactl --cpunodebind`, `--membind`) |
| 6 | Python 3 | Runs the MSI / MESI / MOESI protocol simulator |
| 7 | Ubuntu Terminal | To compile and execute all programs and record timing results |

---

## 3. Theory

- **Cache coherence:** every core has a private cache, so a write by one core can leave stale copies in the others. A coherence protocol (snooping the shared bus) guarantees all cores see one consistent value per memory location.
- **Cache line and false sharing:** coherence is tracked per **cache line** (typically 64 bytes), not per variable. Two threads writing different variables on the **same line** keep invalidating each other's copy, so the line ping-pongs between cores. Results stay correct but performance and scalability drop. Fix: **padding/alignment** so each thread's data has its own line.
- **Protocols:**
  - **MSI**: states Modified, Shared, Invalid. A private line still needs a bus upgrade before its first write.
  - **MESI**: adds **Exclusive** (only copy, clean), so a first write to private data is a silent E to M with no bus transaction.
  - **MOESI**: adds **Owned** (dirty, shared); the owner supplies data cache to cache, so no write-back to memory is needed.
  - Intel uses a MESI variant (MESIF) and AMD a MOESI variant, so real hardware cannot be switched between protocols. A **simulator** is used for the comparison.
- **NUMA:** memory is split between nodes (usually one per socket). Local access is faster than remote access across the interconnect. Linux uses **first-touch** placement; `numactl --cpunodebind=N --membind=N` overrides it. On a single-socket PC (even with virtual NUMA nodes in VMware) little or no local/remote difference is expected.
- **Expected outcome:** all protocols are correct and differ only in bus traffic. Adjacent counters should scale poorly; padded counters should scale well.

| State | Meaning | Memory up to date? | Other caches may hold it? |
|-------|---------|--------------------|---------------------------|
| **M** (Modified) | Only valid copy, dirty | No | No |
| **O** (Owned, MOESI only) | Dirty, owner supplies data | No | Yes (as S) |
| **E** (Exclusive, MESI and MOESI) | Only copy, clean | Yes | No |
| **S** (Shared) | Clean copy, possibly several | Yes (or owner holds newer) | Yes |
| **I** (Invalid) | Not valid | - | - |

---

## 4. Installation and Setup

### 4.1 Create the Virtual Machine

1. Install **VMware Workstation Pro** (from the official Broadcom/VMware site).
2. Create a new VM (Typical) from the **Ubuntu 22.04 LTS** ISO with **4 CPU cores (2 processors x 2 cores)**, **4 GB RAM** and 20 GB+ disk. Multiple cores are needed to see coherence and scalability effects.
3. Install Ubuntu ("Erase disk and install Ubuntu" only affects the virtual disk), then power the VM off.

### 4.2 Expose Two Virtual NUMA Nodes (VMware)

With the VM powered off, add or edit these lines in its `.vmx` file, save, and power the VM on:

```ini
numvcpus = "4"
cpuid.coresPerSocket = "2"
numa.vcpu.min = "2"
numa.vcpu.maxPerVirtualNode = "2"
```

### 4.3 Install Tools and Verify

```bash
sudo apt update
sudo apt install build-essential numactl hwloc python3 -y


# verify GCC and OpenMP
gcc --version
echo '#include <omp.h>' | gcc -E -fopenmp -xc - > /dev/null && echo OpenMP OK


# verify CPU layout and NUMA nodes (note which CPUs belong to node 0 and node 1)
lscpu | grep -E "Socket|Core|Thread|NUMA"
numactl --hardware
lscpu -e

```
<img width="1277" height="807" alt="WhatsApp Image 2026-11-06 at 10 55 11 AM" src="https://github.com/user-attachments/assets/1afeb828-0e94-420a-98e1-930b579bc4e3" />
<img width="1219" height="767" alt="build-essentials" src="https://github.com/user-attachments/assets/b7c6d514-10d7-454d-9860-61165f7ca064" />

<img width="1213" height="767" alt="check installation" src="https://github.com/user-attachments/assets/d9f47556-9211-4172-9df0-eba7795e950c" />



---

## 5. Repository Structure

```text
.
├── README.md
├── coherence_sim.py        
├── false_sharing.c         
├── numa_sweep.c            
├── compare_numa.c          
└── images/                 
```

---

## 6. Programs and Compilation

Each program demonstrates one part of the example. Program 1 compares the three coherence protocols using the two-counter trace. Programs 2 and 3 measure false sharing and NUMA memory access on the real machine.

### 6.1 Program 1: Protocol Simulator (MSI, MESI, MOESI)

The simulator models two cores and runs this trace many times: **core 0 reads and writes `x`, then core 1 reads and writes `y`**. With the *adjacent* layout `x` and `y` share cache line A; with the *padded* layout they use lines A and B. It prints the line states after each operation and counts bus transactions, write-backs to memory and cache-to-cache transfers. 

**Run:**

```bash
python3 coherence_sim.py 1000
```


<img width="1214" height="762" alt="coherence_sim" src="https://github.com/user-attachments/assets/bf095f1f-f358-4e93-ba76-2a2605463174" />
<img width="1275" height="684" alt="moesi" src="https://github.com/user-attachments/assets/6deabf0d-7ebd-4ef4-a3a7-d21e72123095" />


### 6.2 Program 2: False Sharing (Adjacent vs Padded)

**`false_sharing.c`**

```c
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
 for (long i = 0; i < N / nt; i++) (*p)++; /* read-modify-write own counter */
 }
 double t = omp_get_wtime() - t0;
 long total = 0;
 for (int i = 0; i < nt; i++) total += cnt[i * stride];
 printf("%s | threads=%d | total=%ld | time=%.4f s\n",
 stride == 1 ? "adjacent" : "padded ", nt, total, t);
 return 0;
}
```

**Compile:**

```bash
gcc -O2 false_sharing.c -fopenmp -o false_sharing
```

**Run** (set the thread count with `OMP_NUM_THREADS`; argument `adjacent` or `padded`):

```bash
OMP_NUM_THREADS=2 ./false_sharing adjacent
OMP_NUM_THREADS=2 ./false_sharing padded
```

<img width="1214" height="550" alt="fale sharing" src="https://github.com/user-attachments/assets/dbb6e780-f562-4ea5-a05e-4be36a491a7c" />


### 6.3 Program 3: NUMA Memory Sweep

**`numa_sweep.c`**

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
int main(int argc, char **argv) {
 size_t mb = argc > 1 ? atol(argv[1]) : 512;
 size_t n = mb << 20;
 char *buf = malloc(n);
 memset(buf, 1, n); /* first touch: pages are placed by the numactl policy */
 long sum = 0;
 double t0 = omp_get_wtime();
 for (int pass = 0; pass < 4; pass++) {
 #pragma omp parallel for reduction(+:sum)
 for (size_t i = 0; i < n; i += 64) /* one read per 64-byte cache line */
 sum += buf[i];
 }
 printf("buffer=%zu MB | threads=%d | sum=%ld | time=%.4f s\n",
 mb, omp_get_max_threads(), sum, omp_get_wtime() - t0);
 return 0;
}
```

**Compile:**

```bash
gcc -O2 numa_sweep.c -fopenmp -o numa_sweep
```

**Run local, then remote** (replace the node numbers with the ones shown by `numactl --hardware`):

```bash
OMP_NUM_THREADS=2 numactl --cpunodebind=0 --membind=0 ./numa_sweep
OMP_NUM_THREADS=2 numactl --cpunodebind=0 --membind=1 ./numa_sweep
```

<img width="1214" height="550" alt="fale sharing" src="https://github.com/user-attachments/assets/8eb27fa8-860b-424c-9263-7a38bd199a36" />


---

## 7. Comparison Program: Scalability & Execution Time

Program 4 combines Programs 2 and 3 in one benchmark.

- **Table 1** repeats the same 100,000,000-increment workload for the adjacent and padded layouts with 1, 2 and 4 threads, checking the final total against the expected value.
- **Table 2** times the 512 MB memory sweep with 1 and 2 threads.



**`compare_numa.c`**

```c
/* compare_numa.c
 * Table 1: two-counter example, adjacent vs padded layout, 1/2/4 threads.
 * Table 2: memory sweep of a 512 MB buffer, 1/2 threads (run under numactl).
 * Compile: gcc -O2 compare_numa.c -fopenmp -o compare_numa
 * Run : ./compare_numa
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>
#define N 100000000L
#define MB 512UL
double run_counters(int nt, int stride, long *total) {
 size_t bytes = ((size_t)nt * stride * sizeof(long) + 63) / 64 * 64;
 long *cnt = aligned_alloc(64, bytes);
 memset(cnt, 0, bytes);
 omp_set_num_threads(nt);
 double t0 = omp_get_wtime();
 #pragma omp parallel num_threads(nt)
 {
 volatile long *p = &cnt[omp_get_thread_num() * stride];
 for (long i = 0; i < N / nt; i++) (*p)++;
 }
 double t = omp_get_wtime() - t0;
 *total = 0;
 for (int i = 0; i < nt; i++) *total += cnt[i * stride];
 free(cnt);
 return t;
}
double run_sweep(char *buf, size_t n, int nt) {
 long sum = 0;
 omp_set_num_threads(nt);
 double t0 = omp_get_wtime();
 for (int pass = 0; pass < 4; pass++) {
 #pragma omp parallel for reduction(+:sum)
 for (size_t i = 0; i < n; i += 64) sum += buf[i];
 }
 double t = omp_get_wtime() - t0;
 if (sum == 0) printf("unexpected\n");
 return t;
}
int main(void) {
 int tc[] = {1, 2, 4};
 printf("Table 1: false sharing (%ld increments in total)\n", N);
 printf("Layout | Threads | Final Count | Correctness | Time (s)\n");
 printf("---------------------------------------------------------\n");
 for (int i = 0; i < 3; i++) {
 for (int s = 1; s <= 8; s *= 8) {
 long total;
 double t = run_counters(tc[i], s, &total);
 printf("%-8s | %7d | %11ld | %-11s | %8.4f\n", s == 1 ? "adjacent" : "padded",
 tc[i], total, total == N ? "Correct" : "INCORRECT", t);
 }
 printf("---------------------------------------------------------\n");
 }
 size_t n = MB << 20;
 char *buf = malloc(n);
 memset(buf, 1, n); /* first touch decides the NUMA node */
 printf("\nTable 2: memory sweep of %lu MB (4 passes)\n", MB);
 printf("Threads | Time (s)\n");
 printf("-------------------\n");
 for (int i = 0; i < 2; i++) printf("%7d | %8.4f\n", tc[i], run_sweep(buf, n, tc[i]));
 return 0;
}
```

**Compile:**

```bash
gcc -O2 compare_numa.c -fopenmp -o compare_numa
```

**Run:**

```bash
./compare_numa
```
<img width="1222" height="471" alt="compare numa" src="https://github.com/user-attachments/assets/67b79488-b83c-41fb-b956-d4a7a6176ebd" />
<img width="1214" height="422" alt="compare_numa1" src="https://github.com/user-attachments/assets/5ccc4911-40d6-4c89-bec4-88e306b1b49e" />
<img width="1216" height="414" alt="omp 2 threads" src="https://github.com/user-attachments/assets/ed0fbe10-0b45-4cce-8e6d-b1901b1d303c" />


---

### 8. Results

**Test system:** VMware Ubuntu 22.04 guest, 4 vCPUs, 2 virtual NUMA nodes (from `numactl --hardware`).

| Node | CPUs | Size | Distance to node 0 | Distance to node 1 |
|:----:|:----:|:----:|:------------------:|:------------------:|
| 0 | 0, 1 | 3165 MB | 10 | 20 |
| 1 | 2, 3 | 3274 MB | 20 | 10 |

#### Table 1: False sharing (`compare_numa`, 100,000,000 increments in total)

The final count was `100000000` and the correctness check printed **Correct** in every run. Times are in seconds.

| Layout | Threads | Default placement | Local (`--cpunodebind=0 --membind=0`) | Remote (`--cpunodebind=0 --membind=1`) |
|--------|:-------:|:-----------------:|:-------------------------------------:|:--------------------------------------:|
| adjacent | 1 | 0.0233 | 0.0220 | 0.0223 |
| padded | 1 | 0.0220 | 0.0220 | 0.0215 |
| adjacent | 2 | 0.0142 | 0.0151 | 0.0154 |
| padded | 2 | 0.0111 | 0.0111 | 0.0122 |
| adjacent | 4 | 0.0065 | 0.0155 | 0.0160 |
| padded | 4 | 0.0058 | 0.0132 | 0.0126 |

#### Table 2: Memory sweep of 512 MB (`compare_numa`, 4 passes)

| Placement | 1 thread (s) | 2 threads (s) |
|-----------|:------------:|:-------------:|
| Default | 0.1178 | 0.1061 |
| Local (`--membind=0`) | 0.1138 | 0.1036 |
| Remote (`--membind=1`) | 0.1137 | 0.1101 |

#### Program 2 (`false_sharing`, 2 threads) and Program 3 (`numa_sweep`)

| Program | Configuration | Time (s) |
|---------|---------------|:--------:|
| Program 2 | adjacent, 2 threads | 0.0146 |
| Program 2 | padded, 2 threads | 0.0130 |
| Program 3 | local, 1 thread (single run) | 0.1083 |
| Program 3 | remote, 1 thread (single run) | 0.1062 |
| Program 3 | local, 2 threads (single run) | 0.0998 |
| Program 3 | remote, 2 threads (single run) | 0.0970 |

#### Program 3: three repeated runs per configuration

| Configuration | Run 1 | Run 2 | Run 3 | Median (s) |
|---------------|:-----:|:-----:|:-----:|:----------:|
| Local, 1 thread | 0.1756 | 0.1570 | 0.1586 | **0.1586** |
| Local, 2 threads | 0.1055 | 0.1120 | 0.1199 | **0.1120** |
| Remote, 1 thread | 0.1100 | 0.1529 | 0.1109 | **0.1109** |
| Remote, 2 threads | 0.0983 | 0.1248 | 0.1017 | **0.1017** |

### Results Recorded

| Run | Time (s) |
|-----|:--------:|
| adjacent, 2 threads (Program 2) | 0.0146 |
| padded, 2 threads (Program 2) | 0.0130 |
| Table 2, memory LOCAL (`--membind=0`), 1 thread | 0.1138 |
| Table 2, memory LOCAL (`--membind=0`), 2 threads | 0.1036 |
| Table 2, memory REMOTE (`--membind=1`), 1 thread | 0.1137 |
| Table 2, memory REMOTE (`--membind=1`), 2 threads | 0.1101 |
| adjacent, one thread on each node (optional) | Not run |

**Ratios:**

| Ratio | Measurement | Value |
|-------|-------------|:-----:|
| adjacent / padded (cost of false sharing) | Program 2, 2 threads (0.0146 / 0.0130) | **1.12** |
| | Table 1, 2 threads, default (0.0142 / 0.0111) | 1.28 |
| | Table 1, 4 threads, default (0.0065 / 0.0058) | 1.12 |
| remote / local (cost of NUMA placement) | Table 2, 1 thread (0.1137 / 0.1138) | **1.00** |
| | Table 2, 2 threads (0.1101 / 0.1036) | 1.06 |
| | Program 3, 2 threads, median (0.1017 / 0.1120) | 0.91 |


### 9. Observation

- **Correctness:** every run produced the exact final count of 100,000,000. False sharing and NUMA placement changed only the time, never the result.
- **False sharing:** the padded layout was faster than the adjacent layout in every multi-thread run, by about 1.1x to 1.3x. This is a mild penalty, because the runs last only about 6 to 25 ms and the guest is virtualized.
- **Scalability:** with default placement, padded scaled almost ideally (1.98x on 2 threads, 3.79x on 4). Adjacent scaled less well (1.64x and 3.59x), which is the effect of the cache line moving between cores.
- **Effect of `numactl --cpunodebind=0`:** node 0 owns only CPUs 0 and 1, so the 4-thread runs were squeezed onto 2 CPUs. Their times (0.0132 to 0.0160 s) did not improve over 2 threads, and are much higher than the default-placement 4-thread times (0.0058 to 0.0065 s). This slowdown comes from CPU oversubscription, not from NUMA.
- **NUMA:** remote memory was not slower than local memory. The ratio was 1.00 for 1 thread and 1.06 for 2 threads, and the repeated Program 3 runs (0.098 to 0.176 s) show no consistent local-versus-remote ordering. This agrees with the expectation for a single-socket host: the two virtual nodes are backed by the same physical memory.
- **Memory-bound code:** the 512 MB sweep barely scaled from 1 to 2 threads (0.1178 s to 0.1061 s, about 1.11x), so it is limited by memory bandwidth rather than by compute.
- **Noise:** the repeated runs vary noticeably (for example 0.1570 to 0.1756 s for the same configuration), so small differences should be read with care.

---

## 10. Conclusion

The experiment shows that cache coherence protocols keep multi-core caches **correct**, and that they differ only in the **bus traffic** they generate.

- **Protocols (simulation):** MESI removes the upgrade transaction for private data (padded layout: 2 bus transactions for MESI and MOESI against 4 for MSI). MOESI avoids writing a dirty line back to memory when another core reads it (0 write-backs against 1999 for MSI and MESI in the adjacent layout), because the owner supplies the line cache to cache. With the adjacent layout all three protocols generated about 4000 bus transactions per 1000 iterations, against 2 to 4 with the padded layout.
- **False sharing (measurement):** all runs were correct, but putting two independent counters on one cache line made them slower. The adjacent layout cost about 1.12x to 1.28x more time than the padded layout, and it scaled less well (3.59x against 3.79x on 4 threads). The effect was small in this virtual machine, but its direction matches the theory, and padding each counter to its own 64-byte line removes it.
- **NUMA (measurement):** no remote-memory penalty appeared (remote / local about 1.00 to 1.06). The VM exposes two virtual nodes, but both are backed by the same physical memory of a single-socket machine, so a real local-versus-remote difference needs a multi-socket system. The experiment also showed that binding threads to a node with `--cpunodebind` limits them to that node's CPUs, which hurt the 4-thread runs.
- **Overall:** data layout and thread placement matter as much as the choice of coherence protocol for the scalability of a parallel program. Keep each thread's data on its own cache line, and keep threads and their memory on the same NUMA node.

## Appendix A: coherence_sim.py

```python
#!/usr/bin/env python3
"""Tiny 2-core snooping-cache simulator: MSI vs MESI vs MOESI.
Example workload: two counters x and y. Core 0 does x = x + 1 (read, write),
core 1 does y = y + 1 (read, write). Layout 'adjacent' puts x and y on the
SAME cache line (false sharing); 'padded' puts them on DIFFERENT lines."""
import sys
def make_cores(n=2): return [dict() for _ in range(n)]
def access(proto, caches, core, line, op, st):
    """op is 'R' or 'W'. Updates caches and the stats dict st."""
    me = caches[core]
    s = me.get(line, 'I')
    others = [i for i in range(len(caches)) if i != core]
    holders = [i for i in others if caches[i].get(line, 'I') != 'I']
    if op == 'R':
        if s != 'I':
            return  # read hit
        st['BusRd'] += 1
        new = 'S'
        for i in holders:
            o = caches[i][line]
            if o == 'M':
                if proto == 'MOESI':
                    caches[i][line] = 'O'; st['c2c'] += 1  # owner supplies, no write-back
                else:
                    caches[i][line] = 'S'; st['writeback'] += 1  # flush to memory
            elif o == 'O':
                st['c2c'] += 1  # owner keeps supplying
            elif o == 'E':
                caches[i][line] = 'S'
        if not holders and proto in ('MESI', 'MOESI'):
            new = 'E'
        me[line] = new
    else:  # write
        if s == 'M':
            return  # write hit, no bus traffic
        if s == 'E':
            me[line] = 'M'; st['silent E->M'] += 1  # MESI/MOESI only
            return
        if s in ('S', 'O'):
            st['BusUpgr'] += 1
        else:  # s == 'I'
            st['BusRdX'] += 1
        for i in holders:
            o = caches[i][line]
            if o in ('M', 'O'):
                if proto == 'MOESI': st['c2c'] += 1
                else: st['writeback'] += 1
        for i in holders:
            caches[i][line] = 'I'; st['invalidations'] += 1
        me[line] = 'M'
def run(proto, layout, iters):
    st = dict.fromkeys(['BusRd','BusRdX','BusUpgr','silent E->M','invalidations','writeback','c2c'], 0)
    caches = make_cores()
    lx, ly = ('A', 'A') if layout == 'adjacent' else ('A', 'B')
    trace = []
    for _ in range(iters):
        trace += [(0, lx, 'R'), (0, lx, 'W'), (1, ly, 'R'), (1, ly, 'W')]
    log = []
    for core, line, op in trace:
        access(proto, caches, core, line, op, st)
        log.append((core, line, op, caches[0].get('A','I'), caches[1].get('A','I')))
    st['bus transactions'] = st['BusRd'] + st['BusRdX'] + st['BusUpgr']
    return st, log
if __name__ == '__main__':
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    print("State trace, first 2 iterations, adjacent layout (line A: core0 state / core1 state)")
    for proto in ('MSI', 'MESI', 'MOESI'):
        _, log = run(proto, 'adjacent', 2)
        print(f"\n{proto}:")
        for c, l, o, s0, s1 in log:
            print(f"  core{c} {o} -> C0={s0} C1={s1}")
    print(f"\nTotals for {iters} iterations")
    keys = ['bus transactions','BusRd','BusRdX','BusUpgr','invalidations','writeback','c2c','silent E->M']
    print(f"{'layout':9} {'protocol':6} " + " ".join(f"{k:>16}" for k in keys))
    for layout in ('adjacent', 'padded'):
        for proto in ('MSI', 'MESI', 'MOESI'):
            st, _ = run(proto, layout, iters)
            print(f"{layout:9} {proto:6} " + " ".join(f"{st[k]:>16}" for k in keys))
```

---
