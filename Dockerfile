FROM node:24-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    GEODYSSEY_RUNTIME=/tmp/geodyssey GDAL_CACHEMAX=64
WORKDIR /app
COPY requirements-lock.txt ./
RUN pip install --no-cache-dir --only-binary=:all: -r requirements-lock.txt
COPY backend/ ./backend/
COPY content/ ./content/
COPY scripts/ ./scripts/
COPY Data/raw/boundary/thanjavur_boundary.geojson ./Data/raw/boundary/thanjavur_boundary.geojson
COPY Data/raw/dem/output_SRTMGL1.tif ./Data/raw/dem/output_SRTMGL1.tif
COPY Data/raw/osm/thanjavur_osm_alt.geojson ./Data/raw/osm/thanjavur_osm_alt.geojson
COPY deployment/seed/ ./deployment/seed/
COPY deployment/seed/derived/ ./Data/derived/
COPY --from=frontend /build/frontend/dist/ ./frontend/dist/
EXPOSE 10000
CMD ["python", "-m", "scripts.start_hosted"]
