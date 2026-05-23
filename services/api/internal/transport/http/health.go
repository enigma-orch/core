package httpapi

import (
	"context"
	"fmt"
)

type healthCheck struct {
	name string
	run  func(context.Context) error
}

func runHealthChecks(ctx context.Context, checks []healthCheck) (map[string]string, error) {
	results := make(map[string]string, len(checks))

	for _, check := range checks {
		if err := check.run(ctx); err != nil {
			results[check.name] = "down"
			return results, fmt.Errorf("%s readiness check failed: %w", check.name, err)
		}
		results[check.name] = "up"
	}

	return results, nil
}
