# Start from a small Python 3.12 image.
FROM python:3.12-slim

# Make Python print logs straight away so they appear in `docker logs`.
ENV PYTHONUNBUFFERED=1

# Store the application inside /app in the container.
WORKDIR /app

# Copy dependency list first so Docker can cache installed packages.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the server code, including copperbot.py and bot-library/.
COPY . .

# CopperHead listens on port 8765 by default.
EXPOSE 8765

# Start the server with the default settings file.
CMD ["python", "main.py", "server-settings.json"]
