import os
import argparse
from typing import List, Dict, Any

import tensorflow as tf
from absl import logging as absl_logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
tf.get_logger().setLevel('ERROR') 
absl_logging.set_verbosity(absl_logging.ERROR)


from private_detector.utils.preprocess import preprocess_for_evaluation


def read_image(filename: str) -> tf.Tensor:
    """
    Load and preprocess image for inference with the Private Detector

    Parameters
    ----------
    filename : str
        Filename of image

    Returns
    -------
    image : tf.Tensor
        Image ready for inference
    """
    image = tf.io.read_file(filename)
    image = tf.io.decode_jpeg(image, channels=3)

    image = preprocess_for_evaluation(
        image,
        480,
        tf.float16
    )

    image = tf.reshape(image, -1)

    return image


def inference(model: str, image_paths: List[str]) -> List[Dict[str, Any]]:
    model_instance = tf.saved_model.load(model)
    results = []

    for image_path in image_paths:
        image = read_image(image_path)
        preds = model_instance([image])
        results.append({
            'image_path': image_path,
            'probability': 100 * tf.get_static_value(preds[0])[0]
        })

    return results
