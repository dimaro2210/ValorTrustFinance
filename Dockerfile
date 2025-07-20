# -------- STAGE 1: Build Stage --------
FROM python:3.12-slim AS builder

# Install build tools and dependencies
RUN apt-get update && apt-get install -y \
    build-essential libssl-dev libpq-dev libffi-dev curl unzip git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python packages
COPY wealthbridge/requirements.txt /tmp/
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

# -------- STAGE 2: Runtime Stage --------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy installed packages and app
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin
COPY wealthbridge/ /app/

# Django setup
RUN python manage.py collectstatic --no-input && \
    python manage.py makemigrations && \
    python manage.py migrate && \
    python manage.py create_admin || echo "Admin user creation skipped."

EXPOSE 8000

CMD ["gunicorn", "wealthbridge.wsgi:application", "--bind", "0.0.0.0:8000"]
