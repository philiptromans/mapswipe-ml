#   Copyright 2017 Philip Tromans
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import datetime
import itertools
import json
import math
import os
import random
import shapely.geometry
import shutil
import time
import urllib.request

# We're allowed 50000 requests in a 24 hour period.
MIN_DELAY_BETWEEN_REQUESTS = datetime.timedelta(seconds=(24.0 * 60.0 * 60.0) / 50000)


class BingMapsClient(object):
    def __init__(self, api_key):
        self.api_key = api_key

        self._handshake()
        self.last_fetch = datetime.datetime.now()

    def fetch_tile(self, quadkey, dest_path):
        subdomain = random.choice(self.image_url_subdomains)
        request_url = self.template_image_url.replace('{subdomain}', subdomain).replace('{quadkey}', str(quadkey))

        elapsed_between_requests = datetime.datetime.now() - self.last_fetch
        if elapsed_between_requests <= MIN_DELAY_BETWEEN_REQUESTS:
            time.sleep((MIN_DELAY_BETWEEN_REQUESTS - elapsed_between_requests).total_seconds())

        self.last_fetch = datetime.datetime.now()
        (download_filename, headers) = urllib.request.urlretrieve(request_url)

        if 'X-MS-BM-WS-INFO' in headers:
            raise Exception('Exceeded rate limit.')

        if 'X-VE-Tile-Info' in headers and headers['X-VE-Tile-Info'] == 'no-tile':
            os.remove(download_filename)

            # Write an empty file to denote the absent tile.
            open(dest_path, 'a').close()
        else:
            shutil.move(download_filename, dest_path)

    def _handshake(self):
        login_url = 'http://dev.virtualearth.net/REST/v1/Imagery/Metadata/Aerial?key={}'.format(self.api_key)

        with urllib.request.urlopen(login_url) as url:
            data = json.loads(url.read().decode())

            if data['statusCode'] != 200:
                raise Exception('Could not login to Bing maps with key "{}"'.format(self.api_key))

            self.template_image_url = data['resourceSets'][0]['resources'][0]['imageUrl']
            self.image_url_subdomains = data['resourceSets'][0]['resources'][0]['imageUrlSubdomains']


# Ported from: https://msdn.microsoft.com/en-us/library/bb259689.aspx

MIN_LATITUDE = -85.05112878
MAX_LATITUDE = 85.05112878
MIN_LONGITUDE = -180
MAX_LONGITUDE = 180


def calc_map_size(level_of_detail):
    return 256 * (2 ** level_of_detail)


def clip(n, min_value, max_value):
    return min(max(n, min_value), max_value)


def tile_to_pixel(tile_coords):
    return tile_coords[0] * 256, tile_coords[1] * 256


def pixel_to_tile(pixel_coords):
    return int(pixel_coords[0] / 256), int(pixel_coords[1] / 256)


def pixel_to_latlong(pixel_coords, level_of_detail):
    map_size = calc_map_size(level_of_detail)
    x = (clip(pixel_coords[0], 0, map_size - 1) / map_size) - 0.5
    y = 0.5 - (clip(pixel_coords[1], 0, map_size - 1) / map_size)

    latitude = 90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi
    longitude = 360 * x

    return latitude, longitude


def latlong_to_pixel(latlong, level_of_detail):
    latitude = clip(latlong[0], MIN_LATITUDE, MAX_LATITUDE)
    longitude = clip(latlong[1], MIN_LONGITUDE, MAX_LONGITUDE)

    x = (longitude + 180.0) / 360.0
    sin_latitude = math.sin(latitude * math.pi / 180.0)
    y = 0.5 - math.log((1.0 + sin_latitude) / (1.0 - sin_latitude)) / (4.0 * math.pi)

    map_size = calc_map_size(level_of_detail)
    pixel_x = int(clip(x * map_size + 0.5, 0, map_size - 1))
    pixel_y = int(clip(y * map_size + 0.5, 0, map_size - 1))

    return pixel_x, pixel_y


def tile_to_quadkey(tile_coords, level_of_detail):
    quad_key = ''
    for i in range(level_of_detail, 0, -1):
        digit = ord('0')
        mask = 1 << (i - 1)
        if (tile_coords[0] & mask) != 0:
            digit += 1

        if (tile_coords[1] & mask) != 0:
            digit += 2

        quad_key += chr(digit)

    return quad_key


def tile_to_pixel_box(tile):
    top_left_pixel_coords = tile_to_pixel(tile)
    bottom_right_pixel_coords = tile_to_pixel((tile[0] + 1, tile[1] + 1))

    return shapely.geometry.box(top_left_pixel_coords[0], top_left_pixel_coords[1],
                                bottom_right_pixel_coords[0], bottom_right_pixel_coords[1])


def tiles_in_pixel_box(bounds):
    top_left_tile = pixel_to_tile((bounds[0], bounds[1]))
    bottom_right_tile = pixel_to_tile((bounds[2], bounds[3]))

    return itertools.product(range(top_left_tile[0], bottom_right_tile[0] + 1),
                             range(top_left_tile[1], bottom_right_tile[1] + 1))


def quadkey_to_tile(quadkey):
    tile_x = 0
    tile_y = 0
    level_of_detail = len(quadkey);

    for i in range(level_of_detail, 0, -1):
        mask = 1 << (i - 1)
        if quadkey[level_of_detail - i] == '0':
            continue
        elif quadkey[level_of_detail - i] == '1':
            tile_x |= mask
        elif quadkey[level_of_detail - i] == '2':
            tile_y |= mask
        elif quadkey[level_of_detail - i] == '3':
            tile_x |= mask
            tile_y |= mask
        else:
            raise (LookupError('Invalid quadkey character'))

    return tile_x, tile_y, level_of_detail


def quadkey_to_url(quadkey):
    tile = quadkey_to_tile(quadkey)

    lat, long = pixel_to_latlong(tile_to_pixel(tile), tile[2])

    return "http://bing.com/maps/default.aspx?cp={}~{}&lvl={}&style=a".format(lat, long, len(quadkey));
