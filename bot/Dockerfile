FROM python:3.10-alpine
WORKDIR /code
RUN apk add --no-cache gcc musl-dev linux-headers python3-dev libpq-dev
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
CMD ["python3", "main.py"]
