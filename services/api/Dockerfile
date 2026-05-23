FROM golang:1.26 AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /http ./cmd/http

FROM alpine:3.21
RUN apk add --no-cache ca-certificates
COPY --from=builder /http /http
EXPOSE 8080
CMD ["/http"]
