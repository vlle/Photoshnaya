package store

import (
	"context"
	"errors"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"

	"go-api/internal/model"
)

type queryable interface {
	Query(context.Context, string, ...any) (pgx.Rows, error)
	QueryRow(context.Context, string, ...any) pgx.Row
	Exec(context.Context, string, ...any) (pgconn.CommandTag, error)
}

type VoteStore struct {
	pool *pgxpool.Pool
}

func NewVoteStore(pool *pgxpool.Pool) *VoteStore {
	return &VoteStore{pool: pool}
}

func (s *VoteStore) ListContestPhotoIDs(ctx context.Context, groupID int64) ([]int64, error) {
	rows, err := s.pool.Query(ctx, `
		SELECT p.id
		FROM photo p
		JOIN group_photo gp ON p.id = gp.photo_id
		WHERE gp.group_id = (
			SELECT g.id
			FROM "group" g
			WHERE g.telegram_id = $1
		)
		ORDER BY p.id
	`, groupID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	photoIDs := make([]int64, 0)
	for rows.Next() {
		var photoID int64
		if err := rows.Scan(&photoID); err != nil {
			return nil, err
		}
		photoIDs = append(photoIDs, photoID)
	}

	return photoIDs, rows.Err()
}

func (s *VoteStore) GetPhotoByID(ctx context.Context, photoID int64) (model.Photo, error) {
	var photo model.Photo
	err := s.pool.QueryRow(ctx, `
		SELECT id, file_id, telegram_type
		FROM photo
		WHERE id = $1
	`, photoID).Scan(&photo.ID, &photo.FileID, &photo.FileType)
	if errors.Is(err, pgx.ErrNoRows) {
		return model.Photo{}, model.ErrPhotoNotFound
	}
	return photo, err
}

func (s *VoteStore) GetNextContestPhoto(ctx context.Context, groupID int64, currentPhotoID int64) (model.Photo, error) {
	return s.getRelativeContestPhoto(ctx, groupID, currentPhotoID, "ASC", ">")
}

func (s *VoteStore) GetPrevContestPhoto(ctx context.Context, groupID int64, currentPhotoID int64) (model.Photo, error) {
	return s.getRelativeContestPhoto(ctx, groupID, currentPhotoID, "DESC", "<")
}

func (s *VoteStore) IsVoteActive(ctx context.Context, groupID int64) (bool, error) {
	var active bool
	err := s.pool.QueryRow(ctx, `
		SELECT vote_in_progress
		FROM "group"
		WHERE telegram_id = $1
	`, groupID).Scan(&active)
	if errors.Is(err, pgx.ErrNoRows) {
		return false, nil
	}
	return active, err
}

func (s *VoteStore) HasUserVoted(ctx context.Context, groupID int64, userTelegramID int64) (bool, error) {
	contestID, err := s.getContestID(ctx, s.pool, groupID)
	if err != nil {
		if errors.Is(err, model.ErrNoVoteYet) {
			return false, nil
		}
		return false, err
	}

	userID, err := s.getUserID(ctx, s.pool, userTelegramID)
	if err != nil {
		if errors.Is(err, model.ErrUserNotFound) {
			return false, nil
		}
		return false, err
	}

	var marker int
	err = s.pool.QueryRow(ctx, `
		SELECT 1
		FROM contest_user
		WHERE contest_id = $1 AND user_id = $2
	`, contestID, userID).Scan(&marker)
	if errors.Is(err, pgx.ErrNoRows) {
		return false, nil
	}
	return err == nil, err
}

func (s *VoteStore) GetPhotoLikedState(ctx context.Context, userTelegramID int64, photoID int64) (int, error) {
	var likes int
	if err := s.pool.QueryRow(ctx, `
		SELECT COUNT(*)
		FROM tmp_photo_like tpl
		JOIN "user" u ON u.id = tpl.user_id
		WHERE u.telegram_id = $1 AND tpl.photo_id = $2
	`, userTelegramID, photoID).Scan(&likes); err != nil {
		return 0, err
	}

	var ownerTelegramID int64
	err := s.pool.QueryRow(ctx, `
		SELECT u.telegram_id
		FROM "user" u
		JOIN photo p ON p.user_id = u.id
		WHERE p.id = $1
	`, photoID).Scan(&ownerTelegramID)
	if errors.Is(err, pgx.ErrNoRows) {
		return 0, model.ErrPhotoNotFound
	}
	if err != nil {
		return 0, err
	}

	if ownerTelegramID == userTelegramID {
		return -1, nil
	}

	return likes, nil
}

func (s *VoteStore) SetLike(ctx context.Context, userTelegramID int64, photoID int64) error {
	userID, err := s.getUserID(ctx, s.pool, userTelegramID)
	if err != nil {
		return err
	}

	var ownerTelegramID int64
	err = s.pool.QueryRow(ctx, `
		SELECT u.telegram_id
		FROM "user" u
		JOIN photo p ON p.user_id = u.id
		WHERE p.id = $1
	`, photoID).Scan(&ownerTelegramID)
	if errors.Is(err, pgx.ErrNoRows) {
		return model.ErrPhotoNotFound
	}
	if err != nil {
		return err
	}

	if ownerTelegramID == userTelegramID {
		return model.ErrSelfLike
	}

	_, err = s.pool.Exec(ctx, `
		INSERT INTO tmp_photo_like(user_id, photo_id)
		VALUES ($1, $2)
		ON CONFLICT DO NOTHING
	`, userID, photoID)
	return err
}

func (s *VoteStore) UnsetLike(ctx context.Context, userTelegramID int64, photoID int64) error {
	userID, err := s.getUserID(ctx, s.pool, userTelegramID)
	if err != nil {
		if errors.Is(err, model.ErrUserNotFound) {
			return nil
		}
		return err
	}

	_, err = s.pool.Exec(ctx, `
		DELETE FROM tmp_photo_like
		WHERE user_id = $1 AND photo_id = $2
	`, userID, photoID)
	return err
}

func (s *VoteStore) SubmitVote(ctx context.Context, groupID int64, userTelegramID int64) error {
	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return err
	}

	committed := false
	defer func() {
		if !committed {
			_ = tx.Rollback(ctx)
		}
	}()

	contestID, err := s.getContestID(ctx, tx, groupID)
	if err != nil {
		return err
	}

	userID, err := s.getUserID(ctx, tx, userTelegramID)
	if err != nil {
		return err
	}

	var marker int
	err = tx.QueryRow(ctx, `
		SELECT 1
		FROM contest_user
		WHERE contest_id = $1 AND user_id = $2
	`, contestID, userID).Scan(&marker)
	if err == nil {
		return model.ErrAlreadyVoted
	}
	if err != nil && !errors.Is(err, pgx.ErrNoRows) {
		return err
	}

	if _, err := tx.Exec(ctx, `
		INSERT INTO photo_like(user_id, photo_id)
		SELECT tpl.user_id, tpl.photo_id
		FROM tmp_photo_like tpl
		JOIN group_photo gp ON gp.photo_id = tpl.photo_id
		JOIN "group" g ON g.id = gp.group_id
		WHERE g.telegram_id = $1 AND tpl.user_id = $2
		ON CONFLICT DO NOTHING
	`, groupID, userID); err != nil {
		return err
	}

	if _, err := tx.Exec(ctx, `
		DELETE FROM tmp_photo_like tpl
		USING group_photo gp, "group" g
		WHERE tpl.photo_id = gp.photo_id
			AND gp.group_id = g.id
			AND g.telegram_id = $1
			AND tpl.user_id = $2
	`, groupID, userID); err != nil {
		return err
	}

	tag, err := tx.Exec(ctx, `
		INSERT INTO contest_user(contest_id, user_id)
		VALUES ($1, $2)
		ON CONFLICT DO NOTHING
	`, contestID, userID)
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return model.ErrAlreadyVoted
	}

	if err := tx.Commit(ctx); err != nil {
		return err
	}
	committed = true

	return nil
}

