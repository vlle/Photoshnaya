package config

import (
	"fmt"
	"os"
	"strings"
)

type Config struct {
	DatabaseURL string
	Port        string
}

func Load() (Config, error) {
	databaseURL := os.Getenv("PS_URL")
	if databaseURL == "" {
		databaseURL = os.Getenv("ps_url")
	}
	if databaseURL == "" {
		return Config{}, fmt.Errorf("PS_URL or ps_url is required")
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	return Config{
		DatabaseURL: normalizeDatabaseURL(databaseURL),
		Port:        port,
	}, nil
}

func normalizeDatabaseURL(rawURL string) string {
	if strings.HasPrefix(rawURL, "postgresql+psycopg://") {
		return strings.Replace(rawURL, "postgresql+psycopg://", "postgresql://", 1)
	}
	return rawURL
}
