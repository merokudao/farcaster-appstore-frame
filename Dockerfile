# Use an official Python runtime as a parent image
FROM python:3.8-slim

ARG GUNICORN_WORKERS=5

# Define environment variable
ENV FLASK_APP=app.py \
    FLASK_RUN_HOST=0.0.0.0

RUN apt-get update && apt-get install -y \
    libcairo2 \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy only the requirements.txt initially to leverage Docker cache
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Run app.py when the container launches
CMD gunicorn -w $GUNICORN_WORKERS app:app -b 0.0.0.0:5000
