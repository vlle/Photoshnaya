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
	"github.com/vlle/Photoshnaya/internal/domain/voteflow"
	"github.com/vlle/Photoshnaya/internal/store/postgres/repo"
)

func TestVoteFlowLikeAndSubmit(t *testing.T) {
	ctx := context.Background()
	pool := mustOpenVotePool(t, ctx)
	defer pool.Close()

	resetAndMigrateVote(t, ctx, pool)
	seedVoteFlowData(t, ctx, pool)

	svc := voteflow.NewService(repo.NewVoteRepo(pool))

	start := svc.StartVoteSession(ctx, voteflow.StartRequest{
		Text:     "/start 100_3",
		ChatType: "private",
		UserID:   4001,
		UserName: "voter",
		FullName: "Voter User",
	})
	if start.Status != voteflow.StatusOK || start.Code != voteflow.CodeGreetingVote || start.State == nil {
		t.Fatalf("unexpected start result: %+v", start)
	}

	like := svc.SetLike(ctx, voteflow.LikeRequest{
		UserID:            4001,
		GroupID:           100,
		CurrentPhotoID:    start.State.CurrentPhotoID,
		CurrentPhotoCount: start.State.CurrentPhotoCount,
		AmountPhotos:      start.State.AmountPhotos,
	})
	if like.Status != voteflow.StatusOK || like.State == nil || like.State.IsLikedPhoto <= 0 {
		t.Fatalf("unexpected like result: %+v", like)
	}

	submit := svc.SubmitVote(ctx, voteflow.SubmitRequest{UserID: 4001, GroupID: 100})
	if submit.Status != voteflow.StatusOK || submit.Code != voteflow.CodeThanksForVote {
		t.Fatalf("unexpected submit result: %+v", submit)
	}

	assertSingleVotePersisted(t, ctx, pool)
}

func TestVoteFlowSelfLikeAndAlreadyVoted(t *testing.T) {
	ctx := context.Background()
	pool := mustOpenVotePool(t, ctx)
	defer pool.Close()

	resetAndMigrateVote(t, ctx, pool)
	seedVoteFlowData(t, ctx, pool)

	svc := voteflow.NewService(repo.NewVoteRepo(pool))

	selfLike := svc.SetLike(ctx, voteflow.LikeRequest{
		UserID:            1001,
		GroupID:           100,
		CurrentPhotoID:    1,
		CurrentPhotoCount: 1,
		AmountPhotos:      2,
	})
	if selfLike.Status != voteflow.StatusAlert || selfLike.Code != voteflow.CodeVoteSelf {
		t.Fatalf("unexpected self-like result: %+v", selfLike)
	}

	if _, err := pool.Exec(ctx, `INSERT INTO contest_user (contest_id, user_id) VALUES (10, 3)`); err != nil {
		t.Fatalf("insert already-voted row: %v", err)
	}

	already := svc.SubmitVote(ctx, voteflow.SubmitRequest{UserID: 4001, GroupID: 100})
	if already.Status != voteflow.StatusAlert || already.Code != voteflow.CodeAlreadyVoted {
		t.Fatalf("unexpected already-voted result: %+v", already)
	}
}

