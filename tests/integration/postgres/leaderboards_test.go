package postgres_test

import (
	"context"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/vlle/Photoshnaya/internal/config"
	"github.com/vlle/Photoshnaya/internal/domain/leaderboard"
	"github.com/vlle/Photoshnaya/internal/store/postgres/repo"
)

func TestWinnersLeaderboardParity(t *testing.T) {
	ctx := context.Background()
	pool := mustOpenPool(t, ctx)
	defer pool.Close()

	resetAndMigrate(t, ctx, pool)
	seedLeaderboardData(t, ctx, pool)

	service := leaderboard.NewService(repo.NewLeaderboardRepo(pool))
	rows, err := service.WinnerRows(ctx, 100, leaderboard.TopLimit)
	if err != nil {
		t.Fatalf("winner rows query failed: %v", err)
	}

	if len(rows) != 2 {
		t.Fatalf("expected 2 winners, got %d", len(rows))
	}

	if rows[0].Name != "winner_1" || rows[0].Total != 2 {
		t.Fatalf("unexpected first row: %+v", rows[0])
	}
	if rows[1].Name != "winner_2" || rows[1].Total != 1 {
		t.Fatalf("unexpected second row: %+v", rows[1])
	}

	msg := leaderboard.FormatWinnerBoard(rows)
	expectedFirst := "<b>1</b>: <a href=\"https://t.me/winner_1\">winner_1</a>, количество побед: 2"
	if !strings.Contains(msg, expectedFirst) {
		t.Fatalf("formatted text mismatch: %s", msg)
	}
}

func TestWinnersLeaderboardEmptyAndIsolation(t *testing.T) {
	ctx := context.Background()
	pool := mustOpenPool(t, ctx)
	defer pool.Close()

	resetAndMigrate(t, ctx, pool)
	seedLeaderboardData(t, ctx, pool)

	service := leaderboard.NewService(repo.NewLeaderboardRepo(pool))

	rowsForOtherGroup, err := service.WinnerRows(ctx, 200, leaderboard.TopLimit)
	if err != nil {
		t.Fatalf("other group query failed: %v", err)
	}
	if len(rowsForOtherGroup) != 1 {
		t.Fatalf("expected 1 winner in second group, got %d", len(rowsForOtherGroup))
	}
	if rowsForOtherGroup[0].Name != "group2_winner" || rowsForOtherGroup[0].Total != 1 {
		t.Fatalf("unexpected second group row: %+v", rowsForOtherGroup[0])
	}

	emptyRows, err := service.WinnerRows(ctx, 300, leaderboard.TopLimit)
	if err != nil {
		t.Fatalf("empty group query failed: %v", err)
	}
	if leaderboard.FormatWinnerBoard(emptyRows) != leaderboard.EmptyLeaderboardMessage {
		t.Fatalf("unexpected empty message: %q", leaderboard.FormatWinnerBoard(emptyRows))
	}
}

func mustOpenPool(t *testing.T, ctx context.Context) *pgxpool.Pool {
	t.Helper()

	raw := strings.TrimSpace(os.Getenv("TEST_DATABASE_URL"))
	if raw == "" {
		raw = strings.TrimSpace(os.Getenv("testps_url"))
	}
	if raw == "" {
		t.Skip("set TEST_DATABASE_URL or testps_url for postgres integration tests")
	}

	normalized, err := config.NormalizePostgresURL(raw)
	if err != nil {
		t.Fatalf("normalize postgres url: %v", err)
	}

	pool, err := pgxpool.New(ctx, normalized)
	if err != nil {
		t.Fatalf("open pool: %v", err)
	}

	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		t.Fatalf("ping db: %v", err)
	}

	return pool
}

func resetAndMigrate(t *testing.T, ctx context.Context, pool *pgxpool.Pool) {
	t.Helper()

	if _, err := pool.Exec(ctx, `DROP SCHEMA IF EXISTS public CASCADE`); err != nil {
		t.Fatalf("reset schema (drop): %v", err)
	}
	if _, err := pool.Exec(ctx, `CREATE SCHEMA public`); err != nil {
		t.Fatalf("reset schema: %v", err)
	}

	sqlPath := migrationPath(t)
	sqlBytes, err := os.ReadFile(sqlPath)
	if err != nil {
		t.Fatalf("read migration file: %v", err)
	}

	for _, statement := range splitSQL(string(sqlBytes)) {
		if strings.TrimSpace(statement) == "" {
			continue
		}
		if _, err := pool.Exec(ctx, statement); err != nil {
			t.Fatalf("apply migration statement failed: %v\nSQL: %s", err, statement)
		}
	}
}

func seedLeaderboardData(t *testing.T, ctx context.Context, pool *pgxpool.Pool) {
	t.Helper()

	queries := []string{
		`INSERT INTO "group" (id, name, telegram_id, vote_in_progress) VALUES (1, 'g1', 100, FALSE), (2, 'g2', 200, FALSE), (3, 'g3', 300, FALSE);`,
		`INSERT INTO "user" (id, name, full_name, telegram_id) VALUES (1, 'winner_1', 'Winner One', 1001), (2, 'winner_2', 'Winner Two', 1002), (3, 'group2_winner', 'Winner Three', 2001);`,
		`INSERT INTO contest (id, contest_name, contest_duration_sec, group_id) VALUES (1, '#a', 1, 1), (2, '#b', 1, 1), (3, '#c', 1, 1), (4, '#d', 1, 2);`,
		`INSERT INTO contest_winner (contest_id, user_id) VALUES (1, 1), (2, 1), (3, 2), (4, 3);`,
	}

	for _, query := range queries {
		if _, err := pool.Exec(ctx, query); err != nil {
			t.Fatalf("seed query failed: %v", err)
		}
	}
}

func migrationPath(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("cannot locate current file")
	}
	root := filepath.Clean(filepath.Join(filepath.Dir(file), "..", "..", ".."))
	return filepath.Join(root, "migrations", "postgres", "stage", "0001_init.sql")
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
