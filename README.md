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
| `conditionalIgnore` | "If [field1] has a value of [value1], then [field2] is ignored (or shouldn't be provided)" | A dictionary where each key is [field1] and the value is a list of objects that define conditions and [field2] names. If [field2] is in the yaml to validate when the conditions are true, a warning will be given. |
| `conditions` | An object containing specific conditions that must apply before the appropriate action is taken | An object containing keys such as `length` or `value`, where the value of that key is the length or value that must hold true for the key to be required |
