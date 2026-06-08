package service

import (
	"context"

	"go-api/internal/model"
)

type Store interface {
	ListContestPhotoIDs(context.Context, int64) ([]int64, error)
	GetPhotoByID(context.Context, int64) (model.Photo, error)
	GetNextContestPhoto(context.Context, int64, int64) (model.Photo, error)
	GetPrevContestPhoto(context.Context, int64, int64) (model.Photo, error)
	IsVoteActive(context.Context, int64) (bool, error)
	HasUserVoted(context.Context, int64, int64) (bool, error)
	GetPhotoLikedState(context.Context, int64, int64) (int, error)
	SetLike(context.Context, int64, int64) error
	UnsetLike(context.Context, int64, int64) error
	SubmitVote(context.Context, int64, int64) error
}

type VoteService struct {
	store Store
}

func NewVoteService(store Store) *VoteService {
	return &VoteService{store: store}
}

func (s *VoteService) GetVoteSession(ctx context.Context, groupID int64, userID int64) (model.VotePhotoState, error) {
	photoIDs, err := s.store.ListContestPhotoIDs(ctx, groupID)
	if err != nil {
		return model.VotePhotoState{}, err
	}
	if len(photoIDs) == 0 {
		return model.VotePhotoState{}, model.ErrNoPhotos
	}

	active, err := s.store.IsVoteActive(ctx, groupID)
	if err != nil {
		return model.VotePhotoState{}, err
	}
	if !active {
		return model.VotePhotoState{}, model.ErrNoVoteYet
	}

	voted, err := s.store.HasUserVoted(ctx, groupID, userID)
	if err != nil {
		return model.VotePhotoState{}, err
	}
	if voted {
		return model.VotePhotoState{}, model.ErrAlreadyVoted
	}

	photo, err := s.store.GetPhotoByID(ctx, photoIDs[0])
	if err != nil {
		return model.VotePhotoState{}, err
	}

	return s.buildVotePhotoState(ctx, groupID, userID, photo, photoIDs)
}

func (s *VoteService) GetNextVotePhoto(ctx context.Context, groupID int64, userID int64, currentPhotoID int64) (model.VotePhotoState, error) {
	photoIDs, err := s.store.ListContestPhotoIDs(ctx, groupID)
	if err != nil {
		return model.VotePhotoState{}, err
	}
	if len(photoIDs) == 0 {
		return model.VotePhotoState{}, model.ErrNoPhotos
	}

	photo, err := s.store.GetNextContestPhoto(ctx, groupID, currentPhotoID)
	if err != nil {
		return model.VotePhotoState{}, err
	}

	return s.buildVotePhotoState(ctx, groupID, userID, photo, photoIDs)
}

func (s *VoteService) GetPrevVotePhoto(ctx context.Context, groupID int64, userID int64, currentPhotoID int64) (model.VotePhotoState, error) {
	photoIDs, err := s.store.ListContestPhotoIDs(ctx, groupID)
	if err != nil {
		return model.VotePhotoState{}, err
	}
	if len(photoIDs) == 0 {
		return model.VotePhotoState{}, model.ErrNoPhotos
	}

	photo, err := s.store.GetPrevContestPhoto(ctx, groupID, currentPhotoID)
	if err != nil {
		return model.VotePhotoState{}, err
	}

	return s.buildVotePhotoState(ctx, groupID, userID, photo, photoIDs)
}

func (s *VoteService) SetLike(ctx context.Context, groupID int64, userID int64, photoID int64) error {
	_ = groupID
	return s.store.SetLike(ctx, userID, photoID)
}

func (s *VoteService) UnsetLike(ctx context.Context, groupID int64, userID int64, photoID int64) error {
	_ = groupID
	return s.store.UnsetLike(ctx, userID, photoID)
}

func (s *VoteService) SubmitVote(ctx context.Context, groupID int64, userID int64) error {
	return s.store.SubmitVote(ctx, groupID, userID)
}

func (s *VoteService) buildVotePhotoState(
	ctx context.Context, groupID int64, userID int64, photo model.Photo, photoIDs []int64,
) (model.VotePhotoState, error) {
	currentIndex := findPhotoIndex(photoIDs, photo.ID)
	if currentIndex == 0 {
		return model.VotePhotoState{}, model.ErrPhotoNotFound
	}

	likedState, err := s.store.GetPhotoLikedState(ctx, userID, photo.ID)
	if err != nil {
		return model.VotePhotoState{}, err
	}

	return model.VotePhotoState{
		GroupID:      groupID,
		PhotoID:      photo.ID,
		FileID:       photo.FileID,
		FileType:     photo.FileType,
		CurrentIndex: currentIndex,
		TotalPhotos:  len(photoIDs),
		LikedState:   likedState,
	}, nil
}

func findPhotoIndex(photoIDs []int64, photoID int64) int {
	for index, currentID := range photoIDs {
		if currentID == photoID {
			return index + 1
		}
	}
	return 0
}
