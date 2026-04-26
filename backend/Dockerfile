# ─── Stage 1: Build Python dependencies ──────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps needed to compile Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt ./

# Install all main deps (pydantic v2 ecosystem — no openmetadata-ingestion here)
RUN pip install --no-cache-dir --user -r requirements.txt

# Install OM SDK runtime deps that don't conflict
RUN pip install --no-cache-dir --user \
    "grpcio>=1.47.2" \
    "grpcio-tools>=1.47.2" \
    "antlr4-python3-runtime==4.9.2" \
    "importlib-metadata>=4.13.0"

# Install OpenMetadata SDK WITHOUT its deps (avoids pydantic v1 conflict)
RUN pip install --no-cache-dir --user --no-deps openmetadata-ingestion==1.3.3

# Download spaCy model (required by Presidio NLP engine)
# Install directly via pip to avoid spacy download URL resolution issues
RUN pip install --no-cache-dir --user \
    "https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.7.1/en_core_web_lg-3.7.1-py3-none-any.whl"

# ─── Stage 2: Runtime image ───────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Create workspace: /workspace/backend/ will be the package
WORKDIR /workspace

# Runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    tesseract-ocr-tam \
    tesseract-ocr-tel \
    tesseract-ocr-kan \
    tesseract-ocr-mal \
    tesseract-ocr-mar \
    tesseract-ocr-guj \
    tesseract-ocr-pan \
    tesseract-ocr-ben \
    tesseract-ocr-ori \
    tesseract-ocr-urd \
    poppler-utils \
    libmagic1 \
    libpq5 \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*
# Create non-root user first so home dir exists
RUN useradd -m -u 1000 morolo

# Copy installed Python packages from builder stage into morolo's home
COPY --from=builder /root/.local /home/morolo/.local
RUN chown -R morolo:morolo /home/morolo/.local

ENV PATH=/home/morolo/.local/bin:$PATH
# /workspace is on PYTHONPATH so 'import backend' finds /workspace/backend/
ENV PYTHONPATH=/workspace

# Copy application source into /workspace/backend/ so it's importable as 'backend'
COPY . /workspace/backend/
RUN chown -R morolo:morolo /workspace

USER morolo

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
