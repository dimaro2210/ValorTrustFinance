# -------- STAGE 1: Build Stage using mise --------
FROM debian:bullseye-slim AS builder

# Force source compilation of Python
ENV MISE_SETTINGS_PYTHON_COMPILE=1

# Install build tools and dependencies
RUN apt-get update && apt-get install -y \
    curl unzip git build-essential libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev libpq-dev xz-utils tk-dev \
    libncurses5-dev libncursesw5-dev libffi-dev liblzma-dev \
    && rm -rf /var/lib/apt/lists/*

# Install mise
RUN curl https://mise.run | sh
ENV PATH="/root/.local/share/mise/shims:/root/.local/share/mise/bin:$PATH"

# Explicitly force source build (important!)
RUN mise settings set python_compile true

# Install Python from source using mise
RUN mise use -g python@3.12

# Install Python packages
COPY wealthbridge/requirements.txt /tmp/
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

# -------- STAGE 2: Runtime Stage --------
FROM debian:bullseye-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y libpq-dev && rm -rf /var/lib/apt/lists/*

# Copy compiled Python from builder
COPY --from=builder /root/.local/share/mise/installs/python/3.12 /opt/python
ENV PATH="/opt/python/bin:$PATH"

# Copy shim binaries (like `python`, `pip`, etc.)
COPY --from=builder /root/.local/share/mise/shims /usr/local/bin

# Copy your Django app
COPY wealthbridge/ /app/

# Run Django setup commands
RUN python manage.py collectstatic --no-input && \
    python manage.py makemigrations && \
    python manage.py migrate && \
    python manage.py create_admin || echo "Admin user creation skipped."

# Expose Django port
EXPOSE 8000

CMD ["gunicorn", "wealthbridge.wsgi:application", "--bind", "0.0.0.0:8000"]
