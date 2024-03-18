import numpy as np

from Shinjuku.shinjuku import lt


def size(code):
    if code == "":
        return 0
    x = code.split("_")[0]
    y = x[2:]
    try:
        return int(y)
    except ValueError as e:
        print("Failed to get size of", code, "due to", e)
        return 9999


def area(bbox):
    return abs((bbox[3] - bbox[1]) * (bbox[2] - bbox[0]))


def density(code):
    if code == "" or code == "xs0_0":
        return 0
    try:
        a = lt.pattern(code)
        return a.population / area(a.bounding_box)
    except (ValueError, TypeError) as e:
        print("failed to check density of ", code, " due to valueError ", e)
        return 0


def apgcode(rlestr):
    a = lt.pattern(rlestr)
    a.coords()
    return a.apgcode

def pattern_to_dots_and_stars(pattern):
    pattern_string = None
    if isinstance(pattern, str):
        # pattern may be an rle string, or may already be a dots and stars string. RLEs do not include the * character.
        if "*" in pattern:
            return pattern
        else:
            pattern_string = pattern
            pattern = lt.pattern(pattern)
    else:
        pattern_string = pattern.rle_string()
    # we now definitely have a pattern object.
    # 1. We don't actually want to use the bounding box property - since then it'll always tight-fit to the live cells.
    # Instead, extract the x and y attributes from the rle string (start of the string looks like this: "x = 29, y = 29"
    vals = pattern_string.split(",")
    x = int(vals[0].split("=")[1])
    y = int(vals[1].split("=")[1])
    bbox = (0, 0, x, y)
    # 2. iterate over all cells in bounding box
    result = ""
    for x in range(bbox[1], bbox[3]):
        line = ""
        for y in range(bbox[0], bbox[2]):
            if pattern[y, x]:
                line += "*"
            else:
                line += "."
        result += line + "\n"
    return result

def dots_and_stars_to_array(dots_and_stars_string):
    return np.array([[{'.': False, '*': True}[x] for x in line.replace("\n", "")] for line in dots_and_stars_string.split("\n") if len(line) > 0])

if __name__ == "__main__":
    test_pattern = """x = 29, y = 29, rule = B3/S23
2$22bo$21b3o$20b2obo$14b3o3b3o$13bo2bo3b3o$12bo3b2o2b3o$12bo8b2o$3b2o
9bo$3bobo5bobo$3bo2b2o2b2obob2o7b2o$6b2obobobobobo3b2o2bo$3b2o2bobobob
obob2o4bo2bo$5bobobobobobobobobobo$2bo2bo4b2obobobobobo2b2o$3bo2b2o3bo
bobobobob2o$3b2o7b2obob2o2b2o2bo$15bobo5bobo$14bo9b2o$6b2o8bo$6b3o2b2o
3bo$6b3o3bo2bo$6b3o3b3o$5bob2o$5b3o$6bo!
"""
    print(pattern_to_dots_and_stars(test_pattern))