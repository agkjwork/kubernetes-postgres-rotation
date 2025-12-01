# Use the official Python 3.11 image as a base image
FROM python:3.11

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements.txt into the container
COPY requirements.txt .

# Install the dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Alembic configuration and migrations folder into the container
COPY alembic.ini .
COPY migrations/ migrations/

# Set the default entry point to the alembic command
ENTRYPOINT ["alembic"]
