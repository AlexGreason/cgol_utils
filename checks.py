from multiprocessing import Pool

from Shinjuku.shinjuku.checks import rewind_check
from Shinjuku.shinjuku.transcode import realise_comp
from search import read_components


def check_line_worker(args, do_print=True):
    n, line = args
    passed = True
    try:
        base, glider_set = realise_comp(line, separate=True)
        if not rewind_check(base, glider_set):
            raise ValueError(f"{line} is not infinitely rewindable")
        pat = base[-2] + glider_set[-2].s
        out_params = pat.oscar(verbose=False, return_apgcode=True)
        if not out_params:
            raise ValueError(f"input gliders of {line} do not produce a periodic object")
        out_apgcode = out_params["apgcode"]
        expected = line.split(">")[2]
        if not expected: expected = "xs0_0"
        if expected != out_apgcode:
            raise ValueError(f"{line} does not produce expected output: {expected} != {out_apgcode}")
    except Exception as e:
        if do_print:
            print(args, e)
        passed = False
    if n % 10000 == 0:
        print(f"{n}: {passed} {line}")
    return n, passed, line


if __name__ == "__main__":
    lines = read_components(verbose=True)
    nthreads = 24
    print(f"Checking {len(lines)} lines with {nthreads} threads")
    with Pool(nthreads) as pool:
        results = pool.map(check_line_worker, enumerate(lines), chunksize=1000)
