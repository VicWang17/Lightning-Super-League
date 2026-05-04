package engine

import (
	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// CalculatePostMatchRating computes a post-match statistical adjustment
// based on the player's accumulated stats and position.
// This makes the final rating more comprehensive and position-aware.
// The returned value typically ranges between -1.0 and +1.5.
func CalculatePostMatchRating(ps *domain.PlayerMatchStats, position string) float64 {
	adj := 0.0

	// ===== Universal adjustments =====

	// Pass accuracy
	if ps.Passes > 5 {
		acc := float64(ps.PassesSucc) / float64(ps.Passes)
		switch {
		case acc >= 0.92:
			adj += 0.15
		case acc >= 0.85:
			adj += 0.08
		case acc >= 0.75:
			adj += 0.03
		case acc < 0.50:
			adj -= 0.20
		}
	}

	// Key passes
	if ps.KeyPasses >= 4 {
		adj += 0.15
	} else if ps.KeyPasses >= 2 {
		adj += 0.08
	}

	// Assists
	if ps.Assists >= 2 {
		adj += 0.25
	} else if ps.Assists >= 1 {
		adj += 0.15
	}

	// Goals (additional bonus on top of the large in-match event bonus)
	if ps.Goals >= 2 {
		adj += 0.25
	} else if ps.Goals >= 1 {
		adj += 0.15
	}

	// Discipline
	if ps.RedCards > 0 {
		adj -= 0.8
	}
	if ps.YellowCards > 0 {
		adj -= 0.15
	}
	if ps.Fouls >= 4 {
		adj -= 0.15
	} else if ps.Fouls >= 2 {
		adj -= 0.05
	}

	// Offsides
	if ps.Offsides >= 3 {
		adj -= 0.10
	}

	// Turnovers (lost possession)
	if ps.Turnovers >= 5 {
		adj -= 0.10
	}

	// ===== Position-specific adjustments =====
	switch position {
	case config.PosGK:
		if ps.Saves >= 4 {
			adj += 0.20
		} else if ps.Saves >= 2 {
			adj += 0.10
		}
		if ps.Passes > 5 {
			acc := float64(ps.PassesSucc) / float64(ps.Passes)
			if acc >= 0.70 {
				adj += 0.08
			}
		}

	case config.PosCB:
		if ps.Tackles > 0 {
			acc := float64(ps.TacklesSucc) / float64(ps.Tackles)
			if acc >= 0.80 && ps.Tackles >= 3 {
				adj += 0.20
			} else if acc >= 0.70 {
				adj += 0.10
			} else if acc < 0.40 {
				adj -= 0.10
			}
		}
		if ps.Intercepts >= 3 {
			adj += 0.10
		} else if ps.Intercepts >= 1 {
			adj += 0.05
		}
		if ps.Clearances >= 3 {
			adj += 0.10
		} else if ps.Clearances >= 1 {
			adj += 0.05
		}
		if ps.Blocks >= 1 {
			adj += 0.08
		}
		if ps.Headers > 0 {
			acc := float64(ps.HeaderWins) / float64(ps.Headers)
			if acc >= 0.70 {
				adj += 0.08
			}
		}

	case config.PosSB:
		if ps.Tackles > 0 {
			acc := float64(ps.TacklesSucc) / float64(ps.Tackles)
			if acc >= 0.70 {
				adj += 0.10
			}
		}
		if ps.Crosses > 0 {
			acc := float64(ps.CrossesSucc) / float64(ps.Crosses)
			if acc >= 0.40 {
				adj += 0.15
			}
		}
		if ps.Intercepts >= 2 {
			adj += 0.08
		}
		if ps.KeyPasses >= 2 {
			adj += 0.08
		}

	case config.PosDMF:
		if ps.Tackles > 0 {
			acc := float64(ps.TacklesSucc) / float64(ps.Tackles)
			if acc >= 0.75 && ps.Tackles >= 3 {
				adj += 0.20
			} else if acc >= 0.65 {
				adj += 0.10
			} else if acc < 0.40 {
				adj -= 0.10
			}
		}
		if ps.Intercepts >= 2 {
			adj += 0.10
		}
		if ps.Clearances >= 2 {
			adj += 0.08
		}
		if ps.Passes > 5 {
			acc := float64(ps.PassesSucc) / float64(ps.Passes)
			if acc >= 0.88 {
				adj += 0.10
			}
		}

	case config.PosCMF:
		if ps.Passes > 5 {
			acc := float64(ps.PassesSucc) / float64(ps.Passes)
			if acc >= 0.90 {
				adj += 0.15
			} else if acc >= 0.82 {
				adj += 0.08
			}
		}
		if ps.Tackles > 0 {
			acc := float64(ps.TacklesSucc) / float64(ps.Tackles)
			if acc >= 0.65 {
				adj += 0.08
			}
		}
		if ps.Intercepts >= 2 {
			adj += 0.08
		}
		if ps.KeyPasses >= 2 {
			adj += 0.08
		}

	case config.PosAMF:
		if ps.Dribbles > 0 {
			acc := float64(ps.DribblesSucc) / float64(ps.Dribbles)
			if acc >= 0.60 {
				adj += 0.10
			}
		}
		if ps.Shots > 0 {
			acc := float64(ps.ShotsOnTarget) / float64(ps.Shots)
			if acc >= 0.60 {
				adj += 0.10
			}
		}
		if ps.KeyPasses >= 3 {
			adj += 0.10
		}

	case config.PosWF:
		if ps.Dribbles > 0 {
			acc := float64(ps.DribblesSucc) / float64(ps.Dribbles)
			if acc >= 0.55 {
				adj += 0.10
			}
		}
		if ps.Crosses > 0 {
			acc := float64(ps.CrossesSucc) / float64(ps.Crosses)
			if acc >= 0.35 {
				adj += 0.10
			}
		}
		if ps.Shots > 0 {
			acc := float64(ps.ShotsOnTarget) / float64(ps.Shots)
			if acc >= 0.50 {
				adj += 0.10
			}
		}
		if ps.KeyPasses >= 2 {
			adj += 0.08
		}

	case config.PosST:
		if ps.Shots > 0 {
			acc := float64(ps.ShotsOnTarget) / float64(ps.Shots)
			if acc >= 0.60 {
				adj += 0.15
			} else if acc >= 0.40 {
				adj += 0.08
			}
		}
		if ps.Headers > 0 {
			acc := float64(ps.HeaderWins) / float64(ps.Headers)
			if acc >= 0.60 {
				adj += 0.10
			}
		}
		if ps.Dribbles > 0 {
			acc := float64(ps.DribblesSucc) / float64(ps.Dribbles)
			if acc >= 0.50 {
				adj += 0.08
			}
		}
		if ps.Touches >= 2 {
			// High work-rate forwards get a tiny bump
			adj += 0.03
		}
	}

	return adj
}
