package handler

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"testing"

	"go-api/internal/model"
)

type fakeVoteService struct {
	sessionState model.VotePhotoState
	nextState    model.VotePhotoState
	sessionErr   error
	likeErr      error
	submitErr    error
}

func (f fakeVoteService) GetVoteSession(context.Context, int64, int64) (model.VotePhotoState, error) {
	return f.sessionState, f.sessionErr
}

func (f fakeVoteService) GetNextVotePhoto(context.Context, int64, int64, int64) (model.VotePhotoState, error) {
	return f.nextState, nil
}

func (f fakeVoteService) GetPrevVotePhoto(context.Context, int64, int64, int64) (model.VotePhotoState, error) {
	return f.nextState, nil
}

func (f fakeVoteService) SetLike(context.Context, int64, int64, int64) error {
	return f.likeErr
}

func (f fakeVoteService) UnsetLike(context.Context, int64, int64, int64) error {
	return nil
}

func (f fakeVoteService) SubmitVote(context.Context, int64, int64) error {
	return f.submitErr
}

func TestVoteSessionSuccess(t *testing.T) {
	t.Parallel()

	handler := NewVoteHandler(fakeVoteService{
		sessionState: model.VotePhotoState{
			GroupID:      100,
			PhotoID:      12,
			FileID:       "file-1",
			FileType:     "photo",
			CurrentIndex: 1,
			TotalPhotos:  5,
			LikedState:   0,
		},
	}, slog.New(slog.NewTextHandler(io.Discard, nil)))

	req := httptest.NewRequest(http.MethodGet, "/vote/session?group_id=100&user_id=42", nil)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("unexpected status: %d", rec.Code)
	}

	var response model.VotePhotoState
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if response.PhotoID != 12 || response.TotalPhotos != 5 {
		t.Fatalf("unexpected response payload: %+v", response)
	}
}

func TestVoteSessionBusinessError(t *testing.T) {
	t.Parallel()

	handler := NewVoteHandler(fakeVoteService{
		sessionErr: model.ErrNoPhotos,
	}, slog.New(slog.NewTextHandler(io.Discard, nil)))

	req := httptest.NewRequest(http.MethodGet, "/vote/session?group_id=100&user_id=42", nil)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Fatalf("unexpected status: %d", rec.Code)
	}

	var response model.ErrorResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if response.Code != "no_photos" {
		t.Fatalf("unexpected error code: %s", response.Code)
	}
}

func TestSetLikeSelfLikeError(t *testing.T) {
	t.Parallel()

	handler := NewVoteHandler(fakeVoteService{
		likeErr: model.ErrSelfLike,
	}, slog.New(slog.NewTextHandler(io.Discard, nil)))

	body := bytes.NewBufferString(`{"group_id":100,"user_id":42,"photo_id":12}`)
	req := httptest.NewRequest(http.MethodPost, "/vote/likes", body)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusConflict {
		t.Fatalf("unexpected status: %d", rec.Code)
	}
}

func TestSubmitVoteAlreadyVoted(t *testing.T) {
	t.Parallel()

	handler := NewVoteHandler(fakeVoteService{
		submitErr: model.ErrAlreadyVoted,
	}, slog.New(slog.NewTextHandler(io.Discard, nil)))

	body := bytes.NewBufferString(`{"group_id":100,"user_id":42}`)
	req := httptest.NewRequest(http.MethodPost, "/vote/submit", body)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusConflict {
		t.Fatalf("unexpected status: %d", rec.Code)
	}
}

func TestUnexpectedErrorReturnsInternalServerError(t *testing.T) {
	t.Parallel()

	handler := NewVoteHandler(fakeVoteService{
		submitErr: errors.New("boom"),
	}, slog.New(slog.NewTextHandler(io.Discard, nil)))

	body := bytes.NewBufferString(`{"group_id":100,"user_id":42}`)
	req := httptest.NewRequest(http.MethodPost, "/vote/submit", body)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("unexpected status: %d", rec.Code)
	}
}
