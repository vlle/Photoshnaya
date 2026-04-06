package service_test

import (
	"context"
	"errors"
	"os"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"

	"go-api/internal/model"
	"go-api/internal/service"
	"go-api/internal/store"
)

const integrationSchema = `
CREATE TABLE IF NOT EXISTS "user" (
	id BIGSERIAL PRIMARY KEY,
	name VARCHAR(30) NOT NULL,
	full_name TEXT,
	telegram_id BIGINT NOT NULL UNIQUE,
	created_date TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "group" (
	id BIGSERIAL PRIMARY KEY,
	name TEXT NOT NULL,
	telegram_id BIGINT NOT NULL UNIQUE,
	vote_in_progress BOOLEAN NOT NULL DEFAULT FALSE,
	created_date TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contest (
	id BIGSERIAL PRIMARY KEY,
	contest_name TEXT NOT NULL,
	contest_duration_sec BIGINT NOT NULL,
	link_to_results TEXT,
	created_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	group_id BIGINT NOT NULL REFERENCES "group"(id)
);

CREATE TABLE IF NOT EXISTS photo (
	id BIGSERIAL PRIMARY KEY,
	file_id TEXT NOT NULL,
	telegram_type VARCHAR(15) NOT NULL DEFAULT 'photo',
	user_id BIGINT NOT NULL REFERENCES "user"(id)
);

CREATE TABLE IF NOT EXISTS group_photo (
	photo_id BIGINT NOT NULL REFERENCES photo(id),
	group_id BIGINT NOT NULL REFERENCES "group"(id),
	PRIMARY KEY (photo_id, group_id)
);

CREATE TABLE IF NOT EXISTS group_user (
	user_id BIGINT NOT NULL REFERENCES "user"(id),
	group_id BIGINT NOT NULL REFERENCES "group"(id),
	PRIMARY KEY (user_id, group_id)
);

CREATE TABLE IF NOT EXISTS group_admin (
	user_id BIGINT NOT NULL REFERENCES "user"(id),
	group_id BIGINT NOT NULL REFERENCES "group"(id),
	PRIMARY KEY (user_id, group_id)
);

CREATE TABLE IF NOT EXISTS photo_like (
	user_id BIGINT NOT NULL REFERENCES "user"(id),
	photo_id BIGINT NOT NULL REFERENCES photo(id),
	PRIMARY KEY (user_id, photo_id)
);

CREATE TABLE IF NOT EXISTS tmp_photo_like (
	user_id BIGINT NOT NULL REFERENCES "user"(id),
	photo_id BIGINT NOT NULL REFERENCES photo(id),
	PRIMARY KEY (user_id, photo_id)
);

CREATE TABLE IF NOT EXISTS contest_user (
	contest_id BIGINT NOT NULL REFERENCES contest(id),
	user_id BIGINT NOT NULL REFERENCES "user"(id),
	PRIMARY KEY (contest_id, user_id)
);

CREATE TABLE IF NOT EXISTS contest_winner (
	contest_id BIGINT NOT NULL REFERENCES contest(id),
	user_id BIGINT NOT NULL REFERENCES "user"(id),
	PRIMARY KEY (contest_id, user_id)
);

CREATE TABLE IF NOT EXISTS contest_participant (
	contest_id BIGINT NOT NULL REFERENCES contest(id),
	user_id BIGINT NOT NULL REFERENCES "user"(id),
	PRIMARY KEY (contest_id, user_id)
);
`

func TestVoteServiceGetVoteSessionNoPhotos(t *testing.T) {
	ctx := context.Background()
	pool, voteService, _ := newIntegrationServices(t)
	insertGroup(t, pool, 100, true)

	_, err := voteService.GetVoteSession(ctx, 100, 42)
	if !errors.Is(err, model.ErrNoPhotos) {
		t.Fatalf("expected ErrNoPhotos, got %v", err)
	}
}

