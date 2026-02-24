package config

import (
	"fmt"
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"
)

const (
	defaultBridgeAddr      = ":8080"
	defaultHTTPTimeoutMS   = 2000
	defaultPostgresSSLMode = "disable"
)

type Config struct {
	PostgresURL  string
	BridgeAddr   string
	ReadTimeout  time.Duration
	WriteTimeout time.Duration
	IdleTimeout  time.Duration
}

func Load() (Config, error) {
	rawPostgresURL := strings.TrimSpace(os.Getenv("ps_url"))
	if rawPostgresURL == "" {
		return Config{}, fmt.Errorf("ps_url is required")
	}

	postgresURL, err := NormalizePostgresURL(rawPostgresURL)
	if err != nil {
		return Config{}, err
	}

	timeoutMS, err := envInt("GO_BRIDGE_HTTP_TIMEOUT_MS", defaultHTTPTimeoutMS)
	if err != nil {
		return Config{}, err
	}

	addr := strings.TrimSpace(os.Getenv("GO_BRIDGE_HTTP_ADDR"))
	if addr == "" {
		addr = defaultBridgeAddr
	}

	timeout := time.Duration(timeoutMS) * time.Millisecond
	return Config{
		PostgresURL:  postgresURL,
		BridgeAddr:   addr,
		ReadTimeout:  timeout,
		WriteTimeout: timeout,
		IdleTimeout:  timeout,
	}, nil
}

func NormalizePostgresURL(raw string) (string, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return "", fmt.Errorf("postgres url is required")
	}

	normalized := strings.Replace(raw, "postgresql+psycopg://", "postgres://", 1)
	normalized = strings.Replace(normalized, "postgresql://", "postgres://", 1)

	u, err := url.Parse(normalized)
	if err != nil {
		return "", fmt.Errorf("parse postgres url: %w", err)
	}
	if u.Scheme != "postgres" {
		return "", fmt.Errorf("unsupported postgres url scheme %q", u.Scheme)
	}
	if u.Host == "" {
		return "", fmt.Errorf("postgres url host is required")
	}
	if strings.TrimPrefix(u.Path, "/") == "" {
		return "", fmt.Errorf("postgres url database name is required")
	}

	query := u.Query()
	if query.Get("sslmode") == "" {
		query.Set("sslmode", defaultPostgresSSLMode)
		u.RawQuery = query.Encode()
	}

	return u.String(), nil
}

func envInt(name string, defaultValue int) (int, error) {
	raw := strings.TrimSpace(os.Getenv(name))
	if raw == "" {
		return defaultValue, nil
	}

	value, err := strconv.Atoi(raw)
	if err != nil {
		return 0, fmt.Errorf("%s must be an integer: %w", name, err)
	}
	if value <= 0 {
		return 0, fmt.Errorf("%s must be > 0", name)
	}

	return value, nil
}
