FROM python:3.14

RUN apt-get update && \
    apt-get install -y xvfb chromium

# Install python dependencies
RUN pip install beautifulsoup4 lxml pyyaml requests zendriver

COPY moviesync ./moviesync
COPY sync.py .
COPY sync.sh .

RUN chmod +x sync.sh

ENTRYPOINT [ "/sync.sh" ]