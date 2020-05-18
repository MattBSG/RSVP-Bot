FROM python:3.8.2-alpine
WORKDIR /opt/rsvpbot

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]