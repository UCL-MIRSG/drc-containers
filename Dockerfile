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

LABEL org.nrg.commands="[{\"name\": \"share-to-genetic\", \"description\": \"Share subject to genetic project\", \"label\": \"Share subject to genetic project\", \"version\": \"1.0\", \"schema-version\": \"1.0\", \"type\": \"docker\", \"command-line\": \"share_subject_to_genetic_project #SUBJECTID#\", \"image\": \"ghcr.io/ucl-mirsg/drc-containers:latest\", \"override-entrypoint\": true, \"mounts\": [], \"inputs\": [{\"name\": \"SUBJECTID\", \"description\": \"The subject ID\", \"type\": \"string\", \"user-settable\": false, \"required\": true, \"replacement-key\": \"#SUBJECTID#\"}], \"outputs\": [], \"xnat\": [{\"name\": \"share-subject-to-genetic\", \"label\": \"Share subject to genetic project\", \"description\": \"Shares subject to the corresponding genetic project\", \"contexts\": [\"xnat:subjectData\"], \"external-inputs\": [{\"name\": \"subject\", \"description\": \"Input subject\", \"type\": \"Subject\", \"required\": true, \"load-children\": false}], \"derived-inputs\": [{\"name\": \"subject-id\", \"type\": \"string\", \"derived-from-wrapper-input\": \"subject\", \"derived-from-xnat-object-property\": \"id\", \"provides-value-for-command-input\": \"SUBJECTID\", \"user-settable\": false, \"required\": true}], \"output-handlers\": []}]}]"
