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
from collections import Counter
import json
import urllib.request

def pretty_print_map(int_value_map):
    for key, value in sorted(int_value_map.items(), key=lambda x: int(x[1]), reverse=True):
        print('\t{}: {}'.format(key, value))

def main():

    # The most useful functionality for this is probably:
    #   One summary report of all the various lookFors
    #   Define a multimap of synonym lookFors.
    #   Get all the things in any category of the multimap. Sort by id increasing.

    parser = argparse.ArgumentParser()
    parser.add_argument('command', metavar='<types>',
                        help='Commands include lookFors, or a category from the merged lookFors')

    args = parser.parse_args()

    mappings = {
        'buildings only' : 'buildings',
        'roads only': 'roads',
        'houses & roads': 'houses and roads',
        'houses/roads': 'houses and roads'
    }

    states = {0: 'Not started', 1: 'On hold', 2: 'Complete', 3: 'Hidden'}

    # Uses the mapswipe API as defined in: https://docs.google.com/document/d/1RwN4BNhgMT5Nj9EWYRBWxIZck5iaawg9i_5FdAAderw/
    with urllib.request.urlopen("http://api.mapswipe.org/projects.json") as url:
        projects = json.loads(url.read().decode())

    if args.command == 'lookFors':
        project_type_counts = Counter()
        for project_id, project_details in projects.items():
            if 'lookFor' in project_details:
                project_type_counts[project_details['lookFor']] += 1
        
        print('Raw data:')
        pretty_print_map(project_type_counts)

        print('\nMerging a few types:')
        merged_project_type_counts = Counter()
        for key, value in project_type_counts.items():
            key = key.lower()
            if key in mappings:
                look_for = mappings[key]
            else:
                look_for = key
            
            merged_project_type_counts[look_for] += value

        pretty_print_map(merged_project_type_counts)
    else:
        target = args.command

        for project_id, project_details in sorted(projects.items(), key=lambda x: int(x[0])):
            if 'name' not in project_details:
                continue
            if project_details['progress'] != 100:
                continue

            lookFor = project_details['lookFor'].lower()
            if lookFor in mappings:
                lookFor = mappings[lookFor]

            if target == 'all' or lookFor == target:
                print('{0}; {1} [{2}] ({3}%) [{4}]'.format(project_id, project_details['name'], project_details['lookFor'].title(),
                                                   project_details['progress'], states[project_details['state']]))

main()
