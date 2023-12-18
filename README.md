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

## API Changes
- When the Swagger API changes, make sure you upload the newest version as `api.yaml` to the `api_files` directory.
- Once the api file is up-to-date, run 
```
python3 validator.py -f [path_to_file] --update
```

## Logging
To change the log level, edit the value in the .env file.