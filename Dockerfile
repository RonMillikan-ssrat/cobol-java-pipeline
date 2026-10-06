FROM python:3.14

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openjdk-21-jdk-headless \
    gnucobol \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Java home
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install apache-beam[gcp]==2.76.0

# Copy pipeline scripts (these will be in the working directory)
WORKDIR /pipeline

# The pipeline code and supporting scripts will be mounted/copied by Dataflow
ENTRYPOINT ["python3"]