func (s *VoteStore) RegisterContestSubmission(
	ctx context.Context, req model.ContestSubmissionRequest,
) (model.ContestSubmissionStatus, error) {
	tx, err := s.pool.Begin(ctx)
	if err != nil {
		return "", err
	}

	committed := false
	defer func() {
		if !committed {
			_ = tx.Rollback(ctx)
		}
	}()

	groupID, err := s.getGroupID(ctx, tx, req.GroupID)
	if err != nil {
		return "", err
	}

	userID, err := s.ensureUserInGroup(
		ctx,
		tx,
		groupID,
		req.UserID,
		req.Username,
		req.FullName,
	)
	if err != nil {
		return "", err
	}

	photoID, err := s.getGroupPhotoByUser(ctx, tx, groupID, userID)
	if err == nil {
		if _, err := tx.Exec(ctx, `
			UPDATE photo
			SET file_id = $1, telegram_type = $2
			WHERE id = $3
		`, req.FileID, req.FileType, photoID); err != nil {
			return "", err
		}
		if err := tx.Commit(ctx); err != nil {
			return "", err
		}
		committed = true
		return model.ContestSubmissionStatusChanged, nil
	}
	if !errors.Is(err, pgx.ErrNoRows) {
		return "", err
	}

	var newPhotoID int64
	if err := tx.QueryRow(ctx, `
		INSERT INTO photo(file_id, telegram_type, user_id)
		VALUES ($1, $2, $3)
		RETURNING id
	`, req.FileID, req.FileType, userID).Scan(&newPhotoID); err != nil {
		return "", err
	}

	if _, err := tx.Exec(ctx, `
		INSERT INTO group_photo(photo_id, group_id)
		VALUES ($1, $2)
		ON CONFLICT DO NOTHING
	`, newPhotoID, groupID); err != nil {
		return "", err
	}

	contestID, err := s.getContestID(ctx, tx, req.GroupID)
	if err != nil {
		return "", err
	}

	if _, err := tx.Exec(ctx, `
		INSERT INTO contest_participant(contest_id, user_id)
		VALUES ($1, $2)
		ON CONFLICT DO NOTHING
	`, contestID, userID); err != nil {
		return "", err
	}

	if err := tx.Commit(ctx); err != nil {
		return "", err
	}
	committed = true

	return model.ContestSubmissionStatusNew, nil
}

