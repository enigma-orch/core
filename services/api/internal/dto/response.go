package dto

type APIResponse struct {
	Success    bool        `json:"success"`
	Message    string      `json:"message,omitempty"`
	Data       interface{} `json:"data,omitempty"`
	Pagination *Pagination `json:"pagination,omitempty"`
	Error      string      `json:"error,omitempty"`
}

type Pagination struct {
	Page       int `json:"page"`
	PageSize   int `json:"page_size"`
	TotalPages int `json:"total_pages"`
	TotalItems int `json:"total_items"`
}

// FeedItem bundles a shared outfit with its owner's public profile so
// the iOS feed card has everything it needs in one payload.
type FeedItem struct {
	OutfitID        string `json:"outfit_id"`
	OwnerID         string `json:"owner_id"`
	OwnerName       string `json:"owner_name"`
	OwnerAvatarURL  string `json:"owner_avatar_url,omitempty"`
	Name            string `json:"name,omitempty"`
	PreviewImageURL string `json:"preview_image_url,omitempty"`
	Occasion        string `json:"occasion,omitempty"`
	Vibe            string `json:"vibe,omitempty"`
	WearCount       int32  `json:"wear_count"`
	CreatedAt       string `json:"created_at"`
}
