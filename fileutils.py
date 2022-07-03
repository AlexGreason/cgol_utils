import os

from .Shinjuku.shinjuku import lt
from .Shinjuku.shinjuku.checks import rewind_check
from .Shinjuku.shinjuku.transcode import decode_comp, realise_comp
from .paths import cgolroot
from .utils import convert_synths_to_sjk
from .utils import get_minpaths, get_improved, \
    get_improved_synths, trueSLs, get_date_string, filter_helper


def write_components(components, outfile, outdir=cgolroot + "/transfer/"):
    with open(outdir + outfile, "w") as out:
        for c in components:
            out.write(c + "\n")


def filter_comps(min_paths, compfile, outfile, filterunseen=True):
    synths = []
    for line in open(compfile, "r"):
        line = line.replace("%", "").replace("\n", "")
        synths.append(line)
    synths = filter_helper(min_paths, synths, filterunseen=filterunseen)
    write_components(synths, outfile, outdir="")


def read_file(compfile):
    synths = []
    for line in open(compfile, "r"):
        line = line.replace("%", "").replace("\n", "")
        synths.append(line)
    return synths


def write_minpaths(min_paths, objects, outfile):
    mins = get_minpaths(min_paths, objects)
    mins = list(mins)
    write_components(mins, outfile, outdir="")


def find_targets(components):
    left = set()
    right = set()
    uses = {}
    for line in open(components, "r"):
        if len(line) < 3:
            continue
        line = line.replace("\n", "")
        input, compcost, output = decode_comp(line)
        left.add(input)
        right.add(output)
        if input not in uses:
            uses[input] = set()
        uses[input].add(output)
    targets = set()
    for x in right:
        if x not in left:
            targets.add(x)
    return targets, uses


def filter_file_validate(file, outfile):
    with open(file, "r") as f, open(outfile, "w") as o:
        for line in f:
            if rewind_check(*realise_comp(line, separate=True)):
                o.write(line)
            else:
                print("removed", line)
    return


def parse_objects_file(fname):
    # format: apgcode, space, other stuff
    res = []
    with open(fname, "r") as Fin:
        for line in Fin:
            vals = line.split(" ")
            res.append(vals[0])
    return res


def get_inputs(compfile, maxpop=9999):
    inputs = set([])
    for line in open(compfile, "r"):
        line = line.replace("%", "").replace("\n", "")
        try:
            input, compcost, output = decode_comp(line)
        except ValueError as e:
            print("failed to decode line (", line, ") due to", e)
            continue
        pop = lt.pattern(input).population
        if pop <= maxpop:
            inputs.add(input)
    print(compfile, f"contained {len(inputs)} stills")
    return list(inputs)


def get_all_prev(n, maxpop=9999, lookingfor="none"):
    prevstills = set([])
    for i in range(n):
        path = f"{cgolroot}/transfer/specialrequest_{i}.sjk"
        if os.path.isfile(path):
            tmp = get_inputs(path, maxpop=maxpop)
            if lookingfor in tmp:
                print(f"found {lookingfor} in {path}")
            for code in tmp:
                prevstills.add(code)

    print(f"{len(prevstills)} total past stills")
    return prevstills


def get_outputs(compfile, maxpop=9999):
    outputs = set([])
    for line in open(compfile, "r"):
        line = line.replace("%", "").replace("\n", "")
        input, compcost, output = decode_comp(line)
        pop = lt.pattern(output).population
        if pop <= maxpop:
            outputs.add(output)
    print(compfile, f"contained {len(outputs)} stills")
    return list(outputs)


def write_improved_synths(min_paths, redundancies=True, forcecheck=None, nthreads=24):
    cheaper, catagolue_costs = get_improved(min_paths, trueSLs, forcecheck=forcecheck)
    synths = get_improved_synths(min_paths, cheaper, catagolue_costs, redundancies=redundancies)
    synths = convert_synths_to_sjk(synths, nthreads=nthreads)
    write_components(synths, f"improvedsynths-{get_date_string(True, True, True, True, True, True)}.sjk")

