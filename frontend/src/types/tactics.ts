export type TacticsSetup = {
  passing_style: number
  attack_width: number
  attack_tempo: number
  defensive_line_height: number
  crossing_strategy: number
  shooting_mentality: number
  playmaker_focus: number
  pressing_intensity: number
  defensive_compactness: number
  marking_strategy: number
  offside_trap: number
  tackling_aggression: number
}

export type InPossessionInstructions = {
  build_up_style: 'short' | 'balanced' | 'direct' | 'long_ball'
  chance_creation: 'patient' | 'balanced' | 'early_shot' | 'work_into_box'
  attack_route: 'left' | 'center' | 'right' | 'both_wings' | 'mixed'
  width: number
  tempo: number
  passing_risk: number
  crossing_frequency: number
  dribble_frequency: number
  shooting_frequency: number
}

export type TransitionInstructions = {
  after_possession_lost: 'counter_press' | 'balanced' | 'regroup'
  after_possession_won: 'counter' | 'balanced' | 'hold_shape'
  counter_directness: number
  reset_under_pressure: number
}

export type OutOfPossessionInstructions = {
  defensive_line_height: number
  pressing_intensity: number
  pressing_trigger: 'passive' | 'bad_touch' | 'wide_trap' | 'center_trap' | 'always'
  compactness: number
  marking: 'zonal' | 'mixed' | 'man'
  tackling_aggression: number
  offside_trap: number
}

export type GoalkeeperDistributionInstructions = {
  distribution_target: 'center_backs' | 'fullbacks' | 'midfield' | 'target_forward' | 'mixed'
  distribution_length: 'short' | 'balanced' | 'long'
  release_speed: 'slow' | 'balanced' | 'quick'
}

export type PlayerInstruction = {
  player_id: string
  carry_ball: number
  passing_risk: number
  shooting_frequency: number
  crossing_frequency: number
  pressing_intensity: number
  hold_position: number
  forward_runs: number
}

export type SituationalRuleCondition = {
  minute_gte?: number
  minute_lt?: number
  goal_diff_lte?: number
  goal_diff_gte?: number
  team_stamina_avg_lte?: number
}

export type SituationalRuleOverride = {
  tempo?: number
  shooting_frequency?: number
  defensive_line_height?: number
  pressing_intensity?: number
  passing_risk?: number
  crossing_frequency?: number
  width?: number
  after_possession_won?: 'counter' | 'balanced' | 'hold_shape'
  after_possession_lost?: 'counter_press' | 'balanced' | 'regroup'
  build_up_style?: 'short' | 'balanced' | 'direct' | 'long_ball'
  chance_creation?: 'patient' | 'balanced' | 'early_shot' | 'work_into_box'
}

export type SituationalRule = {
  id: string
  name: string
  enabled: boolean
  condition: SituationalRuleCondition
  override: SituationalRuleOverride
}

export type TeamInstructions = {
  legacy_team_sliders: TacticsSetup
  in_possession: InPossessionInstructions
  transition: TransitionInstructions
  out_of_possession: OutOfPossessionInstructions
  goalkeeper_distribution: GoalkeeperDistributionInstructions
  player_instructions: PlayerInstruction[]
  situational_rules: SituationalRule[]
}

export type TeamTactics = {
  team_id: string
  formation_id: string
  lineup_player_ids: string[]
  bench_player_ids: string[]
  team_instructions: TeamInstructions
  set_piece_instructions: Record<string, unknown>
  substitution_rules: Record<string, unknown>
  ai_profile?: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export type TeamTacticsUpdate = {
  formation_id: string
  lineup_player_ids: string[]
  bench_player_ids: string[]
  team_instructions: TeamInstructions
  set_piece_instructions?: Record<string, unknown>
  substitution_rules?: Record<string, unknown>
}
