FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /home/appuser/.streamlit \
    && chown -R appuser:appuser /app /home/appuser/.streamlit

COPY --chown=appuser:appuser streamlit_app.py students_service.py test_deployed.py ./

USER appuser

EXPOSE 8080

CMD ["sh", "-c", "streamlit run streamlit_app.py --server.address=0.0.0.0 --server.port=${PORT:-8080}"]
