package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"runtime/debug"
	"strings"
	"time"

	engineapi "match-engine/internal/api"
	"match-engine/internal/domain"
	"match-engine/internal/engine"
)

type startResponse struct {
	MatchID string                `json:"match_id"`
	Status  string                `json:"status"`
	Result  domain.SimulateResult `json:"result"`
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/health", handleHealth)
	mux.HandleFunc("/api/v1/engine/matches/", handleMatchStart)

	port := getenv("MATCH_ENGINE_PORT", "8080")
	fmt.Printf("Match engine server running at http://localhost:%s\n", port)
	log.Fatal(http.ListenAndServe(":"+port, mux))
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]string{"status": "ok", "service": "match-engine"})
}

func handleMatchStart(w http.ResponseWriter, r *http.Request) {
	defer func() {
		if recovered := recover(); recovered != nil {
			log.Printf("match engine panic: %v\n%s", recovered, debug.Stack())
			http.Error(w, fmt.Sprintf("match engine panic: %v", recovered), http.StatusInternalServerError)
		}
	}()

	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	matchID, ok := parseMatchID(r.URL.Path)
	if !ok {
		http.Error(w, "invalid match start path", http.StatusNotFound)
		return
	}

	var req engineapi.SimulateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	if req.MatchID == "" {
		req.MatchID = matchID
	}

	seed := req.Seed
	if seed == 0 {
		seed = uint64(time.Now().UnixNano())
	}

	mode := req.Mode
	if mode == "" {
		mode = "instant"
	}
	if mode != "instant" && mode != "accelerated" && mode != "realtime" {
		http.Error(w, "invalid engine mode", http.StatusBadRequest)
		return
	}

	tickMs := req.TickIntervalMs
	if tickMs <= 0 {
		tickMs = defaultTickMs(mode)
	}

	// The authoritative football logic is identical for every mode. This first
	// service pass returns the final result synchronously; realtime fan-out can
	// layer on top of the same request/result contract.
	if mode != "instant" {
		time.Sleep(time.Duration(tickMs) * time.Millisecond)
	}

	simReq := domain.SimulateRequest{
		MatchID:        req.MatchID,
		HomeTeam:       req.HomeTeam,
		AwayTeam:       req.AwayTeam,
		HomeAdvantage:  req.HomeAdvantage,
		RequiresWinner: req.RequiresWinner,
	}
	result := engine.NewSimulator(seed).Simulate(simReq)

	writeJSON(w, startResponse{
		MatchID: req.MatchID,
		Status:  "finished",
		Result:  result,
	})
}

func parseMatchID(path string) (string, bool) {
	prefix := "/api/v1/engine/matches/"
	if !strings.HasPrefix(path, prefix) || !strings.HasSuffix(path, "/start") {
		return "", false
	}
	id := strings.TrimSuffix(strings.TrimPrefix(path, prefix), "/start")
	id = strings.Trim(id, "/")
	return id, id != ""
}

func defaultTickMs(mode string) int {
	switch mode {
	case "realtime":
		return 1000
	case "accelerated":
		return 25
	default:
		return 0
	}
}

func getenv(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}

func writeJSON(w http.ResponseWriter, value interface{}) {
	w.Header().Set("Content-Type", "application/json")
	if err := json.NewEncoder(w).Encode(value); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}
