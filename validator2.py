import argparse
import yaml
from logger import LogLevel, Logger
from decouple import config

API_YAML = config('API_YAML')

TYPE_MAP = {
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
        required = schema['Scenario']['required']
        return self.validate_one_level('top', self.loaded_yaml, top_level, required)

    def validate_one_level(self, level_name, to_validate, typed_keys, required):
        '''
        Takes in an object to validate and the yaml schema describing the 
        expected types
        '''
        is_valid = True
        found_keys = []
        if to_validate == None and len(required) == 0:
            return True
        elif to_validate == None and len(required) > 0:
            self.logger.log(LogLevel.SEVERE_WARN, "Level " + level_name + " is empty but must contain keys " + str(required))
            return False
        for key in to_validate:
            # make sure it is a valid key
            if key not in typed_keys:
                self.logger.log(LogLevel.SEVERE_WARN, "'" + key + "' is not a valid key at the " + level_name + " level of the yaml file. Allowed keys are " + str(list(typed_keys.keys())))
                is_valid = False
            else:
                # begin type-checking
                this_key_data = typed_keys[key]
                if 'type' in this_key_data:
                    key_type = typed_keys[key]['type']
                    # Basic types listed in TYPE_MAP
                    if key_type in TYPE_MAP:
                        # allow ints to take the place of floats, but not the other way around
                        if not (isinstance(to_validate[key], TYPE_MAP[key_type]) or (TYPE_MAP[key_type] == float and isinstance(to_validate[key], int))):
                            self.logger.log(LogLevel.SEVERE_WARN, "'" + key + "' should be type " + key_type + " but is " + str(type(to_validate[key])) + " instead.")
                            is_valid = False
                        elif TYPE_MAP[key_type] == str:
                            if 'enum' in typed_keys[key]:
                                allowed = typed_keys[key]['enum']
                                if to_validate[key] not in allowed:
                                    self.logger.log(LogLevel.MINOR_WARN, "'" + key + "' at level " + level_name + " must be one of the following values: " + str(allowed) + ". Instead received " + to_validate[key])
                    elif key_type == 'array':
                        if not isinstance(to_validate[key], list):
                            self.logger.log(LogLevel.SEVERE_WARN, "'" + key + "' should be type " + key_type + " but is " + str(type(to_validate[key])) + " instead.")
                            is_valid = False
                        else:
                            # get type of item in array and check that each item matches
                            item_type = typed_keys[key]['items']
                            if '$ref' in item_type:
                                location = item_type['$ref'].split('/')[1:]
                                ref_loc = self.api_yaml
                                for x in location:
                                    ref_loc = ref_loc[x]
                                for item in to_validate[key]:
                                    if not self.validate_one_level(key, item, ref_loc['properties'], ref_loc['required']):
                                        is_valid = False
                            else:
                                # TODO: see if a ref can be a basic data type
                                pass
                        pass
                elif '$ref' in this_key_data:
                    # get the ref type and check that (skip starting hashtag)
                    location = typed_keys[key]['$ref'].split('/')[1:]
                    ref_loc = self.api_yaml
                    for x in location:
                        ref_loc = ref_loc[x]
                    if not self.validate_one_level(key, to_validate[key], ref_loc['properties'], ref_loc['required']):
                        is_valid = False
            found_keys.append(key)
        for key in typed_keys:
            if key not in found_keys:
                if (key in required):
                    self.logger.log(LogLevel.MINOR_WARN, "Required key '" + key + "' is missing at the " + level_name + " level of the yaml file")
                    is_valid = False
                else:
                    self.logger.log(LogLevel.INFO, "Optional '" + key + "' is missing at the " + level_name + " level of the yaml file")
        return is_valid

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
    # print the answer for validity (after a new line for better readability)
    print("")
    if field_names_valid:
        validator.logger.log(LogLevel.CRITICAL_INFO, "\033[93m" + file + " is valid!")
    else:
        validator.logger.log(LogLevel.CRITICAL_INFO, "\033[91m" + file + " is not valid.")
