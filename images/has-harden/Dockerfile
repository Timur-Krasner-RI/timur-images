# Aikido has a harden image for this base.
# 3.10-slim has a larger official-vs-Aikido CVE delta than 3.13-slim.
FROM python:3.10-slim

# Do not set aik:repository / org.opencontainers.image.source — those hard-link
# the container. This fixture is meant to exercise name + SBOM *suggestions*.
LABEL org.opencontainers.image.title="timur-images-has-harden"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-c", "print('timur-images: has-harden')"]