func TestVoteFlowSubmitIsolationByGroup(t *testing.T) {
	ctx := context.Background()
	pool := mustOpenVotePool(t, ctx)
	defer pool.Close()

	resetAndMigrateVote(t, ctx, pool)
	seedVoteFlowData(t, ctx, pool)
	seedSecondVoteGroup(t, ctx, pool)

	svc := voteflow.NewService(repo.NewVoteRepo(pool))

	start := svc.StartVoteSession(ctx, voteflow.StartRequest{
		Text:     "/start 100_3",
		ChatType: "private",
		UserID:   4001,
		UserName: "voter",
		FullName: "Voter User",
	})
	if start.Status != voteflow.StatusOK || start.State == nil {
		t.Fatalf("unexpected start result: %+v", start)
	}

	like := svc.SetLike(ctx, voteflow.LikeRequest{
		UserID:            4001,
		GroupID:           100,
		CurrentPhotoID:    start.State.CurrentPhotoID,
		CurrentPhotoCount: start.State.CurrentPhotoCount,
		AmountPhotos:      start.State.AmountPhotos,
	})
	if like.Status != voteflow.StatusOK {
		t.Fatalf("unexpected like result: %+v", like)
	}

	if _, err := pool.Exec(ctx, `INSERT INTO tmp_photo_like (user_id, photo_id) VALUES (3, 3)`); err != nil {
		t.Fatalf("seed tmp like for second group: %v", err)
	}

	submit := svc.SubmitVote(ctx, voteflow.SubmitRequest{UserID: 4001, GroupID: 100})
	if submit.Status != voteflow.StatusOK {
		t.Fatalf("unexpected submit result: %+v", submit)
	}

	var group1Likes int
	if err := pool.QueryRow(ctx, `
SELECT COUNT(*)
FROM photo_like pl
JOIN group_photo gp ON gp.photo_id = pl.photo_id
WHERE gp.group_id = 1`).Scan(&group1Likes); err != nil {
		t.Fatalf("count group1 likes: %v", err)
	}
	if group1Likes != 1 {
		t.Fatalf("expected 1 committed like in group1, got %d", group1Likes)
	}

	var group2Likes int
	if err := pool.QueryRow(ctx, `
SELECT COUNT(*)
FROM photo_like pl
JOIN group_photo gp ON gp.photo_id = pl.photo_id
WHERE gp.group_id = 2`).Scan(&group2Likes); err != nil {
		t.Fatalf("count group2 likes: %v", err)
	}
	if group2Likes != 0 {
		t.Fatalf("expected 0 committed likes in group2, got %d", group2Likes)
	}

	var group2TmpLikes int
	if err := pool.QueryRow(ctx, `
SELECT COUNT(*)
FROM tmp_photo_like tpl
JOIN group_photo gp ON gp.photo_id = tpl.photo_id
WHERE gp.group_id = 2 AND tpl.user_id = 3`).Scan(&group2TmpLikes); err != nil {
		t.Fatalf("count group2 tmp likes: %v", err)
	}
	if group2TmpLikes != 1 {
		t.Fatalf("expected tmp like for group2 to stay untouched, got %d", group2TmpLikes)
	}

	var contest1Votes int
	if err := pool.QueryRow(ctx, `SELECT COUNT(*) FROM contest_user WHERE contest_id = 10 AND user_id = 3`).Scan(&contest1Votes); err != nil {
		t.Fatalf("count contest1 votes: %v", err)
	}
	if contest1Votes != 1 {
		t.Fatalf("expected contest1 vote mark, got %d", contest1Votes)
	}

	var contest2Votes int
	if err := pool.QueryRow(ctx, `SELECT COUNT(*) FROM contest_user WHERE contest_id = 20 AND user_id = 3`).Scan(&contest2Votes); err != nil {
		t.Fatalf("count contest2 votes: %v", err)
	}
	if contest2Votes != 0 {
		t.Fatalf("expected no vote mark in contest2, got %d", contest2Votes)
	}
}

func assertSingleVotePersisted(t *testing.T, ctx context.Context, pool *pgxpool.Pool) {
	t.Helper()

	var likes int
	if err := pool.QueryRow(ctx, `SELECT COUNT(*) FROM photo_like`).Scan(&likes); err != nil {
		t.Fatalf("count photo_like: %v", err)
	}
	if likes != 1 {
		t.Fatalf("expected 1 committed like, got %d", likes)
	}

	var tmpLikes int
	if err := pool.QueryRow(ctx, `SELECT COUNT(*) FROM tmp_photo_like`).Scan(&tmpLikes); err != nil {
		t.Fatalf("count tmp_photo_like: %v", err)
	}
	if tmpLikes != 0 {
		t.Fatalf("expected tmp likes to be cleared, got %d", tmpLikes)
	}

	var voted int
	if err := pool.QueryRow(ctx, `SELECT COUNT(*) FROM contest_user WHERE contest_id = 10 AND user_id = 3`).Scan(&voted); err != nil {
		t.Fatalf("count contest_user vote mark: %v", err)
	}
	if voted != 1 {
		t.Fatalf("expected vote mark row, got %d", voted)
	}
}

