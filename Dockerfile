FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --upgrade pip
# RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
RUN pip install -r requirements.txt
EXPOSE 8080
CMD ["python","openai_connect.py","-p","8080"]