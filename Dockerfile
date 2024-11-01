# Python image to use in both stages
ARG PYTHON_IMAGE=python
ARG PYTHON_VERSION=3.13-alpine3.20@sha256:c38ead8bcf521573dad837d7ecfdebbc87792202e89953ba8b2b83a9c5a520b6

# Build stage
FROM ${PYTHON_IMAGE}:${PYTHON_VERSION} AS builder

# Create python virtual environment
RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Install package and its dependencies
WORKDIR /build
COPY . .
RUN pip install --no-cache-dir .

# Runtime stage
FROM ${PYTHON_IMAGE}:${PYTHON_VERSION}

# Copy the python virtual environment from the builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

# Default command to execute
CMD ["share-to-genetic"]
