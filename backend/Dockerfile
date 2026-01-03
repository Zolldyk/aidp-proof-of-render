# Use Python 3.13 base image (closest to 3.14.2)
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies for Blender
RUN apt-get update && apt-get install -y \
    wget \
    xz-utils \
    libgl1 \
    libgomp1 \
    libxi6 \
    libxrender1 \
    libxkbcommon0 \
    libsm6 \
    libxext6 \
    libxfixes3 \
    && rm -rf /var/lib/apt/lists/*

# Download and install Blender 3.6 LTS
RUN wget -q https://download.blender.org/release/Blender3.6/blender-3.6.15-linux-x64.tar.xz \
    && tar -xf blender-3.6.15-linux-x64.tar.xz -C /opt \
    && rm blender-3.6.15-linux-x64.tar.xz \
    && ln -s /opt/blender-3.6.15-linux-x64/blender /usr/bin/blender

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create storage directory
RUN mkdir -p /app/storage

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
