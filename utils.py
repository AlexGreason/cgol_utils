import copy
import itertools
from datetime import datetime
import subprocess
import time
import os
from pathlib import Path

import lifelib
import requests
from Shinjuku.shinjuku import lt
from Shinjuku.shinjuku.checks import check_line_worker
from Shinjuku.shinjuku.gliderset import gset
from Shinjuku.shinjuku.transcode import decode_comp, encode_comp, realise_comp
from Shinjuku.shinjuku.search import read_components, dijkstra
import multiprocessing as mp
from cgolutils.paths import cgolroot

min_paths = dijkstra()
overrides = {}
cata_costs = {}
trueSLs = set([])


def cost(apgcode, overrides=overrides):
    if apgcode == "":
        return 0
    if apgcode in overrides:
        return overrides[apgcode]
    if apgcode in min_paths:
        return min_paths[apgcode][0]
    return 9999


def run(command):
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    return output, error


def fetch_if_old(fname, url, maxage=86400):
    if not os.path.isfile(fname) or ((time.time() - os.path.getmtime(fname)) > maxage):
        os.makedirs(Path(fname).parent, exist_ok=True)
        print(f"fetching {url}")
        run(f"curl -o {fname} {url}")


def cached_fetch_contents(baseaddress, url, maxage=28800):
    fname = f"{cgolroot}/censuses/{url.replace('/','-')}.txt"
    fetch_if_old(fname, baseaddress+url, maxage=maxage)
    return open(fname, "r").read()


def fetch_xs_synthesis_costs():
    address = "https://catagolue.appspot.com/textcensus/b3s23/"

    tabs = cached_fetch_contents(address, "synthesis-costs/objcount")

    tabs = [x for x in tabs.split('\n') if ' tabulation ' in x]
    tabs = [x.split(' tabulation ')[-1].strip() for x in tabs]

    knowns = []
    tabs = [x for x in tabs if x.startswith("xs")]
    for t in tabs:
        res = cached_fetch_contents(address, 'synthesis-costs/' + t)
        knowns += [tuple(s.replace('"', '').split(',')) for s in res.split('\n') if ',' in s][1:]

    return knowns


def get_sorted_sls(min_paths, true, cata_costs, printdiffs=False, min_cost=0, max_cost=9999):
    objs = []
    knowns = fetch_xs_synthesis_costs()
    for (apgcode, cost) in knowns:
        if not apgcode.startswith("xs"):
            continue  # not a still life
        if apgcode.startswith("xs0"):
            continue
        cost = int(cost)
        if cost == 999999_999999_999999:
            cost = 9999
        if cost < 100000_000000_000002:  # pseudo
            pass
        else:
            cost -= 100000_000000_000000  # cost according to Cata
            true.add(apgcode)
        cata_costs[apgcode] = cost
        if apgcode not in min_paths:
            if printdiffs:
                print(f"{apgcode} is not in local Shinjuku but in Cata!")
            min_paths[apgcode] = (cost, None, None)
        sjk_cost = min_paths[apgcode][0]
        if sjk_cost != cost:
            if printdiffs:
                print(f"{apgcode} has cost {sjk_cost} by local Shinjuku but {cost} by Cata")
            min_paths[apgcode][0] = min(cost, sjk_cost)
        objs.append((apgcode, cost))
    objs.sort(key=lambda x: x[1])
    objs = [x[0] for x in objs if max_cost >= x[1] >= min_cost]
    return objs


def get_unsynthed_sls():
    objs = []
    r = requests.get("https://catagolue.appspot.com/textcensus/b3s23/synthesis-costs")
    lines = r.content.decode().partition("\n")[2].splitlines()
    llines = len(lines)
    for (k, line) in enumerate(lines, 1):
        apgcode, cost = [x.strip('"') for x in line.split(",")]
        if k % 100 == 0:
            print(f"{k}/{llines} - {line}")
        if not apgcode.startswith("xs"):
            continue  # not a still life
        if apgcode.startswith("xs0"):
            continue
        cost = int(cost)
        if cost != 999999_999999_999999:
            continue  # infinity
        objs.append(apgcode)
    return objs


def get_useful_components(min_paths, max_cost=None):
    if max_cost is None:
        max_cost = 9999
    res = []
    for k, v in min_paths.items():
        if v[2] is None:
            continue
        input, compcost, output = decode_comp(v[2])
        if k.startswith('xs') and output.startswith('xs') and compcost <= max_cost:
            res.append(v[2])
    return res


def get_all_components(max_cost=None):
    if max_cost is None:
        max_cost = 9999
    comps = read_components()
    result = []
    for c in comps:
        input, compcost, output = decode_comp(c)
        if input.startswith('xs') and output.startswith('xs') and compcost <= max_cost:
            result.append(c)
    return result


def objects_minpaths(min_paths, objects):
    synths = set()
    tmp = copy.copy(objects)
    while len(tmp) != 0:
        o = tmp[0]
        tmp.remove(o)
        if o in min_paths:
            synth = min_paths[o][2]
            synths.add(synth)
            if min_paths[o][1] != "":
                tmp.append(min_paths[o][1])
    return list(synths)


