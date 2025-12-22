# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install uv
RUN pip install uv

# Copy the project files
COPY . .

# Generate requirements.txt from pyproject.toml
RUN uv pip compile pyproject.toml -o requirements.txt

# Install dependencies using uv
RUN uv pip install -r requirements.txt

# Command to run the bot by default
CMD ["python", "scripts/run_bot.py"]
