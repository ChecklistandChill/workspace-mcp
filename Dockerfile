FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
        && rm -rf /var/lib/apt/lists/*

        COPY . .

        # Install Python dependencies
        RUN pip install --no-cache-dir -r requirements.txt

        # Create non-root user for security
        RUN useradd --create-home --shell /bin/bash app \
            && chown -R app:app /app

            # Give read and write access to the store_creds volume
            RUN mkdir -p /app/store_creds \
                && chown -R app:app /app/store_creds \
                    && chmod 755 /app/store_creds

                    USER app

                    EXPOSE 8000

                    # Use shell form so $PORT gets expanded properly
                    CMD uvicorn fastmcp_server:app --host 0.0.0.0 --port ${PORT:-8000}
