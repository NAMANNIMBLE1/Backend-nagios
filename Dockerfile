# Use official Python image as base
FROM python:3.10-slim
WORKDIR /app
# Copy requirements
COPY requirements.txt ./
# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt
# Copy project
COPY . .
# Expose port (change if your app uses a different port)
EXPOSE 8000
# Command to run the app with uvicorn
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
