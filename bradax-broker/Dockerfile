FROM python:3.11-slim

LABEL maintainer="Bradesco Seguros - AI Generativa <ai-generativa@bradesco.com.br>"
LABEL description="bradax Broker - AI Generative Runtime for Corporate Environment"
LABEL version="1.0.0"

# Configurar timezone
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Criar usuário não-root para segurança
RUN groupadd -r bradax && useradd -r -g bradax -m -d /app -s /bin/bash bradax

# Copiar e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copiar código fonte
COPY src/ ./src/

# Ajustar permissões
RUN chown -R bradax:bradax /app
USER bradax

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Configurações padrão
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000

# Comando padrão
CMD ["uvicorn", "src.broker.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
