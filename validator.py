import argparse
import yaml
from api_files.generator import ApiGenerator
from logger import LogLevel, Logger
from decouple import config

API_YAML = config('API_YAML')
STATE_YAML = config('STATE_YAML')

PRIMITIVE_TYPE_MAP = {
    'string': str,
    'boolean': bool,
    'number': float,
    'int': int,
    'integer': int
}
# state in scene should follow state_changes.yaml

class YamlValidator:
    logger = Logger("yamlValidator")
    file = None
    api_file = None
    state_change_file = None
    loaded_yaml = None
    api_yaml = None
    state_changes_yaml = None
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
            self.state_change_file = open(STATE_YAML)
            self.state_changes_yaml = yaml.load(self.state_change_file, Loader=yaml.CLoader)
        except Exception as e:
            self.logger.log(LogLevel.ERROR, "Error while loading in state api yaml. Please check the .env to make sure the location is correct and try again.\n\n" + str(e) + "\n")
        try:
            self.loaded_yaml = yaml.load(self.file, Loader=yaml.CLoader)
        except Exception as e:
            self.logger.log(LogLevel.ERROR, "Error while loading in yaml file. Please ensure the file is a valid yaml format and try again.\n\n" + str(e) + "\n")
    

    def __del__(self):
        '''
        Basic cleanup: closing the file loaded in on close.
        '''
        self.logger.log(LogLevel.DEBUG, "Program closing...")
        if (self.file):
            self.file.close()
        if (self.api_file):
            self.api_file.close()
        if (self.state_change_file):
            self.state_change_file.close()


    def validate_field_names(self):
        '''
        Ensures all fields are supported by the API
        '''
        # start by checking the top level
        schema = self.api_yaml['components']['schemas']
        top_level = schema['Scenario']['properties']
        required = schema['Scenario']['required'] if 'required' in schema['Scenario'] else []
        return self.validate_one_level('top', self.loaded_yaml, top_level, required, self.api_yaml)


    def validate_one_level(self, level_name, to_validate, type_obj, required, api_yaml):
        '''
        Takes in an object to validate (to_validate) and the yaml schema describing the 
        expected types (type_obj)
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
            if key not in type_obj:
                self.logger.log(LogLevel.WARN, "'" + key + "' is not a valid key at the '" + level_name + "' level of the yaml file. Allowed keys are " + str(list(type_obj.keys())))
                self.invalid_keys += 1
                is_valid = False
            else:
                # begin type-checking
                this_key_data = type_obj[key]
                # check for the 'type' property - otherwise it might only have a $ref
                if 'type' in this_key_data:
                    key_type = type_obj[key]['type']
                    # Basic types listed in PRIMITIVE_TYPE_MAP
                    if key_type in PRIMITIVE_TYPE_MAP:
                        if not self.validate_primitive(to_validate[key], key_type, key, level_name, type_obj[key]):
                            is_valid = False
                    # check for objects (key:value pairs)
                    elif key_type == 'object':
                        if 'additionalProperties' in type_obj[key]:
                            if not self.validate_additional_properties(type_obj[key], to_validate[key], key, level_name, api_yaml):
                                is_valid = False
                        else:
                            self.logger.log(LogLevel.ERROR, "API error: Missing additionalProperties on '" + key + "' object at the '" + level_name + "' level. Please contact TA3 for assistance.")
                            return False
                        
                    elif key_type == 'array':
                        if not self.validate_array(to_validate[key], key, level_name, key_type, type_obj, api_yaml):
                            is_valid = False
                    else:
                        self.logger.log(LogLevel.ERROR, "API error: Unhandled validation for type '" +  key_type + "' at the " + level_name + "' level. Please contact TA3 for assistance.")
                        return False
                        
                # check deep objects (more than simple key-value)
                elif '$ref' in this_key_data:
                    # get the ref type and check that location (skip starting hashtag)
                    location = type_obj[key]['$ref'].split('/')[1:]
                    if level_name == 'scenes' and location[len(location)-1] == 'State':
                        # state at the scenes level should follow state_changes.yaml
                        if not self.validate_state_change(to_validate[key]):
                            is_valid = False
                    else:
                        ref_loc = api_yaml
                        # access the currect location to get the type map
                        for x in location:
                            ref_loc = ref_loc[x]
                        if 'enum' in ref_loc:
                            if not self.validate_enum(ref_loc, key, level_name, to_validate[key]):
                                is_valid = False
                        elif isinstance(to_validate[key], dict):
                            if not self.validate_object(to_validate[key], ref_loc, key, level_name, type_obj[key]['$ref'], api_yaml):
                                is_valid = False
                        else:
                            self.log_wrong_type(key, level_name, location[len(location)-1], type(to_validate[key]))
                            is_valid = False 
                else:
                    self.logger.log(LogLevel.ERROR, "API Error: Key '" + key + "' at level '" + level_name + "' has no defined type or reference. Please contact TA3 for assistance.")
                    return False
            found_keys.append(key)
        # check for missing keys
        for key in type_obj:
            if key not in found_keys:
                if (key in required):
                    self.logger.log(LogLevel.WARN, "Required key '" + key + "' at level '" + level_name + "' is missing in the yaml file.")
                    self.missing_keys += 1
                    is_valid = False
                else:
                    self.logger.log(LogLevel.DEBUG, "Optional key '" + key + "' at level '" + level_name + "' is missing in the yaml file.")
        return is_valid

    def validate_state_change(self, obj_to_validate):
        '''
        Under Scenes in the API, state should be defined slightly differently.
        Use state_changes.yaml and perform as before.
        '''
        schema = self.state_changes_yaml['components']['schemas']
        top_level = schema['State']['properties']
        required = schema['State']['required'] if 'required' in schema['State'] else []
        return self.validate_one_level('Scenes/State', obj_to_validate, top_level, required, self.state_changes_yaml)

    def validate_enum(self, type_obj, key, level, item):
        '''
        Accepts as parameters the object that describes expected types, 
        the key of the object, the level we're looking at, and the value 
        to check        
        '''
        is_valid = True
        # we are expecting a string here (will this ever be an int/float?)
        if isinstance(item, str):
                allowed = type_obj['enum']
                if item not in allowed:
                    self.logger.log(LogLevel.WARN, "Key '" + key + "' at level '" + level + "' must be one of the following values: " + str(allowed) + " but is '" + item + "' instead.")
                    self.invalid_values += 1
                    is_valid = False
        else:
            self.log_wrong_type(key, level, str(str), type(item))
            is_valid = False 
        return is_valid


    def validate_object(self, item, location, key, level, ref_name, api_yaml):
        '''
        Checks if an item matches the reference location. The reference location
        may reference a full object, small object, or enum. Checks all 3 possibilities.
        '''
        is_valid = True
        # check large object
        if 'properties' in location:
            if not self.validate_one_level(key, item, location['properties'], location['required'] if 'required' in location else [], api_yaml):
                is_valid = False
        # check small object
        elif 'additionalProperties' in location:
            if not self.validate_additional_properties(location, item, key, level, api_yaml):
                is_valid = False
        # check enum
        elif 'enum' in location:
            if not self.validate_enum(location, key, level, item):
                is_valid = False
        else:
            self.logger.log(LogLevel.ERROR, "API missing enum, property, or additional properties for '" + ref_name + "'. Cannot parse. Please contact TA3 for assistance.")
        return is_valid
    

    def validate_additional_properties(self, type_obj, item, key, level, api_yaml):
        '''
        Accepts an object that describes the type we're looking for and an item to validate
        '''
        is_valid = True
        if 'type' in type_obj['additionalProperties']:
            val_type = type_obj['additionalProperties']['type']
            # two types of objects exist: 1. list of key-value 
            if isinstance(item, list):
                for pair_set in item:
                    for k in pair_set:
                        if not self.do_types_match(pair_set[k], PRIMITIVE_TYPE_MAP[val_type]):
                            self.log_wrong_type(k, level, val_type, type(pair_set[k]))
                            is_valid = False
            # 2. object with key-value
            else:
                if isinstance(item, dict):
                    for k in item:
                        if not self.do_types_match(item[k], PRIMITIVE_TYPE_MAP[val_type]):
                            self.log_wrong_type(k, level, val_type, type(item[k]))
                            is_valid = False
                else:
                    self.log_wrong_type(key, level, 'object', type(item))
                    is_valid = False 
        elif '$ref' in type_obj['additionalProperties']:
            location = type_obj['additionalProperties']['$ref'].split('/')[1:]
            ref_loc = api_yaml
            for x in location:
                ref_loc = ref_loc[x]
            if isinstance(item, list):
                for pair_set in item:
                    for k in pair_set:
                        if not self.validate_object(pair_set[k], ref_loc, key, level, type_obj['additionalProperties']['$ref'], api_yaml):
                            is_valid = False
            else:
                if isinstance(item, dict):
                    for k in item:
                        if not self.validate_object(item[k], ref_loc, key, level, type_obj['additionalProperties']['$ref'], api_yaml):
                            is_valid = False
                else:
                    self.log_wrong_type(key, level, 'object', type(item))
                    is_valid = False      
        else:
            self.logger.log(LogLevel.ERROR, "API Error: Additional Properties must either have a type or ref, but at level '" + level + "' for property '" + key + "' it does not. Please contact TA3 for assistance.")
            return False
        return is_valid


    def validate_array(self, item, key, level, key_type, typed_keys, api_yaml):
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
                ref_loc = api_yaml
                for x in location:
                    ref_loc = ref_loc[x]
                for i in item:
                    if not self.validate_object(i, ref_loc, key, level, typed_keys[key]['items']['$ref'], api_yaml):
                        is_valid = False
            # check basic types
            elif 'type' in item_type:
                expected = item_type['type']
                if expected in PRIMITIVE_TYPE_MAP:
                    for i in item:
                        if not self.validate_primitive(i, expected, key, level, item_type):
                            is_valid = False
            else:
                self.logger.log(LogLevel.ERROR, "API Error: Missing type definition or reference at level '" + level + "' for property '" + key + "'. Please contact TA3 for assistance.")
                return False
        return is_valid
    

    def validate_primitive(self, item, expected_type, key, level, type_obj):
        '''
        Looks at an object against an expected primitive type to see if it matches
        '''
        is_valid = True 
        # first validate enums
        if PRIMITIVE_TYPE_MAP[expected_type] == str and 'enum' in type_obj:
            if not self.validate_enum(type_obj, key, level, item):
                is_valid = False
        # then validate the rest
        elif not self.do_types_match(item, PRIMITIVE_TYPE_MAP[expected_type]):
            self.log_wrong_type(key, level, expected_type, type(item))
            is_valid = False

        return is_valid


    def do_types_match(self, item, type):
        '''
        Checks the basic data types, allowing integers in place of floats and ints and floats in place of strings (think stringified numbers)
        '''
        return isinstance(item, type) or (type == float and isinstance(item, int)) or (type == str and (isinstance(item, float) or isinstance(item, int)))


    def log_wrong_type(self, key, level, expected, actual):
        '''
        Logs when an incorrect type is found for a key
        '''
        self.logger.log(LogLevel.WARN, "Key '" + key + "' at level '" + level + "' should be type '" + expected + "' but is " + str(actual) + " instead.")
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
    parser = argparse.ArgumentParser(description='ITM - YAML Validator', usage='validator.py [-h] [-u [-f PATH] | -f PATH ]')

    parser.add_argument('-f', '--filepath', dest='path', type=str, help='The path to the yaml file. Required if -u is not specified.')
    parser.add_argument('-u', '--update', dest='update', action='store_true', help='Switch to update the api files or not. Required if -f is not specified.')
    args = parser.parse_args()
    if args.update:
        generator = ApiGenerator()
        generator.generate_new_api()
        generator.generate_state_change_api()
    if args.update and not args.path:
        exit(0)
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
