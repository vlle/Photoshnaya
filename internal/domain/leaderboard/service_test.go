package leaderboard

import "testing"

func TestFormatWinnerBoard_Empty(t *testing.T) {
	if got := FormatWinnerBoard(nil); got != EmptyLeaderboardMessage {
		t.Fatalf("expected empty message, got %q", got)
	}
}

func TestFormatWinnerBoard_WithRows(t *testing.T) {
	rows := []WinnerRow{{Name: "alice", Total: 3}, {Name: "bob", Total: 1}}
	got := FormatWinnerBoard(rows)

	expected := "<b>1</b>: <a href=\"https://t.me/alice\">alice</a>, количество побед: 3\n" +
		"<b>2</b>: <a href=\"https://t.me/bob\">bob</a>, количество побед: 1\n"
	if got != expected {
		t.Fatalf("unexpected formatted message:\n%s\nexpected:\n%s", got, expected)
	}
}
