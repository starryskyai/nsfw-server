from flask import Flask, request, jsonify, abort
import logging
from werkzeug.utils import secure_filename
import os
from nsfw_detector import predict

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
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

server.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# This utility function checks for allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@server.route('/', methods=['GET', 'POST'])
def inference():
    if request.method == 'GET':
        return 'The model is up and running. Send a POST request with a list of images.'

    # Check if the post request has the file part
    if 'files[]' not in request.files:
        return jsonify(error="No files part"), 400

    files = request.files.getlist('files[]')

    if not files:
        return jsonify(error="No files uploaded"), 400

    results = []
    for file in files:
        # Check the file extension and save it temporarily for prediction
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(server.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            result = predict.classify(model, filepath)
            results.append({
                'filename': filename,
                'result': result
            })

            # Clean up
            os.remove(filepath)

    if not results:
        return jsonify(error="None of the uploaded files are valid"), 400

    return jsonify(results)

@server.route('/health', methods=['GET'])
def health_check():
    return jsonify(status="healthy"), 200
