# Stage 1: Build stage
FROM ubuntu:24.04 AS build

# Install dependencies
RUN apt-get update && apt-get install -y \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-good \
        gstreamer1.0-tools \
        libgstreamer-plugins-bad1.0-dev \
        libgstreamer-plugins-base1.0-dev \
        libgstreamer1.0-dev \
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

# Stage 2: Runtime stage
FROM ubuntu:24.04

# Install only the necessary runtime dependencies
RUN apt-get update && apt-get install -y \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-good \
        gstreamer1.0-tools \
        && rm -rf /var/lib/apt/lists/*

# Copy the built application from the build stage
COPY --from=build /app/bin/recorder /app/bin/recorder

# Set the entrypoint for the container
ENTRYPOINT ["/app/bin/recorder"]
