'''
    A collection of expected elements at each level of the yaml file.
    https://nextcentury.atlassian.net/wiki/spaces/ITMC/pages/3041951763/Scenario+YAML+Documentation#Condition-level-elements
'''

### TODO: change each to have {type: [type], required: [bool], list: [bool], min: [float], max: [float], allowed_vals: [list]}

MISSION_LEVEL = {
    'unstructured': str,
    'mission_type': str,
    'critical_ids': list,
    'civilian_presence': str,
    'communication_capability': str,
    'roe': str,
    'political_climate': str,
    'medical_policies': str
}

SIM_ENVIRONMENT_LEVEL = {
    'type': str,
    'terrain': str,
    'weather': str,
    'lighting': str,
    'visibility': str,
    'noise_ambient': str,
    'noise_peak': str,
    'temperature': float,
    'humidity': float,
    'flora': str,
    'fauna': str
}

AID_LEVEL = {
    'delay': float, # must be positive
    'type': str,
    'max_transport': int # must be positive
}

DECISION_ENVIRONMENT_LEVEL = {
    'unstructured': str,
    'aid_delay': AID_LEVEL,
    'movement_restriction': str,
    'sound_restriction': str,
    'oxygen_levels': str,
    'population_density': float,
    'injury_triggers': str,
    'air_quality': int,
    'city_infrastructure': str
}

ENVIRONMENT_LEVEL = {
    'sim-environment': SIM_ENVIRONMENT_LEVEL,
    'decision-environment': DECISION_ENVIRONMENT_LEVEL
}

THREAT_LEVEL = {
    'unstructured': str,
    'threats': list
}


SUPPLY_LEVEL = {
    'type': str,
    'quantity': float, # 0-999
    'reusable': bool
}

DEMOGRAPHIC_LEVEL = {
    'age': float, # positive
    'sex': str,
    'race': str,
    'military_disposition': str,
    'military_branch': str,
    'rank': str,
    'rank_title': str,
    'skills': dict,
    'role': str,
    'mission_importance': str
}

VITAL_LEVEL = {
    'conscious': bool,
    'avpu': str,
    'mental_status': str,
    'breathing': str,
    'hrpmin': float, # must be positive
    'Spo2': float # must be positive
}
 
INJURY_LEVEL = {
  'name': str,
  'location': str,
  'severity': float, # 0.0-1.0
  'hidden': bool
}

CHARACTER_LEVEL = {
    'id': str,
    'name': str,
    'unstructured': str,
    'unstructured_postassess': str,
    'rapport': float, # 0-10
    'demographics': DEMOGRAPHIC_LEVEL,
    'vitals': VITAL_LEVEL,
    'injuries': INJURY_LEVEL
}

STATE_LEVEL = {
    'unstructured': str,
    'mission': MISSION_LEVEL,
    'environment': ENVIRONMENT_LEVEL,
    'threat_state': THREAT_LEVEL,
    'supplies': SUPPLY_LEVEL,
    'characters': CHARACTER_LEVEL
}

CONDITION_LEVEL = {
    'elapsed_time_lt': int, # positive
    'elapsed_time_gt': int, # positive
    'actions': list, # list of lists
    'probes': bool,
    'probe_responses': bool, # not a list of bools?
    'character_vitals': list, # TODO: update this
    'supplies': list # TODO: update this
}

ACTION_LEVEL = {
    'id': str,
    'type': str,
    'unstructured': str,
    'repeatable': bool,
    'character_id': str,
    'parameters': str, # what is this? dict? what properties are allowed?
    'probe_id': str,
    'choice': str,
    'kdma_association': dict, # TODO: this is key-value (Fairness: 8)
    'condition_semantics': str,
    'conditions': CONDITION_LEVEL
}

TAGGING_LEVEL = {
    'enabled': bool,
    'repeatable': bool,
    'probe_responses': list,
    'reference': str # or int?
}

PROBE_LEVEL = {
    'character_id': str,
    'probe_id': str,
    'minimal': str,
    'delayed': str,
    'immediate': str,
    'expectant': str
}

SCENE_LEVEL = {
    'index': int,
    'state': STATE_LEVEL, # TODO: not the same type of state I think
    'end_scenario_allowed': bool,
    'tagging': TAGGING_LEVEL,
    'actions': ACTION_LEVEL,
    'transition_semantics': str,
    'transitions': CONDITION_LEVEL
}

TOP_LEVEL = {
    'id': str,
    'name': str,
    'state': STATE_LEVEL,
    'scenes': SCENE_LEVEL
}
