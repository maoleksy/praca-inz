FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Nigdy nie odpalamy z debug/reloaderem na produkcji — pilnuje tego też
# domyślna wartość FLASK_DEBUG w app.py, ale ustawiamy explicit dla jasności.
ENV FLASK_DEBUG=0

EXPOSE 5050

CMD ["python", "app.py"]
