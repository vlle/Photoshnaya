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

type fakeSubmissionService struct {
	status model.ContestSubmissionStatus
	err    error
}

func (f fakeSubmissionService) RegisterContestSubmission(
	context.Context, model.ContestSubmissionRequest,
) (model.ContestSubmissionStatus, error) {
	return f.status, f.err
}

func TestContestSubmissionReturnsNewStatus(t *testing.T) {
	t.Parallel()

	handler := NewSubmissionHandler(
		fakeSubmissionService{status: model.ContestSubmissionStatusNew},
		slog.New(slog.NewTextHandler(io.Discard, nil)),
	)

	body := bytes.NewBufferString(`{"group_id":100,"user_id":42,"username":"user","full_name":"User Name","file_id":"file-1","file_type":"photo"}`)
	req := httptest.NewRequest(http.MethodPost, "/contest/submissions", body)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("unexpected status: %d", rec.Code)
	}

	var response model.ContestSubmissionResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if response.Status != model.ContestSubmissionStatusNew {
		t.Fatalf("unexpected response status: %s", response.Status)
	}
}

func TestContestSubmissionReturnsChangedStatus(t *testing.T) {
	t.Parallel()

	handler := NewSubmissionHandler(
		fakeSubmissionService{status: model.ContestSubmissionStatusChanged},
		slog.New(slog.NewTextHandler(io.Discard, nil)),
	)

	body := bytes.NewBufferString(`{"group_id":100,"user_id":42,"username":"user","full_name":"User Name","file_id":"file-2","file_type":"document"}`)
	req := httptest.NewRequest(http.MethodPost, "/contest/submissions", body)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("unexpected status: %d", rec.Code)
	}
}

func TestContestSubmissionGroupNotFound(t *testing.T) {
	t.Parallel()

	handler := NewSubmissionHandler(
		fakeSubmissionService{err: model.ErrGroupNotFound},
		slog.New(slog.NewTextHandler(io.Discard, nil)),
	)

	body := bytes.NewBufferString(`{"group_id":100,"user_id":42,"username":"user","full_name":"User Name","file_id":"file-1","file_type":"photo"}`)
	req := httptest.NewRequest(http.MethodPost, "/contest/submissions", body)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Fatalf("unexpected status: %d", rec.Code)
	}
}

func TestContestSubmissionInternalError(t *testing.T) {
	t.Parallel()

	handler := NewSubmissionHandler(
		fakeSubmissionService{err: errors.New("boom")},
		slog.New(slog.NewTextHandler(io.Discard, nil)),
	)

	body := bytes.NewBufferString(`{"group_id":100,"user_id":42,"username":"user","full_name":"User Name","file_id":"file-1","file_type":"photo"}`)
	req := httptest.NewRequest(http.MethodPost, "/contest/submissions", body)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("unexpected status: %d", rec.Code)
	}
}
