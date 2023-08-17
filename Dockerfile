# Using the builder stage to install and compile dependencies
FROM python:3.10.12 as builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends wget unzip git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

# Fetch the nsfw_model and its requirements
RUN wget https://github.com/GantMan/nsfw_model/releases/download/1.2.0/mobilenet_v2_140_224.1.zip \
    && wget https://storage.googleapis.com/private_detector/private_detector_with_frozen.zip \
    && unzip ./mobilenet_v2_140_224.1.zip \
    && unzip ./private_detector_with_frozen.zip -d private_detector_with_frozen \
    && git clone https://github.com/GantMan/nsfw_model.git \
    && git clone https://github.com/bumble-tech/private-detector.git

# Fetch your project requirements
COPY ./requirements.txt .

# Build wheels for all requirements
RUN pip wheel --no-cache-dir --wheel-dir /usr/src/app/wheels -r requirements.txt

# Start the second stage
FROM python:3.10.12 as runner

WORKDIR /usr/src/flask_app

# Copy the model from the builder stage
COPY --from=builder /tmp/mobilenet_v2_140_224 /models/mobilenet_v2_140_224/
COPY --from=builder /tmp/private_detector_with_frozen /models/private_detector_with_frozen/
COPY --from=builder /tmp/nsfw_model /usr/src/flask_app/nsfw_model
COPY --from=builder /tmp/private-detector /usr/src/flask_app/private-detector

# Copy requirements file and pre-built wheels from the builder
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /tmp/requirements.txt .

# Install Python packages using the pre-built wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Copy the rest of your project
COPY . .

ENV PYTHONPATH="${PYTHONPATH}:/usr/src/flask_app/nsfw_model"
ENV PYTHONPATH="${PYTHONPATH}:/usr/src/flask_app/private-detector"

EXPOSE 9090

CMD ["uwsgi", "--http", "0.0.0.0:9090", "--module", "wsgi:server", "--processes", "1", "--threads", "2"]

# CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:9090", "wsgi:server", "-t", "0"]