func TestVoteServiceGetVoteSessionNoVoteYet(t *testing.T) {
	ctx := context.Background()
	pool, voteService, _ := newIntegrationServices(t)
	groupID := insertGroup(t, pool, 100, false)
	ownerID := insertUser(t, pool, 200, "owner", "Owner User")
	insertPhoto(t, pool, ownerID, groupID, "file-1", "photo")

	_, err := voteService.GetVoteSession(ctx, 100, 42)
	if !errors.Is(err, model.ErrNoVoteYet) {
		t.Fatalf("expected ErrNoVoteYet, got %v", err)
	}
}

func TestVoteServiceGetVoteSessionAlreadyVoted(t *testing.T) {
	ctx := context.Background()
	pool, voteService, _ := newIntegrationServices(t)
	groupID := insertGroup(t, pool, 100, true)
	contestID := insertContest(t, pool, groupID)
	ownerID := insertUser(t, pool, 200, "owner", "Owner User")
	insertPhoto(t, pool, ownerID, groupID, "file-1", "photo")
	voterID := insertUser(t, pool, 300, "voter", "Voter User")
	addUserToGroup(t, pool, voterID, groupID)
	markUserVoted(t, pool, contestID, voterID)

	_, err := voteService.GetVoteSession(ctx, 100, 300)
	if !errors.Is(err, model.ErrAlreadyVoted) {
		t.Fatalf("expected ErrAlreadyVoted, got %v", err)
	}

	if countRows(t, pool, `SELECT COUNT(*) FROM contest_user`) != 1 {
		t.Fatal("expected vote marker to remain in contest_user")
	}
}

func TestVoteServiceGetVoteSessionSuccess(t *testing.T) {
	ctx := context.Background()
	pool, voteService, _ := newIntegrationServices(t)
	groupID := insertGroup(t, pool, 100, true)
	insertContest(t, pool, groupID)
	ownerOneID := insertUser(t, pool, 200, "owner1", "Owner One")
	firstPhotoID := insertPhoto(t, pool, ownerOneID, groupID, "file-1", "photo")
	ownerTwoID := insertUser(t, pool, 201, "owner2", "Owner Two")
	insertPhoto(t, pool, ownerTwoID, groupID, "file-2", "document")
	voterID := insertUser(t, pool, 300, "voter", "Voter User")
	addUserToGroup(t, pool, voterID, groupID)
	insertTempLike(t, pool, voterID, firstPhotoID)

	state, err := voteService.GetVoteSession(ctx, 100, 300)
	if err != nil {
		t.Fatalf("expected success, got %v", err)
	}

	if state.PhotoID != firstPhotoID || state.CurrentIndex != 1 || state.TotalPhotos != 2 {
		t.Fatalf("unexpected vote session: %+v", state)
	}
	if state.FileID != "file-1" || state.FileType != "photo" || state.LikedState != 1 {
		t.Fatalf("unexpected vote payload: %+v", state)
	}
	if countRows(t, pool, `SELECT COUNT(*) FROM tmp_photo_like`) != 1 {
		t.Fatal("expected staged like to remain after session read")
	}
}

func TestVoteServiceNavigationAndBoundaries(t *testing.T) {
	ctx := context.Background()
	pool, voteService, _ := newIntegrationServices(t)
	groupID := insertGroup(t, pool, 100, true)
	insertContest(t, pool, groupID)
	ownerOneID := insertUser(t, pool, 200, "owner1", "Owner One")
	firstPhotoID := insertPhoto(t, pool, ownerOneID, groupID, "file-1", "photo")
	ownerTwoID := insertUser(t, pool, 201, "owner2", "Owner Two")
	secondPhotoID := insertPhoto(t, pool, ownerTwoID, groupID, "file-2", "document")
	voterID := insertUser(t, pool, 300, "voter", "Voter User")
	addUserToGroup(t, pool, voterID, groupID)

	nextState, err := voteService.GetNextVotePhoto(ctx, 100, 300, firstPhotoID)
	if err != nil {
		t.Fatalf("expected next photo, got %v", err)
	}
	if nextState.PhotoID != secondPhotoID || nextState.CurrentIndex != 2 {
		t.Fatalf("unexpected next state: %+v", nextState)
	}

	prevState, err := voteService.GetPrevVotePhoto(ctx, 100, 300, secondPhotoID)
	if err != nil {
		t.Fatalf("expected prev photo, got %v", err)
	}
	if prevState.PhotoID != firstPhotoID || prevState.CurrentIndex != 1 {
		t.Fatalf("unexpected prev state: %+v", prevState)
	}

	_, err = voteService.GetNextVotePhoto(ctx, 100, 300, secondPhotoID)
	if !errors.Is(err, model.ErrPhotoNotFound) {
		t.Fatalf("expected ErrPhotoNotFound for next boundary, got %v", err)
	}

	_, err = voteService.GetPrevVotePhoto(ctx, 100, 300, firstPhotoID)
	if !errors.Is(err, model.ErrPhotoNotFound) {
		t.Fatalf("expected ErrPhotoNotFound for prev boundary, got %v", err)
	}
}

