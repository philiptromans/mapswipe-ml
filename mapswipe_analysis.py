import os
import pickle

import numpy as np

import sklearn.metrics

from itertools import islice, zip_longest
import numpy as np
from IPython.display import HTML, Markdown
from bing_maps import *
import pandas as pd
import mapswipe
from pathlib import Path
from collections import defaultdict, namedtuple
import bing_maps

TileVotes = namedtuple('TileVotes', ['yes_count', 'maybe_count', 'bad_imagery_count'])
TileVotes.__iadd__ = lambda x,y: TileVotes(x.yes_count + y.yes_count,
                     x.maybe_count + y.maybe_count,
                     x.bad_imagery_count + y.bad_imagery_count)

class_names = ['bad_imagery', 'built', 'empty']
class_number_to_name = {k: v for k, v in enumerate(class_names)}
class_name_to_number = {v: k for k, v in class_number_to_name.items()}

def ground_truth_solutions_file_to_map(solutions_path):
    retval = {}
    with open(solutions_path) as solutions_file:
        for line in solutions_file:
            tokens = line.strip().split(',')
            retval[tokens[0]] = tokens[1]

    return retval

def predictions_file_to_map(predictions_path):
    with open(predictions_path, 'rb') as f:
        (paths, prediction_vectors) = zip(*pickle.load(f))

        quadkeys = []
        for path in paths:
            filename = os.path.basename(path)
            quadkeys.append(filename[0:filename.index('.')])
        
        return dict(zip(quadkeys, prediction_vectors))

def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)

def tableau(quadkeys, solution = None):
    retVal = "<table>"
    for row in grouper(quadkeys, 3):
        html_row = "<tr>"
        for quadkey in row:
            html_row += "<td align=\"center\" style=\"text-align: center\">"
            if quadkey is not None:
                html_row += cell_renderer(quadkey, solution)
            html_row += "</td>"
        html_row += "</tr>"
        retVal += html_row
    retVal += "</table>"
    display(HTML(retVal))
    
def cell_renderer(quadkey, solution):
    retVal = ""
    retVal = "Quadkey: <a href=\"{}\" target=\"_blank\">{}</a><br>".format(quadkey_to_url(quadkey), quadkey)
    if solution is not None:
        retVal += "Officially: {}<br>".format(solution.ground_truth[quadkey])
        retVal += "Predicted class: " + solution.predicted_class(quadkey) + "<br>"
    
    retVal += "<img align=\"center\" src=\"mapswipe_working_dir/{}\"/><br>".format(os.path.relpath(mapswipe.get_tile_path(quadkey),
                                                                         os.path.join(str(Path.home()),'.mapswipe')))
    if solution is not None:
        retVal += "PV:" + str(solution.prediction_vectors[quadkey])
    
    return retVal

def get_all_tile_votes_for_projects(project_ids):
    retval = defaultdict(lambda: TileVotes(0, 0, 0))

    for project_id in project_ids:
        with mapswipe.get_project_details_file(project_id) as project_details_file:
            tile_json = json.loads(project_details_file.read())

        for tile in tile_json:
            quadkey = bing_maps.tile_to_quadkey((int(tile['task_x']), int(tile['task_y'])), int(tile['task_z']))
            votes = TileVotes(tile['yes_count'], tile['maybe_count'], tile['bad_imagery_count'])
            retval[quadkey] += votes
    
    return retval


class Solution:
    def __init__(self, ground_truth, prediction_vectors):
        self.ground_truth = ground_truth
        self.prediction_vectors = prediction_vectors

        if self.ground_truth.keys() != self.prediction_vectors.keys():
            raise(KeyError('Ground truth tiles != prediction tiles'))

        ground_truth_classes = []
        prediction_vector_classes = []
        for quadkey in ground_truth.keys():
            ground_truth_classes.append(class_name_to_number[ground_truth[quadkey]])
            prediction_vector_classes.append(np.argmax(prediction_vectors[quadkey]))

        self.confusion_matrix = sklearn.metrics.confusion_matrix(ground_truth_classes, prediction_vector_classes)
        self.category_accuracies = [self.confusion_matrix[i][i] / sum(self.confusion_matrix[i]) for i in range(len(self.confusion_matrix))]
        self.accuracy = np.mean(self.category_accuracies)
        self.tile_count = len(ground_truth)
    
    def classified_as(self, predicted_class, solution_class):
        if predicted_class in class_name_to_number:
            predict_class_index = class_name_to_number[predicted_class]
            solution_class_index = class_name_to_number[solution_class]
        else:
            predict_class_index = predicted_class
            solution_class_index = solution_class

        retval = {k : v for k,v in self.prediction_vectors.items() 
            if np.argmax(v) == predict_class_index and class_name_to_number[self.ground_truth[k]] == solution_class_index}

        return sorted(retval.items(), key=lambda x:x[1][np.argmax(x[1])], reverse=True)

    def predicted_class(self, quadkey):
        return class_number_to_name[np.argmax(self.prediction_vectors[quadkey])]
