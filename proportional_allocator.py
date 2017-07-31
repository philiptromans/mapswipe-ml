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

from collections import Counter
import operator


class ProportionalAllocator(object):
    def __init__(self, classes_and_proportions_map):
        total_props = sum(classes_and_proportions_map.values())
        self.classes_and_proportions = {key: classes_and_proportions_map[key] / total_props for key in
                                        classes_and_proportions_map}
        self.counts = Counter({key: 0 for key in classes_and_proportions_map.keys()})
        self.total = 0

    def allocate(self):
        self.total += 1
        errors = {key: self.classes_and_proportions[key] - self.counts[key] / self.total for key in self.counts}

        allocated_class = max(errors.items(), key=operator.itemgetter(1))[0]
        self.counts[allocated_class] += 1
        return allocated_class

    def __str__(self):
        return ', '.join(key + ': ' + str(self.counts[key]) for key in sorted(self.counts))
