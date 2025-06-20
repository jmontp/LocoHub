# MATLAB Development Container for Locomotion Data Analysis
# 
# Created: 2025-06-20 with user permission
# Purpose: Complete MATLAB development environment with locomotion analysis libraries
#
# Intent: Provide consistent MATLAB development environment across all platforms
# with pre-installed locomotion data analysis tools and dependencies.

FROM mathworks/matlab:r2023b

# Metadata
LABEL maintainer="Locomotion Data Standardization Team"
LABEL version="1.0.0"
LABEL description="MATLAB development environment for biomechanical data analysis"

# Set environment variables
ENV MATLAB_PREFDIR=/tmp/.matlab
ENV LOCOMOTION_LIB=/opt/locomotion
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    git \
    curl \
    wget \
    unzip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create locomotion library directory
RUN mkdir -p ${LOCOMOTION_LIB}/{matlab,python,data,output,docs}

# Copy MATLAB libraries and utilities
COPY source/lib/matlab/ ${LOCOMOTION_LIB}/matlab/
COPY docs/tutorials/matlab/ ${LOCOMOTION_LIB}/docs/matlab/

# Copy Python bridge components
COPY lib/core/ ${LOCOMOTION_LIB}/python/core/
COPY lib/validation/ ${LOCOMOTION_LIB}/python/validation/

# Install Python dependencies for data bridge
COPY requirements-container.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements-container.txt

# Create MATLAB startup script that adds paths
RUN echo "addpath('${LOCOMOTION_LIB}/matlab');" > ${LOCOMOTION_LIB}/startup.m && \
    echo "addpath(genpath('${LOCOMOTION_LIB}/matlab'));" >> ${LOCOMOTION_LIB}/startup.m && \
    echo "fprintf('Locomotion Data Analysis Environment Loaded\\n');" >> ${LOCOMOTION_LIB}/startup.m && \
    echo "fprintf('Available classes: LocomotionData\\n');" >> ${LOCOMOTION_LIB}/startup.m && \
    echo "fprintf('Data directory: ${LOCOMOTION_LIB}/data\\n');" >> ${LOCOMOTION_LIB}/startup.m

# Set up MATLAB toolbox cache directory
RUN mkdir -p /tmp/.matlab/R2023b

# Create volumes for data and output
VOLUME ["${LOCOMOTION_LIB}/data", "${LOCOMOTION_LIB}/output"]

# Set working directory
WORKDIR ${LOCOMOTION_LIB}

# Health check for MATLAB availability
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD matlab -batch "fprintf('MATLAB Health Check: OK\\n'); exit(0)" || exit 1

# Set default startup file
ENV MATLAB_STARTUP_FILE=${LOCOMOTION_LIB}/startup.m

# Default command - start MATLAB with locomotion libraries loaded
CMD ["matlab", "-batch", "run('${LOCOMOTION_LIB}/startup.m'); fprintf('Locomotion Data Analysis Ready\\n'); pause(inf)"]