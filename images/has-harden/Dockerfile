# Aikido has a harden image for this base.
FROM python:3.13-slim

# Do not set aik:repository / org.opencontainers.image.source — those hard-link
# the container. This fixture is meant to exercise name + SBOM *suggestions*.
LABEL org.opencontainers.image.title="timur-images-has-harden"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-c", "print('timur-images: has-harden')"]
