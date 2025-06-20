# MATLAB Runtime Container for Locomotion Data Analysis
# 
# Created: 2025-06-20 with user permission
# Purpose: Lightweight MATLAB Runtime for compiled locomotion analysis applications
#
# Intent: Provide production-ready runtime environment for compiled MATLAB applications
# without full MATLAB installation, optimized for containerized deployment.

FROM mathworks/matlab-runtime:r2023b

# Metadata
LABEL maintainer="Locomotion Data Standardization Team"
LABEL version="1.0.0"
LABEL description="MATLAB Runtime for compiled biomechanical data analysis applications"

# Set environment variables
ENV LOCOMOTION_LIB=/opt/locomotion
ENV MCR_CACHE_ROOT=/tmp/mcr_cache
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    wget \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create application directory structure
RUN mkdir -p ${LOCOMOTION_LIB}/{apps,data,output,logs}

# Copy compiled MATLAB applications (placeholder - will be populated during build)
# COPY compiled_apps/ ${LOCOMOTION_LIB}/apps/

# Install minimal Python dependencies for data I/O
RUN pip3 install --no-cache-dir \
    pandas \
    numpy \
    pyarrow \
    matplotlib

# Create MCR cache directory
RUN mkdir -p ${MCR_CACHE_ROOT} && chmod 777 ${MCR_CACHE_ROOT}

# Create non-root user for security
RUN useradd -m -u 1001 -s /bin/bash locomotion && \
    chown -R locomotion:locomotion ${LOCOMOTION_LIB} && \
    chown -R locomotion:locomotion ${MCR_CACHE_ROOT}

# Set up volumes
VOLUME ["${LOCOMOTION_LIB}/data", "${LOCOMOTION_LIB}/output", "${LOCOMOTION_LIB}/logs"]

# Switch to non-root user
USER locomotion

# Set working directory
WORKDIR ${LOCOMOTION_LIB}

# Health check for MCR availability
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD test -d ${MATLABROOT} || exit 1

# Default command - display available applications
CMD ["sh", "-c", "echo 'MATLAB Runtime Container Ready'; echo 'Available applications:'; ls -la ${LOCOMOTION_LIB}/apps/; tail -f /dev/null"]