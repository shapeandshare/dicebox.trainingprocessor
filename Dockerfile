# https://hub.docker.com/r/tiangolo/uwsgi-nginx/
FROM tiangolo/uwsgi-nginx:python2.7

WORKDIR /app

COPY ./app /app
COPY ./dicebox/lib /app/lib

RUN pip install -r requirements.txt \
    && useradd -M -U -u 1000 trainingprocessor \
    && chown -R trainingprocessor /app

# CMD ["su", "-", "trainingprocessor", "-c", "python", "./trainingprocessor.py"]
ENTRYPOINT ["python", "./trainingprocessor.py"]
CMD ["su", "-", "trainingprocessor", "-c", "tail", "-f", "./logs/trainingprocessor.log"]
