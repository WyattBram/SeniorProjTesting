FROM python:3.13.2

WORKDIR /app

COPY main.py .
COPY FinalModel.pt .
COPY Picture.jpg .

RUN pip install ultralytics pathlib

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

CMD ["python", "main.py"]