# Incremental API protection update

These commands target the existing single-node Swarm deployment at `/home/tflab/IsoAPA-deploy`, with services `isoapa_backend` and `isoapa_frontend`. Run them on the node hosting those services so the locally rebuilt images are available. Change the directory or service names to match your installation.

From the local repository, replace `USER@HOST` with your server login and transfer only these source/configuration files:

```bash
rsync -avR \
  backend/app/api/routes.py \
  backend/app/services/downloads.py \
  frontend/nginx.conf \
  stack.yml \
  USER@HOST:/home/tflab/IsoAPA-deploy/
```

The download service file is included because the updated routes depend on the earlier streaming-download change. If that change is already deployed, the file will be unchanged. Existing database, data, release archives and statistics files stay on the server. This update does not require rebuilding `stats_cache.json`.

On the server, build the two images using Docker's existing build cache, then validate NGINX and the stack configuration:

```bash
cd /home/tflab/IsoAPA-deploy
docker build -t isoapa-backend:latest backend
docker build -t isoapa-frontend:latest frontend
docker run --rm --entrypoint nginx isoapa-frontend:latest -t
docker stack config -c stack.yml > /dev/null
```

Apply each service update once. The explicit resource flags also apply the limits to the running backend; copying `stack.yml` alone does not do that.

```bash
docker service update --no-resolve-image \
  --image isoapa-backend:latest \
  --limit-cpu 2 --limit-memory 2G \
  --force isoapa_backend
docker service update --no-resolve-image \
  --image isoapa-frontend:latest \
  --force isoapa_frontend
```

If you choose different CPU or memory limits, use those values in the service update and set `ISOAPA_BACKEND_CPUS` / `ISOAPA_BACKEND_MEMORY` for future `docker stack deploy` commands. The default backend limit is 2 CPUs and 2 GiB, and the restart policy restarts a task if it exits.

Check the deployed services and limits:

```bash
docker service ps isoapa_backend
docker service ps isoapa_frontend
docker service inspect isoapa_backend --format '{{json .Spec.TaskTemplate.Resources.Limits}}'
curl -fsS 'https://isoapa.sls.cuhk.edu.hk/api/v1/species' > /dev/null
curl -fsS 'https://isoapa.sls.cuhk.edu.hk/api/v1/stats/multiplicity?species=Human'
```

The default protection limits are:

| Resource | Limit |
| --- | --- |
| Concurrent downloads per IP, including static release archives | 2 |
| Concurrent dynamic exports across the frontend instance | 4 |
| Concurrent statistics requests across the frontend instance | 8 |
| Backend CPU | 2 CPUs |
| Backend memory | 2 GiB |

Requests exceeding NGINX limits receive HTTP 429. New statistics are computed once per endpoint/species, then reused until the backend restarts. A production request with a missing statistics file receives HTTP 503 instead of triggering an atlas rebuild. Invalid statistics species return HTTP 404; empty or overlong species values return HTTP 422.

Concurrency zones and in-memory caches are local to each instance. This stack runs one frontend and one backend replica. If you later scale out, account for the multiplied limits or enforce shared limits at the ingress. These controls reduce resource exhaustion risk; they do not replace upstream protection against large traffic floods.
