FROM python:3.10-slim AS base

# Set environment variables to prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
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
