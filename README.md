# ITM Scenario Validator

## Getting Started

### Creating a Virtual Environment
```
python3.8 -m venv validator
```
Note: You may have to install venv tools on your system. For linux, the command is
```
sudo apt install python3.8-venv
```

To activate the virtual environment:

**Windows:**
```
validator\Scripts\activate
```

**MacOS/Linux:**
```
source validator/bin/activate
```

You are now in a virtual environment where you can install the requirements and run the main script.

To deactivate the environment, run
```
deactivate
```

### Installing from Requirements
```
pip install -r requirements.txt
```

## Running the Program
To run the validator, execute the following command:
```
python3 validator.py -f [path_to_file]
```
Ensure that the path leads to a yaml file.

See full usage options below:
```
usage: validator.py [-h] [-f PATH] [-u] [-t]
options:
  -h, --help                Show this help message and exit.
  -f PATH, --filepath PATH  The path to the yaml file. Required if -u is not specified.
  -u, --update              Switch to update the api files or not. Required if -f is not specified.
  -t, --train               Validate a training scenario yaml.```

## API Changes
- When the Swagger API changes, make sure you upload the newest version as `api.yaml` to the `api_files` directory.
- Once the api file is up-to-date, run 
```
python3 validator.py --update
```

## Logging
To change the log level, edit the value in the .env file.

## Dependencies JSON
The dependencies json lists specific rules for the validator to follow. When listing a field, use '.' between each level. For levels that contain arrays, ensure you put '[]' at the end of the level name. For example, `scenes[].id`, or `state.characters[].demographics.skills[].level`.

| key | description | value |
| -- | -- | -- |
| `simpleRequired` | "If [field1] is provided, then [field2] is required." | A dictionary where each key is [field1] and the value is a list of [field2] names |
| `conditionalRequired` | "If [field1] is provided and [conditions] apply, then [field2] is required." | A dictionary where each key is [field1] and the value is a list of objects that define conditions and [field2] names|
| `conditionalForbid` | "If [field1] has a value of [value1], then [field2] should not be provided" | A dictionary where each key is [field1] and the value is a list of objects that define conditions and [field2] names. If [field2] is in the yaml to validate when the conditions are true, a warning will be given. |
| `simpleAllowedValues` | "If [field1] has a value of [value1], then [field2] values must be [...]" | A dictionary where each key is a [field1] and the value is an object where each key is a possible value for field 1. Those keys are mapped to objects whose keys are [field2] names with a matching value of an array of possible allowed values for field2 |
| `deepLinks` | "If [field1] has a value matching one of [a, b, ...] and [field2] has a value matching one of [c, d, ...], then [field3] value must match one of [e, f, ...]" | An object where each key is a shared parent of all fields throughout the rest of the object. For example, fa.fb[].fc is the parent of field1, field2, and field3. Each value contains "sharedParent", "condition" and "requirement".  "condition" is an object where each key-value pair refers to a field (key) and the list of its possible values it must match (value) in order for "requirement" to be required. "requirement" is an object where each key-value pair refers to a field (key) and the list of allowed values (value) for it given the conditions |
| `valueMatch` | "[field1] must match one of the values from [field2]" | An object in the form [field1]: [field2]. Each value of the object is a field name whose values form the complete list of valid values for the corresponding key, [field1]. The value of [field1] must match one of these values. |
| `characterMatching` | Character ids found at the locations in this list must match state.characters[].id if the scene is the first scene, and scenes[ind].state.characters[].id otherwise | A list of locations that must follow this rule |
| `unique` | "all values of [field1] must be unique within the scope of [field2]" | An object in the form [field1]: [field2]. Both must be a complete path. `field1` refers to the path where unique values must live. `field2` refers to the path that begins the uniqueness. For example, `scenes[]` as `field2`  means that `field1` cannot have a repeated value in each individual scene. To get uniqueness for an id throughout the entire yaml, `field2` should be `""` |
| `conditions` | An object containing specific conditions that must apply before the appropriate action is taken | An object containing keys such as `length`, `exists`, or `value`, where the value of that key is the length or value that must hold true for the key to be required or ignored, or to require/forbid keys based on the existence of another key |


