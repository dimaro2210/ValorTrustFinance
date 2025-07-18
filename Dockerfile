# Use a stable and available base image
FROM python:3.12-slim

# Optional: Enable compiling Python from source via mise (if using mise at all)
# Currently unused — can be removed unless mise is explicitly installed and used
ENV MISE_SETTINGS_PYTHON_COMPILE=1

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY wealthbridge/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY wealthbridge/ /app/

# Run Django management commands
RUN python manage.py collectstatic --no-input && \
    python manage.py makemigrations && \
    python manage.py migrate

# Optional: Create admin user if script/command exists
RUN python manage.py create_admin || echo "Admin user creation skipped."

# Expose the app port
EXPOSE 8000

# Start Gunicorn server
CMD ["gunicorn", "wealthbridge.wsgi:application", "--bind", "0.0.0.0:8000"]
