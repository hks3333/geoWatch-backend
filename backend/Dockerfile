# Use the official Python image as a base image.
FROM python:3.11-slim-buster

# Set the working directory in the container.
WORKDIR /app

# Install production dependencies.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code to the container.
COPY . .

# Expose the port that the application listens on.
# Cloud Run will inject the PORT environment variable, so we use that.
ENV PORT 8080
EXPOSE $PORT

# Run the application using Uvicorn.
# The --host 0.0.0.0 makes the server accessible from outside the container.
# The --port $PORT ensures it listens on the port provided by Cloud Run.
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT