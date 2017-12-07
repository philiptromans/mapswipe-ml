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
import math
import numpy as np
import os
import pickle

from keras.models import load_model
from keras.preprocessing import image

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--dataset-dir', '-i', metavar='<dataset_dir>', required=True,
                    help='Input directory')
    parser.add_argument('--model', '-m', required=True, metavar='<model_file>',
                        help='Model to use')
    parser.add_argument('--batch-size', '-b', required=False,
                        default=64, type=int, help='The test batch size')
    parser.add_argument('--output', '-o', metavar='<output_file>', required=True,
                        help="Output file path")

    args = parser.parse_args()

    model = load_model(args.model)

    test_datagen = image.ImageDataGenerator(rescale=1. / 255)

    test_generator = test_datagen.flow_from_directory(
        args.dataset_dir,
        target_size=(256, 256),
        batch_size=args.batch_size,
        class_mode='categorical',
        follow_links=True,
        shuffle=False)
    prediction_vectors = model.predict_generator(test_generator, math.ceil(len(test_generator.filenames) / args.batch_size))

    with open(args.output, "wb") as output_file:
        abs_filenames = (os.path.abspath(os.path.join(args.dataset_dir, x)) for x in test_generator.filenames)
        pickle.dump(list(zip(abs_filenames, prediction_vectors)), output_file)

    print('Wrote {} results to {}'.format(len(prediction_vectors), os.path.abspath(args.output)))

main()
