# TUH Chatbot AI — Backend (FastAPI + HybridRetriever: ChromaDB แบบฝังใน process + BM25)
# build context = root ของ repo เพราะ backend import โค้ดใน Admin/ (emb.py, rebuild_db.py, pdf_ocr.py)
# โครงในอิมเมจตรงกับ repo: /app/Backend, /app/Admin, /app/uploads, /app/index_db
# — config.py คำนวณ path จากตำแหน่งไฟล์ จึงไม่ต้องแก้โค้ด
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/cache/huggingface \
    PYTHAINLP_DATA_DIR=/cache/pythainlp

# Tesseract + ภาษาไทย ใช้หาตำแหน่งบรรทัดบนหน้าสแกนเพื่อไฮไลท์อ้างอิง (Admin/pdf_ocr.py)
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-tha \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY Backend/requirements.txt docker/constraints.txt /tmp/
# torch รุ่น CPU ก่อน (เครื่องนี้ไม่มี GPU) — ถ้าปล่อยให้ sentence-transformers ดึงเอง จะได้รุ่น CUDA ที่ใหญ่กว่าหลาย GB
RUN pip install --index-url https://download.pytorch.org/whl/cpu "torch==2.12.1" \
    && pip install -r /tmp/requirements.txt -c /tmp/constraints.txt

# SQL Server (เตรียมไว้ — ยังใช้ TiDB): build ด้วย --build-arg WITH_MSSQL=true เพื่อติดตั้ง Microsoft ODBC Driver 18
# + pyodbc/aioodbc แล้วตั้ง DB_ENGINE=mssql ใน Backend/.env (ดู docs/SQLSERVER_MIGRATION.md)
ARG WITH_MSSQL=false
COPY Backend/requirements-mssql.txt /tmp/
RUN if [ "$WITH_MSSQL" = "true" ]; then \
        apt-get update \
        && apt-get install -y --no-install-recommends curl ca-certificates \
        && . /etc/os-release \
        && curl -fsSL -o /tmp/ms.deb "https://packages.microsoft.com/config/debian/${VERSION_ID%%.*}/packages-microsoft-prod.deb" \
        && dpkg -i /tmp/ms.deb && rm /tmp/ms.deb \
        && apt-get update \
        && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc \
        && apt-get purge -y curl && apt-get autoremove -y \
        && rm -rf /var/lib/apt/lists/* \
        && pip install -r /tmp/requirements-mssql.txt; \
    fi

RUN useradd --uid 1000 --create-home app \
    && mkdir -p /app/uploads /app/index_db /data/chroma /cache \
    && chown -R app:app /app /data /cache
COPY --chown=app:app Admin /app/Admin
COPY --chown=app:app Backend /app/Backend

USER app
WORKDIR /app/Backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=4)"

# worker เดียวเท่านั้น — retriever (ดัชนีที่ใช้ตอบ) และความคืบหน้า rebuild อยู่ในหน่วยความจำของ process
# ถ้ามีหลาย worker แต่ละตัวจะถือดัชนีคนละชุด และสถานะ "กำลังสร้างฐานข้อมูล %" จะไม่ตรงกัน
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
