FROM golang:1.25-alpine
WORKDIR /app
COPY . .
RUN go build -o /http ./cmd/http
EXPOSE 8080
CMD ["/http"]
