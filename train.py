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

# This draws heavily on the examples in: https://keras.io/applications/

import argparse
import os
import pickle

from keras import applications, callbacks, layers, metrics, models, optimizers, preprocessing
from keras.preprocessing import image


def step_count(sample_count, batch_size):
        if sample_count < batch_size:
                return 1
        else:
                return sample_count // batch_size


def main():
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--dataset-dir', '-i', metavar='<dataset_dir>', required=True,
                        help='Input dataset')
        parser.add_argument('--start_model', '-m', metavar='<model_file>',
                            help='Model to train (will not be overwritten)')
        parser.add_argument(
            '--output-dir', '-o', metavar='<output_dir>', required=True,
                        help='Output directory')
        parser.add_argument(
            '--model-prefix', '-p', metavar='<prefix>', required=False, default=None,
                        help='The prefix to give the trained model files. Default: model (if no input model specified), or the starting model\'s filename.')
        parser.add_argument(
            '--fine-tune', '-ft', required=False, default=False, action='store_true',
                            help='Fine tune only (particularly useful if you\'re creating a new model from a pre-trained one)')
        parser.add_argument(
            '--num-epochs', '-n', required=False, default=8,
                            type=int, help='The number of training epochs to complete.')
        parser.add_argument('--batch-size', '-b', required=False,
                            default=64, type=int, help='The training batch size')

        args = parser.parse_args()

        if not args.model_prefix:
                if not args.start_model:
                        args.model_prefix = 'model'
                else:
                        args.model_prefix = os.path.basename(args.start_model)

        # TODO: Check if it exists, and prompt the user if it does, because that
        # could be a problem.
        if not os.path.exists(args.output_dir):
                os.makedirs(args.output_dir)

        print("Using {} as the output directory".format(args.output_dir))

        if args.start_model:
                model = models.load_model(args.start_model)
        else:
                input_tensor = layers.Input(shape=(256, 256, 3))
                                     # this assumes K.image_data_format() ==
                                     # 'channels_last'

                base_model = applications.inception_v3.InceptionV3(
                    input_tensor=input_tensor, weights='imagenet', include_top=False)

                x = base_model.output
                x = layers.GlobalAveragePooling2D()(x)
                x = layers.Dense(1024, activation='relu')(x)
                predictions = layers.Dense(3, activation='softmax')(x)

                model = models.Model(
                    inputs=base_model.input, outputs=predictions)

        if args.fine_tune:
                for layer in model.layers[0:-3]:
                        layer.trainable = False

                model.compile(
                    optimizer='rmsprop', loss='categorical_crossentropy', metrics=[metrics.categorical_accuracy])
        else:
                for layer in model.layers:
                        layer.trainable = True

                model.compile(
                    optimizer=optimizers.SGD(lr=0.0001, momentum=0.9),
                             loss='categorical_crossentropy', metrics=[metrics.categorical_accuracy])

        train_datagen = preprocessing.image.ImageDataGenerator(
            rescale=1. / 255,  # makes all picture values between 0 and 1
                horizontal_flip=True,
                vertical_flip=True)

        test_datagen = preprocessing.image.ImageDataGenerator(rescale=1. / 255)

        train_generator = train_datagen.flow_from_directory(
            os.path.join(args.dataset_dir, 'train'),
                target_size=(256, 256),
                batch_size=args.batch_size,
                class_mode='categorical',
                follow_links=True
        )

        validation_generator = test_datagen.flow_from_directory(
            os.path.join(args.dataset_dir, 'valid'),
                target_size=(256, 256),
                batch_size=args.batch_size,
                class_mode='categorical',
                follow_links=True)

        callback = callbacks.ModelCheckpoint(
            os.path.join(args.output_dir, args.model_prefix + ".{epoch:02d}-{val_loss:.3f}-{val_categorical_accuracy:.3f}.hdf5"), monitor='val_loss', verbose=0, save_best_only=False, save_weights_only=False, mode='auto', period=1)

        history = model.fit_generator(
            train_generator,
                steps_per_epoch=step_count(
                    train_generator.samples, args.batch_size),
                epochs=args.num_epochs,
                validation_data=validation_generator,
                validation_steps=step_count(
                    validation_generator.samples, args.batch_size),
                callbacks=[callback]
        )

        with open(os.path.join(args.output_dir, args.model_prefix + "_fit_history.pickle"), "wb") as history_file:
                pickle.dump(history.history, history_file)

main()
