FROM spex.common:latest

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

EXPOSE 8080

COPY ./microservices/ms-omero-sessions /app/services/app
COPY ./common /app/common

WORKDIR /app/services/app

RUN pipenv install --system --deploy --ignore-pipfile && pip install flask-restx==0.5.1

CMD ["python", "app.py"]
