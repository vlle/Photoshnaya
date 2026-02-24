package voteflow

import (
	"context"
	"errors"
	"testing"
)

type fakeRepo struct {
	countPhotos     int
	voteInProgress  bool
	alreadyVoted    bool
	startPhoto      PhotoRef
	startPhotoFound bool
	likedState      int
	likeSelf        bool
	submitErr       error
	genericErr      error
}

func (f *fakeRepo) CountContestPhotos(context.Context, int64) (int, error) {
	if f.genericErr != nil {
		return 0, f.genericErr
	}
	return f.countPhotos, nil
}

func (f *fakeRepo) GetCurrentVoteStatus(context.Context, int64) (bool, error) {
	if f.genericErr != nil {
		return false, f.genericErr
	}
	return f.voteInProgress, nil
}

func (f *fakeRepo) IsUserNotAllowedToVote(context.Context, int64, int64) (bool, error) {
	if f.genericErr != nil {
		return false, f.genericErr
	}
	return f.alreadyVoted, nil
}

func (f *fakeRepo) RegisterUserInGroup(context.Context, string, string, int64, int64) error {
	return f.genericErr
}

func (f *fakeRepo) SelectNextContestPhoto(context.Context, int64, int64) (PhotoRef, bool, error) {
	if f.genericErr != nil {
		return PhotoRef{}, false, f.genericErr
	}
	return f.startPhoto, f.startPhotoFound, nil
}

func (f *fakeRepo) SelectPrevContestPhoto(context.Context, int64, int64) (PhotoRef, bool, error) {
	if f.genericErr != nil {
		return PhotoRef{}, false, f.genericErr
	}
	return f.startPhoto, f.startPhotoFound, nil
}

func (f *fakeRepo) SelectPhotoByID(context.Context, int64) (PhotoRef, error) {
	if f.genericErr != nil {
		return PhotoRef{}, f.genericErr
	}
	return f.startPhoto, nil
}

func (f *fakeRepo) IsPhotoLiked(context.Context, int64, int64) (int, error) {
	if f.genericErr != nil {
		return 0, f.genericErr
	}
	return f.likedState, nil
}

func (f *fakeRepo) LikePhoto(context.Context, int64, int64) (bool, error) {
	if f.genericErr != nil {
		return false, f.genericErr
	}
	return f.likeSelf, nil
}

func (f *fakeRepo) RemoveLikePhoto(context.Context, int64, int64) error {
	return f.genericErr
}

func (f *fakeRepo) SubmitVote(context.Context, int64, int64) error {
	if f.submitErr != nil {
		return f.submitErr
	}
	return f.genericErr
}

func TestStartVoteWrongLink(t *testing.T) {
	svc := NewService(&fakeRepo{})
	res := svc.StartVoteSession(context.Background(), StartRequest{
		Text: "/start bad",
	})
	if res.Status != StatusAlert || res.Code != CodeWrongLink {
		t.Fatalf("unexpected response: %+v", res)
	}
}

func TestStartVoteNotPrivateChat(t *testing.T) {
	svc := NewService(&fakeRepo{})
	res := svc.StartVoteSession(context.Background(), StartRequest{
		Text:     "/start 100_3",
		ChatType: "group",
	})
	if res.Status != StatusAlert || res.Code != CodeNotPrivateChat {
		t.Fatalf("unexpected response: %+v", res)
	}
}

func TestStartVoteNoPhotos(t *testing.T) {
	svc := NewService(&fakeRepo{countPhotos: 0, voteInProgress: true})
	res := svc.StartVoteSession(context.Background(), StartRequest{
		Text:     "/start 100_3",
		ChatType: "private",
	})
	if res.Status != StatusAlert || res.Code != CodeNoPhotos {
		t.Fatalf("unexpected response: %+v", res)
	}
}

func TestStartVoteInactive(t *testing.T) {
	svc := NewService(&fakeRepo{countPhotos: 2, voteInProgress: false})
	res := svc.StartVoteSession(context.Background(), StartRequest{
		Text:     "/start 100_3",
		ChatType: "private",
	})
	if res.Status != StatusAlert || res.Code != CodeNoVoteYet {
		t.Fatalf("unexpected response: %+v", res)
	}
}

func TestSetLikeSelfBlocked(t *testing.T) {
	svc := NewService(&fakeRepo{likeSelf: true})
	res := svc.SetLike(context.Background(), LikeRequest{
		UserID:            7,
		GroupID:           10,
		CurrentPhotoID:    2,
		CurrentPhotoCount: 1,
		AmountPhotos:      3,
	})
	if res.Status != StatusAlert || res.Code != CodeVoteSelf {
		t.Fatalf("unexpected response: %+v", res)
	}
}

func TestNavigateBoundaryNoop(t *testing.T) {
	svc := NewService(&fakeRepo{})
	res := svc.Navigate(context.Background(), NavigateRequest{
		Direction:         "next",
		CurrentPhotoCount: 3,
		AmountPhotos:      3,
	})
	if res.Status != StatusNoop || res.Code != CodeBoundaryReached {
		t.Fatalf("unexpected response: %+v", res)
	}
}

func TestNavigateSuccessNext(t *testing.T) {
	svc := NewService(&fakeRepo{
		startPhotoFound: true,
		startPhoto: PhotoRef{
			PhotoID:   11,
			FileID:    "file-11",
			MediaType: "photo",
		},
		likedState: 1,
	})

	res := svc.Navigate(context.Background(), NavigateRequest{
		Direction:         "next",
		UserID:            9,
		GroupID:           10,
		CurrentPhotoID:    7,
		CurrentPhotoCount: 1,
		AmountPhotos:      3,
	})
	if res.Status != StatusOK || res.Code != CodeNavigated || res.State == nil {
		t.Fatalf("unexpected response: %+v", res)
	}
	if res.State.CurrentPhotoCount != 2 || res.State.CurrentPhotoID != 11 || res.State.IsLikedPhoto != 1 {
		t.Fatalf("unexpected state: %+v", res.State)
	}
}

func TestUnsetLikeSuccess(t *testing.T) {
	svc := NewService(&fakeRepo{
		startPhoto: PhotoRef{
			PhotoID:   8,
			FileID:    "file-8",
			MediaType: "photo",
		},
		likedState: 0,
	})

	res := svc.UnsetLike(context.Background(), LikeRequest{
		UserID:            1,
		GroupID:           2,
		CurrentPhotoID:    8,
		CurrentPhotoCount: 1,
		AmountPhotos:      2,
	})
	if res.Status != StatusOK || res.Code != CodeLikeUnset || res.State == nil {
		t.Fatalf("unexpected response: %+v", res)
	}
	if res.State.IsLikedPhoto != 0 {
		t.Fatalf("unexpected state after unlike: %+v", res.State)
	}
}

func TestSubmitAlreadyVoted(t *testing.T) {
	svc := NewService(&fakeRepo{alreadyVoted: true})
	res := svc.SubmitVote(context.Background(), SubmitRequest{UserID: 1, GroupID: 2})
	if res.Status != StatusAlert || res.Code != CodeAlreadyVoted {
		t.Fatalf("unexpected response: %+v", res)
	}
}

func TestSubmitUnexpectedError(t *testing.T) {
	svc := NewService(&fakeRepo{submitErr: errors.New("boom")})
	res := svc.SubmitVote(context.Background(), SubmitRequest{UserID: 1, GroupID: 2})
	if res.Status != StatusError || res.Code != CodeUnexpectedError {
		t.Fatalf("unexpected response: %+v", res)
	}
}
