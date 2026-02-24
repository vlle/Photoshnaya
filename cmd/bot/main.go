package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os/signal"
	"syscall"
	"time"

	"github.com/vlle/Photoshnaya/internal/app"
	"github.com/vlle/Photoshnaya/internal/config"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatal(err)
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	application, err := app.New(ctx, cfg)
	if err != nil {
		log.Fatal(err)
	}

	errCh := make(chan error, 1)
	go func() {
		errCh <- application.Run()
	}()

	var runErr error
	select {
	case <-ctx.Done():
	case runErr = <-errCh:
		if !errors.Is(runErr, http.ErrServerClosed) {
			log.Printf("bridge server failed: %v", runErr)
		}
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := application.Shutdown(shutdownCtx); err != nil {
		log.Printf("bridge shutdown error: %v", err)
	}

	if runErr != nil && !errors.Is(runErr, http.ErrServerClosed) {
		log.Fatal(runErr)
	}
}
