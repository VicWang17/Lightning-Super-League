package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"match-engine/internal/domain"
	"match-engine/internal/engine"
)

var (
	sim *engine.Simulator
	ms  *domain.MatchState
)

type InitRequest struct {
	HomeTeam      domain.TeamSetup `json:"homeTeam"`
	AwayTeam      domain.TeamSetup `json:"awayTeam"`
	Seed          uint64           `json:"seed"`
	HomeAdvantage bool             `json:"homeAdvantage"`
}

type InitResponse struct {
	Success bool              `json:"success"`
	State   engine.MatchSnapshot `json:"state"`
	Events  []domain.MatchEvent `json:"events"`
}

type StepResponse struct {
	Success bool            `json:"success"`
	Done    bool            `json:"done"`
	Step    *engine.StepInfo `json:"step,omitempty"`
	State   engine.MatchSnapshot `json:"state"`
}

func main() {
	fs := http.FileServer(http.Dir("static"))
	http.Handle("/", fs)
	http.HandleFunc("/api/init", handleInit)
	http.HandleFunc("/api/step", handleStep)
	http.HandleFunc("/api/state", handleState)
	http.HandleFunc("/api/reset", handleReset)

	port := "8080"
	fmt.Printf("Preview server running at http://localhost:%s\n", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}

func handleInit(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req InitRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	seed := req.Seed
	if seed == 0 {
		seed = uint64(time.Now().UnixNano())
	}
	sim = engine.NewSimulator(seed)

	matchReq := domain.SimulateRequest{
		MatchID:       "preview_match",
		HomeTeam:      req.HomeTeam,
		AwayTeam:      req.AwayTeam,
		HomeAdvantage: req.HomeAdvantage,
	}
	ms = sim.InitMatchState(matchReq)

	resp := InitResponse{
		Success: true,
		State:   buildSnapshot(ms),
		Events:  ms.Events,
	}
	writeJSON(w, resp)
}

func handleStep(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	if sim == nil || ms == nil {
		http.Error(w, "Match not initialized", http.StatusBadRequest)
		return
	}

	info, ok := sim.Step(ms)
	resp := StepResponse{
		Success: true,
		Done:    !ok,
		Step:    info,
		State:   buildSnapshot(ms),
	}
	writeJSON(w, resp)
}

func handleState(w http.ResponseWriter, r *http.Request) {
	if ms == nil {
		http.Error(w, "Match not initialized", http.StatusBadRequest)
		return
	}
	writeJSON(w, map[string]interface{}{
		"success": true,
		"state":   buildSnapshot(ms),
		"events":  ms.Events,
	})
}

func handleReset(w http.ResponseWriter, r *http.Request) {
	sim = nil
	ms = nil
	writeJSON(w, map[string]bool{"success": true})
}

func buildSnapshot(ms *domain.MatchState) engine.MatchSnapshot {
	zone := ms.ActiveZone
	return engine.MatchSnapshot{
		Score:            ms.Score,
		Minute:           ms.Minute,
		Half:             ms.Half,
		Possession:       ms.Possession.String(),
		ActiveZone:       zone,
		ControlMatrix:    ms.ControlMatrix,
		ZoneMomentum:     [3][3]float64{},
		PossessionTicks:  ms.PossessionTicks,
		CounterBoost:     ms.CounterBoostRemaining,
		Control:          ms.EffectiveControl(zone),
		Momentum:         ms.GlobalMomentum,
		HomeFlags:        ms.HomeTeam.ComputeTacticalFlags(),
		AwayFlags:        ms.AwayTeam.ComputeTacticalFlags(),
		HomePlayers:      buildPlayerSnapshots(ms.HomeTeam),
		AwayPlayers:      buildPlayerSnapshots(ms.AwayTeam),
		ControlBreakdown: engine.ComputeControlBreakdown(ms, zone),
	}
}

func buildPlayerSnapshots(team *domain.TeamRuntime) []engine.PlayerSnapshot {
	var result []engine.PlayerSnapshot
	for _, p := range team.PlayerRuntimes {
		result = append(result, engine.PlayerSnapshot{
			ID:       p.PlayerID,
			Name:     p.Name,
			Position: p.Position,
			Stamina:  p.CurrentStamina,
			OnField:  true,
		})
	}
	for _, p := range team.BenchRuntimes {
		result = append(result, engine.PlayerSnapshot{
			ID:       p.PlayerID,
			Name:     p.Name,
			Position: p.Position,
			Stamina:  p.CurrentStamina,
			OnField:  false,
		})
	}
	return result
}

func writeJSON(w http.ResponseWriter, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(v)
}
