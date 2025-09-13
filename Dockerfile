# Use a stable and widely supported Python version.
# 3.10.11 has pre-built wheels for most packages.
FROM python:3.10.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Set environment variables for the virtual environment
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Create a virtual environment
RUN python -m venv $VIRTUAL_ENV

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies into the virtual environment
# The --no-cache-dir flag is recommended for Docker builds
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port your Flask app runs on
EXPOSE 5000

# Command to run the application using Gunicorn from within the virtual environment
# The port is set to 5000 as per your request
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
