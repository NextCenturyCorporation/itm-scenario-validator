import argparse
import yaml
from api import TOP_LEVEL
from logger import LogLevel, Logger

class YamlValidator:
    logger = Logger("yamlValidator")
    file = None
    loadedYaml = None

    def __init__(self, filename):
        '''
        Load in the file and parse the yaml
        '''
        self.file = self.validate_file_location(filename)
        try:
            self.loadedYaml = yaml.load(self.file, Loader=yaml.CLoader)
        except Exception as e:
            self.logger.log(LogLevel.ERROR, "Error while loading in yaml file. Please ensure the file is a valid yaml format and try again.\n\n" + str(e) + "\n")
    
    def validate_field_names(self):
        '''
        Ensures all fields are supported by the API
        '''
        # start by checking the top level
        return self.validate_sublevel('top', self.loadedYaml, TOP_LEVEL)
    
    def validate_sublevel(self, level_name, to_validate, typed_keys):
        '''
        Takes in an object to validate and a dictionary mapping
        allowed keys to their types. 
        '''
        is_valid = True
        # some things (like scenes) are lists of a type. We need to check each entry in the list
        # eventually we will probably want to check that if it's a list, we are expecting a list. for now, just leave this
        if isinstance(to_validate, list):
            for x in to_validate:
                is_valid = is_valid and self.validate_sublevel(level_name, x, typed_keys)
        else:
            is_valid = True
            found_keys = []
            try:
                for key in to_validate:
                    if key in found_keys:
                        self.logger.log(LogLevel.SEVERE_WARN, "'" + key + "' is duplicated at the " + level_name + " level of the yaml file")
                        is_valid = False
                    # check if the key is expected
                    if key not in typed_keys:
                        self.logger.log(LogLevel.SEVERE_WARN, "'" + key + "' is not a valid key at the " + level_name + " level of the yaml file. Allowed keys are " + str(typed_keys.keys()))
                        is_valid = False
                    else:
                        # check type of object
                        if isinstance(typed_keys[key], dict):
                            if not self.validate_sublevel(key, to_validate[key], typed_keys[key]):
                                is_valid = False
                        # check basic type (string, int, etc)
                        elif not (isinstance(to_validate[key], typed_keys[key]) or (typed_keys[key] == float and isinstance(to_validate[key], int))):
                            self.logger.log(LogLevel.SEVERE_WARN, "'" + key + "' should be type " + str(typed_keys[key]) + " but is " + str(type(to_validate[key])) + " instead.")
                            is_valid = False
                    found_keys.append(key)
            except:
                self.logger.log(LogLevel.SEVERE_WARN, "'" + key + "' does not have a defined type at the " + level_name + " level of the yaml file")
            for key in typed_keys:
                if key not in found_keys:
                    self.logger.log(LogLevel.MINOR_WARN, "'" + key + "' is missing at the " + level_name + " level of the yaml file")
                    is_valid = False
        return is_valid

    def __del__(self):
        '''
        Basic cleanup closing the file loaded in on close.
        '''
        self.logger.log(LogLevel.DEBUG, "Program closing...")
        if (self.file):
            self.file.close()

    def validate_file_location(self, filename):
        '''
        Try to load in the yaml file. Checks that a path has been given, that the path leads to a yaml file,
        and that the file is found. Returns the open binary file object.
        '''
        if not filename:
            self.logger.log(LogLevel.ERROR, "No filename received. To run, please use 'python3 validator.py -f [filename]'")
        if filename.strip()[-5:] != '.yaml':
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
