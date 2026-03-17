package handler

import (
	"context"
	"errors"
	"log/slog"
	"net/http"

	"go-api/internal/model"
)

type SubmissionService interface {
	RegisterContestSubmission(context.Context, model.ContestSubmissionRequest) (model.ContestSubmissionStatus, error)
}

type SubmissionHandler struct {
	service SubmissionService
	logger  *slog.Logger
}

func NewSubmissionHandler(service SubmissionService, logger *slog.Logger) http.Handler {
	handler := &SubmissionHandler{
		service: service,
		logger:  logger,
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/contest/submissions", handler.handleContestSubmission)
	return mux
}

func (h *SubmissionHandler) handleContestSubmission(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, http.StatusMethodNotAllowed, "method_not_allowed")
		return
	}

	var req model.ContestSubmissionRequest
	if err := decodeJSON(r.Body, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_request")
		return
	}

	status, err := h.service.RegisterContestSubmission(r.Context(), req)
	if err != nil {
		h.writeSubmissionError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, model.ContestSubmissionResponse{Status: status})
}

func (h *SubmissionHandler) writeSubmissionError(w http.ResponseWriter, err error) {
	status := http.StatusInternalServerError
	code := "internal_error"

	switch {
	case errors.Is(err, model.ErrGroupNotFound):
		status = http.StatusNotFound
		code = "group_not_found"
	case errors.Is(err, model.ErrUserNotFound):
		status = http.StatusNotFound
		code = "user_not_found"
	default:
		h.logger.Error("unexpected submission handler error", "error", err)
	}

	writeError(w, status, code)
}
