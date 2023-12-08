import argparse
import yaml
from logger import LogLevel, Logger
from decouple import config

API_YAML = config('API_YAML')

PRIMITIVE_TYPE_MAP = {
    'string': str,
    'boolean': bool,
    'float': float,
    'int': int
}

class YamlValidator:
    logger = Logger("yamlValidator")
    file = None
    api_file = None
    loaded_yaml = None
    api_yaml = None
    missing_keys = 0
    wrong_types = 0
    invalid_values = 0
    invalid_keys = 0
    empty_levels = 0

    def __init__(self, filename):
        '''
        Load in the file and parse the yaml
        '''
        self.file = self.validate_file_location(filename)
        try:
            self.api_file = open(API_YAML)
            self.api_yaml = yaml.load(self.api_file, Loader=yaml.CLoader)
        except Exception as e:
            self.logger.log(LogLevel.ERROR, "Error while loading in api yaml. Please check the .env to make sure the location is correct and try again.\n\n" + str(e) + "\n")
        try:
            self.loaded_yaml = yaml.load(self.file, Loader=yaml.CLoader)
        except Exception as e:
            self.logger.log(LogLevel.ERROR, "Error while loading in yaml file. Please ensure the file is a valid yaml format and try again.\n\n" + str(e) + "\n")
    
    def __del__(self):
        '''
        Basic cleanup closing the file loaded in on close.
        '''
        self.logger.log(LogLevel.DEBUG, "Program closing...")
        if (self.file):
            self.file.close()
        if (self.api_file):
            self.api_file.close()

    def validate_field_names(self):
        '''
        Ensures all fields are supported by the API
        '''
        # start by checking the top level
        schema = self.api_yaml['components']['schemas']
        top_level = schema['Scenario']['properties']
        required = schema['Scenario']['required'] if 'required' in schema['Scenario'] else []
        return self.validate_one_level('top', self.loaded_yaml, top_level, required)

    def validate_one_level(self, level_name, to_validate, typed_keys, required):
        '''
        Takes in an object to validate and the yaml schema describing the 
        expected types
        '''
        is_valid = True
        found_keys = []
        # see if an object is empty (and if it's allowed to be)
        if to_validate == None and len(required) == 0:
            return True
        elif to_validate == None and len(required) > 0:
            self.logger.log(LogLevel.WARN, "Level '" + level_name + "' is empty but must contain keys " + str(required))
            self.empty_levels += 1
            return False
        # loop through keys to check each value against expectations
        for key in to_validate:
            # make sure it is a valid key
            if key not in typed_keys:
                self.logger.log(LogLevel.WARN, "'" + key + "' is not a valid key at the '" + level_name + "' level of the yaml file. Allowed keys are " + str(list(typed_keys.keys())))
                self.invalid_keys += 1
                is_valid = False
            else:
                # begin type-checking
                this_key_data = typed_keys[key]
                if 'type' in this_key_data:
                    key_type = typed_keys[key]['type']
                    # Basic types listed in PRIMITIVE_TYPE_MAP
                    if key_type in PRIMITIVE_TYPE_MAP:
                        # allow ints to take the place of floats, but not the other way around
                        if not self.do_types_match(to_validate[key], PRIMITIVE_TYPE_MAP[key_type]):
                            self.log_wrong_type(key, level_name, key_type, type(to_validate[key]))
                            is_valid = False
                        # check for enums
                        elif PRIMITIVE_TYPE_MAP[key_type] == str:
                            if 'enum' in typed_keys[key]:
                                allowed = typed_keys[key]['enum']
                                if to_validate[key] not in allowed:
                                    self.logger.log(LogLevel.WARN, "'" + key + "' at the '" + level_name + "' level must be one of the following values: " + str(allowed) + ". Instead received '" + to_validate[key] + "'")
                                    self.invalid_values += 1
                                    is_valid = False

                    # check for objects (key:value pairs)
                    elif key_type == 'object':
                        if 'additionalProperties' in typed_keys[key]:
                            val_type = typed_keys[key]['additionalProperties']['type']
                            # two types of objects exist: 1. list of key-value 
                            if isinstance(to_validate[key], list):
                                for pair_set in to_validate[key]:
                                    for k in pair_set:
                                        if not self.do_types_match(pair_set[k], PRIMITIVE_TYPE_MAP[val_type]):
                                            self.log_wrong_type(k, level_name, val_type, type(pair_set[k]))
                                            is_valid = False
                            # 2. object with key-value
                            else:
                                for k in to_validate[key]:
                                    if not self.do_types_match(to_validate[key][k], PRIMITIVE_TYPE_MAP[val_type]):
                                        self.log_wrong_type(k, level_name, val_type, type(to_validate[key][k]))
                                        is_valid = False
                    elif key_type == 'array':
                        if not self.validate_array(to_validate[key], key, level_name, key_type, typed_keys):
                            is_valid = False
                        
                # check deep objects (more than simple key-value)
                elif '$ref' in this_key_data:
                    # get the ref type and check that (skip starting hashtag)
                    location = typed_keys[key]['$ref'].split('/')[1:]
                    ref_loc = self.api_yaml
                    for x in location:
                        ref_loc = ref_loc[x]
                    if not self.validate_one_level(key, to_validate[key], ref_loc['properties'], ref_loc['required'] if 'required' in ref_loc else []):
                        is_valid = False
            found_keys.append(key)
        # check for missing keys
        for key in typed_keys:
            if key not in found_keys:
                if (key in required):
                    self.logger.log(LogLevel.WARN, "Required key '" + key + "' is missing at the '" + level_name + "' level of the yaml file")
                    self.missing_keys += 1
                    is_valid = False
                else:
                    self.logger.log(LogLevel.DEBUG, "Optional '" + key + "' is missing at the '" + level_name + "' level of the yaml file")
        return is_valid

    def validate_array(self, item, key, level, key_type, typed_keys):
        '''
        Looks at an array and ensures that each item in the array matches expectations
        '''
        is_valid = True
        if not isinstance(item, list):
            self.log_wrong_type(key, level, key_type, type(item))
            is_valid = False
        else:
            # get type of item in array and check that each item matches
            item_type = typed_keys[key]['items']
            # check complex object types 
            if '$ref' in item_type:
                location = item_type['$ref'].split('/')[1:]
                ref_loc = self.api_yaml
                for x in location:
                    ref_loc = ref_loc[x]
                for item in item:
                    if not self.validate_one_level(key, item, ref_loc['properties'], ref_loc['required'] if 'required' in ref_loc else []):
                        is_valid = False
            # check basic types
            elif 'type' in item_type:
                expected = item_type['type']
                if expected in PRIMITIVE_TYPE_MAP:
                    for item in item:
                        if not self.do_types_match(item, PRIMITIVE_TYPE_MAP[expected]):
                            self.log_wrong_type(key, level, expected, type(item))
                            is_valid = False
        return is_valid
    
    def do_types_match(self, item, type):
        '''
        Checks the basic data types, allowing integers in place of floats
        '''
        return isinstance(item, type) or (type == float and isinstance(item, int))

    def log_wrong_type(self, key, level, expected, actual):
        '''
        Logs when an incorrect type is found for a key
        '''
        self.logger.log(LogLevel.WARN, "Key '" + key + "' at level " + level + " should be type " + expected + " but is " + str(actual) + " instead.")
        self.wrong_types += 1
    
    def validate_file_location(self, filename):
        '''
        Try to load in the yaml file. Checks that a path has been given, that the path leads to a yaml file,
        and that the file is found. Returns the open binary file object.
        '''
        if not filename:
            self.logger.log(LogLevel.ERROR, "No filename received. To run, please use 'python3 validator.py -f [filename]'")
        if not filename.strip().endswith('.yaml'):
            self.logger.log(LogLevel.ERROR, "File must be a yaml file.")
        try:
            f = open(filename, 'r')
            return f
        except:
            self.logger.log(LogLevel.ERROR, "Could not open file " + filename + ". Please make sure the path is valid and the file exists.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ITM - YAML Validator')

    parser.add_argument('-f', '--filepath', dest='path', type=str, help='The path to the yaml file.')
    args = parser.parse_args()

    file = args.path
    validator = YamlValidator(file)
    # validate the field names in the valid
    field_names_valid = validator.validate_field_names()
    # print the answer for validity
    print("")

    validator.logger.log(LogLevel.CRITICAL_INFO, ("\033[92m" if validator.missing_keys == 0 else "\033[91m") + "Missing Required Keys: " + str(validator.missing_keys))
    validator.logger.log(LogLevel.CRITICAL_INFO, ("\033[92m" if validator.wrong_types == 0 else "\033[91m") + "Incorrect Data Type: " + str(validator.wrong_types))
    validator.logger.log(LogLevel.CRITICAL_INFO, ("\033[92m" if validator.invalid_keys == 0 else "\033[91m") + "Invalid Keys: " + str(validator.invalid_keys))
    validator.logger.log(LogLevel.CRITICAL_INFO, ("\033[92m" if validator.invalid_values == 0 else "\033[91m") + "Invalid Values (mismatched enum): " + str(validator.invalid_values))
    validator.logger.log(LogLevel.CRITICAL_INFO, ("\033[92m" if validator.empty_levels == 0 else "\033[91m") + "Properties Missing Data (empty level): " + str(validator.empty_levels))
    total_errors = validator.missing_keys + validator.wrong_types + validator.invalid_keys + validator.invalid_values + validator.empty_levels
    validator.logger.log(LogLevel.CRITICAL_INFO, ("\033[92m" if total_errors == 0 else "\033[91m") + "Total Errors: " + str(total_errors))
    if field_names_valid:
        validator.logger.log(LogLevel.CRITICAL_INFO, "\033[92m" + file + " is valid!")
    else:
        validator.logger.log(LogLevel.CRITICAL_INFO, "\033[91m" + file + " is not valid.")