func (s *VoteStore) getRelativeContestPhoto(
	ctx context.Context, groupID int64, currentPhotoID int64, order string, compare string,
) (model.Photo, error) {
	query := `
		SELECT p.id, p.file_id, p.telegram_type
		FROM photo p
		JOIN group_photo gp ON p.id = gp.photo_id
		WHERE gp.group_id = (
			SELECT g.id
			FROM "group" g
			WHERE g.telegram_id = $1
		)
		AND p.id ` + compare + ` $2
		ORDER BY p.id ` + order + `
		LIMIT 1
	`

	var photo model.Photo
	err := s.pool.QueryRow(ctx, query, groupID, currentPhotoID).Scan(
		&photo.ID,
		&photo.FileID,
		&photo.FileType,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return model.Photo{}, model.ErrPhotoNotFound
	}
	return photo, err
}

func (s *VoteStore) getContestID(ctx context.Context, db queryable, groupID int64) (int64, error) {
	var contestID int64
	err := db.QueryRow(ctx, `
		SELECT c.id
		FROM contest c
		JOIN "group" g ON g.id = c.group_id
		WHERE g.telegram_id = $1
		ORDER BY c.id DESC
		LIMIT 1
	`, groupID).Scan(&contestID)
	if errors.Is(err, pgx.ErrNoRows) {
		return 0, model.ErrNoVoteYet
	}
	return contestID, err
}

func (s *VoteStore) getGroupID(ctx context.Context, db queryable, groupTelegramID int64) (int64, error) {
	var groupID int64
	err := db.QueryRow(ctx, `
		SELECT id
		FROM "group"
		WHERE telegram_id = $1
	`, groupTelegramID).Scan(&groupID)
	if errors.Is(err, pgx.ErrNoRows) {
		return 0, model.ErrGroupNotFound
	}
	return groupID, err
}

func (s *VoteStore) getUserID(ctx context.Context, db queryable, userTelegramID int64) (int64, error) {
	var userID int64
	err := db.QueryRow(ctx, `
		SELECT id
		FROM "user"
		WHERE telegram_id = $1
	`, userTelegramID).Scan(&userID)
	if errors.Is(err, pgx.ErrNoRows) {
		return 0, model.ErrUserNotFound
	}
	return userID, err
}

func (s *VoteStore) ensureUserInGroup(
	ctx context.Context,
	db queryable,
	groupID int64,
	userTelegramID int64,
	username string,
	fullName string,
) (int64, error) {
	userID, err := s.getUserID(ctx, db, userTelegramID)
	if errors.Is(err, model.ErrUserNotFound) {
		if err := db.QueryRow(ctx, `
			INSERT INTO "user"(name, full_name, telegram_id)
			VALUES ($1, $2, $3)
			RETURNING id
		`, username, fullName, userTelegramID).Scan(&userID); err != nil {
			return 0, err
		}
	} else if err != nil {
		return 0, err
	}

	if _, err := db.Exec(ctx, `
		INSERT INTO group_user(user_id, group_id)
		VALUES ($1, $2)
		ON CONFLICT DO NOTHING
	`, userID, groupID); err != nil {
		return 0, err
	}

	return userID, nil
}

func (s *VoteStore) getGroupPhotoByUser(
	ctx context.Context, db queryable, groupID int64, userID int64,
) (int64, error) {
	var photoID int64
	err := db.QueryRow(ctx, `
		SELECT p.id
		FROM photo p
		JOIN group_photo gp ON gp.photo_id = p.id
		WHERE gp.group_id = $1 AND p.user_id = $2
	`, groupID, userID).Scan(&photoID)
	return photoID, err
}
