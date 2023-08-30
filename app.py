import os
import uuid
import logging
from io import BytesIO
from urllib.request import urlretrieve, urlopen
from flask import Flask, request, jsonify, abort
from werkzeug.utils import secure_filename
from nsfw_detector_inference import classify, load_model
from private_detector_inference import inference as pd_inference

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Load the model
try:
    logging.info("Loading model...")
    model = load_model('/models/mobilenet_v2_140_224/')
    logging.info("Model loaded successfully!")
except Exception as e:
    logging.error("Failed to load model: %s", e)

server = Flask(__name__)

UPLOAD_FOLDER = '/tmp/uploads/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
server.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# This utility function checks for allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

from urllib.request import urlretrieve

@server.route('/', methods=['GET', 'POST'])
def inference():
    run_pd_inference = True

    try:
        if request.method == 'GET':
            return 'The model is up and running. Send a POST request with a list of images.'

        saved_filepaths = []
        original_filenames = []

        # Handle uploaded files
        if 'files[]' in request.files:
            files = request.files.getlist('files[]')
            if not files:
                return jsonify(error="No files uploaded"), 400

            for file in files:
                if file and allowed_file(file.filename):
                    in_memory_file = BytesIO()
                    file.save(in_memory_file)
                    saved_filepaths.append(in_memory_file)
                    original_filenames.append(file.filename)

        # Handle pre-signed URLs
        elif 'urls[]' in request.json:
            urls = request.json['urls[]']
            if not urls:
                return jsonify(error="No URLs provided"), 400

            for url in urls:
                response = urlopen(url)
                in_memory_file = BytesIO(response.read())
                saved_filepaths.append(in_memory_file)
                original_filenames.append(f"temp_{uuid.uuid4()}.jpg")

        else:
            return jsonify(error="Either provide files or URLs"), 400

        nsfw_detector_results = classify(model, saved_filepaths)

        private_detector_results = []
        if run_pd_inference:
            private_detector_results = pd_inference('/models/private_detector_with_frozen/private_detector 5/saved_model', saved_filepaths)

        results = []
        for idx, filepath in enumerate(saved_filepaths):
            filename = original_filenames[idx]

            nsfw_result = nsfw_detector_results.get(filepath, None)
            private_result = [res for res in private_detector_results if res["image_path"] == filepath][0] if private_detector_results else None

            if nsfw_result is not None:
                results.append({
                    'filename': filename,
                    'result_1': nsfw_result,
                    'result_2': private_result
                })
            else:
                return jsonify(error=f"No nsfw result for file: {filename}"), 500

        if not results:
            return jsonify(error="No results found"), 500

        return jsonify(results)

    except Exception as e:
        # This will catch any exception and return its message.
        return jsonify(error=str(e)), 500



@server.route('/health', methods=['GET'])
def health_check():
    return jsonify(status="healthy"), 200
