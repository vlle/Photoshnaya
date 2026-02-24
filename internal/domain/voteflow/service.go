package voteflow

import (
	"context"
	"errors"
	"strconv"
	"strings"
)

const (
	StatusOK    = "ok"
	StatusAlert = "alert"
	StatusError = "error"
	StatusNoop  = "noop"

	CodeWrongLink       = "wrong_link"
	CodeNotPrivateChat  = "not_private_chat"
	CodeNoPhotos        = "no_photos"
	CodeNoVoteYet       = "no_vote_yet"
	CodeAlreadyVoted    = "already_voted"
	CodeVoteSelf        = "vote_self"
	CodeUnexpectedError = "unexpected_error"
	CodeGreetingVote    = "greeting_message_vote"
	CodeThanksForVote   = "thanks_for_vote"
	CodeNavigated       = "navigated"
	CodeLikeSet         = "like_set"
	CodeLikeUnset       = "like_unset"
	CodeBoundaryReached = "boundary_reached"
)

type PhotoRef struct {
	PhotoID   int64
	FileID    string
	MediaType string
}

type VoteState struct {
	GroupID           int64  `json:"group_id"`
	AmountPhotos      int    `json:"amount_photos"`
	CurrentPhotoID    int64  `json:"current_photo_id"`
	CurrentPhotoCount int    `json:"current_photo_count"`
	IsLikedPhoto      int    `json:"is_liked_photo"`
	MediaType         string `json:"media_type"`
	MediaFileID       string `json:"media_file_id"`
}

type ActionResult struct {
	Status string     `json:"status"`
	Code   string     `json:"code,omitempty"`
	State  *VoteState `json:"state,omitempty"`
}

type StartRequest struct {
	Text     string
	ChatType string
	UserID   int64
	UserName string
	FullName string
}

type NavigateRequest struct {
	Direction         string
	UserID            int64
	GroupID           int64
	CurrentPhotoID    int64
	CurrentPhotoCount int
	AmountPhotos      int
}

type LikeRequest struct {
	UserID            int64
	GroupID           int64
	CurrentPhotoID    int64
	CurrentPhotoCount int
	AmountPhotos      int
}

type SubmitRequest struct {
	UserID  int64
	GroupID int64
}

type Repository interface {
	CountContestPhotos(ctx context.Context, groupTelegramID int64) (int, error)
	GetCurrentVoteStatus(ctx context.Context, groupTelegramID int64) (bool, error)
	IsUserNotAllowedToVote(ctx context.Context, groupTelegramID int64, userTelegramID int64) (bool, error)
	RegisterUserInGroup(ctx context.Context, userName, fullName string, userTelegramID int64, groupTelegramID int64) error
	SelectNextContestPhoto(ctx context.Context, groupTelegramID int64, currentPhotoID int64) (PhotoRef, bool, error)
	SelectPrevContestPhoto(ctx context.Context, groupTelegramID int64, currentPhotoID int64) (PhotoRef, bool, error)
	SelectPhotoByID(ctx context.Context, photoID int64) (PhotoRef, error)
	IsPhotoLiked(ctx context.Context, userTelegramID int64, photoID int64) (int, error)
	LikePhoto(ctx context.Context, userTelegramID int64, photoID int64) (bool, error)
	RemoveLikePhoto(ctx context.Context, userTelegramID int64, photoID int64) error
	SubmitVote(ctx context.Context, userTelegramID int64, groupTelegramID int64) error
}

type Service struct {
	repo Repository
}

func NewService(repo Repository) *Service {
	return &Service{repo: repo}
}

func (s *Service) StartVoteSession(ctx context.Context, req StartRequest) ActionResult {
	groupID, err := parseStartGroupID(req.Text)
	if err != nil {
		return alert(CodeWrongLink)
	}
	if req.ChatType != "private" {
		return alert(CodeNotPrivateChat)
	}

	amountPhotos, err := s.repo.CountContestPhotos(ctx, groupID)
	if err != nil {
		return errResult(CodeUnexpectedError)
	}
	if amountPhotos == 0 {
		return alert(CodeNoPhotos)
	}

	voteInProgress, err := s.repo.GetCurrentVoteStatus(ctx, groupID)
	if err != nil {
		return errResult(CodeUnexpectedError)
	}
	if !voteInProgress {
		return alert(CodeNoVoteYet)
	}

	notAllowed, err := s.repo.IsUserNotAllowedToVote(ctx, groupID, req.UserID)
	if err != nil {
		return errResult(CodeUnexpectedError)
	}
	if notAllowed {
		return alert(CodeAlreadyVoted)
	}

	if err := s.repo.RegisterUserInGroup(ctx, req.UserName, req.FullName, req.UserID, groupID); err != nil {
		return errResult(CodeUnexpectedError)
	}

	photo, found, err := s.repo.SelectNextContestPhoto(ctx, groupID, 0)
	if err != nil {
		return errResult(CodeUnexpectedError)
	}
	if !found {
		return alert(CodeNoPhotos)
	}

	isLiked, err := s.repo.IsPhotoLiked(ctx, req.UserID, photo.PhotoID)
	if err != nil {
		return errResult(CodeUnexpectedError)
	}

	return ok(
		CodeGreetingVote,
		VoteState{
			GroupID:           groupID,
			AmountPhotos:      amountPhotos,
			CurrentPhotoID:    photo.PhotoID,
			CurrentPhotoCount: 1,
			IsLikedPhoto:      isLiked,
			MediaType:         photo.MediaType,
			MediaFileID:       photo.FileID,
		},
	)
}

