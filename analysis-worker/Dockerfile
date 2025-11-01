# Use a specific version of the NVIDIA CUDA runtime as the base image
# This provides the necessary CUDA libraries for PyTorch
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04 AS base

# Set environment variables to prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install Python, pip, and other essential system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3-venv \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for better security
RUN useradd --create-home appuser
WORKDIR /home/appuser

# --- Builder Stage ---
# This stage installs Python dependencies into a virtual environment.
# This helps keep the final image clean and small.
FROM base AS builder

# Create and activate a virtual environment
RUN python3 -m venv /home/appuser/venv
ENV PATH="/home/appuser/venv/bin:$PATH"

# Copy the requirements file and install dependencies
# We copy only the requirements file first to leverage Docker layer caching.
COPY --chown=appuser:appuser ./requirements.txt .

# Install PyTorch and related libraries first, as they are the largest.
# Using a specific index URL for CUDA 12.1 can speed up installation.
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install the rest of the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# --- Final Stage ---
# This stage creates the final, lean production image.
FROM base AS final

# Copy the virtual environment from the builder stage
COPY --from=builder /home/appuser/venv /home/appuser/venv

# Copy the application code
COPY --chown=appuser:appuser . /home/appuser/app

# Set the working directory
WORKDIR /home/appuser/app

# Switch to the non-root user
USER appuser

# Make the virtual environment's Python the default
ENV PATH="/home/appuser/venv/bin:$PATH"

# Expose the port the application will run on
EXPOSE 8080

# Define the command to run the application using Uvicorn
# The host 0.0.0.0 makes the server accessible from outside the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
