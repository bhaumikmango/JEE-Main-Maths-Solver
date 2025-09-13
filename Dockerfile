# Use a Python 3.10 slim base image for a smaller footprint
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python dependencies from the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port on which the Flask app will run
EXPOSE 5000

# The CMD instruction executes the command to run the application using gunicorn
CMD gunicorn --bind 0.0.0.0:5000 index:app