func TestVoteServiceLikeAndUnlikeIdempotency(t *testing.T) {
	ctx := context.Background()
	pool, voteService, _ := newIntegrationServices(t)
	groupID := insertGroup(t, pool, 100, true)
	insertContest(t, pool, groupID)
	ownerID := insertUser(t, pool, 200, "owner", "Owner User")
	photoID := insertPhoto(t, pool, ownerID, groupID, "file-1", "photo")
	voterID := insertUser(t, pool, 300, "voter", "Voter User")
	addUserToGroup(t, pool, voterID, groupID)

	if err := voteService.SetLike(ctx, 100, 200, photoID); !errors.Is(err, model.ErrSelfLike) {
		t.Fatalf("expected ErrSelfLike, got %v", err)
	}

	if err := voteService.SetLike(ctx, 100, 300, photoID); err != nil {
		t.Fatalf("expected first like to succeed, got %v", err)
	}
	if err := voteService.SetLike(ctx, 100, 300, photoID); err != nil {
		t.Fatalf("expected repeated like to stay idempotent, got %v", err)
	}

	if countRows(t, pool, `SELECT COUNT(*) FROM tmp_photo_like`) != 1 {
		t.Fatal("expected exactly one staged like after duplicate likes")
	}

	if err := voteService.UnsetLike(ctx, 100, 300, photoID); err != nil {
		t.Fatalf("expected unlike to succeed, got %v", err)
	}
	if err := voteService.UnsetLike(ctx, 100, 300, photoID); err != nil {
		t.Fatalf("expected repeated unlike to stay idempotent, got %v", err)
	}

	if countRows(t, pool, `SELECT COUNT(*) FROM tmp_photo_like`) != 0 {
		t.Fatal("expected staged likes to be cleared after unlike")
	}
}

func TestVoteServiceSubmitVoteMovesLikesAndPreventsSecondSubmit(t *testing.T) {
	ctx := context.Background()
	pool, voteService, _ := newIntegrationServices(t)
	groupID := insertGroup(t, pool, 100, true)
	insertContest(t, pool, groupID)
	ownerID := insertUser(t, pool, 200, "owner", "Owner User")
	photoID := insertPhoto(t, pool, ownerID, groupID, "file-1", "photo")
	voterID := insertUser(t, pool, 300, "voter", "Voter User")
	addUserToGroup(t, pool, voterID, groupID)

	if err := voteService.SetLike(ctx, 100, 300, photoID); err != nil {
		t.Fatalf("expected staged like to succeed, got %v", err)
	}
	if err := voteService.SubmitVote(ctx, 100, 300); err != nil {
		t.Fatalf("expected submit to succeed, got %v", err)
	}

	if countRows(t, pool, `SELECT COUNT(*) FROM photo_like`) != 1 {
		t.Fatal("expected final like to be persisted")
	}
	if countRows(t, pool, `SELECT COUNT(*) FROM tmp_photo_like`) != 0 {
		t.Fatal("expected staged likes to be deleted after submit")
	}
	if countRows(t, pool, `SELECT COUNT(*) FROM contest_user`) != 1 {
		t.Fatal("expected contest_user marker to be inserted after submit")
	}

	err := voteService.SubmitVote(ctx, 100, 300)
	if !errors.Is(err, model.ErrAlreadyVoted) {
		t.Fatalf("expected ErrAlreadyVoted on second submit, got %v", err)
	}
}

