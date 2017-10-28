#!/usr/bin/python3

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

import argparse
import itertools
import json
import os
import random
import shutil
import sys

import bing_maps
import mapswipe
from proportional_allocator import ProportionalAllocator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project_ids', metavar='<project_id>', type=int, nargs='+',
                        help='Project IDs to use to generate the dataset.')
    parser.add_argument('--bing-maps-key', '-k', metavar='<bing_maps_api_key>', required=True,
                        help='Bing Maps API key to use to download map tiles.')
    parser.add_argument('--output-dir', '-o', metavar='<output_directory>', default='dataset',
                        help='Output directory to generate dataset in. Default: "dataset".')
    parser.add_argument('--seed', '-s', metavar='<random_seed>', default=0, type=int,
                        help='The random seed to use when picking tiles, this allows generated datasets to be '
                             'reproducible. Default: 0.')
    parser.add_argument('--max-size', '-n', metavar='<class_size>', default=sys.maxsize, type=int,
                        help='The maximum total number of items per class to output for each output subset ("train", '
                             '"valid", etc.')

    args = parser.parse_args()

    output_dir = args.output_dir
    if os.path.exists(output_dir):
        if query_yes_no('Directory {} already exists. Delete?'.format(output_dir), default='no') == 'yes':
            shutil.rmtree(output_dir)
        else:
            exit()

    bing_maps_client = bing_maps.BingMapsClient(args.bing_maps_key)

    built_floor = 1
    bad_imagery_floor = 1

    classes_and_proportions = {'train': 80, 'valid': 10, 'test': 10}

    tile_classes = ['built', 'bad_imagery', 'empty']
    for x in itertools.product(['train', 'valid'], tile_classes):
        os.makedirs(os.path.join(output_dir, *x))

    os.makedirs(os.path.join(output_dir, 'test'))

    # We have to store all of the tiles in a set to stop us from selecting the same tile twice if it appears in multiple projects
    # (sometimes the boundaries overlap a little)
    all_tiles = set()

    with open(os.path.join(output_dir, 'test', 'solutions.csv'), 'w') as solutions_file:
        for project_id in args.project_ids:
            allocator = ProportionalAllocator(classes_and_proportions)
            
            print('Selecting tiles from project (#{})... '.format(project_id))
            fresh_project_tiles = set(mapswipe.get_all_tile_quadkeys(project_id)) - all_tiles

            built_tiles = set()
            bad_imagery_tiles = set()
            empty_tiles = set()

            with mapswipe.get_project_details_file(project_id, verbose=True) as project_details_file:
                project_details = json.load(project_details_file)

            annotated_tiles = set()
            # Normally, we'd just iterate through project details and do our stuff. But project_details is a big blob,
            # so instead we dismantle it as we go, in the hope that we'll lower our overall memory usage.
            while project_details:
                task = project_details.pop()
                quadkey = bing_maps.tile_to_quadkey((int(task['task_x']), int(task['task_y'])), int(task['task_z']))
                if quadkey not in fresh_project_tiles:
                    continue

                annotated_tiles.add(quadkey)

                if task['yes_count'] >= built_floor and task['maybe_count'] == 0 and task['bad_imagery_count'] == 0:
                    built_tiles.add(quadkey)
                elif task['yes_count'] == 0 and task['maybe_count'] == 0 and task['bad_imagery_count'] >= bad_imagery_floor:
                    bad_imagery_tiles.add(quadkey)

            empty_tiles |= (fresh_project_tiles - annotated_tiles)

            all_tiles |= fresh_project_tiles

            # We allow the user to set a random seed for the shuffling, so this means that it's possible to
            # reproduce a dataset.
            random.seed(args.seed)

            # The data structures are sets, so we have to sort after converting it to a list to gives us a stable sort order (so that you can generate the same dataset with just a random seed).
            # Obviously this goes out the window if the ground truth data changes at MapSwipe's end.
            built_tiles = list(built_tiles)
            built_tiles.sort()
            random.shuffle(built_tiles)

            bad_imagery_tiles = list(bad_imagery_tiles)
            bad_imagery_tiles.sort()
            random.shuffle(bad_imagery_tiles)

            empty_tiles = list(empty_tiles)
            empty_tiles.sort()
            random.shuffle(empty_tiles)

            while built_tiles and bad_imagery_tiles and empty_tiles and allocator.total < args.max_size:
                sample_built = pick_from(built_tiles, bing_maps_client)
                sample_bad_imagery = pick_from(bad_imagery_tiles, bing_maps_client)
                sample_empty = pick_from(empty_tiles, bing_maps_client)

                if sample_built is not None and sample_bad_imagery is not None and sample_empty is not None:
                    clazz = allocator.allocate()

                    if clazz == 'test':
                        output_tile(sample_built, os.path.join(output_dir, clazz))
                        output_tile(sample_bad_imagery, os.path.join(output_dir, clazz))
                        output_tile(sample_empty, os.path.join(output_dir, clazz))

                        solutions_file.write(sample_built + ',built\n')
                        solutions_file.write(sample_bad_imagery + ',bad_imagery\n')
                        solutions_file.write(sample_empty + ',empty\n')
                        solutions_file.flush()
                    else:
                        output_tile(sample_built, os.path.join(output_dir, clazz, 'built'))
                        output_tile(sample_bad_imagery, os.path.join(output_dir, clazz, 'bad_imagery'))
                        output_tile(sample_empty, os.path.join(output_dir, clazz, 'empty'))

                sys.stdout.write('\r\tTiles picked: {} in each of {}. Total: {}'.format(allocator, tile_classes, allocator.total * 3))

            sys.stdout.write('\n')


def pick_from(pool, bing_maps_client):
    while pool:
        quadkey = pool.pop()

        tile_path = mapswipe.get_tile_path(quadkey)

        if not os.path.exists(tile_path):
            bing_maps_client.fetch_tile(quadkey, tile_path)

        if os.path.getsize(tile_path) > 0:
            return quadkey

    return None


def output_tile(quadkey, output_path):
    tile_path = mapswipe.get_tile_path(quadkey)
    destination_path = os.path.join(output_path, quadkey + '.jpg')

    if sys.platform == 'linux' or sys.platform == 'darwin':
        os.symlink(tile_path, destination_path)
    else:
        shutil.copy(tile_path, destination_path)


# From http://code.activestate.com/recipes/577058/
def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes": "yes", "y": "yes", "ye": "yes",
             "no": "no", "n": "no"}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


main()
