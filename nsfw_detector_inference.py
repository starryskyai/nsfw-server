#! python

import argparse
import json
from os import listdir
from os.path import isfile, join, exists, isdir, abspath
from PIL import Image
import numpy as np
import tensorflow as tf
from tensorflow import keras
import tensorflow_hub as hub


IMAGE_DIM = 224   # required/default image dimensionality

def load_images(inputs, image_size, verbose=True):
    '''
    Function for loading images into numpy arrays for passing to model.predict.
    Inputs can either be image paths or a list of io.BytesIO objects.
    '''
    loaded_images = []
    loaded_image_inputs = []

    if isinstance(inputs, str):  # for single image path or directory
        if isdir(inputs):
            parent = abspath(inputs)
            inputs = [join(parent, f) for f in listdir(inputs) if isfile(join(parent, f))]
        else:
            inputs = [inputs]

    for item in inputs:
        try:
            if isinstance(item, str):  # It's a filepath
                if verbose:
                    print(item, "size:", image_size)
                image = keras.preprocessing.image.load_img(item, target_size=image_size)
            else:  # Assuming it's an io.BytesIO object
                item.seek(0)
                image = Image.open(item).resize(image_size)

            image = keras.preprocessing.image.img_to_array(image)
            image /= 255
            loaded_images.append(image)
            loaded_image_inputs.append(item)
        except Exception as ex:
            print("Image Load Failure: ", item, ex)

    return np.asarray(loaded_images), loaded_image_inputs

def load_model(model_path):
    if model_path is None or not exists(model_path):
    	raise ValueError("saved_model_path must be the valid directory of a saved model to load.")

    model = tf.keras.models.load_model(model_path, custom_objects={'KerasLayer': hub.KerasLayer},compile=False)
    return model


def classify(model, input_paths, image_dim=IMAGE_DIM, predict_args={}):
    """
    Classify given a model, input paths (could be single string), and image dimensionality.

    Optionally, pass predict_args that will be passed to tf.keras.Model.predict().
    """
    images, image_paths = load_images(input_paths, (image_dim, image_dim))
    probs = classify_nd(model, images, predict_args)
    return dict(zip(image_paths, probs))


def classify_nd(model, nd_images, predict_args={}):
    """
    Classify given a model, image array (numpy)

    Optionally, pass predict_args that will be passed to tf.keras.Model.predict().
    """
    model_preds = model.predict(nd_images, **predict_args)
    # preds = np.argsort(model_preds, axis = 1).tolist()

    categories = ['drawings', 'hentai', 'neutral', 'porn', 'sexy']

    probs = []
    for i, single_preds in enumerate(model_preds):
        single_probs = {}
        for j, pred in enumerate(single_preds):
            single_probs[categories[j]] = float(pred)
        probs.append(single_probs)
    return probs


def main(args=None):
    parser = argparse.ArgumentParser(
        description="""A script to perform NFSW classification of images""",
        epilog="""
        Launch with default model and a test image
            python nsfw_detector/predict.py --saved_model_path mobilenet_v2_140_224 --image_source test.jpg
    """, formatter_class=argparse.RawTextHelpFormatter)

    submain = parser.add_argument_group('main execution and evaluation functionality')
    submain.add_argument('--image_source', dest='image_source', type=str, required=True,
                            help='A directory of images or a single image to classify')
    submain.add_argument('--saved_model_path', dest='saved_model_path', type=str, required=True,
                            help='The model to load')
    submain.add_argument('--image_dim', dest='image_dim', type=int, default=IMAGE_DIM,
                            help="The square dimension of the model's input shape")
    if args is not None:
        config = vars(parser.parse_args(args))
    else:
        config = vars(parser.parse_args())

    if config['image_source'] is None or not exists(config['image_source']):
    	raise ValueError("image_source must be a valid directory with images or a single image to classify.")

    model = load_model(config['saved_model_path'])
    image_preds = classify(model, config['image_source'], config['image_dim'])
    print(json.dumps(image_preds, indent=2), '\n')


if __name__ == "__main__":
	main()