func mustOpenVotePool(t *testing.T, ctx context.Context) *pgxpool.Pool {
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

func resetAndMigrateVote(t *testing.T, ctx context.Context, pool *pgxpool.Pool) {
	t.Helper()

	if _, err := pool.Exec(ctx, `DROP SCHEMA IF EXISTS public CASCADE`); err != nil {
		t.Fatalf("drop schema: %v", err)
	}
	if _, err := pool.Exec(ctx, `CREATE SCHEMA public`); err != nil {
		t.Fatalf("create schema: %v", err)
	}

	sqlPath := voteMigrationPath(t)
	sqlBytes, err := os.ReadFile(sqlPath)
	if err != nil {
		t.Fatalf("read migration file: %v", err)
	}

	for _, statement := range splitVoteSQL(string(sqlBytes)) {
		if strings.TrimSpace(statement) == "" {
			continue
		}
		if _, err := pool.Exec(ctx, statement); err != nil {
			t.Fatalf("apply migration statement failed: %v\nSQL: %s", err, statement)
		}
	}
}

func seedVoteFlowData(t *testing.T, ctx context.Context, pool *pgxpool.Pool) {
	t.Helper()

	queries := []string{
		`INSERT INTO "group" (id, name, telegram_id, vote_in_progress) VALUES (1, 'vote-group', 100, TRUE);`,
		`INSERT INTO contest (id, contest_name, contest_duration_sec, group_id) VALUES (10, '#theme', 1000, 1);`,
		`INSERT INTO "user" (id, name, full_name, telegram_id) VALUES (1, 'owner1', 'Owner One', 1001), (2, 'owner2', 'Owner Two', 2001), (3, 'voter', 'Voter User', 4001);`,
		`INSERT INTO group_user (user_id, group_id) VALUES (1, 1), (2, 1), (3, 1);`,
		`INSERT INTO photo (id, file_id, telegram_type, user_id) VALUES (1, 'p1', 'photo', 1), (2, 'p2', 'photo', 2);`,
		`INSERT INTO group_photo (photo_id, group_id) VALUES (1, 1), (2, 1);`,
	}

	for _, query := range queries {
		if _, err := pool.Exec(ctx, query); err != nil {
			t.Fatalf("seed query failed: %v", err)
		}
	}
}

func seedSecondVoteGroup(t *testing.T, ctx context.Context, pool *pgxpool.Pool) {
	t.Helper()

	queries := []string{
		`INSERT INTO "group" (id, name, telegram_id, vote_in_progress) VALUES (2, 'vote-group-2', 200, TRUE);`,
		`INSERT INTO contest (id, contest_name, contest_duration_sec, group_id) VALUES (20, '#theme2', 1000, 2);`,
		`INSERT INTO "user" (id, name, full_name, telegram_id) VALUES (4, 'owner3', 'Owner Three', 5001);`,
		`INSERT INTO group_user (user_id, group_id) VALUES (4, 2), (3, 2);`,
		`INSERT INTO photo (id, file_id, telegram_type, user_id) VALUES (3, 'p3', 'photo', 4);`,
		`INSERT INTO group_photo (photo_id, group_id) VALUES (3, 2);`,
	}

	for _, query := range queries {
		if _, err := pool.Exec(ctx, query); err != nil {
			t.Fatalf("seed second group query failed: %v", err)
		}
	}
}

func voteMigrationPath(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("cannot locate file")
	}
	root := filepath.Clean(filepath.Join(filepath.Dir(file), "..", "..", ".."))
	return filepath.Join(root, "migrations", "postgres", "stage", "0001_init.sql")
}

func splitVoteSQL(content string) []string {
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
