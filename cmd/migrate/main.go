package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/vlle/Photoshnaya/internal/config"
)

const migrationTableDDL = `
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);`

func main() {
	ctx := context.Background()
	postgresURL, err := config.NormalizePostgresURL(os.Getenv("ps_url"))
	if err != nil {
		log.Fatal(err)
	}

	env := strings.TrimSpace(os.Getenv("MIGRATIONS_ENV"))
	if env == "" {
		env = "stage"
	}
	dir := filepath.Join("migrations", "postgres", env)

	pool, err := pgxpool.New(ctx, postgresURL)
	if err != nil {
		log.Fatal(err)
	}
	defer pool.Close()

	if err := applyMigrations(ctx, pool, dir); err != nil {
		log.Fatal(err)
	}

	log.Printf("migrations applied for env=%s", env)
}

func applyMigrations(ctx context.Context, pool *pgxpool.Pool, dir string) error {
	if _, err := pool.Exec(ctx, migrationTableDDL); err != nil {
		return fmt.Errorf("create schema_migrations: %w", err)
	}

	entries, err := os.ReadDir(dir)
	if err != nil {
		return fmt.Errorf("read migration dir: %w", err)
	}

	files := make([]string, 0)
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".sql") {
			continue
		}
		files = append(files, e.Name())
	}
	sort.Strings(files)

	for _, fileName := range files {
		version := strings.TrimSuffix(fileName, ".sql")
		applied, err := isApplied(ctx, pool, version)
		if err != nil {
			return err
		}
		if applied {
			continue
		}

		content, err := os.ReadFile(filepath.Join(dir, fileName))
		if err != nil {
			return fmt.Errorf("read migration %s: %w", fileName, err)
		}

		if err := runMigration(ctx, pool, version, string(content)); err != nil {
			return fmt.Errorf("apply migration %s: %w", fileName, err)
		}
	}

	return nil
}

func runMigration(ctx context.Context, pool *pgxpool.Pool, version, content string) error {
	tx, err := pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer func() {
		_ = tx.Rollback(ctx)
	}()

	for _, statement := range splitSQL(content) {
		if strings.TrimSpace(statement) == "" {
			continue
		}
		if _, err := tx.Exec(ctx, statement); err != nil {
			return err
		}
	}

	if _, err := tx.Exec(ctx, "INSERT INTO schema_migrations(version, applied_at) VALUES ($1, $2)", version, time.Now().UTC()); err != nil {
		return err
	}

	return tx.Commit(ctx)
}

func isApplied(ctx context.Context, pool *pgxpool.Pool, version string) (bool, error) {
	const query = `SELECT EXISTS(SELECT 1 FROM schema_migrations WHERE version = $1)`
	var exists bool
	if err := pool.QueryRow(ctx, query, version).Scan(&exists); err != nil {
		return false, err
	}
	return exists, nil
}

func splitSQL(content string) []string {
	statements := make([]string, 0)
	var current strings.Builder

	inSingle := false
	inDouble := false
	inDollar := false

	for i := 0; i < len(content); i++ {
		ch := content[i]
		nextTwo := ""
		if i+1 < len(content) {
			nextTwo = content[i : i+2]
		}

		if !inSingle && !inDouble && nextTwo == "$$" {
			inDollar = !inDollar
			current.WriteString(nextTwo)
			i++
			continue
		}
		if inDollar {
			current.WriteByte(ch)
			continue
		}

		if ch == '\'' && !inDouble {
			inSingle = !inSingle
		}
		if ch == '"' && !inSingle {
			inDouble = !inDouble
		}

		if ch == ';' && !inSingle && !inDouble {
			statements = append(statements, current.String())
			current.Reset()
			continue
		}
		current.WriteByte(ch)
	}

	tail := strings.TrimSpace(current.String())
	if tail != "" {
		statements = append(statements, tail)
	}

	return statements
}
