FROM alpine:latest
LABEL application="Exocortex XMPP Bridge"
RUN apk update && \
    apk add python2 && \
    apk add py2-pip
ADD . /app/
RUN pip install -r /app/requirements.txt
EXPOSE 8003
WORKDIR /app
USER nobody
CMD ["python", "exocortex_xmpp_bridge.py"]
