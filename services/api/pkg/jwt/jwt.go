package jwt

import (
	"errors"

	"github.com/golang-jwt/jwt/v5"
)

// Claims matches FastAPI's JWT format: sub = user UUID string, HS256.
type Claims struct {
	jwt.RegisteredClaims
}

// Verifier validates Bearer tokens with a configured HS256 secret. Build one
// at startup with NewVerifier so callers don't reach into globals.
type Verifier struct {
	secret []byte
}

func NewVerifier(secret string) *Verifier {
	return &Verifier{secret: []byte(secret)}
}

func (v *Verifier) Parse(tokenString string) (*Claims, error) {
	claims := &Claims{}
	token, err := jwt.ParseWithClaims(tokenString, claims, func(t *jwt.Token) (any, error) {
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, errors.New("unexpected signing method")
		}
		return v.secret, nil
	})
	if err != nil {
		return nil, err
	}
	if !token.Valid {
		return nil, errors.New("invalid token")
	}
	return claims, nil
}

// UserID extracts the user UUID string from the `sub` claim.
func UserID(claims *Claims) (string, error) {
	sub, err := claims.GetSubject()
	if err != nil || sub == "" {
		return "", errors.New("missing sub claim")
	}
	return sub, nil
}
