# Python image to use in both stages
ARG PYTHON_IMAGE=python
ARG PYTHON_VERSION=3.10-alpine3.20

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
