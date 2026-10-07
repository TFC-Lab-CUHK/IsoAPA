FROM mambaorg/micromamba:1.5.10

WORKDIR /app/backend

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba create -y -f /tmp/environment.yml \
    && micromamba clean --all --yes

COPY --chown=$MAMBA_USER:$MAMBA_USER . /app/backend

EXPOSE 8000

CMD ["micromamba", "run", "-n", "isoapa", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
