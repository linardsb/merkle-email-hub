FROM pgvector/pgvector:pg16@sha256:7d400e340efb42f4d8c9c12c6427adb253f726881a9985d2a471bf0eed824dff

# Patch openssl/libssl3 to debian-security version (CVE-2026-31789 + 4 related HIGH).
# Upstream pgvector:pg16 hasn't been rebuilt with the patched debian base yet;
# pulling debian-security on top is the cleanest forward fix until it is.
# Trivy verifies the installed version is >= the fix version after this step.
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends libssl3 openssl && \
    rm -rf /var/lib/apt/lists/*

# pgvector is pre-installed in this image
# PostGIS can be added if spatial queries are needed:
# RUN apt-get update && apt-get install -y postgresql-16-postgis-3 && rm -rf /var/lib/apt/lists/*
