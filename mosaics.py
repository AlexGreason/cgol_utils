from .Shinjuku.shinjuku import lt
from .Shinjuku.shinjuku.search import dijkstra, lookup_synth
from .Shinjuku.shinjuku.transcode import realise_comp, decode_comp
from .paths import cgolroot
from .utils import min_paths, cost, get_improved, get_improved_synths, trueSLs, objects_minpaths


def improved_synths_mosaic(min_paths, sidelen=50, spacing=200, redundancies=False, forcecheck=None):
    cheaper, catagolue_costs = get_improved(min_paths, trueSLs, forcecheck=forcecheck)
    synths = get_improved_synths(min_paths, cheaper, catagolue_costs, redundancies=redundancies)
    print(f"found {len(synths)} improvements")
    makemosaic_autoscale(synths, sidelen=sidelen, spacing=spacing)


def makemosaic_autoscale(synths, sidelen=50, spacing=200):
    synthmap = {}
    oversized = {}
    maxoversized = 0
    for s in synths:
        synth = realise_comp(s)
        bbox = synth.bounding_box
        input, compcost, output = decode_comp(s)
        if max(bbox[2], bbox[3]) > spacing - 20:
            print("Oversize component! " + str(max(bbox[2]-bbox[0], bbox[3]-bbox[1])), bbox)
            maxoversized = max(maxoversized, max(bbox[2]-bbox[0], bbox[3]-bbox[1]))
            oversized[output] = [0, synth]
            continue
        synthmap[output] = [0, synth]
    makemosaic_helper(synthmap, sidelen=sidelen, spacing=spacing)
    if len(oversized) > 0:
        makemosaic_helper(oversized, sidelen=10000//(maxoversized+30), spacing=maxoversized+20, fileprefix="oversized-mosaic")


def synthlist_to_synthmap(synths, spacing=300):
    synthmap = {}
    for s in synths:
        synth = realise_comp(s)
        bbox = synth.bounding_box
        if max(bbox[2], bbox[3]) > spacing - 20:
            print("Oversize component! " + str(max(bbox[2]-bbox[0], bbox[3]-bbox[1])))
            continue
        input, compcost, output = decode_comp(s)
        synthmap[output] = [0, synth]
    return synthmap


def makemosaic(outfile, sidelen=40, startindex=0, spacing=100):
    synths = {}

    for line in open(outfile, "r"):
        line = line.replace("%", "")
        input, compcost, output = decode_comp(line)
        if output in min_paths and line == min_paths[output][2]:
            continue
        if cost(input) == 9999:
            continue
        synth = realise_comp(line)
        bbox = synth.bounding_box
        if max(bbox[2], bbox[3]) > spacing - 20:
            print("Oversize component! " + str(max(bbox[2], bbox[3])))
            continue
        if output not in synths:
            synths[output] = (9999, synth)
        if cost(input) + compcost < synths[output][0]:
            synths[output] = (cost(input) + compcost, synth)

    nsynths = len(synths)
    print(f"Found {nsynths} synths")

    makemosaic_helper(synths, sidelen=sidelen, startindex=startindex, spacing=spacing)


def makemosaic_helper(synths, sidelen=40, startindex=0, spacing=100, fileprefix="mosaic", directory="mosaics"):
    synthlist = list(synths.keys())
    nsynths = len(synthlist)
    j = 0
    while startindex < len(synthlist):
        mosaic = lt.pattern()
        for i in range(startindex, min(len(synthlist), startindex + sidelen ** 2)):
            synth = synthlist[i]
            xoff = (i % sidelen) * spacing
            yoff = (i // sidelen) * spacing
            mosaic += synths[synth][1](xoff, yoff)
        print(f"wrote synths up to {i}, from {synthlist[startindex]} to {synthlist[i]}")
        mosaic.write_rle(f"{cgolroot}/{directory}/{fileprefix}{nsynths}_{j}.rle")
        startindex += sidelen ** 2
        j += 1


def mosaic_minpaths(min_paths, objects, sidelen=30, spacing=300):
    synths = objects_minpaths(min_paths, objects)
    synthmap = synthlist_to_synthmap(synths, spacing=spacing)
    makemosaic_helper(synthmap, sidelen, spacing)


def makemosaic_apgcodes(codes, sidelen=40, spacing=100, startindex=0, original="xs0_0"):
    filtobjs = []
    if original != "xs0_0":
        startobj = lt.pattern(original)
        for i in range(len(codes)):
            object = lt.pattern(codes[i])
            if startobj.__xor__(object).__and__(startobj).population != 0:
                filtobjs.append(codes[i])
        print(f"{len(filtobjs)} passed filtering out of {len(codes)} initial objects")
        codes = filtobjs
    j = 0
    while startindex < len(codes):
        mosaic = lt.pattern()
        for i in range(startindex, min(len(codes), startindex + sidelen ** 2)):
            code = codes[i]
            print(code)
            xoff = (i % sidelen) * spacing
            yoff = (i // sidelen) * spacing
            object = lt.pattern(code)
            mosaic += object(xoff, yoff)
        print(f"wrote objects up to {i}, from {codes[startindex]} to {codes[i]}")
        mosaic.write_rle(f"{cgolroot}/mosaics/mosaic{len(codes)}_{j}.rle")
        startindex += sidelen ** 2
        j += 1


def synth_mosaic(min_paths, objects):
    mosaic = lt.pattern()
    objects = list(objects)
    y = 0
    for i in range(len(objects)):
        code = objects[i]
        synth = lookup_synth(min_paths, code)
        yspace = abs(synth[1].bounding_box[3] - synth[1].bounding_box[1]) + 30
        y += yspace // 2
        mosaic += synth[1](0, y)
        y += yspace // 2
    return mosaic


def improved_mosaic():
    min_paths = dijkstra()
    objects, _ = get_improved(trueSLs)
    objects = list(set(objects))
    for o in list(objects):
        if min_paths[o][1] in objects:
            objects.remove(min_paths[o][1])
    print("improved: ", len(objects))
    return synth_mosaic(min_paths, objects)


def makemosaic_reachable(outfile, sidelen=40, startindex=0, spacing=100):
    overrides = {}
    synths = {}
    reachable = set()
    nreachable = -1
    while nreachable != len(reachable):
        nreachable = len(reachable)
        print(nreachable, " reachable")
        for line in open(outfile, "r"):
            if len(line) < 3:
                continue
            line = line.replace("%", "")
            line = line.replace("\n", "")
            input, compcost, output = decode_comp(line)
            output = output.replace("\n", "")
            if cost(input, overrides=overrides) != 9999 or input in reachable:
                reachable.add(output)
                overrides[output] = min(cost(input, overrides=overrides) + compcost, cost(output, overrides=overrides))
    for line in open(outfile, "r"):
        if len(line) < 3:
            continue
        line = line.replace("%", "")
        line = line.replace("\n", "")
        input, compcost, output = decode_comp(line)
        if output in min_paths and line == min_paths[output][2]:
            continue
        if (input not in reachable) and cost(input, overrides=overrides) == 9999:
            continue
        if cost(input, overrides=overrides) + compcost >= cost(output):
            continue
        synth = realise_comp(line)
        bbox = synth.bounding_box
        if max(bbox[2], bbox[3]) > spacing - 20:
            print("Oversize component!")
            continue
        if output not in synths:
            synths[output] = (9999, synth)
        if cost(input, overrides=overrides) + compcost < synths[output][0]:
            synths[output] = (cost(input, overrides=overrides) + compcost, synth)
            # min_paths[output][0] = cost(input) + compcost

    nsynths = len(synths)
    print(f"Found {nsynths} synths")
    synthlist = list(synths.keys())
    j = 0
    while startindex < len(synthlist):
        mosaic = lt.pattern()
        for i in range(startindex, min(len(synthlist), startindex + sidelen ** 2)):
            synth = synthlist[i]
            xoff = (i % sidelen) * spacing
            yoff = (i // sidelen) * spacing
            mosaic += synths[synth][1](xoff, yoff)
        print(f"wrote synths up to {i}, from {synthlist[startindex]} to {synthlist[i]}")
        mosaic.write_rle(f"{cgolroot}/mosaics/mosaic{nsynths}_{j}.rle")
        startindex += sidelen ** 2
        j += 1

if __name__ == "__main__":
    makemosaic_reachable(f"{cgolroot}/transfer/transfer-collisearch-recent-20210111.sjk")