def patt_to_code(rle):
    tmp = lt.pattern(rle)
    return tmp.apgcode


def expensive_stills(min_paths, cells=17, cost=17, maxcost=10000, force_true=False):
    result = []
    tocheck = min_paths
    if force_true:
        tocheck = trueSLs
    for code in tocheck:
        if code.startswith(f"xs{cells}_"):
            if maxcost >= min_paths[code][0] >= cost:
                result.append(code)
    return result


def backtrack(apgcode, sofar, used_by, min_paths):
    pred = min_paths[apgcode][1]
    if pred is None:
        return
    sofar.add(apgcode)
    if pred not in used_by:
        used_by[pred] = set([])
    for x in sofar:
        used_by[pred].add(x)
    backtrack(pred, sofar, used_by, min_paths)


def get_uses(min_paths):
    used_by = {}
    i = 0
    for code in min_paths:
        backtrack(code, set([]), used_by, min_paths)
        i += 1
    return used_by


def print_uses(used_by, apgcode):
    if apgcode not in used_by:
        return "no uses"
    uses = used_by[apgcode]
    return f"used by {len(uses)}, first 5 uses: {list(uses)[:5]}"


def get_improved(min_paths, trueSLs, forcecheck=None):
    if forcecheck is None:
        forcecheck = set()
    cheaper = set([])
    knowns = fetch_xs_synthesis_costs()
    catagolue_costs = {}
    for (apgcode, cost) in knowns:
        if apgcode.startswith("xs0"):
            continue
        cost = int(cost)
        if cost == 999999_999999_999999:
            cost = 9999
        if cost < 100000_000000_000002:  # pseudo
            pass
        else:
            cost -= 100000_000000_000000  # cost according to Cata
            trueSLs.add(apgcode)

        if apgcode not in min_paths:
            continue
        sjk_cost = min_paths[apgcode][0]
        catagolue_costs[apgcode] = cost
        if sjk_cost < cost:
            print(f"{apgcode} has cost {sjk_cost} by local Shinjuku but {cost} by Cata")
            cheaper.add(apgcode)
    for apgcode in forcecheck:
        if apgcode not in catagolue_costs and apgcode in min_paths:
            cheaper.add(apgcode)
    return cheaper, catagolue_costs


def get_synth(min_paths, obj):
    if obj not in min_paths:
        print(f"tried to get synth for {obj}, not in min-paths")
        return []
    result = []
    cost, input, comp = min_paths[obj]
    result += [comp]
    if input != '' and input is not None:
        result += get_synth(min_paths, input)
    return result


def get_improved_synths(min_paths, cheaper, catagolue_costs, redundancies=True):
    allobjs = []
    catagolue_costs[""] = 0
    catagolue_costs["xs0_0"] = 0
    for c in cheaper:
        path = get_synth(min_paths, c)
        if redundancies:
            allobjs.append(c)
        for p in path:
            input, compcost, output = decode_comp(p)
            if input not in catagolue_costs or output not in catagolue_costs:
                allobjs.append(output)
            if input in catagolue_costs and output in catagolue_costs \
                    and catagolue_costs[output] - catagolue_costs[input] > compcost:
                allobjs.append(output)
    allobjs = [x for x in allobjs if len(x) > 0]
    comps = []
    for o in allobjs:
        comps.append(min_paths[o][2])
    comps = list(set(comps))
    return comps


def filter_helper(min_paths, synths, filterunseen=True):
    res = set()
    for line in synths:
        input, compcost, output = decode_comp(line)
        if output in min_paths and line == min_paths[output][2]:
            continue
        if cost(input) == 9999 and filterunseen:
            continue
        res.add(line)
    return list(res)


def sort_by_pop(codes):
    codes = list(codes)
    tmp = []
    for code in codes:
        obj = lt.pattern(code)
        pop = obj.population
        tmp.append((code, pop))
    tmp.sort(key=lambda x: x[1])
    tmp = [x[0] for x in tmp]
    return tmp


def trace_forwards(targets, uses, object):
    produces = set()
    if object in targets:
        produces.add(object)
    elif object in uses:
        for o in uses[object]:
            forwards = trace_forwards(targets, uses, o)
            produces = produces.union(forwards)
    return produces


def backtrack_uses(apgcode, sofar, used_by, min_paths):
    pred = min_paths[apgcode][1]
    if pred is None:
        return
    sofar.add(apgcode)
    if pred not in used_by:
        used_by[pred] = set([])
    for x in sofar:
        used_by[pred].add(x)
    backtrack_uses(pred, sofar, used_by, min_paths)


def getuses(min_paths):
    used_by = {}
    i = 0
    for code in min_paths:
        backtrack_uses(code, set([]), used_by, min_paths)
        i += 1
    return used_by


used_by = getuses(min_paths)


