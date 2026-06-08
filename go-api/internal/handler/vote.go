package handler

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"strconv"

	"go-api/internal/model"
)

type VoteService interface {
	GetVoteSession(context.Context, int64, int64) (model.VotePhotoState, error)
	GetNextVotePhoto(context.Context, int64, int64, int64) (model.VotePhotoState, error)
	GetPrevVotePhoto(context.Context, int64, int64, int64) (model.VotePhotoState, error)
	SetLike(context.Context, int64, int64, int64) error
	UnsetLike(context.Context, int64, int64, int64) error
	SubmitVote(context.Context, int64, int64) error
}

type VoteHandler struct {
	service VoteService
	logger  *slog.Logger
}

func NewVoteHandler(service VoteService, logger *slog.Logger) http.Handler {
	handler := &VoteHandler{
		service: service,
		logger:  logger,
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/vote/session", handler.handleVoteSession)
	mux.HandleFunc("/vote/photos/next", handler.handleVoteNext)
	mux.HandleFunc("/vote/photos/prev", handler.handleVotePrev)
	mux.HandleFunc("/vote/likes", handler.handleVoteLikes)
	mux.HandleFunc("/vote/submit", handler.handleVoteSubmit)
	return mux
}

func (h *VoteHandler) handleVoteSession(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}

	groupID, err := parseIntQuery(r, "group_id")
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_group_id")
		return
	}
	userID, err := parseIntQuery(r, "user_id")
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_user_id")
		return
	}

	state, err := h.service.GetVoteSession(r.Context(), groupID, userID)
	if err != nil {
		h.writeServiceError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, state)
}

func (h *VoteHandler) handleVoteNext(w http.ResponseWriter, r *http.Request) {
	h.handleVotePhoto(w, r, true)
}

func (h *VoteHandler) handleVotePrev(w http.ResponseWriter, r *http.Request) {
	h.handleVotePhoto(w, r, false)
}

func (h *VoteHandler) handleVotePhoto(w http.ResponseWriter, r *http.Request, next bool) {
	if r.Method != http.MethodGet {
		writeError(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}

	groupID, err := parseIntQuery(r, "group_id")
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_group_id")
		return
	}
	userID, err := parseIntQuery(r, "user_id")
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_user_id")
		return
	}
	currentPhotoID, err := parseIntQuery(r, "current_photo_id")
	if err != nil {
		writeError(w, http.StatusBadRequest, "invalid_current_photo_id")
		return
	}

	var state model.VotePhotoState
	if next {
		state, err = h.service.GetNextVotePhoto(r.Context(), groupID, userID, currentPhotoID)
	} else {
		state, err = h.service.GetPrevVotePhoto(r.Context(), groupID, userID, currentPhotoID)
	}
	if err != nil {
		h.writeServiceError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, state)
}

func (h *VoteHandler) handleVoteLikes(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost && r.Method != http.MethodDelete {
		writeError(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}

	var req model.LikeRequest
	if err := decodeJSON(w, r.Body, &req); err != nil {
		if isMaxBytesError(err) {
			writeError(w, http.StatusRequestEntityTooLarge, "request_too_large")
			return
		}
		writeError(w, http.StatusBadRequest, "invalid_request")
		return
	}

	var err error
	if r.Method == http.MethodPost {
		err = h.service.SetLike(r.Context(), req.GroupID, req.UserID, req.PhotoID)
	} else {
		err = h.service.UnsetLike(r.Context(), req.GroupID, req.UserID, req.PhotoID)
	}
	if err != nil {
		h.writeServiceError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (h *VoteHandler) handleVoteSubmit(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}

	var req model.SubmitVoteRequest
	if err := decodeJSON(w, r.Body, &req); err != nil {
		if isMaxBytesError(err) {
			writeError(w, http.StatusRequestEntityTooLarge, "request_too_large")
			return
		}
		writeError(w, http.StatusBadRequest, "invalid_request")
		return
	}

	if err := h.service.SubmitVote(r.Context(), req.GroupID, req.UserID); err != nil {
		h.writeServiceError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (h *VoteHandler) writeServiceError(w http.ResponseWriter, err error) {
	status := http.StatusInternalServerError
	code := "internal_error"

	switch {
	case errors.Is(err, model.ErrNoPhotos):
		status = http.StatusNotFound
		code = "no_photos"
	case errors.Is(err, model.ErrNoVoteYet):
		status = http.StatusConflict
		code = "no_vote_yet"
	case errors.Is(err, model.ErrAlreadyVoted):
		status = http.StatusConflict
		code = "already_voted"
	case errors.Is(err, model.ErrSelfLike):
		status = http.StatusConflict
		code = "self_like"
	case errors.Is(err, model.ErrPhotoNotFound):
		status = http.StatusNotFound
		code = "photo_not_found"
	case errors.Is(err, model.ErrUserNotFound):
		status = http.StatusNotFound
		code = "user_not_found"
	default:
		h.logger.Error("unexpected vote handler error", "error", err)
	}

	writeError(w, status, code)
}

func parseIntQuery(r *http.Request, key string) (int64, error) {
	value := r.URL.Query().Get(key)
	return strconv.ParseInt(value, 10, 64)
}

const maxBodySize = 1 << 20 // 1 MB

func decodeJSON(w http.ResponseWriter, body io.ReadCloser, dest any) error {
	limited := http.MaxBytesReader(w, body, maxBodySize)
	defer func() {
		_ = limited.Close()
	}()

	data, err := io.ReadAll(limited)
	if err != nil {
		return err // MaxBytesError propagates cleanly
	}

	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.DisallowUnknownFields()
	return decoder.Decode(dest)
}

func isMaxBytesError(err error) bool {
	var maxBytesErr *http.MaxBytesError
	return errors.As(err, &maxBytesErr)
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func writeError(w http.ResponseWriter, status int, code string) {
	writeJSON(w, status, model.ErrorResponse{Code: code})
}
