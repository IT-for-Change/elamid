FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# The app will be baked in to the image:
# 1) to minimize moving parts 
# 2) avoid additional configuration and hence install complexity
# 3) the app once productionized will only need infrequent updates given its minimal focused technical function
COPY app.py .

CMD ["python", "app.py"]