def printuses(apgcode):
    if apgcode not in used_by:
        return "no uses"
    uses = used_by[apgcode]
    n = len(list(uses))
    if n > 1:
        nstr = f"first {min(n, 5)} uses"
    else:
        nstr = "only use"
    return f"used by {n}, {nstr}: {sorted(list(uses))[:5]}"


popcache = {}
def getpop(code):
    global popcache
    if code in popcache:
        return popcache[code]
    if code.startswith("xs"):
        head, tail = code.split("_")
        pop = int(head[2:])
    else:
        pop = lt.pattern(code).population
    popcache[code] = pop
    return pop


usecache = {}
def usecount(code, bitlimit=None):
    if bitlimit is None:
        if code not in used_by:
            return 0
        return len(used_by[code])
    global usecache
    if (code, bitlimit) in usecache:
        return usecache[(code, bitlimit)]
    uses = used_by[code]
    res = 0
    for u in uses:
        if getpop(u) <= bitlimit:
            res += 1
    usecache[(code, bitlimit)] = res
    return res


def filter_by_uses(codes, min_uses=0, max_uses=99999):
    res = []
    for x in codes:
        nuses = usecount(x)
        if min_uses <= nuses <= max_uses:
            res.append(x)
    return res


def filter_by_pop(codes, min_pop=0, max_pop=99999):
    res = []
    for x in codes:
        pop = getpop(x)
        if min_pop <= pop <= max_pop:
            res.append(x)
    return res


def get_date_string(year=True, month=True, day=True, hour=False, minute=False, second=False):
    now = datetime.now()
    formatstr = ""
    vals = ["%Y", "%m", "%d", "%H", "%M", "%S"]
    add = [year, month, day, hour, minute, second]
    for i, include in enumerate(add):
        if include:
            formatstr += vals[i]
    return now.strftime(formatstr)


def print_rle(code):
    if isinstance(code, lifelib.pythlib.pattern.Pattern):
        print(code.rle_string())
        return
    print(lt.pattern(code).rle_string())


def escapenewlines(x):
    return x.replace("\n", "\\n")


def unescapenewlines(x):
    return x.replace("\\n", "\n")


allsls = get_sorted_sls(min_paths, trueSLs, cata_costs, printdiffs=False)


def convert_synth_to_sjk_worker(s):
    if ">" in s:
        return s
    else:
        collrle, n_gliders, input, output = s.split(" ")
        collrle = unescapenewlines(collrle)
        return encode_comp(collrle)


def convert_synths_to_sjk(synths, nthreads=8):
    result = set()
    print(f"converting {len(synths)} synths to sjk")
    with mp.Pool(processes=nthreads) as pool:
        for synth in pool.imap_unordered(convert_synth_to_sjk_worker, synths, chunksize=64):
            result.add(synth)
    return result


def get_minpaths(min_paths, objects):
    res = set()
    for o in objects:
        synth = get_synth(min_paths, o)
        for c in synth:
            if c is not None:
                res.add(c)
    return res


def filter_invalid_synths(synths, nthreads=8):
    passedlines = []
    with mp.Pool(processes=nthreads) as pool:
        for (n, passed, line) in pool.imap_unordered(check_line_worker, enumerate(synths, 1), chunksize=64):
            if passed:
                passedlines.append(line)
    return passedlines


def remove_useless_gliders(compstr, maxgliders=6):
    incode, gstr, outcode = compstr.split(">")
    fields, trans_str = gstr.split("@")
    constell, glider_set = realise_comp(compstr, separate=True)
    ngliders = sum(glider_set.ngliders())
    if ngliders > maxgliders:
        print(f"tried to brute-force remove gliders from comp {compstr} with ngliders {ngliders}!")
        return compstr
    glider_set = gset.reconstruct(fields)
    pairs = glider_set.pairs()
    gliders = []
    for i, salvo in enumerate(pairs):
        for glider in salvo:
            gliders.append((i, glider))

    def pairs_str(pairs):
        return "/".join(" ".join(str(n) for n in itertools.chain.from_iterable(direc)) for direc in pairs)

    def reconstruct_compstr(combo):
        salvos = [[], [], [], []]
        for glider in combo:
            salvos[glider[0]].append(glider[1])
        gliderstr = pairs_str(salvos)
        return f"{incode}>{gliderstr}@{trans_str}>{outcode}"

    for n in range(1, ngliders):
        for combo in itertools.combinations(gliders, r=n):
            n, valid, comp = check_line_worker((1, reconstruct_compstr(combo)), do_print=False)
            if valid:
                return comp
    return compstr


def add_costs(codes):
    return [(c, cost(c)) for c in codes]


def mul(iterable):
    res = 1


def listcombs(ngliders, nvals):
    for n in range(nvals**ngliders//mul(range(1, ngliders+1))):
        currnum = nvals
        vals = [0 for i in range(ngliders)]
        for i in range(ngliders):
            j = n % currnum
            n //= currnum
            vals[i] = j
        print(vals)