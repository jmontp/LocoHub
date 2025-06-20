# Python Analysis Container for Locomotion Data
# 
# Created: 2025-06-20 with user permission
# Purpose: Python-based analysis environment for locomotion data processing
#
# Intent: Provide Python-based analysis capabilities that complement MATLAB workflows,
# including data validation, visualization, and statistical analysis.

FROM python:3.11-slim

# Metadata
LABEL maintainer="Locomotion Data Standardization Team"
LABEL version="1.0.0"
LABEL description="Python environment for locomotion data analysis and validation"

# Set environment variables
ENV LOCOMOTION_LIB=/opt/locomotion
ENV PYTHONPATH=${LOCOMOTION_LIB}/python:$PYTHONPATH
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create application directory structure
RUN mkdir -p ${LOCOMOTION_LIB}/{python,data,output,logs,config}

# Copy Python libraries
COPY lib/ ${LOCOMOTION_LIB}/python/
COPY docs/tutorials/python/ ${LOCOMOTION_LIB}/docs/python/

# Copy requirements and install dependencies
COPY requirements-container.txt /tmp/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements-container.txt

# Install additional scientific computing packages
RUN pip install --no-cache-dir \
    scikit-learn \
    scipy \
    statsmodels \
    plotly \
    bokeh \
    jupyter \
    ipykernel

# Create non-root user for security
RUN useradd -m -u 1001 -s /bin/bash locomotion && \
    chown -R locomotion:locomotion ${LOCOMOTION_LIB}

# Set up Jupyter configuration
RUN mkdir -p /home/locomotion/.jupyter && \
    echo "c.NotebookApp.ip = '0.0.0.0'" > /home/locomotion/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.open_browser = False" >> /home/locomotion/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.port = 8888" >> /home/locomotion/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.token = ''" >> /home/locomotion/.jupyter/jupyter_notebook_config.py && \
    chown -R locomotion:locomotion /home/locomotion/.jupyter

# Set up volumes
VOLUME ["${LOCOMOTION_LIB}/data", "${LOCOMOTION_LIB}/output", "${LOCOMOTION_LIB}/logs"]

# Switch to non-root user
USER locomotion

# Set working directory
WORKDIR ${LOCOMOTION_LIB}

# Expose Jupyter port
EXPOSE 8888

# Health check for Python environment
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; from lib.core.locomotion_analysis import LocomotionData; print('Python Analysis Container: OK')" || exit 1

# Default command - start Jupyter lab
CMD ["jupyter", "lab", "--notebook-dir=/opt/locomotion", "--allow-root"]