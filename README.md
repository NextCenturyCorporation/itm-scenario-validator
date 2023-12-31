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
usage: validator.py [-h] [-u [-f PATH] | -f PATH ]
```

## API Changes
- When the Swagger API changes, make sure you upload the newest version as `api.yaml` to the `api_files` directory.
- Once the api file is up-to-date, run 
```
python3 validator.py --update
```

## Logging
To change the log level, edit the value in the .env file.

## Dependencies JSON
The dependencies json lists specific rules for the validator to follow. When listing a field, use '.' between each level. For levels that contain arrays, ensure you put '[]' at the end of the level name. For example, `scenes[].index`, or `state.characters[].demographics.skills[].level`.

| key | description | value |
| -- | -- | -- |
| `simpleRequired` | "If [field1] is provided, then [field2] is required." | A dictionary where each key is [field1] and the value is a list of [field2] names |
| `conditionalRequired` | "If [field1] is provided and [conditions] apply, then [field2] is required." | A dictionary where each key is [field1] and the value is a list of objects that define conditions and [field2] names|
| `conditionalForbid` | "If [field1] has a value of [value1], then [field2] should not be provided" | A dictionary where each key is [field1] and the value is a list of objects that define conditions and [field2] names. If [field2] is in the yaml to validate when the conditions are true, a warning will be given. |
| `simpleAllowedValues` | "If [field1] has a value of [value1], then [field2] values must be [...]" | A dictionary where each key is a [field1] and the value is an object where each key is a possible value for field 1. Those keys are mapped to objects whose keys are [field2] names with a matching value of an array of possible allowed values for field2 |
| `deepLinks` | "If [field1] has a value matching one of [a, b, ...] and [field2] has a value matching one of [c, d, ...], then [field3] value must match one of [e, f, ...]" | An object where each key is a shared parent of all fields throughout the rest of the object. For example, fa.fb[].fc is the parent of field1, field2, and field3. Each value contains "sharedParent", "condition" and "requirement".  "condition" is an object where each key-value pair refers to a field (key) and the list of its possible values it must match (value) in order for "requirement" to be required. "requirement" is an object where each key-value pair refers to a field (key) and the list of allowed values (value) for it given the conditions |
| `valueMatch` | "[field1] must match one of the values from [field2]" | An object in the form [field1]: [field2]. Each value of the object is a field name whose values form the complete list of valid values for the corresponding key, [field1]. The value of [field1] must match one of these values. |
| `conditions` | An object containing specific conditions that must apply before the appropriate action is taken | An object containing keys such as `length`, `exists`, or `value`, where the value of that key is the length or value that must hold true for the key to be required or ignored, or to require/forbid keys based on the existence of another key |

