from math import atan, pi, tan
from array import array
from bisect import bisect_left
from collections import namedtuple
import importlib.resources as pkg_resources
from pathlib import Path

Rconj = 15000

Semaphore_t = namedtuple("Semaphore", ["coord", "name"])
Station_t = namedtuple("Station", ["coord", "length", "name"])


def get_track_path(filename: str) -> Path:
    """Получить путь к изображению из пакета"""
    try:
        return str(pkg_resources.files("track_profile.data") / filename)
    except AttributeError:
        with pkg_resources.path("track_profile.data", filename) as path:
            return str(Path(path))
    except:
        return filename


PATHS = {
    "MSK_BOLOGOE": get_track_path("msk_bologoe.txt"),
    "BOLOGOE_OSTASHKOV": get_track_path("bologoe_ostashkov.txt"),
    "slope1": get_track_path("ex1.txt"),
    "slope2": get_track_path("ex2.txt"),
    "slope3": get_track_path("ex3.txt"),
    "slope4": get_track_path("ex4.txt"),
    "slope5": get_track_path("ex5.txt"),
    "slope6": get_track_path("ex6.txt"),
    "slope7": get_track_path("ex7.txt"),
}


def arange(x0, xk, dx):
    length = int((xk - x0) / dx)
    ret = array("d", [x0] * length)

    for i in range(1, length):
        ret[i] = ret[i - 1] + dx
    return ret


def interpolate(x, x_arr, y_arr):
    if x_arr[1] - x_arr[0] == 0:
        return y_arr[0]
    return y_arr[0] + (x - x_arr[0]) / (x_arr[1] - x_arr[0]) * (y_arr[1] - y_arr[0])


def get_available_slopes():
    return list(PATHS.keys())


def decode_slope_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            slopes = []
            semaphores = []
            stations = []
            four_digit_blocking = False

            while (line := f.readline()).find("semaphores:") < 0 and line:
                buf = line.split()
                length = int(buf[0])
                slope = float(buf[1])
                slopes.append((length, slope))
            else:
                buf = line.split(':')
                if len(buf) == 2 and int(buf[1]) == 4:
                    four_digit_blocking = True
            while (line := f.readline()).find("stations:") < 0 and line:
                buf = line.split()
                semaphores.append(Semaphore_t(coord=int(buf[0]), name=buf[1]))
            while line := f.readline():
                buf = line.split()
                stations.append(Station_t(coord=int(buf[0]), length=int(buf[1]), name=" ".join(buf[2:])))
        return slopes, semaphores, stations, four_digit_blocking
    except FileNotFoundError:
        return None


class SlopeCreator:

    def __init__(self, slope_name='slope1', reverse=False, dx=10, cyclic=True):
        self.__dx = dx
        self.__slope_name = slope_name
        self.__reverse = reverse
        self.__cyclic = cyclic

        result = decode_slope_file(PATHS[slope_name])

        if result:
            slopes, self.semaphores, self.stations, self.four_digit_blocking = result
            if reverse:
                slopes = list(reversed(slopes))
            self.__coords, self.__slopes, self.__conj, self.__radiuses = self.__add_conjugation(slopes)
            self.__coords = self.__cumulative_coords(self.__coords)
            self.__absolute_heights = self.__form_absolute_heights(self.__coords)
        else:
            self.__coords = [0]
            self.__slopes = [0]
            self.__conj = [0]
            self.__absolute_heights = [[0, 0], [0, 0]]
            self.semaphores = None
            self.stations = None

    def __len__(self):
        return self.__coords[-1]

    @property
    def cyclic(self):
        return self.__cyclic

    @staticmethod
    def __add_conjugation(slopes):
        radiuses = array("d", [Rconj] * len(slopes))
        coords = array("I", [0] * len(slopes))
        slopes_ret = array("d", [0] * len(slopes))
        conjugations = array("d", [0] * len(slopes))

        for i, el in enumerate(slopes):
            length, ang = el
            coords[i] = length
            slopes_ret[i] = ang
            if i == 0:
                continue

            if ang == slopes[i - 1][1]:
                conjugations[i - 1] = 0
                continue
            arc = atan(1 / (0.001 * abs(slopes[i - 1][1] - ang))) + pi / 2
            opposite_angle = (pi - arc) / 2

            radius = Rconj
            conj = radius * tan(opposite_angle)
            while conj >= length / 3 or conj >= length / 3:
                radius /= 2
                conj = radius * tan(opposite_angle)
            conjugations[i - 1] = conj
            radiuses[i - 1] = radius

        return coords, slopes_ret, conjugations, radiuses

    @staticmethod
    def __cumulative_coords(slopes: array) -> array:
        ret = array("I", slopes)
        for i, sl in enumerate(slopes):
            if i == 0:
                continue
            else:
                ret[i] = ret[i - 1] + slopes[i]
        return ret

    def __repr__(self):
        return (f"SlopeCreator(slope_name='{self.__slope_name}',"
                f"reverse={self.__reverse}, dx={self.__dx}) | ID: 0x{id(self):X}")

    def __form_absolute_heights(self, coords):
        xk = coords[-1]
        res_x = array("d", arange(self.__dx, xk, self.__dx))
        res_h = array("d", [0.0] * len(res_x))
        for i, x in enumerate(res_x):
            sl = self.get_slope(x)
            res_h[i] = (res_h[i - 1] + (0.001 * sl) * self.__dx)
        return res_x, res_h

    def get_absolute_height(self, x):
        if self.__slopes == 0 or x < 0:
            return 0
        indx = bisect_left(self.__absolute_heights[0], int(x) % len(self))
        if indx == 0:
            return self.__absolute_heights[0][0]
        elif indx < len(self.__absolute_heights[0]) - 1:
            return interpolate(x,
                               [self.__absolute_heights[0][indx - 1], self.__absolute_heights[0][indx]],
                               [self.__absolute_heights[1][indx - 1], self.__absolute_heights[1][indx]])
        elif indx == len(self.__absolute_heights[0]) - 1:
            return self.__absolute_heights[1][indx - 1]
        else:
            return 0

    def get_slope(self, x, no_conj=False):
        if self.__cyclic:
            x = x % len(self)
        i0 = max(0, bisect_left(self.__coords, x) - 1)

        i = i0
        for coord, slope, d_to_radius in zip(self.__coords[i0:], self.__slopes[i0:], self.__conj[i0:]):
            if i == len(self.__slopes) - 1:
                return slope
            else:
                if no_conj:
                    if x < coord:
                        return slope
                    continue

                if x < coord - d_to_radius:
                    return slope
                elif coord - d_to_radius <= x <= coord + d_to_radius:
                    signum = 1 if self.__slopes[i + 1] >= slope else -1
                    return slope + 1000 / self.__radiuses[i] * signum * (x - (coord - d_to_radius))
            i += 1

    def get_absolute_heights(self):
        return self.__absolute_heights