func TestSubmissionServiceRegisterAndReplaceContestSubmission(t *testing.T) {
	ctx := context.Background()
	pool, _, submissionService := newIntegrationServices(t)
	groupID := insertGroup(t, pool, 100, false)
	insertContest(t, pool, groupID)

	status, err := submissionService.RegisterContestSubmission(
		ctx,
		model.ContestSubmissionRequest{
			GroupID:  100,
			UserID:   300,
			Username: "voter",
			FullName: "Voter User",
			FileID:   "file-1",
			FileType: "photo",
		},
	)
	if err != nil {
		t.Fatalf("expected new submission to succeed, got %v", err)
	}
	if status != model.ContestSubmissionStatusNew {
		t.Fatalf("expected new status, got %s", status)
	}

	if countRows(t, pool, `SELECT COUNT(*) FROM photo`) != 1 {
		t.Fatal("expected one photo after first submission")
	}
	if countRows(t, pool, `SELECT COUNT(*) FROM contest_participant`) != 1 {
		t.Fatal("expected one contest participant after first submission")
	}
	if countRows(t, pool, `SELECT COUNT(*) FROM group_user`) != 1 {
		t.Fatal("expected one group_user row after first submission")
	}

	status, err = submissionService.RegisterContestSubmission(
		ctx,
		model.ContestSubmissionRequest{
			GroupID:  100,
			UserID:   300,
			Username: "voter",
			FullName: "Voter User",
			FileID:   "file-2",
			FileType: "document",
		},
	)
	if err != nil {
		t.Fatalf("expected replacement submission to succeed, got %v", err)
	}
	if status != model.ContestSubmissionStatusChanged {
		t.Fatalf("expected changed status, got %s", status)
	}

	if countRows(t, pool, `SELECT COUNT(*) FROM photo`) != 1 {
		t.Fatal("expected replacement to reuse the existing photo row")
	}
	if countRows(t, pool, `SELECT COUNT(*) FROM contest_participant`) != 1 {
		t.Fatal("expected replacement to avoid duplicating contest participants")
	}

	fileID, fileType := fetchPhotoDataByTelegramUser(t, pool, 300)
	if fileID != "file-2" || fileType != "document" {
		t.Fatalf("expected updated file payload, got file_id=%s telegram_type=%s", fileID, fileType)
	}
}

func newIntegrationServices(t *testing.T) (*pgxpool.Pool, *service.VoteService, *service.SubmissionService) {
	t.Helper()

	databaseURL := os.Getenv("PS_URL")
	if databaseURL == "" {
		t.Skip("PS_URL is required for Go integration tests")
	}

	ctx := context.Background()
	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		t.Fatalf("failed to connect to postgres: %v", err)
	}
	t.Cleanup(pool.Close)

	if err := setupIntegrationSchema(ctx, pool); err != nil {
		t.Fatalf("failed to initialize schema: %v", err)
	}
	if err := resetIntegrationDatabase(ctx, pool); err != nil {
		t.Fatalf("failed to reset database: %v", err)
	}

	voteStore := store.NewVoteStore(pool)
	return pool, service.NewVoteService(voteStore), service.NewSubmissionService(voteStore)
}

func setupIntegrationSchema(ctx context.Context, pool *pgxpool.Pool) error {
	_, err := pool.Exec(ctx, integrationSchema)
	return err
}

func resetIntegrationDatabase(ctx context.Context, pool *pgxpool.Pool) error {
	_, err := pool.Exec(ctx, `
		TRUNCATE TABLE
			contest_participant,
			contest_user,
			contest_winner,
			tmp_photo_like,
			photo_like,
			group_admin,
			group_user,
			group_photo,
			contest,
			photo,
			"group",
			"user"
		RESTART IDENTITY CASCADE
	`)
	return err
}