## Validator Rules
In order for a yaml file to be considered "valid", the following conditions must be met:
### General Formatting
* The yaml must not contain duplicate keys at the same level
* The yaml must be in valid yaml format. To check your yaml format, use [yamllint](https://www.yamllint.com/)
### General Type Checking and Required Keys
* All value types should follow the `api.yaml` file
* All keys defined as required by `api.yaml` are required
* Exceptions to the two rules above include the following:
    * `scenario.scenes` is required
    * All vitals properties are required
        * `avpu`
        * `mental_status`
        * `breathing`
        * `heart_rate`
        * `spo2`
    * `restricted_actions` cannot include `end_scene`
    * `session_complete` is a prohibited key in `scenario`
    * `scenario_complete` is a prohibited key in `state`
    * `elapsed_time` is a prohibited key in `state`
    * `action_type` in `action_mapping` cannot be one of `restricted_actions`
    * In `scenes.state`:
        * Only `characters` is required (if `persist_characters` is false)
        * Only one `unstructured` property is required in the whole object
        * `Mission`, `Environment`, `DecisionEnvironment`, and `SimEnvironment` only require the `unstructured` property
        * `type` is a prohibted key in `SimEnvironment`
        * `AidDelay` only requires `id`
        
### Dependencies
#### Conditional Requirements
* If `scenes[n].action_mapping[m].conditions` has a length of 2 or more, `scenes[n].action_mapping[m].condition_semantics` is required
* If `scenes[n].transitions` has a length of 2 or more, `scenes[n].transition_semantics` is required 
* If `state.characters[n].demographics.military_disposition` is "Allied US", `state.characters[n].demographics.military_branch` is required 
* If `state.characters[n].injuries[m].name` is "Burn", `state.characters[n].injuries[m].severity` is required 
* If `scenes[n].action_mapping[m].action_type` is "APPLY_TREATMENT", `scenes[n].action_mapping[m].character_id` is required
* If `scenes[n].action_mapping[m].action_type` is "CHECK_ALL_VITALS", `scenes[n].action_mapping[m].character_id` is required
* If `scenes[n].action_mapping[m].action_type` is "CHECK_PULSE", `scenes[n].action_mapping[m].character_id` is required
* If `scenes[n].action_mapping[m].action_type` is "CHECK_RESPIRATION", `scenes[n].action_mapping[m].character_id` is required
* If `scenes[n].action_mapping[m].action_type` is "CHECK_BLOOD_OXYGEN", `scenes[n].action_mapping[m].character_id` is required
* If `scenes[n].action_mapping[m].action_type` is "MOVE_TO_EVAC", `scenes[n].action_mapping[m].character_id` is required
* If `scenes[n].action_mapping[m].action_type` is "MOVE_TO_EVAC", `scenes[n].action_mapping[m].parameters.evac_id` is required
* If `scenes[n].action_mapping[m].action_type` is "TAG_CHARACTER", `scenes[n].action_mapping[m].character_id` is required
* If `scenes[n].action_mapping[m].action_type` is "TAG_CHARACTER", `scenes[n].action_mapping[m].parameters.category` is required

#### Conditional Prohibitions
* If `state.characters[n].demographics.military_branch` does not exist, `state.characters[n].demographics.rank` *and* `state.characters[n].demographics.rank_title` should _not_ be provided 
* If `scenes[n].action_mapping[m].action_type' is "CHECK_BLOOD_OXYGEN" or "CHECK_ALL_VITALS" and there is no pulse oximeter correctly configured in the supplies for the scene, a warning will be given. 
* If `scenes[n].persist_characters` is false or does not exist, `scenes[n].removed_characters` must not exist

#### Value Matching
* `state.characters[n].injuries[m].source_character` must be one of the `state.characters.character_id`'s
* `scenes[n].tagging.reference` must be one of the `scenes[n].id`'s 
* `scenes[n].action_mapping[m].next_scene` must be one of the `scenes[n].id`'s
* `scenes[n].action_mapping[m].parameters.evac_id` must be one of the `scenes[n].state.environment.decision_environment.aid_delay[p].id`'s

#### Character Matching
If persist_characters is false:
* `scenes[0].action_mapping[].character_id`: `state.characters[].id`,
* `scenes[0].tagging.probe_responses[].character_id`: `state.characters[].id`,
* `scenes[0].transitions.character_vitals[].character_id`: `state.characters[].id`,
* `scenes[0].action_mapping[].conditions.character_vitals[].character_id`: `state.characters[].id`
* For scenes[n] where (n>0):
    * `scenes[n].action_mapping[].character_id`: `scenes[n].state.characters[].id`,
    * `scenes[n].tagging.probe_responses[].character_id`: `scenes[n].state.characters[].id`,
    * `scenes[n].transitions.character_vitals[].character_id`: `scenes[n].state.characters[].id`,
    * `scenes[n].action_mapping[].conditions.character_vitals[].character_id`: `scenes[n].state.characters[].id`
Otherwise, complete the same checks, but match it up against all characters defined throughout the scenario file. Note that this may give some false validity, as a character may end up being used before it is defined. Please be cautious when defining characters and using persist_characters. 
In addition, if a character is removed anywhere in a scene, a warning will be issued. Please make sure that your branching scenes do not cause a situation where a character has been removed and then used.

#### Uniqueness
* `scenes[].state.environment.decision_environment.aid_delay[].id` must not have any repeated values within each `scene`
* `scenes[].state.characters[].id` must not have any repeated values within each `scene`
* `scenes[].action_mapping[].action_id` must not have any repeated values within each `scene`
* `state.characters[].id` must not have any repeated values
* `scenes[].id` must not have any repeated values
* `state.environment.decision_environment.aid_delay[].id` must not have any repeated values

#### Training Only Supplies
Any supply name placed in this array will be excluded from the allowed supplies if eval mode is true.

#### Other Rules
* At least one scene must have `final_scene=true`
* `scenes[n].action_mapping[m].parameters.treatment` must come from `SupplyTypeEnum` 
* `scenes[n].action_mapping[m].parameters.location` must come from `InjuryLocationEnum` 
* `scenes[n].action_mapping[m].parameters.category` must come from `CharacterTagEnum` 
* If there are `N` `scenario.scenes`, then all scenes except first must contain state 
* `scenario.state.characters.demographics.mission_importance` must be consistent with `scenario.state.mission.character_importance `
    * Every character with `mission_importance` should be an entry in `character_importance`, and vice-versa 
    * This does not include "normal", which is the default level of importance. For example, a character may not specify `mission_importance` and `character_importance` may explicitly specify the character with importance "normal", or a character may specify `mission_importance` with "normal" and `character_importance` may not list that character 
* If the scene is the first scene, `scenes[].state` should _not_ be provided


#### Eval Mode
When not running in training mode (-t), additional checks are implemented:
* No supplies or treatments are allowed that are not in the simulator. Put the names of these treatments in the trainingOnlySupplies array in dependencies.json
* No blanket can appear on the character at the start. 

#### Injury/Location Matches
* Only a maximum of 8 injuries can be shown on the simulation, not counting ear bleed, asthmatic, broken bones, and
internal injuries.
* Injuries are only allowed to have specific locations. Please follow the table to create valid matches. 
| Injury name | Allowed Locations |
| --- | --- |
| `Ear Bleed` | `left face`, `right face` |
| `Asthmatic` | `unspecified`, `internal` |
| `Laceration` | `left forearm`, `right forearm`, `left stomach`, `right stomach`, `left thigh`, `right thigh`, `left calf`, `right calf`, `left wrist`, `right wrist` |
| `Puncture` | `left neck`, `right neck`, `left bicep`, `right bicep`, `left shoulder`, `right shoulder`, `left stomach`, `right stomach`, `left side`, `right side`, `left thigh`, `right thigh`, `left chest`, `right chest`, `center chest` |
| `Shrapnel` | `left face`, `right face`, `left calf`, `right calf` |
| `Chest Collapse` | `left chest`, `right chest` |
| `Amputation` | `left wrist`, `right wrist`, `left leg`, `right leg` |
| `Burn` | `right forearm`, `left forearm`, `right leg`, `left leg`, `right calf`, `left calf`, `right thigh`, `left thigh`, `right stomach`, `left stomach`, `right bicep`, `left bicep`, `right shoulder`, `left shoulder`, `right side`, `left side`, `right chest`, `left chest`, `right wrist`, `left wrist`, `left face`, `right face`, `left neck`, `right neck`, `unspecified` |
| `Abrasion` | `right forearm`, `left forearm`, `right hand`, `left hand`, `right leg`, `left leg`, `right calf`, `left calf`, `right thigh`, `left thigh`, `right stomach`, `left stomach`, `right bicep`, `left bicep`, `right shoulder`, `left shoulder`, `right side`, `left side`, `right chest`, `left chest`, `right wrist`, `left wrist`, `left face`, `right face`, `left neck`, `right neck`, `unspecified` |
| `Broken Bone` | `right forearm`, `left forearm`, `right hand`, `left hand`, `right leg`, `left leg`, `right thigh`, `left thigh`, `right shoulder`, `left shoulder`, `right side`, `left side`, `right wrist`, `left wrist`, `left neck`, `right neck`, `unspecified` |
| `Internal` | `internal` | 

#### Military Branches, Ranks, and Rank Titles
* `military_branch` is only allowed if `military_disposition` is "Allied US"
* `rank` and `rank_title` are not allowed if `military_branch` is not provided
* `military_branch`, `rank`, and `rank_title` must match the information found [here](https://www.military.com/join-military/military-ranks-everything-you-need-know.html)

