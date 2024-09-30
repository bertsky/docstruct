ARG DOCKER_BASE_IMAGE
FROM $DOCKER_BASE_IMAGE
ARG VCS_REF
ARG BUILD_DATE
LABEL \
    maintainer="https://ocr-d.de/kontakt" \
    org.label-schema.vcs-ref=$VCS_REF \
    org.label-schema.vcs-url="https://github.com/bertsky/docstruct" \
    org.label-schema.build-date=$BUILD_DATE

WORKDIR /build/docstruct
COPY setup.py .
COPY docstruct/ocrd-tool.json .
COPY docstruct ./docstruct
COPY requirements.txt .
COPY README.md .
COPY Makefile .
RUN make install
RUN rm -rf /build/docstruct

WORKDIR /data
VOLUME ["/data"]