func insertGroup(t *testing.T, pool *pgxpool.Pool, telegramID int64, voteInProgress bool) int64 {
	t.Helper()

	var id int64
	err := pool.QueryRow(
		context.Background(),
		`INSERT INTO "group"(name, telegram_id, vote_in_progress) VALUES ($1, $2, $3) RETURNING id`,
		"group",
		telegramID,
		voteInProgress,
	).Scan(&id)
	if err != nil {
		t.Fatalf("failed to insert group: %v", err)
	}
	return id
}

func insertContest(t *testing.T, pool *pgxpool.Pool, groupID int64) int64 {
	t.Helper()

	var id int64
	err := pool.QueryRow(
		context.Background(),
		`INSERT INTO contest(contest_name, contest_duration_sec, group_id) VALUES ($1, $2, $3) RETURNING id`,
		"contest",
		3600,
		groupID,
	).Scan(&id)
	if err != nil {
		t.Fatalf("failed to insert contest: %v", err)
	}
	return id
}

func insertUser(t *testing.T, pool *pgxpool.Pool, telegramID int64, name string, fullName string) int64 {
	t.Helper()

	var id int64
	err := pool.QueryRow(
		context.Background(),
		`INSERT INTO "user"(name, full_name, telegram_id) VALUES ($1, $2, $3) RETURNING id`,
		name,
		fullName,
		telegramID,
	).Scan(&id)
	if err != nil {
		t.Fatalf("failed to insert user: %v", err)
	}
	return id
}

func addUserToGroup(t *testing.T, pool *pgxpool.Pool, userID int64, groupID int64) {
	t.Helper()
	mustExec(
		t,
		pool,
		`INSERT INTO group_user(user_id, group_id) VALUES ($1, $2) ON CONFLICT DO NOTHING`,
		userID,
		groupID,
	)
}

func insertPhoto(t *testing.T, pool *pgxpool.Pool, userID int64, groupID int64, fileID string, fileType string) int64 {
	t.Helper()

	var photoID int64
	err := pool.QueryRow(
		context.Background(),
		`INSERT INTO photo(file_id, telegram_type, user_id) VALUES ($1, $2, $3) RETURNING id`,
		fileID,
		fileType,
		userID,
	).Scan(&photoID)
	if err != nil {
		t.Fatalf("failed to insert photo: %v", err)
	}

	mustExec(
		t,
		pool,
		`INSERT INTO group_photo(photo_id, group_id) VALUES ($1, $2)`,
		photoID,
		groupID,
	)
	return photoID
}

func insertTempLike(t *testing.T, pool *pgxpool.Pool, userID int64, photoID int64) {
	t.Helper()
	mustExec(
		t,
		pool,
		`INSERT INTO tmp_photo_like(user_id, photo_id) VALUES ($1, $2)`,
		userID,
		photoID,
	)
}

func markUserVoted(t *testing.T, pool *pgxpool.Pool, contestID int64, userID int64) {
	t.Helper()
	mustExec(
		t,
		pool,
		`INSERT INTO contest_user(contest_id, user_id) VALUES ($1, $2)`,
		contestID,
		userID,
	)
}

func fetchPhotoDataByTelegramUser(t *testing.T, pool *pgxpool.Pool, telegramUserID int64) (string, string) {
	t.Helper()

	var fileID string
	var fileType string
	err := pool.QueryRow(
		context.Background(),
		`
		SELECT p.file_id, p.telegram_type
		FROM photo p
		JOIN "user" u ON u.id = p.user_id
		WHERE u.telegram_id = $1
	`,
		telegramUserID,
	).Scan(&fileID, &fileType)
	if err != nil {
		t.Fatalf("failed to fetch photo data: %v", err)
	}
	return fileID, fileType
}

func countRows(t *testing.T, pool *pgxpool.Pool, query string, args ...any) int {
	t.Helper()

	var count int
	err := pool.QueryRow(context.Background(), query, args...).Scan(&count)
	if err != nil {
		t.Fatalf("failed to count rows: %v", err)
	}
	return count
}

func mustExec(t *testing.T, pool *pgxpool.Pool, query string, args ...any) {
	t.Helper()

	if _, err := pool.Exec(context.Background(), query, args...); err != nil {
		t.Fatalf("failed to execute query %q: %v", query, err)
	}
}
