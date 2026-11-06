
# Build frontend
FROM oven/bun:1 AS build

WORKDIR /app

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .
RUN bun run build

# Production image
FROM oven/bun:1 AS production

WORKDIR /app

# Install Python
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Create Python virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install backend dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application files
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/bun.lock ./bun.lock
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY --from=build /app/server.ts ./server.ts
COPY --from=build /app/backend ./backend

# Set permissions
RUN mkdir -p /app/backend/instance && \
    chown -R bun:bun /app

ENV NODE_ENV=production
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV FLASK_PORT=5001

EXPOSE 10000

USER bun

CMD ["bun", "run", "server.ts"]
