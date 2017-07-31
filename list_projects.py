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

import json
import urllib.request

# Uses the mapswipe API as defined in: https://docs.google.com/document/d/1RwN4BNhgMT5Nj9EWYRBWxIZck5iaawg9i_5FdAAderw/

states = {0: 'Not started', 1: 'On hold', 2: 'Complete', 3: 'Hidden'}
with urllib.request.urlopen("http://api.mapswipe.org/projects.json") as url:
    projects = json.loads(url.read().decode())

for project_id, project_details in sorted(projects.items(), key=lambda x: int(x[0])):
    if 'name' not in project_details:
        continue
    if project_details['progress'] != 100:
        continue
    if project_details['lookFor'].lower() != 'buildings only':
        continue

    print('{0}: {1} [{2}] ({3}%) [{4}]'.format(project_id, project_details['name'], project_details['lookFor'].title(),
                                               project_details['progress'], states[project_details['state']]))
