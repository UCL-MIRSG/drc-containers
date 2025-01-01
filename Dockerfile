# Python image to use in both stages
ARG PYTHON_IMAGE=python
ARG PYTHON_VERSION=3.13-alpine3.20@sha256:804ad02b9ba67ea1f8307eeb6407b121c6bd6bb19d3f182aae166821eb59d6a4

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
