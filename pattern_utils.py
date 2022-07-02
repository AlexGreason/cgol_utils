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