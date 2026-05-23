package httpapi

import (
	"context"
	"errors"
	"testing"
)

func TestRunHealthChecks(t *testing.T) {
	errUnavailable := errors.New("unavailable")

	tests := []struct {
		name        string
		checks      []healthCheck
		wantResults map[string]string
		wantErr     bool
	}{
		{
			name: "all dependencies up",
			checks: []healthCheck{
				{name: "postgres", run: func(context.Context) error { return nil }},
				{name: "redis", run: func(context.Context) error { return nil }},
			},
			wantResults: map[string]string{
				"postgres": "up",
				"redis":    "up",
			},
		},
		{
			name: "stops at first failed dependency",
			checks: []healthCheck{
				{name: "postgres", run: func(context.Context) error { return nil }},
				{name: "redis", run: func(context.Context) error { return errUnavailable }},
			},
			wantResults: map[string]string{
				"postgres": "up",
				"redis":    "down",
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			results, err := runHealthChecks(context.Background(), tt.checks)
			if (err != nil) != tt.wantErr {
				t.Fatalf("error = %v, wantErr %v", err, tt.wantErr)
			}
			if len(results) != len(tt.wantResults) {
				t.Fatalf("results length = %d, want %d", len(results), len(tt.wantResults))
			}
			for key, want := range tt.wantResults {
				if got := results[key]; got != want {
					t.Fatalf("results[%q] = %q, want %q", key, got, want)
				}
			}
		})
	}
}
