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

import json
import os
import pickle
import shapely.geometry
import shutil
import sys
import urllib.request

import bing_maps

working_dir_path = os.path.join(os.path.expanduser('~'), '.mapswipe')
tile_cache_path = os.path.join(working_dir_path, 'tiles')


def get_tile_path(quadkey, make_directories=True):
    # This hopefully stops us from having directories with loads of files.
    quadkey_int = int(quadkey, base=4)
    cache_subdir = '{:03d}'.format(quadkey_int % 128)

    tile_path = os.path.join(tile_cache_path, cache_subdir, quadkey + '.jpg')

    if make_directories:
        tile_parent_path = os.path.dirname(tile_path)

        if not os.path.isdir(tile_parent_path):
            os.makedirs(tile_parent_path)

    return tile_path


def get_project_details_file(project_id, verbose=True):
    project_details_path = os.path.join(working_dir_path, str(project_id), 'project_details.json')

    if not os.path.isfile(project_details_path):
        if verbose:
            sys.stdout.write('Downloading project details (#' + str(project_id) + ')... ')

        download_url = 'http://api.mapswipe.org/projects/{0}.json'.format(str(project_id))
        (download_filename, headers) = urllib.request.urlretrieve(download_url)

        if os.path.getsize(download_filename) == 0:
            raise Exception('Empty response.')

        parent_path = os.path.dirname(project_details_path)
        if not os.path.isdir(parent_path):
            os.makedirs(parent_path)

        shutil.move(download_filename, project_details_path)

        if verbose:
            sys.stdout.write(' Done\n')

    return open(project_details_path)


def get_all_tile_quadkeys(project_id, verbose=True):
    all_tiles_path = os.path.join(working_dir_path, str(project_id), 'all_tiles.pickled')

    if os.path.isfile(all_tiles_path):
        with open(all_tiles_path, 'rb') as f:
            return pickle.load(f)

    if verbose:
        sys.stdout.write('Calculating all tiles in project (#' + str(project_id) + ')... ')
        sys.stdout.flush()

    parent_path = os.path.dirname(all_tiles_path)
    if not os.path.isdir(parent_path):
        os.makedirs(parent_path)

    with urllib.request.urlopen('http://mapswipe.geog.uni-heidelberg.de/data/projects.geojson') as url:
        data = json.loads(url.read().decode())

    features = [x for x in data['features'] if x['properties']['project_id'] == int(project_id)]

    if len(features) == 0:
        raise Exception('Could not find feature.')
    elif len(features) > 1:
        raise Exception('Found multiple projects with the target id.')

    feature = features[0]

    bounding_poly = shapely.geometry.Polygon((bing_maps.latlong_to_pixel((point[1], point[0]), 18)
                                              for point in feature['geometry']['coordinates'][0]))

    ret_val = [bing_maps.tile_to_quadkey(tile, 18) for tile in bing_maps.tiles_in_pixel_box(bounding_poly.bounds)
               if bounding_poly.contains(bing_maps.tile_to_pixel_box(tile))]

    with open(all_tiles_path, 'wb') as f:
        pickle.dump(ret_val, f)

    if verbose:
        sys.stdout.write('Done\n')
        sys.stdout.flush()

    return ret_val
