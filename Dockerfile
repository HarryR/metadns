FROM jfloff/alpine-python:2.7-onbuild

COPY . /app

WORKDIR /app

ENTRYPOINT ["/usr/bin/python", "-mmetadns"]
