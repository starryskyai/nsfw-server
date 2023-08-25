import os
import logging
from urllib.request import urlretrieve
from flask import Flask, request, jsonify, abort
from werkzeug.utils import secure_filename
from nsfw_detector_inference import classify
from private_detector_inference import inference as pd_inference

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Load the model
try:
    logging.info("Loading model...")
    model = predict.load_model('/models/mobilenet_v2_140_224/')
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
    run_pd_inference = False  # Default is set to False

    try:
        if request.method == 'GET':
            return 'The model is up and running. Send a POST request with a list of images.'

        saved_filepaths = []

        # Handle uploaded files
        if 'files[]' in request.files:
            files = request.files.getlist('files[]')
            if not files:
                return jsonify(error="No files uploaded"), 400

            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(server.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    saved_filepaths.append(filepath)

        # Handle pre-signed URLs
        elif 'urls[]' in request.json:
            urls = request.json['urls[]']
            if not urls:
                return jsonify(error="No URLs provided"), 400

            for i, url in enumerate(urls):
                unique_id = uuid.uuid4()
                filename = f"temp_{unique_id}.jpg"
                filepath = os.path.join(server.config['UPLOAD_FOLDER'], filename)
                urlretrieve(url, filepath)
                saved_filepaths.append(filepath)

        else:
            return jsonify(error="Either provide files or URLs"), 400

        nsfw_detector_results = classify(model, server.config['UPLOAD_FOLDER'])

        private_detector_results = []
        if run_pd_inference:
            private_detector_results = pd_inference('/models/private_detector_with_frozen/private_detector 5/saved_model', saved_filepaths)

        results = []
        for filepath in saved_filepaths:
            filename = os.path.basename(filepath)

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

        for filepath in saved_filepaths:
            os.remove(filepath)

        if not results:
            return jsonify(error="No results found"), 500

        return jsonify(results)

    except Exception as e:
        # This will catch any exception and return its message.
        return jsonify(error=str(e)), 500



@server.route('/health', methods=['GET'])
def health_check():
    return jsonify(status="healthy"), 200
