package repo

import (
	"context"
	"errors"
	"fmt"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/vlle/Photoshnaya/internal/domain/voteflow"
)

type VoteRepo struct {
	pool *pgxpool.Pool
}

func NewVoteRepo(pool *pgxpool.Pool) *VoteRepo {
	return &VoteRepo{pool: pool}
}

func (r *VoteRepo) CountContestPhotos(ctx context.Context, groupTelegramID int64) (int, error) {
	const query = `
SELECT COUNT(gp.photo_id)
FROM group_photo gp
JOIN "group" g ON gp.group_id = g.id
WHERE g.telegram_id = $1`

	var count int
	if err := r.pool.QueryRow(ctx, query, groupTelegramID).Scan(&count); err != nil {
		return 0, err
	}
	return count, nil
}

func (r *VoteRepo) GetCurrentVoteStatus(ctx context.Context, groupTelegramID int64) (bool, error) {
	const query = `SELECT vote_in_progress FROM "group" WHERE telegram_id = $1 LIMIT 1`

	var voteInProgress bool
	err := r.pool.QueryRow(ctx, query, groupTelegramID).Scan(&voteInProgress)
	if errors.Is(err, pgx.ErrNoRows) {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	return voteInProgress, nil
}

func (r *VoteRepo) IsUserNotAllowedToVote(ctx context.Context, groupTelegramID int64, userTelegramID int64) (bool, error) {
	contestID, err := r.getContestID(ctx, r.pool, groupTelegramID)
	if err != nil {
		return false, err
	}
	if contestID == -1 {
		return false, nil
	}

	userID, err := r.getUserID(ctx, r.pool, userTelegramID)
	if err != nil {
		return false, err
	}
	if userID == -1 {
		return false, nil
	}

	const query = `
SELECT EXISTS(
	SELECT 1
	FROM contest_user
	WHERE user_id = $1 AND contest_id = $2
)`
	var exists bool
	if err := r.pool.QueryRow(ctx, query, userID, contestID).Scan(&exists); err != nil {
		return false, err
	}
	return exists, nil
}

func (r *VoteRepo) RegisterUserInGroup(ctx context.Context, userName, fullName string, userTelegramID int64, groupTelegramID int64) error {
	groupID, err := r.getGroupID(ctx, r.pool, groupTelegramID)
	if err != nil {
		return err
	}
	if groupID == -1 {
		return fmt.Errorf("group with telegram_id=%d not found", groupTelegramID)
	}

	userID, err := r.getUserID(ctx, r.pool, userTelegramID)
	if err != nil {
		return err
	}
	if userID == -1 {
		const insertUserQuery = `
INSERT INTO "user" (name, full_name, telegram_id)
VALUES ($1, $2, $3)
RETURNING id`
		if err := r.pool.QueryRow(ctx, insertUserQuery, userName, fullName, userTelegramID).Scan(&userID); err != nil {
			return err
		}
	}

	const insertGroupUserQuery = `
INSERT INTO group_user (user_id, group_id)
VALUES ($1, $2)
ON CONFLICT (user_id, group_id) DO NOTHING`
	if _, err := r.pool.Exec(ctx, insertGroupUserQuery, userID, groupID); err != nil {
		return err
	}

	return nil
}

func (r *VoteRepo) SelectNextContestPhoto(ctx context.Context, groupTelegramID int64, currentPhotoID int64) (voteflow.PhotoRef, bool, error) {
	const query = `
SELECT p.id, p.file_id, p.telegram_type
FROM photo p
JOIN group_photo gp ON p.id = gp.photo_id
WHERE gp.group_id = (
	SELECT id FROM "group" WHERE telegram_id = $1
)
  AND p.id > $2
ORDER BY p.id ASC
LIMIT 1`

	var photo voteflow.PhotoRef
	err := r.pool.QueryRow(ctx, query, groupTelegramID, currentPhotoID).Scan(&photo.PhotoID, &photo.FileID, &photo.MediaType)
	if errors.Is(err, pgx.ErrNoRows) {
		return voteflow.PhotoRef{}, false, nil
	}
	if err != nil {
		return voteflow.PhotoRef{}, false, err
	}
	return photo, true, nil
}

func (r *VoteRepo) SelectPrevContestPhoto(ctx context.Context, groupTelegramID int64, currentPhotoID int64) (voteflow.PhotoRef, bool, error) {
	const query = `
SELECT p.id, p.file_id, p.telegram_type
FROM photo p
JOIN group_photo gp ON p.id = gp.photo_id
WHERE gp.group_id = (
	SELECT id FROM "group" WHERE telegram_id = $1
)
  AND p.id < $2
ORDER BY p.id DESC
LIMIT 1`

	var photo voteflow.PhotoRef
	err := r.pool.QueryRow(ctx, query, groupTelegramID, currentPhotoID).Scan(&photo.PhotoID, &photo.FileID, &photo.MediaType)
	if errors.Is(err, pgx.ErrNoRows) {
		return voteflow.PhotoRef{}, false, nil
	}
	if err != nil {
		return voteflow.PhotoRef{}, false, err
	}
	return photo, true, nil
}

func (r *VoteRepo) SelectPhotoByID(ctx context.Context, photoID int64) (voteflow.PhotoRef, error) {
	const query = `
SELECT p.id, p.file_id, p.telegram_type
FROM photo p
WHERE p.id = $1`

	var photo voteflow.PhotoRef
	if err := r.pool.QueryRow(ctx, query, photoID).Scan(&photo.PhotoID, &photo.FileID, &photo.MediaType); err != nil {
		return voteflow.PhotoRef{}, err
	}
	return photo, nil
}

func (r *VoteRepo) IsPhotoLiked(ctx context.Context, userTelegramID int64, photoID int64) (int, error) {
	const countQuery = `
SELECT COUNT(*)
FROM tmp_photo_like tpl
JOIN "user" u ON tpl.user_id = u.id
JOIN photo p ON tpl.photo_id = p.id
WHERE u.telegram_id = $1 AND p.id = $2`

	var likes int
	if err := r.pool.QueryRow(ctx, countQuery, userTelegramID, photoID).Scan(&likes); err != nil {
		return 0, err
	}

	const ownerQuery = `
SELECT u.telegram_id
FROM "user" u
JOIN photo p ON u.id = p.user_id
WHERE p.id = $1`
	var ownerTelegramID int64
	if err := r.pool.QueryRow(ctx, ownerQuery, photoID).Scan(&ownerTelegramID); err != nil {
		return 0, err
	}

	if ownerTelegramID == userTelegramID {
		return -1, nil
	}
	return likes, nil
}

func (r *VoteRepo) LikePhoto(ctx context.Context, userTelegramID int64, photoID int64) (bool, error) {
	userID, err := r.getUserID(ctx, r.pool, userTelegramID)
	if err != nil {
		return false, err
	}
	if userID == -1 {
		return false, fmt.Errorf("user with telegram_id=%d not found", userTelegramID)
	}

	const ownerQuery = `
SELECT u.telegram_id
FROM photo p
JOIN "user" u ON p.user_id = u.id
WHERE p.id = $1`
	var ownerTelegramID int64
	if err := r.pool.QueryRow(ctx, ownerQuery, photoID).Scan(&ownerTelegramID); err != nil {
		return false, err
	}
	if ownerTelegramID == userTelegramID {
		return true, nil
	}

	const insertQuery = `
INSERT INTO tmp_photo_like (user_id, photo_id)
VALUES ($1, $2)
ON CONFLICT (user_id, photo_id) DO NOTHING`
	if _, err := r.pool.Exec(ctx, insertQuery, userID, photoID); err != nil {
		return false, err
	}

	return false, nil
}

func (r *VoteRepo) RemoveLikePhoto(ctx context.Context, userTelegramID int64, photoID int64) error {
	const deleteQuery = `
DELETE FROM tmp_photo_like
WHERE user_id = (
	SELECT id FROM "user" WHERE telegram_id = $1
)
  AND photo_id = $2`
	_, err := r.pool.Exec(ctx, deleteQuery, userTelegramID, photoID)
	return err
}

func (r *VoteRepo) SubmitVote(ctx context.Context, userTelegramID int64, groupTelegramID int64) error {
	tx, err := r.pool.Begin(ctx)
	if err != nil {
		return err
	}
	defer func() {
		_ = tx.Rollback(ctx)
	}()

	const insertLikesQuery = `
INSERT INTO photo_like (user_id, photo_id)
SELECT tpl.user_id, tpl.photo_id
FROM tmp_photo_like tpl
JOIN "user" u ON u.id = tpl.user_id
JOIN group_photo gp ON tpl.photo_id = gp.photo_id
JOIN photo p ON p.id = tpl.photo_id
JOIN "group" g ON g.id = gp.group_id
WHERE g.telegram_id = $2
  AND u.telegram_id = $1
ON CONFLICT (user_id, photo_id) DO NOTHING`
	if _, err := tx.Exec(ctx, insertLikesQuery, userTelegramID, groupTelegramID); err != nil {
		return err
	}

	const deleteTmpQuery = `
DELETE FROM tmp_photo_like tpl
USING "user" u, group_photo gp, "group" g
WHERE tpl.user_id = u.id
  AND tpl.photo_id = gp.photo_id
  AND gp.group_id = g.id
  AND u.telegram_id = $1
  AND g.telegram_id = $2`
	if _, err := tx.Exec(ctx, deleteTmpQuery, userTelegramID, groupTelegramID); err != nil {
		return err
	}

	contestID, err := r.getContestID(ctx, tx, groupTelegramID)
	if err != nil {
		return err
	}
	if contestID == -1 {
		return fmt.Errorf("contest for group telegram_id=%d not found", groupTelegramID)
	}

	userID, err := r.getUserID(ctx, tx, userTelegramID)
	if err != nil {
		return err
	}
	if userID == -1 {
		return fmt.Errorf("user with telegram_id=%d not found", userTelegramID)
	}

	const markVotedQuery = `
INSERT INTO contest_user (contest_id, user_id)
VALUES ($1, $2)
ON CONFLICT (contest_id, user_id) DO NOTHING`
	if _, err := tx.Exec(ctx, markVotedQuery, contestID, userID); err != nil {
		return err
	}

	return tx.Commit(ctx)
}

type queryRunner interface {
	QueryRow(ctx context.Context, sql string, args ...any) pgx.Row
}

func (r *VoteRepo) getContestID(ctx context.Context, runner queryRunner, groupTelegramID int64) (int64, error) {
	const query = `
SELECT c.id
FROM contest c
JOIN "group" g ON g.id = c.group_id
WHERE g.telegram_id = $1
ORDER BY c.id DESC
LIMIT 1`

	var contestID int64
	err := runner.QueryRow(ctx, query, groupTelegramID).Scan(&contestID)
	if errors.Is(err, pgx.ErrNoRows) {
		return -1, nil
	}
	if err != nil {
		return 0, err
	}
	return contestID, nil
}

func (r *VoteRepo) getUserID(ctx context.Context, runner queryRunner, userTelegramID int64) (int64, error) {
	const query = `
SELECT id
FROM "user"
WHERE telegram_id = $1
LIMIT 1`

	var userID int64
	err := runner.QueryRow(ctx, query, userTelegramID).Scan(&userID)
	if errors.Is(err, pgx.ErrNoRows) {
		return -1, nil
	}
	if err != nil {
		return 0, err
	}
	return userID, nil
}

func (r *VoteRepo) getGroupID(ctx context.Context, runner queryRunner, groupTelegramID int64) (int64, error) {
	const query = `
SELECT id
FROM "group"
WHERE telegram_id = $1
LIMIT 1`

	var groupID int64
	err := runner.QueryRow(ctx, query, groupTelegramID).Scan(&groupID)
	if errors.Is(err, pgx.ErrNoRows) {
		return -1, nil
	}
	if err != nil {
		return 0, err
	}
	return groupID, nil
}
