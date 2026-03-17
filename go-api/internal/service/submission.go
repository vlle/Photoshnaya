package service

import (
	"context"

	"go-api/internal/model"
)

type SubmissionStore interface {
	RegisterContestSubmission(context.Context, model.ContestSubmissionRequest) (model.ContestSubmissionStatus, error)
}

type SubmissionService struct {
	store SubmissionStore
}

func NewSubmissionService(store SubmissionStore) *SubmissionService {
	return &SubmissionService{store: store}
}

func (s *SubmissionService) RegisterContestSubmission(
	ctx context.Context, req model.ContestSubmissionRequest,
) (model.ContestSubmissionStatus, error) {
	return s.store.RegisterContestSubmission(ctx, req)
}
