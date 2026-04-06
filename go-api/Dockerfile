FROM golang:1.23-alpine AS build

WORKDIR /src
COPY . .
RUN go build -o /out/go-api ./cmd/api

FROM alpine:3.20

WORKDIR /app
COPY --from=build /out/go-api /usr/local/bin/go-api
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD wget -qO- http://127.0.0.1:8080/health >/dev/null 2>&1 || exit 1

CMD ["go-api"]
