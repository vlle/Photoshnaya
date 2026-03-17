FROM golang:1.23-alpine AS build

WORKDIR /src
COPY . .
RUN go build -o /out/go-api ./cmd/api

FROM alpine:3.20

WORKDIR /app
COPY --from=build /out/go-api /usr/local/bin/go-api

EXPOSE 8080

CMD ["go-api"]
