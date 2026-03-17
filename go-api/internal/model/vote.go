package model

import "errors"

var (
	ErrNoPhotos      = errors.New("no_photos")
	ErrNoVoteYet     = errors.New("no_vote_yet")
	ErrAlreadyVoted  = errors.New("already_voted")
	ErrSelfLike      = errors.New("self_like")
	ErrPhotoNotFound = errors.New("photo_not_found")
	ErrGroupNotFound = errors.New("group_not_found")
	ErrUserNotFound  = errors.New("user_not_found")
)

type ContestSubmissionStatus string

const (
	ContestSubmissionStatusNew     ContestSubmissionStatus = "new"
	ContestSubmissionStatusChanged ContestSubmissionStatus = "changed"
)

type Photo struct {
	ID       int64
	FileID   string
	FileType string
}

type VotePhotoState struct {
	GroupID      int64  `json:"group_id"`
	PhotoID      int64  `json:"photo_id"`
	FileID       string `json:"file_id"`
	FileType     string `json:"file_type"`
	CurrentIndex int    `json:"current_index"`
	TotalPhotos  int    `json:"total_photos"`
	LikedState   int    `json:"liked_state"`
}

type LikeRequest struct {
	GroupID int64 `json:"group_id"`
	UserID  int64 `json:"user_id"`
	PhotoID int64 `json:"photo_id"`
}

type SubmitVoteRequest struct {
	GroupID int64 `json:"group_id"`
	UserID  int64 `json:"user_id"`
}

type ContestSubmissionRequest struct {
	GroupID  int64  `json:"group_id"`
	UserID   int64  `json:"user_id"`
	Username string `json:"username"`
	FullName string `json:"full_name"`
	FileID   string `json:"file_id"`
	FileType string `json:"file_type"`
}

type ContestSubmissionResponse struct {
	Status ContestSubmissionStatus `json:"status"`
}

type ErrorResponse struct {
	Code    string `json:"code"`
	Message string `json:"message,omitempty"`
}
