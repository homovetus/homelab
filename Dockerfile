FROM ubuntu:24.04

# Install dependencies
RUN apt-get update && apt-get install -y \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-good \
        gstreamer1.0-tools \
        libgstreamer-plugins-bad1.0-dev \
        libgstreamer-plugins-base1.0-dev \
        libgstreamer1.0-dev \
        python3 \
        python3-pip \
        7zip \
        build-essential \
        git \
        xmake \
        && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m nonrootuser

# Copy project files
COPY . /app
WORKDIR /app

# Ensure non-root user has permissions to /app
RUN chown -R nonrootuser:nonrootuser /app

# Switch to the non-root user
USER nonrootuser

# Build the recorder
RUN xmake

# Set the entrypoint for the container
ENTRYPOINT ["./bin/recorder"]