func (s *Service) Navigate(ctx context.Context, req NavigateRequest) ActionResult {
	if req.AmountPhotos <= 0 {
		return noop(CodeBoundaryReached)
	}

	var newCount int
	switch req.Direction {
	case "next":
		if req.CurrentPhotoCount+1 > req.AmountPhotos {
			return noop(CodeBoundaryReached)
		}
		newCount = req.CurrentPhotoCount + 1
	case "prev":
		if req.CurrentPhotoCount-1 < 1 {
			return noop(CodeBoundaryReached)
		}
		newCount = req.CurrentPhotoCount - 1
	default:
		return errResult(CodeUnexpectedError)
	}

	var (
		photo PhotoRef
		found bool
		err   error
	)
	if req.Direction == "next" {
		photo, found, err = s.repo.SelectNextContestPhoto(ctx, req.GroupID, req.CurrentPhotoID)
	} else {
		photo, found, err = s.repo.SelectPrevContestPhoto(ctx, req.GroupID, req.CurrentPhotoID)
	}
	if err != nil {
		return errResult(CodeUnexpectedError)
	}
	if !found {
		return noop(CodeBoundaryReached)
	}

	isLiked, err := s.repo.IsPhotoLiked(ctx, req.UserID, photo.PhotoID)
	if err != nil {
		return errResult(CodeUnexpectedError)
	}

	return ok(
		CodeNavigated,
		VoteState{
			GroupID:           req.GroupID,
			AmountPhotos:      req.AmountPhotos,
			CurrentPhotoID:    photo.PhotoID,
			CurrentPhotoCount: newCount,
			IsLikedPhoto:      isLiked,
			MediaType:         photo.MediaType,
			MediaFileID:       photo.FileID,
		},
	)
}

func (s *Service) SetLike(ctx context.Context, req LikeRequest) ActionResult {
	selfLike, err := s.repo.LikePhoto(ctx, req.UserID, req.CurrentPhotoID)
	if err != nil {
		return errResult(CodeUnexpectedError)
	}
	if selfLike {
		return alert(CodeVoteSelf)
	}

	photo, err := s.repo.SelectPhotoByID(ctx, req.CurrentPhotoID)
	if err != nil {
		return errResult(CodeUnexpectedError)
	}
	isLiked, err := s.repo.IsPhotoLiked(ctx, req.UserID, req.CurrentPhotoID)
	if err != nil {
		return errResult(CodeUnexpectedError)
	}

	return ok(
		CodeLikeSet,
		VoteState{
			GroupID:           req.GroupID,
			AmountPhotos:      req.AmountPhotos,
			CurrentPhotoID:    req.CurrentPhotoID,
			CurrentPhotoCount: req.CurrentPhotoCount,
			IsLikedPhoto:      isLiked,
			MediaType:         photo.MediaType,
			MediaFileID:       photo.FileID,
		},
	)
}

func (s *Service) UnsetLike(ctx context.Context, req LikeRequest) ActionResult {
	if err := s.repo.RemoveLikePhoto(ctx, req.UserID, req.CurrentPhotoID); err != nil {
		return errResult(CodeUnexpectedError)
	}

	photo, err := s.repo.SelectPhotoByID(ctx, req.CurrentPhotoID)
	if err != nil {
		return errResult(CodeUnexpectedError)
	}
	isLiked, err := s.repo.IsPhotoLiked(ctx, req.UserID, req.CurrentPhotoID)
	if err != nil {
		return errResult(CodeUnexpectedError)
	}

	return ok(
		CodeLikeUnset,
		VoteState{
			GroupID:           req.GroupID,
			AmountPhotos:      req.AmountPhotos,
			CurrentPhotoID:    req.CurrentPhotoID,
			CurrentPhotoCount: req.CurrentPhotoCount,
			IsLikedPhoto:      isLiked,
			MediaType:         photo.MediaType,
			MediaFileID:       photo.FileID,
		},
	)
}

func (s *Service) SubmitVote(ctx context.Context, req SubmitRequest) ActionResult {
	notAllowed, err := s.repo.IsUserNotAllowedToVote(ctx, req.GroupID, req.UserID)
	if err != nil {
		return errResult(CodeUnexpectedError)
	}
	if notAllowed {
		return alert(CodeAlreadyVoted)
	}

	if err := s.repo.SubmitVote(ctx, req.UserID, req.GroupID); err != nil {
		return errResult(CodeUnexpectedError)
	}

	return ok(CodeThanksForVote, VoteState{GroupID: req.GroupID})
}

func parseStartGroupID(text string) (int64, error) {
	startData := strings.Fields(strings.ReplaceAll(text, "_", " "))
	if len(startData) != 3 {
		return 0, errors.New("wrong deep-link format")
	}
	groupID, err := strconv.ParseInt(startData[1], 10, 64)
	if err != nil {
		return 0, err
	}
	return groupID, nil
}

func ok(code string, state VoteState) ActionResult {
	return ActionResult{Status: StatusOK, Code: code, State: &state}
}

func alert(code string) ActionResult {
	return ActionResult{Status: StatusAlert, Code: code}
}

func noop(code string) ActionResult {
	return ActionResult{Status: StatusNoop, Code: code}
}

func errResult(code string) ActionResult {
	return ActionResult{Status: StatusError, Code: code}
}
