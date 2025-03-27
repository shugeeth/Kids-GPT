# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="${PATH}:/root/.local/bin"

# Copy project files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry
RUN poetry config virtualenvs.create false

# Install project dependencies
# Updated command to remove --no-dev flag
RUN poetry install --no-interaction --no-ansi

# Copy the entire project
COPY . .

# Expose the port Gradio will run on
EXPOSE 7860

# Command to run the application
CMD ["poetry", "run", "python", "kids_gpt/main.py"]