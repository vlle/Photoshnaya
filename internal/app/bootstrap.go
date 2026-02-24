package app

import (
	"context"
	"net/http"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/vlle/Photoshnaya/internal/config"
	"github.com/vlle/Photoshnaya/internal/domain/leaderboard"
	"github.com/vlle/Photoshnaya/internal/domain/voteflow"
	"github.com/vlle/Photoshnaya/internal/store/postgres/repo"
	"github.com/vlle/Photoshnaya/internal/telegram/bridge"
)

type App struct {
	db         *pgxpool.Pool
	httpServer *http.Server
}

func New(ctx context.Context, cfg config.Config) (*App, error) {
	poolCfg, err := pgxpool.ParseConfig(cfg.PostgresURL)
	if err != nil {
		return nil, err
	}

	pool, err := pgxpool.NewWithConfig(ctx, poolCfg)
	if err != nil {
		return nil, err
	}

	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, err
	}

	leaderboardRepo := repo.NewLeaderboardRepo(pool)
	leaderboardService := leaderboard.NewService(leaderboardRepo)
	voteRepo := repo.NewVoteRepo(pool)
	voteService := voteflow.NewService(voteRepo)
	bridgeHandler := bridge.NewHandler(leaderboardService, voteService)

	mux := http.NewServeMux()
	bridgeHandler.RegisterRoutes(mux)

	httpServer := &http.Server{
		Addr:         cfg.BridgeAddr,
		Handler:      mux,
		ReadTimeout:  cfg.ReadTimeout,
		WriteTimeout: cfg.WriteTimeout,
		IdleTimeout:  cfg.IdleTimeout,
	}

	return &App{db: pool, httpServer: httpServer}, nil
}

func (a *App) Run() error {
	return a.httpServer.ListenAndServe()
}

func (a *App) Shutdown(ctx context.Context) error {
	err := a.httpServer.Shutdown(ctx)
	a.db.Close()
	return err
}
