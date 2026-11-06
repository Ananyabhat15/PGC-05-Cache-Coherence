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
            return                                    # read hit
        st['BusRd'] += 1
        new = 'S'
        for i in holders:
            o = caches[i][line]
            if o == 'M':
                if proto == 'MOESI':
                     caches[i][line] = 'O'; st['c2c'] += 1       # owner supplies, no write-back
                else:
                     caches[i][line] = 'S'; st['writeback'] += 1 # flush to memory
            elif o == 'O':
                st['c2c'] += 1                                    # owner keeps supplying
            elif o == 'E':
                caches[i][line] = 'S'
        if not holders and proto in ('MESI', 'MOESI'):
            new = 'E'
        me[line] = new
    else: # write
        if s == 'M':
            return                                    # write hit, no bus traffic
        if s == 'E':
            me[line] = 'M'; st['silent E->M'] += 1    # MESI/MOESI only
            return
        if s in ('S', 'O'):
            st['BusUpgr'] += 1
        else:                                         # s == 'I'
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
            print(f" core{c} {o} -> C0={s0} C1={s1}")
    print(f"\nTotals for {iters} iterations")
    keys = ['bus transactions','BusRd','BusRdX','BusUpgr','invalidations','writeback','c2c','silent E->M']
    print(f"{'layout':9} {'protocol':6} " + " ".join(f"{k:>16}" for k in keys))
    for layout in ('adjacent', 'padded'):
        for proto in ('MSI', 'MESI', 'MOESI'):
            st, _ = run(proto, layout, iters)
            print(f"{layout:9} {proto:6} " + " ".join(f"{st[k]:>16}" for k in keys))
