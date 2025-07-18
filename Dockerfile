# -------- STAGE 1: Build Stage using mise --------
FROM debian:bullseye-slim as builder

ENV MISE_SETTINGS_PYTHON_COMPILE=1

# Install mise and its dependencies
RUN apt-get update && apt-get install -y \
    curl unzip git build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install mise
RUN curl https://mise.run | sh
ENV PATH="/root/.local/share/mise/shims:/root/.local/share/mise/bin:$PATH"

# Use mise to install Python
RUN mise use -g python@3.12

# Install Python packages
COPY wealthbridge/requirements.txt /tmp/
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

# -------- STAGE 2: Runtime Stage --------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Copy only the installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy your actual app code
COPY wealthbridge/ /app/

# Run Django commands
RUN apt-get update && apt-get install -y libpq-dev && \
    python manage.py collectstatic --no-input && \
    python manage.py makemigrations && \
    python manage.py migrate && \
    python manage.py create_admin || echo "Admin user creation skipped." && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Expose Django port
EXPOSE 8000

# Start Gunicorn server
CMD ["gunicorn", "wealthbridge.wsgi:application", "--bind", "0.0.0.0:8000"]
